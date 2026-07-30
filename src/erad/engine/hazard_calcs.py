"""Vectorized hazard vector computation using DuckDB SQL."""

from __future__ import annotations

import duckdb
from loguru import logger


def compute_earthquake_vectors(con: duckdb.DuckDBPyConnection):
    """Compute PGA and PGV for all assets × all earthquake models using vectorized SQL."""
    count = con.execute("SELECT COUNT(*) FROM earthquake_models").fetchone()[0]
    if count == 0:
        return

    con.execute(
        """
        INSERT INTO asset_states (asset_id, timestamp, pgv_cms, pga_fraction_g)
        SELECT
            a.asset_id,
            e.timestamp,
            pgv_from_mmi(
                mmi_from_magnitude(
                    e.magnitude,
                    hypocentral_distance_km(
                        haversine_km(a.latitude, a.longitude, e.origin_lat, e.origin_lon),
                        e.depth_km
                    )
                )
            ) AS pgv_cms,
            pga_from_mmi(
                mmi_from_magnitude(
                    e.magnitude,
                    hypocentral_distance_km(
                        haversine_km(a.latitude, a.longitude, e.origin_lat, e.origin_lon),
                        e.depth_km
                    )
                )
            ) AS pga_fraction_g
        FROM assets a
        CROSS JOIN earthquake_models e
    """
    )

    logger.info(f"Computed earthquake vectors for all assets × {count} earthquake models")


def compute_wind_vectors(con: duckdb.DuckDBPyConnection):
    """Compute wind speeds for all assets × all wind models using Holland model."""
    count = con.execute("SELECT COUNT(*) FROM wind_models").fetchone()[0]
    if count == 0:
        return

    # Compute distance in nautical miles, then apply Holland model
    con.execute(
        """
        INSERT OR REPLACE INTO asset_states (asset_id, timestamp, wind_speed_mph)
        SELECT
            a.asset_id,
            w.timestamp,
            knots_to_mph(
                holland_wind_speed_kt(
                    km_to_nautical_miles(
                        haversine_km(a.latitude, a.longitude, w.center_lat, w.center_lon)
                    ),
                    w.max_wind_speed_kt,
                    w.radius_max_wind_nm,
                    w.radius_closest_isobar_nm
                )
            ) AS wind_speed_mph
        FROM assets a
        CROSS JOIN wind_models w
    """
    )

    logger.info(f"Computed wind vectors for all assets × {count} wind models")


def compute_flood_vectors(con: duckdb.DuckDBPyConnection):
    """Compute flood depth and velocity for assets within flood polygons.

    Uses DuckDB spatial extension for point-in-polygon tests at scale.
    """
    count = con.execute("SELECT COUNT(*) FROM flood_models").fetchone()[0]
    if count == 0:
        return

    # Try to use spatial extension for point-in-polygon
    try:
        con.execute("INSTALL spatial; LOAD spatial;")
        _compute_flood_vectors_spatial(con)
    except Exception:
        # Fallback: use Python-side spatial check
        _compute_flood_vectors_fallback(con)

    logger.info(f"Computed flood vectors for all assets × {count} flood areas")


def _compute_flood_vectors_spatial(con: duckdb.DuckDBPyConnection):
    """Flood vector computation using DuckDB spatial extension."""
    con.execute(
        """
        INSERT OR REPLACE INTO asset_states (
            asset_id, timestamp, flood_depth_m, flood_velocity_mps,
            soil_saturation, snow_water_equivalent_m, runoff_volume, groundwater_flow
        )
        SELECT
            a.asset_id,
            f.timestamp,
            f.water_elevation_m - (a.elevation_m + a.height_m) AS flood_depth_m,
            f.water_velocity_mps,
            f.soil_saturation,
            f.snow_water_equivalent_m,
            f.runoff_volume,
            f.groundwater_flow
        FROM assets a
        CROSS JOIN flood_models f
        WHERE ST_Contains(
            ST_GeomFromText(f.polygon_wkt),
            ST_Point(a.longitude, a.latitude)
        )
    """
    )


