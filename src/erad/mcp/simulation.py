"""
Simulation tools for ERAD MCP Server.
"""

from datetime import datetime
from pathlib import Path

from dist_stack.manifest import write_manifest
from dist_stack.registry import resolve_model_ref
from loguru import logger
from gdm.distribution import DistributionSystem

from erad import __version__
from erad.runner import HazardSimulator, HazardScenarioGenerator
from erad.systems.asset_system import AssetSystem
from erad.systems.hazard_system import HazardSystem
from erad.constants import HAZARD_TYPES

from .state import state
from .helpers import get_cache_directory, get_hazard_cache_directory, load_metadata


def _resolve_model_ref_to_path(model_ref: dict) -> Path:
    """Resolve model_ref payload into a local file path."""
    return Path(resolve_model_ref(model_ref))


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


# Default ForeFIRE propagation tuning validated for the LANDFIRE/sup3rmm
# landscape files. Callers may override via the extra_parameters argument.
_FOREFIRE_DEFAULT_PARAMS = {
    "spatialIncrement": "3",
    "minimalPropagativeFrontDepth": "20",
    "relax": "0.5",
    "propagationSpeedAdjustmentFactor": "0.6",
    "windReductionFactor": "0.4",
    "noInitialScan": "1",
    "minSpeed": "0.009",
}


def _parse_forefire_args(args: dict) -> dict:
    """Validate and normalize arguments for the ForeFIRE hazard tool."""
    from datetime import datetime as _dt

    landscape_path = args.get("landscape_path")
    fuels_path = args.get("fuels_path")
    if not landscape_path or not fuels_path:
        raise ValueError("landscape_path and fuels_path are required")
    if "ignition_lon" not in args or "ignition_lat" not in args:
        raise ValueError("ignition_lon and ignition_lat are required")

    landscape = Path(landscape_path)
    fuels = Path(fuels_path)
    if not landscape.exists():
        raise FileNotFoundError(f"Landscape file not found: {landscape}")
    if not fuels.exists():
        raise FileNotFoundError(f"Fuels file not found: {fuels}")

    ignition_time_raw = args.get("ignition_time")
    if ignition_time_raw:
        ignition_time = _dt.fromisoformat(str(ignition_time_raw).replace("Z", "+00:00"))
    else:
        ignition_time = _dt(2025, 1, 1, 0, 0, 0)

    bbox = args.get("domain_bbox")
    if bbox and len(bbox) == 4:
        domain_bbox = tuple(float(v) for v in bbox)
    else:
        lon = float(args["ignition_lon"])
        lat = float(args["ignition_lat"])
        domain_bbox = (lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5)

    return {
        "landscape": landscape,
        "fuels": fuels,
        "ignition_lon": float(args["ignition_lon"]),
        "ignition_lat": float(args["ignition_lat"]),
        "ignition_time": ignition_time,
        "duration_seconds": int(args.get("duration_seconds", 82800)),
        "step_seconds": int(args.get("step_seconds", 10800)),
        "wind_u": float(args.get("wind_u", 0.0)),
        "wind_v": float(args.get("wind_v", 0.0)),
        "domain_bbox": domain_bbox,
        "extra_parameters": args.get("extra_parameters") or dict(_FOREFIRE_DEFAULT_PARAMS),
    }


def _fire_perimeter_rings(area) -> list:
    """Extract [lon, lat] coordinate rings from a fire-affected area geometry."""
    polys = getattr(area, "geoms", None) or [area]
    rings = []
    for poly in polys:
        exterior = getattr(poly, "exterior", None)
        if exterior is None:
            continue
        rings.append([[round(c[0], 6), round(c[1], 6)] for c in exterior.coords])
    return rings


def _format_forefire_result(system_id: str, fire_models: list, config) -> dict:
    """Build the response payload from a completed ForeFIRE simulation."""
    lons = [
        b
        for fm in fire_models
        for b in (
            fm.affected_areas[0].affected_area.bounds[0],
            fm.affected_areas[0].affected_area.bounds[2],
        )
    ]
    lats = [
        b
        for fm in fire_models
        for b in (
            fm.affected_areas[0].affected_area.bounds[1],
            fm.affected_areas[0].affected_area.bounds[3],
        )
    ]
    perimeters = [
        {
            "timestamp": fm.timestamp.isoformat(),
            "rings": [
                ring
                for fma in fm.affected_areas
                for ring in _fire_perimeter_rings(fma.affected_area)
            ],
        }
        for fm in fire_models
    ]
    return {
        "success": True,
        "system_id": system_id,
        "hazard_count": len(fire_models),
        "timestamps": [fm.timestamp.isoformat() for fm in fire_models],
        "bounds": [round(v, 6) for v in [min(lons), min(lats), max(lons), max(lats)]],
        "ignition": [config.ignition_lon, config.ignition_lat],
        "perimeters": perimeters,
        "message": (
            f"ForeFIRE wildfire hazard system created with {len(fire_models)} "
            "time-stepped fire perimeters."
        ),
    }


