"""Vectorized fragility curve evaluation using DuckDB."""

from __future__ import annotations

import duckdb
from loguru import logger


# Mapping from asset_state field names to the corresponding column in asset_states table
HAZARD_PARAM_TO_COLUMN = {
    "wind_speed": "wind_speed_mph",
    "flood_depth": "flood_depth_m",
    "flood_velocity": "flood_velocity_mps",
    "fire_boundary_dist": "fire_distance_km",
    "peak_ground_velocity": "pgv_cms",
    "peak_ground_acceleration": "pga_fraction_g",
    "soil_saturation": "soil_saturation",
    "snow_water_equivalent": "snow_water_equivalent_m",
    "runoff_volume": "runoff_volume",
    "groundwater_flow": "groundwater_flow",
}

# Mapping from hazard parameter to its survival probability column
HAZARD_PARAM_TO_SURV_COLUMN = {
    "wind_speed": "wind_speed_surv",
    "flood_depth": "flood_depth_surv",
    "flood_velocity": "flood_velocity_surv",
    "fire_boundary_dist": "fire_distance_surv",
    "peak_ground_velocity": "pgv_surv",
    "peak_ground_acceleration": "pga_surv",
    "soil_saturation": "soil_saturation_surv",
    "snow_water_equivalent": "snow_water_equivalent_surv",
    "runoff_volume": "runoff_volume_surv",
    "groundwater_flow": "groundwater_flow_surv",
}

# Unit conversions needed: fragility curves may have different units than computed vectors
# The fragility curves store their own units, and the computed vectors are in specific units.
# We need to convert the computed value to the fragility curve's units before CDF evaluation.
COLUMN_UNITS = {
    "wind_speed_mph": "mile / hour",
    "flood_depth_m": "meter",
    "flood_velocity_mps": "meter / second",
    "fire_distance_km": "kilometer",
    "pgv_cms": "centimeter / second",
    "pga_fraction_g": "dimensionless",  # fraction of g
    "soil_saturation": "dimensionless",
    "snow_water_equivalent_m": "meter",
    "runoff_volume": "dimensionless",
    "groundwater_flow": "dimensionless",
}


def compute_survival_probabilities(con: duckdb.DuckDBPyConnection):
    """Compute survival probability for each (asset, timestamp) by evaluating fragility curves.

    For each hazard parameter that has a non-null value, looks up the matching fragility
    curve for that asset_type and applies the CDF. Final survival = product of all
    individual survival probabilities (independence assumption).
    """

    # First check what fragility curves we have
    curves = con.execute(
        """
        SELECT DISTINCT hazard_parameter, distribution
        FROM fragility_curves
    """
    ).fetchall()

    if not curves:
        logger.warning("No fragility curves loaded — survival probabilities will all be 1.0")
        con.execute("UPDATE asset_states SET survival_probability = 1.0")
        return

    # Build a single SQL expression that computes all survival probabilities at once
    # by joining asset_states with assets and fragility_curves
    # This avoids 84 separate UPDATE scans

    # For each (hazard_parameter, column) pair, build a CASE expression
    # that evaluates the CDF based on the distribution type
    surv_expressions = []

    for hazard_param in HAZARD_PARAM_TO_COLUMN:
        col_name = HAZARD_PARAM_TO_COLUMN[hazard_param]
        surv_col = HAZARD_PARAM_TO_SURV_COLUMN[hazard_param]

        # Check if this hazard parameter has any curves defined
        param_curves = con.execute(
            "SELECT COUNT(*) FROM fragility_curves WHERE hazard_parameter = ?",
            [hazard_param],
        ).fetchone()[0]
        if param_curves == 0:
            continue

        # Build the CDF expression as a correlated subquery
        # 'expon' encodes the wildfire model: failure probability decays with
        # distance from the fire boundary as P_max * exp(-dist / L), where
        # param_1 = L (decay length, km) and param_2 = P_max. Assets inside the
        # burned polygon (fire_distance_km <= 0) are a certain outage (failure 1.0
        # -> survival 0.0).
        cdf_sql = f"""
        COALESCE(
            (SELECT
                CASE fc.distribution
                    WHEN 'norm' THEN normal_cdf(s.{col_name}, fc.param_1, fc.param_2)
                    WHEN 'lognorm' THEN lognormal_cdf(s.{col_name}, fc.param_1, fc.param_2, fc.param_3)
                    WHEN 'expon' THEN
                        CASE
                            WHEN s.{col_name} <= 0 THEN 1.0
                            ELSE LEAST(1.0, fc.param_2 * exp(-s.{col_name} / NULLIF(fc.param_1, 0)))
                        END
                    ELSE 0.0
                END
            FROM fragility_curves fc
            WHERE fc.asset_type = a.asset_type
              AND fc.hazard_parameter = '{hazard_param}'
            LIMIT 1),
            0.0
        )
        """

        surv_expressions.append((surv_col, col_name, cdf_sql))

    if not surv_expressions:
        con.execute("UPDATE asset_states SET survival_probability = 1.0")
        return

    # Build UPDATE SET clauses for per-parameter survival columns
    set_clauses = []
    overall_parts = []
    for surv_col, col_name, cdf_sql in surv_expressions:
        set_clauses.append(
            f"{surv_col} = CASE WHEN s.{col_name} IS NOT NULL THEN (1.0 - {cdf_sql}) ELSE 1.0 END"
        )
        overall_parts.append(
            f"CASE WHEN s.{col_name} IS NOT NULL THEN (1.0 - {cdf_sql}) ELSE 1.0 END"
        )

    overall_expr = " * ".join(overall_parts)
    set_clauses.append(f"survival_probability = {overall_expr}")

    update_sql = f"""
        UPDATE asset_states SET
            {', '.join(set_clauses)}
        FROM asset_states s
        JOIN assets a ON s.asset_id = a.asset_id
        WHERE asset_states.asset_id = s.asset_id
          AND asset_states.timestamp = s.timestamp
    """

    try:
        con.execute(update_sql)
    except Exception as e:
        logger.warning(f"Single-pass fragility failed ({e}), falling back to iterative approach")
        _compute_survival_iterative(con)
        return

    n_computed = con.execute(
        "SELECT COUNT(*) FROM asset_states WHERE survival_probability < 1.0"
    ).fetchone()[0]
    logger.info(
        f"Computed survival probabilities: {n_computed} asset-states have probability < 1.0"
    )


