"""Vectorized Monte Carlo scenario generation using DuckDB."""

from __future__ import annotations


import duckdb
import numpy as np
from loguru import logger


def generate_scenarios(
    con: duckdb.DuckDBPyConnection,
    n_samples: int = 1,
    seed: int = 0,
) -> list[dict]:
    """Generate Monte Carlo damage scenarios via vectorized Bernoulli sampling.

    For each sample, draws a uniform random number per (asset, timestamp). If random > survival_probability,
    the asset is marked as failed. Only the first failure per asset is recorded (matching original behavior
    where once an asset fails, it stays failed for all subsequent timestamps).

    Returns:
        List of dicts with keys: scenario_name, timestamp, asset_id (distribution_asset UUID)
    """
    np.random.seed(seed)

    # Get dimensions
    n_assets = con.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    n_timestamps = con.execute("SELECT COUNT(DISTINCT timestamp) FROM asset_states").fetchone()[0]

    if n_assets == 0 or n_timestamps == 0:
        return []

    # Fetch survival probabilities as a structured result
    # Ordered by asset_id, timestamp for consistent indexing
    results = con.execute(
        """
        SELECT s.asset_id, s.timestamp, s.survival_probability, a.asset_name
        FROM asset_states s
        JOIN assets a ON s.asset_id = a.asset_id
        ORDER BY s.asset_id, s.timestamp
    """
    ).fetchall()

    # Build lookup structures
    asset_ids = []
    asset_names = {}
    timestamps_per_asset = {}
    probs_per_asset = {}

    current_asset = None
    for asset_id, ts, surv_prob, asset_name in results:
        if asset_id != current_asset:
            current_asset = asset_id
            asset_ids.append(asset_id)
            asset_names[asset_id] = asset_name
            timestamps_per_asset[asset_id] = []
            probs_per_asset[asset_id] = []
        timestamps_per_asset[asset_id].append(ts)
        probs_per_asset[asset_id].append(surv_prob)

    all_tracked_changes = []

    for sample_idx in range(n_samples):
        scenario_name = f"sample_{sample_idx}"
        outaged_assets = set()

        for asset_id in asset_ids:
            timestamps = timestamps_per_asset[asset_id]
            probs = probs_per_asset[asset_id]
            # Evaluate each asset once at its worst exposure (minimum survival
            # across timesteps = the hazard's closest approach). Drawing an
            # independent Bernoulli per timestep compounds a modest per-step
            # failure probability into an unrealistically high one, which made
            # assets fail far from a time-evolving hazard front.
            worst_idx = int(np.argmin(probs))
            if np.random.random() > probs[worst_idx]:
                all_tracked_changes.append(
                    {
                        "scenario_name": scenario_name,
                        "timestamp": timestamps[worst_idx],
                        "asset_id": asset_id,
                        "asset_name": asset_names[asset_id],
                    }
                )
                outaged_assets.add(asset_id)

        logger.info(f"Sample {sample_idx + 1}/{n_samples}: {len(outaged_assets)} assets failed")

    return all_tracked_changes


def generate_scenarios_fast(
    con: duckdb.DuckDBPyConnection,
    n_samples: int = 1,
    seed: int = 0,
) -> list[dict]:
    """Fully vectorized scenario generation for maximum performance at scale.

    Uses numpy vectorization over the entire (asset × timestamp) matrix.
    Best for 100K+ assets where the Python loop approach becomes slow.
    """
    np.random.seed(seed)

    # Fetch all survival probabilities in bulk as numpy array
    df = con.execute(
        """
        SELECT s.asset_id, s.timestamp, s.survival_probability
        FROM asset_states s
        ORDER BY s.asset_id, s.timestamp
    """
    ).fetchdf()

    if df.empty:
        return []

    # Get asset ordering
    unique_assets = df["asset_id"].unique()
    unique_timestamps = sorted(df["timestamp"].unique())
    n_assets = len(unique_assets)
    n_timestamps = len(unique_timestamps)

    # Reshape into matrix (n_assets × n_timestamps)
    surv_matrix = df["survival_probability"].values.reshape(n_assets, n_timestamps)

    # Fetch asset names
    names_df = con.execute("SELECT asset_id, asset_name FROM assets").fetchdf()
    asset_name_map = dict(zip(names_df["asset_id"], names_df["asset_name"]))

    # Evaluate each asset once at its worst exposure (minimum survival across
    # timesteps = the hazard's closest approach), rather than an independent
    # Bernoulli per timestep which compounds into unrealistically high failure.
    worst_survival = surv_matrix.min(axis=1)  # (n_assets,)
    worst_ts_idx = surv_matrix.argmin(axis=1)  # (n_assets,)

    all_tracked_changes = []

    for sample_idx in range(n_samples):
        scenario_name = f"sample_{sample_idx}"
        randoms = np.random.random(n_assets)
        failed_asset_indices = np.where(randoms > worst_survival)[0]

        for asset_idx in failed_asset_indices:
            ts_idx = worst_ts_idx[asset_idx]
            asset_id = unique_assets[asset_idx]
            all_tracked_changes.append(
                {
                    "scenario_name": scenario_name,
                    "timestamp": unique_timestamps[ts_idx],
                    "asset_id": asset_id,
                    "asset_name": asset_name_map.get(asset_id, ""),
                }
            )

        logger.info(
            f"Sample {sample_idx + 1}/{n_samples}: {len(failed_asset_indices)} assets failed"
        )

    return all_tracked_changes