async def create_forefire_hazard_tool(args: dict) -> dict:
    """Build a wildfire hazard system from a ForeFIRE propagation simulation.

    Runs the erad-plugin-forefire physics simulation over a landscape NetCDF
    file, igniting a fire at the requested point, and registers the resulting
    time-stepped HazardSystem for use by run_simulation.
    """
    try:
        try:
            from erad_plugin_forefire import ForefireConfig, run_forefire_scenario
            from erad.models.hazard.wild_fire import FireModel
        except ImportError as exc:
            return {
                "error": (
                    "erad-plugin-forefire (and its pyforefire dependency) is not "
                    f"installed in this environment: {exc}"
                )
            }

        parsed = _parse_forefire_args(args)
        config = ForefireConfig(
            landscape_path=parsed["landscape"],
            fuels_path=parsed["fuels"],
            ignition_lon=parsed["ignition_lon"],
            ignition_lat=parsed["ignition_lat"],
            ignition_time=parsed["ignition_time"],
            duration_seconds=parsed["duration_seconds"],
            step_seconds=parsed["step_seconds"],
            wind_u=parsed["wind_u"],
            wind_v=parsed["wind_v"],
            domain_bbox=parsed["domain_bbox"],
            extra_parameters=parsed["extra_parameters"],
        )

        logger.info(
            f"Running ForeFIRE scenario: landscape={parsed['landscape'].name}, "
            f"ignition=({config.ignition_lon},{config.ignition_lat}), "
            f"duration={config.duration_seconds}s, step={config.step_seconds}s"
        )
        hazard_system = run_forefire_scenario(config)

        fire_models = list(hazard_system.get_components(FireModel))
        if not fire_models:
            return {
                "error": (
                    "ForeFIRE simulation produced no fire perimeters. Check that "
                    "the ignition point lies within the landscape domain and that "
                    "the fuels table matches the landscape fuel indices."
                )
            }

        system_id = state.generate_id()
        state.hazard_systems[system_id] = hazard_system

        logger.info(
            f"Created ForeFIRE hazard system {system_id} with {len(fire_models)} fire perimeters"
        )
        return _format_forefire_result(system_id, fire_models, config)

    except Exception as e:
        logger.error(f"Error creating ForeFIRE hazard: {e}")
        return {"error": str(e)}


async def run_simulation_tool(args: dict) -> dict:
    """Run a hazard simulation."""
    asset_system_id = args["asset_system_id"]
    hazard_system_id = args["hazard_system_id"]
    curve_set = args.get("curve_set", "DEFAULT_CURVES")
    output_path = args.get("output_path")

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

        # Persist the simulation output artifact and write a provenance manifest
        # sidecar alongside it.
        if not output_path:
            output_path = get_hazard_cache_directory() / f"simulation_{simulation_id}.json"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        hazard_system.to_json(output_path)

        hazard_types = [
            hazard_type.__name__
            for hazard_type in HAZARD_TYPES
            if any(True for _ in hazard_system.get_components(hazard_type))
        ]
        write_manifest(
            output_path,
            artifact_type="erad_simulation",
            tool="run_simulation",
            tool_version=__version__,
            package="erad",
            package_version=__version__,
            config={
                "hazard_type": ",".join(hazard_types) if hazard_types else "unknown",
                "scenario_count": 1,
            },
        )

        logger.info(
            f"Simulation {simulation_id} completed with {len(simulator.timestamps)} timesteps; "
            f"wrote manifest sidecar for {output_path}"
        )

        return {
            "success": True,
            "simulation_id": simulation_id,
            "asset_count": len(simulator.assets),
            "timesteps": len(simulator.timestamps),
            "timestamps": [ts.isoformat() for ts in simulator.timestamps],
            "output_path": str(output_path),
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


async def apply_scenario_to_system_tool(args: dict) -> dict:
    """Apply a Monte Carlo scenario's tracked changes to a distribution system.

    Loads the original DistributionSystem from ``system_path``, applies the
    tracked changes stored for ``simulation_id`` (optionally filtered to a single
    ``scenario_name``), and writes the updated system to ``output_path``.
    """
    system_path = args["system_path"]
    simulation_id = args["simulation_id"]
    scenario_name = args.get("scenario_name")
    output_path = args["output_path"]

    try:
        from gdm.tracked_changes import (
            apply_updates_to_system,
            filter_tracked_changes_by_name_and_date,
        )

        if simulation_id not in state.simulation_results:
            return {"error": f"Simulation not found: {simulation_id}"}

        sim_info = state.simulation_results[simulation_id]
        if "tracked_changes" not in sim_info:
            return {"error": "No tracked changes found. Run generate_scenarios first."}

        tracked_changes = sim_info["tracked_changes"]

        if scenario_name:
            tracked_changes = filter_tracked_changes_by_name_and_date(
                tracked_changes=tracked_changes, scenario_name=scenario_name
            )
            if not tracked_changes:
                return {"error": f"No tracked changes found for scenario '{scenario_name}'"}

        if not Path(system_path).exists():
            return {"error": f"System file not found: {system_path}"}

        logger.info(
            f"Loading distribution system from {system_path} and applying "
            f"{len(tracked_changes)} tracked changes"
        )
        system = DistributionSystem.from_json(system_path)
        updated_system = apply_updates_to_system(tracked_changes, system, catalog=None)

        updated_system.to_json(output_path)

        logger.info(
            f"Applied {len(tracked_changes)} tracked changes and wrote result to {output_path}"
        )

        return {
            "success": True,
            "output_path": output_path,
            "applied_change_count": len(tracked_changes),
            "scenario_name": scenario_name,
            "message": f"Scenario applied to system and written to {output_path}",
        }

    except Exception as e:
        logger.error(f"Error applying scenario to system: {e}")
        return {"error": str(e)}