def _compute_survival_iterative(con: duckdb.DuckDBPyConnection):
    """Fallback: iterative UPDATE per (asset_type, hazard_parameter) pair."""
    con.execute("UPDATE asset_states SET survival_probability = 1.0")

    curves = con.execute(
        """
        SELECT DISTINCT hazard_parameter FROM fragility_curves
    """
    ).fetchall()

    for (hazard_param,) in curves:
        col_name = HAZARD_PARAM_TO_COLUMN.get(hazard_param)
        if col_name is None:
            continue

        has_data = con.execute(
            f"SELECT COUNT(*) FROM asset_states WHERE {col_name} IS NOT NULL"
        ).fetchone()[0]
        if has_data == 0:
            continue

        param_curves = con.execute(
            "SELECT asset_type, distribution, param_1, param_2, param_3 FROM fragility_curves WHERE hazard_parameter = ?",
            [hazard_param],
        ).fetchall()

        surv_col = HAZARD_PARAM_TO_SURV_COLUMN[hazard_param]

        for asset_type, distribution, p1, p2, p3 in param_curves:
            if distribution == "norm":
                cdf_expr = f"normal_cdf(asset_states.{col_name}, {p1}, {p2})"
            elif distribution == "lognorm":
                cdf_expr = f"lognormal_cdf(asset_states.{col_name}, {p1}, {p2}, {p3})"
            elif distribution == "expon":
                # Wildfire: failure = P_max * exp(-dist / L); inside the boundary
                # (dist <= 0) is a certain outage. param_1 = L (km), param_2 = P_max.
                cdf_expr = (
                    f"CASE WHEN asset_states.{col_name} <= 0 THEN 1.0 "
                    f"ELSE LEAST(1.0, {p2} * exp(-asset_states.{col_name} / NULLIF({p1}, 0))) END"
                )
            else:
                continue

            con.execute(
                f"""
                UPDATE asset_states SET
                    {surv_col} = (1.0 - {cdf_expr}),
                    survival_probability = survival_probability * (1.0 - {cdf_expr})
                WHERE asset_id IN (
                    SELECT asset_id FROM assets WHERE asset_type = ?
                )
                AND {col_name} IS NOT NULL
            """,
                [asset_type],
            )

    n_computed = con.execute(
        "SELECT COUNT(*) FROM asset_states WHERE survival_probability < 1.0"
    ).fetchone()[0]
    logger.info(
        f"Computed survival probabilities (iterative): {n_computed} asset-states have probability < 1.0"
    )