def _compute_flood_vectors_fallback(con: duckdb.DuckDBPyConnection):
    """Fallback flood computation using chunked Python-side spatial checks."""
    from shapely import wkt
    from shapely.geometry import Point
    from shapely.prepared import prep

    # Fetch flood polygons
    flood_areas = con.execute(
        """
        SELECT hazard_id, timestamp, area_idx, polygon_wkt,
               water_velocity_mps, water_elevation_m,
               soil_saturation, snow_water_equivalent_m,
               runoff_volume, groundwater_flow
        FROM flood_models
    """
    ).fetchall()

    if not flood_areas:
        return

    # Fetch all asset coordinates
    assets = con.execute(
        "SELECT asset_id, latitude, longitude, elevation_m, height_m FROM assets"
    ).fetchall()

    results = []
    for area in flood_areas:
        (
            hazard_id,
            timestamp,
            area_idx,
            polygon_wkt,
            water_vel,
            water_elev,
            soil_sat,
            swe,
            runoff,
            gw_flow,
        ) = area
        polygon = prep(wkt.loads(polygon_wkt))

        for asset_id, lat, lon, elev, height in assets:
            if polygon.contains(Point(lon, lat)):
                flood_depth = water_elev - (elev + height)
                results.append(
                    (asset_id, timestamp, flood_depth, water_vel, soil_sat, swe, runoff, gw_flow)
                )

    if results:
        con.executemany(
            """INSERT OR REPLACE INTO asset_states
               (asset_id, timestamp, flood_depth_m, flood_velocity_mps,
                soil_saturation, snow_water_equivalent_m, runoff_volume, groundwater_flow)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            results,
        )


def compute_fire_vectors(con: duckdb.DuckDBPyConnection):
    """Compute each asset's geodesic distance (km) to the nearest fire boundary.

    Assets inside a burned polygon get distance 0.0; assets outside get the true
    great-circle distance in kilometres to the nearest boundary point. Shapely's
    planar operation is only used to *locate* the nearest point on the boundary
    (adequate for the small areas involved); the distance itself is then measured
    geodesically so the fragility decay length stays in real kilometres rather
    than degrees of latitude/longitude.
    """
    count = con.execute("SELECT COUNT(*) FROM fire_models").fetchone()[0]
    if count == 0:
        return

    from collections import defaultdict

    from geopy.distance import geodesic
    from shapely import wkt
    from shapely.geometry import Point
    from shapely.ops import nearest_points

    fire_areas = con.execute(
        "SELECT hazard_id, timestamp, area_idx, polygon_wkt FROM fire_models"
    ).fetchall()
    if not fire_areas:
        return

    assets = con.execute("SELECT asset_id, latitude, longitude FROM assets").fetchall()

    # Group fire areas by (hazard_id, timestamp) so an asset's distance is the
    # minimum over all fronts present at that time.
    grouped: dict[tuple, list] = defaultdict(list)
    for hazard_id, timestamp, area_idx, polygon_wkt in fire_areas:
        grouped[(hazard_id, timestamp)].append(wkt.loads(polygon_wkt))

    results = []
    for (hazard_id, timestamp), polygons in grouped.items():
        for asset_id, lat, lon in assets:
            point = Point(lon, lat)
            min_km = float("inf")
            for poly in polygons:
                if poly.contains(point):
                    min_km = 0.0
                    break
                boundary_pt = nearest_points(poly.exterior, point)[0]
                dist_km = geodesic((lat, lon), (boundary_pt.y, boundary_pt.x)).km
                if dist_km < min_km:
                    min_km = dist_km
            results.append((asset_id, timestamp, min_km))

    if results:
        con.executemany(
            "INSERT OR REPLACE INTO asset_states (asset_id, timestamp, fire_distance_km) VALUES (?, ?, ?)",
            results,
        )

    logger.info(f"Computed fire vectors for all assets × {count} fire areas")
