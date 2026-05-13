"""
Simulation tools for ERAD MCP Server.
"""

from datetime import datetime
import os
from pathlib import Path
import sqlite3

from loguru import logger
from gdm.distribution import DistributionSystem

from erad.runner import HazardSimulator, HazardScenarioGenerator
from erad.systems.asset_system import AssetSystem
from erad.systems.hazard_system import HazardSystem
from erad.constants import HAZARD_TYPES

from .state import state
from .helpers import get_cache_directory, load_metadata


def _resolve_model_ref_to_path(model_ref: dict) -> Path:
    """Resolve model_ref payload into a local file path."""
    for key in ("stored_path", "path", "source_path"):
        value = model_ref.get(key)
        if isinstance(value, str) and value.strip():
            return Path(value)

    model_id = model_ref.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("model_ref must include a path or model_id")

    version = model_ref.get("version")
    db_path = model_ref.get("registry_db") or os.getenv("DIST_STACK_MODEL_REGISTRY_DB")
    if not db_path:
        raise ValueError(
            "model_ref requires DIST_STACK_MODEL_REGISTRY_DB (or model_ref.registry_db) "
            "when path fields are not provided"
        )

    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        if version is None:
            row = conn.execute(
                """
                SELECT stored_path FROM models
                WHERE model_id = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                (model_id,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT stored_path FROM models
                WHERE model_id = ? AND version = ?
                LIMIT 1
                """,
                (model_id, int(version)),
            ).fetchone()

    if row is None:
        suffix = "latest" if version is None else f"version={version}"
        raise ValueError(f"model_ref not found for model_id={model_id}, {suffix}")

    return Path(str(row["stored_path"]))


async def load_distribution_model_tool(args: dict) -> dict:
    """Load a distribution model from file or cache."""
    source = args.get("source")
    model_ref = args.get("model_ref")
    from_cache = args.get("from_cache", False)

    try:
        if from_cache:
            # Load from cache
            cache_dir = get_cache_directory()
            metadata = load_metadata(cache_dir)

            if source not in metadata:
                return {"error": f"Model '{source}' not found in cache"}

            file_path = cache_dir / metadata[source]["filename"]
        else:
            # Load from file path
            if isinstance(model_ref, dict):
                file_path = _resolve_model_ref_to_path(model_ref)
            elif isinstance(source, str) and source.strip():
                file_path = Path(source)
            else:
                return {"error": "Expected either source or model_ref"}

            if not file_path.exists():
                return {"error": f"File not found: {file_path}"}

        # Load the distribution system
        logger.info(f"Loading distribution model from {file_path}")
        dist_system = DistributionSystem.from_json(file_path)

        # Create asset system
        asset_system = AssetSystem.from_gdm(dist_system)

        # Store in state
        system_id = state.generate_id()
        state.asset_systems[system_id] = asset_system

        from erad.models.asset import Asset

        asset_count = len(list(asset_system.get_components(Asset)))

        logger.info(f"Loaded asset system {system_id} with {asset_count} assets")

        return {
            "success": True,
            "system_id": system_id,
            "asset_count": asset_count,
            "source": str(file_path),
        }

    except Exception as e:
        logger.error(f"Error loading distribution model: {e}")
        return {"error": str(e)}


async def load_hazard_model_tool(args: dict) -> dict:
    """Load a hazard model from JSON file."""
    model_ref = args.get("model_ref")
    if isinstance(model_ref, dict):
        file_path = _resolve_model_ref_to_path(model_ref)
    else:
        file_arg = args.get("file_path")
        if not isinstance(file_arg, str) or not file_arg.strip():
            return {"error": "Expected either file_path or model_ref"}
        file_path = Path(file_arg)

    try:
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}

        logger.info(f"Loading hazard model from {file_path}")
        hazard_system = HazardSystem.from_json(file_path)

        # Store in state
        system_id = state.generate_id()
        state.hazard_systems[system_id] = hazard_system

        # Count hazard models
        hazard_count = sum(
            len(list(hazard_system.get_components(hazard_type))) for hazard_type in HAZARD_TYPES
        )

        logger.info(f"Loaded hazard system {system_id} with {hazard_count} hazard models")

        return {
            "success": True,
            "system_id": system_id,
            "hazard_count": hazard_count,
            "source": str(file_path),
        }

    except Exception as e:
        logger.error(f"Error loading hazard model: {e}")
        return {"error": str(e)}


async def create_hazard_system_tool(args: dict) -> dict:
    """Create a new empty hazard system."""
    try:
        hazard_system = HazardSystem()
        system_id = state.generate_id()
        state.hazard_systems[system_id] = hazard_system

        logger.info(f"Created new hazard system {system_id}")

        return {
            "success": True,
            "system_id": system_id,
            "message": "Empty hazard system created. Use load_historic_* tools to add hazards.",
        }

    except Exception as e:
        logger.error(f"Error creating hazard system: {e}")
        return {"error": str(e)}


async def run_simulation_tool(args: dict) -> dict:
    """Run a hazard simulation."""
    asset_system_id = args["asset_system_id"]
    hazard_system_id = args["hazard_system_id"]
    curve_set = args.get("curve_set", "DEFAULT_CURVES")

    try:
        # Validate systems exist
        if asset_system_id not in state.asset_systems:
            return {"error": f"Asset system not found: {asset_system_id}"}
        if hazard_system_id not in state.hazard_systems:
            return {"error": f"Hazard system not found: {hazard_system_id}"}

        asset_system = state.asset_systems[asset_system_id]
        hazard_system = state.hazard_systems[hazard_system_id]

        # Create simulator
        logger.info(
            f"Running simulation: asset={asset_system_id}, hazard={hazard_system_id}, curves={curve_set}"
        )
        simulator = HazardSimulator(asset_system)

        # Run simulation
        simulator.run(hazard_system, curve_set)

        # Store results
        simulation_id = state.generate_id()
        state.hazard_simulators[simulation_id] = simulator
        state.simulation_results[simulation_id] = {
            "asset_system_id": asset_system_id,
            "hazard_system_id": hazard_system_id,
            "curve_set": curve_set,
            "timestamp": datetime.now().isoformat(),
            "asset_count": len(simulator.assets),
            "timestamps": [ts.isoformat() for ts in simulator.timestamps],
        }

        logger.info(
            f"Simulation {simulation_id} completed with {len(simulator.timestamps)} timesteps"
        )

        return {
            "success": True,
            "simulation_id": simulation_id,
            "asset_count": len(simulator.assets),
            "timesteps": len(simulator.timestamps),
            "timestamps": [ts.isoformat() for ts in simulator.timestamps],
        }

    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        return {"error": str(e)}


async def generate_scenarios_tool(args: dict) -> dict:
    """Generate Monte Carlo scenarios from simulation."""
    simulation_id = args["simulation_id"]
    num_samples = args.get("num_samples", 1)
    seed = args.get("seed", 0)

    try:
        if simulation_id not in state.simulation_results:
            return {"error": f"Simulation not found: {simulation_id}"}

        sim_info = state.simulation_results[simulation_id]
        asset_system_id = sim_info["asset_system_id"]
        hazard_system_id = sim_info["hazard_system_id"]
        curve_set = sim_info["curve_set"]

        asset_system = state.asset_systems[asset_system_id]
        hazard_system = state.hazard_systems[hazard_system_id]

        logger.info(f"Generating {num_samples} scenarios for simulation {simulation_id}")

        # Generate scenarios
        generator = HazardScenarioGenerator(asset_system, hazard_system, curve_set)
        tracked_changes = generator.samples(num_samples, seed)

        # Store tracked changes
        state.simulation_results[simulation_id]["tracked_changes"] = tracked_changes

        # Summarize results
        scenarios = {}
        for change in tracked_changes:
            if change.scenario_name not in scenarios:
                scenarios[change.scenario_name] = {"outages": 0, "timestamps": set()}
            scenarios[change.scenario_name]["outages"] += len(change.edits)
            scenarios[change.scenario_name]["timestamps"].add(change.timestamp.isoformat())

        # Convert sets to lists for JSON serialization
        for scenario in scenarios.values():
            scenario["timestamps"] = sorted(list(scenario["timestamps"]))

        logger.info(
            f"Generated {num_samples} scenarios with total {len(tracked_changes)} tracked changes"
        )

        return {
            "success": True,
            "simulation_id": simulation_id,
            "num_samples": num_samples,
            "total_tracked_changes": len(tracked_changes),
            "scenarios": scenarios,
        }

    except Exception as e:
        logger.error(f"Error generating scenarios: {e}")
        return {"error": str(e)}
