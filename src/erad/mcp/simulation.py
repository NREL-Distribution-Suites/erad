"""
Simulation tools for ERAD MCP Server.
"""

from datetime import datetime
from pathlib import Path

from dist_stack import (
    RunstoreError,
    attach_artifact,
    create_run,
    get_runstore_path,
    make_run_id,
    update_run,
)
from dist_stack.manifest import write_manifest
from dist_stack.registry import ModelNotFoundError, lookup, resolve_model_ref
from loguru import logger
from gdm.distribution import DistributionSystem
from mcp.server import MCPServer

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


def _resolve_provenance(model_ref: dict | None) -> dict:
    """Best-effort resolution of registry provenance from a ``model_ref``.

    Returns ``{"model_id", "model_version", "model_hash"}``. Path-only refs
    (no ``model_id``) stay honest: all three values are None rather than
    fabricated. A missing registry row is logged and skipped.
    """
    provenance = {"model_id": None, "model_version": None, "model_hash": None}
    if not isinstance(model_ref, dict) or not model_ref.get("model_id"):
        return provenance
    try:
        record = lookup(model_ref["model_id"])
        provenance["model_id"] = record.model_id
        provenance["model_version"] = record.version
        provenance["model_hash"] = record.model_hash
    except ModelNotFoundError:
        logger.warning(
            f"model_id {model_ref['model_id']} not found in registry; "
            "provenance skipped for loaded system"
        )
    return provenance


def _record_system_provenance(system_id: str, model_ref: dict | None) -> None:
    """Record best-effort registry provenance for a loaded system in state."""
    state.model_provenance[system_id] = _resolve_provenance(model_ref)


def _mint_run_id(run_id: str | None) -> str | None:
    """Best-effort: return a caller-supplied run_id or mint ``sim_<hex12>``.

    Returns None when the runstore is unavailable (``DIST_STACK_RUNSTORE_DB``
    unset) so callers keep today's behavior exactly.
    """
    if run_id:
        return run_id
    try:
        get_runstore_path()  # raises RunstoreUnavailableError when unset
        return make_run_id("sim")
    except RunstoreError as exc:
        logger.warning(f"runstore unavailable; runstore recording skipped: {exc}")
        return None


def _create_run_best_effort(
    run_id: str,
    *,
    asset_system_id: str,
    hazard_system_id: str,
    curve_set: str,
    simulation_id: str,
    timestamps: list[str],
) -> None:
    """Best-effort create_run; never raises. The runstore is the durable mirror."""
    provenance = state.model_provenance.get(asset_system_id, {})
    try:
        create_run(
            tool="run_simulation",
            run_type="erad_simulation",
            run_id=run_id,
            status="succeeded",
            model_id=provenance.get("model_id"),
            model_version=provenance.get("model_version"),
            model_hash=provenance.get("model_hash"),
            payload={
                "asset_system_id": asset_system_id,
                "hazard_system_id": hazard_system_id,
                "curve_set": curve_set,
                "timestamps": timestamps,
                "simulation_id": simulation_id,
            },
        )
    except RunstoreError as exc:
        logger.warning(f"runstore create_run skipped for run_id={run_id}: {exc}")


def _attach_artifact_best_effort(run_id: str | None, output_path: Path | str) -> None:
    """Best-effort attach_artifact; never raises."""
    if not run_id:
        return
    try:
        attach_artifact(run_id, output_path)
    except RunstoreError as exc:
        logger.warning(f"runstore attach_artifact skipped for run_id={run_id}: {exc}")


def _update_run_best_effort(run_id: str, *, payload: dict) -> None:
    """Best-effort update_run (payload REPLACES); never raises."""
    try:
        update_run(run_id, payload=payload)
    except RunstoreError as exc:
        logger.warning(f"runstore update_run skipped for run_id={run_id}: {exc}")


async def load_distribution_model(
    source: str | None = None,
    model_ref: dict | None = None,
    from_cache: bool = False,
) -> dict:
    """Load a distribution system model from file or cache. Returns a system ID for use in other tools.

    Args:
        source: File path or cached model name.
        model_ref: Optional model reference ({model_id/version} or direct stored_path/path).
        from_cache: Whether to load from cache (true) or file path (false).

    Returns:
        JSON payload with system_id, asset_count, and source on success, or an error payload.
    """
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
        _record_system_provenance(system_id, model_ref)

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


async def load_hazard_model(
    file_path: str | None = None,
    model_ref: dict | None = None,
) -> dict:
    """Load a hazard system model from JSON file. Returns a system ID.

    Args:
        file_path: Path to hazard model JSON file.
        model_ref: Optional model reference ({model_id/version} or direct stored_path/path).

    Returns:
        JSON payload with system_id, hazard_count, and source on success, or an error payload.
    """
    if isinstance(model_ref, dict):
        file_path_resolved = _resolve_model_ref_to_path(model_ref)
    else:
        if not isinstance(file_path, str) or not file_path.strip():
            return {"error": "Expected either file_path or model_ref"}
        file_path_resolved = Path(file_path)

    try:
        if not file_path_resolved.exists():
            return {"error": f"File not found: {file_path_resolved}"}

        logger.info(f"Loading hazard model from {file_path_resolved}")
        hazard_system = HazardSystem.from_json(file_path_resolved)

        # Store in state
        system_id = state.generate_id()
        state.hazard_systems[system_id] = hazard_system
        _record_system_provenance(system_id, model_ref)

        # Count hazard models
        hazard_count = sum(
            len(list(hazard_system.get_components(hazard_type))) for hazard_type in HAZARD_TYPES
        )

        logger.info(f"Loaded hazard system {system_id} with {hazard_count} hazard models")

        return {
            "success": True,
            "system_id": system_id,
            "hazard_count": hazard_count,
            "source": str(file_path_resolved),
        }

    except Exception as e:
        logger.error(f"Error loading hazard model: {e}")
        return {"error": str(e)}


async def create_hazard_system() -> dict:
    """Create a new empty hazard system. Returns a system ID.

    Returns:
        JSON payload with the new system_id on success, or an error payload.
    """
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


def _parse_forefire_args(
    landscape_path: str,
    fuels_path: str,
    ignition_lon: float | None,
    ignition_lat: float | None,
    ignition_time: str | None = None,
    duration_seconds: int = 82800,
    step_seconds: int = 10800,
    domain_bbox: list | None = None,
    wind_u: float = 0.0,
    wind_v: float = 0.0,
    extra_parameters: dict | None = None,
) -> dict:
    """Validate and normalize arguments for the ForeFIRE hazard tool."""
    if not landscape_path or not fuels_path:
        raise ValueError("landscape_path and fuels_path are required")
    if ignition_lon is None or ignition_lat is None:
        raise ValueError("ignition_lon and ignition_lat are required")

    landscape = Path(landscape_path)
    fuels = Path(fuels_path)
    if not landscape.exists():
        raise FileNotFoundError(f"Landscape file not found: {landscape}")
    if not fuels.exists():
        raise FileNotFoundError(f"Fuels file not found: {fuels}")

    if ignition_time:
        ignition_time_dt = datetime.fromisoformat(str(ignition_time).replace("Z", "+00:00"))
    else:
        ignition_time_dt = datetime(2025, 1, 1, 0, 0, 0)

    if domain_bbox and len(domain_bbox) == 4:
        domain_bbox_final = tuple(float(v) for v in domain_bbox)
    else:
        lon = float(ignition_lon)
        lat = float(ignition_lat)
        domain_bbox_final = (lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5)

    return {
        "landscape": landscape,
        "fuels": fuels,
        "ignition_lon": float(ignition_lon),
        "ignition_lat": float(ignition_lat),
        "ignition_time": ignition_time_dt,
        "duration_seconds": int(duration_seconds),
        "step_seconds": int(step_seconds),
        "wind_u": float(wind_u),
        "wind_v": float(wind_v),
        "domain_bbox": domain_bbox_final,
        "extra_parameters": extra_parameters or dict(_FOREFIRE_DEFAULT_PARAMS),
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


async def create_forefire_hazard(
    landscape_path: str,
    fuels_path: str,
    ignition_lon: float,
    ignition_lat: float,
    ignition_time: str | None = None,
    duration_seconds: int = 82800,
    step_seconds: int = 10800,
    domain_bbox: list[float] | None = None,
    wind_u: float = 0.0,
    wind_v: float = 0.0,
    extra_parameters: dict | None = None,
) -> dict:
    """Build a wildfire hazard system by running a ForeFIRE fire-spread simulation.

    Runs the erad-plugin-forefire physics simulation over a landscape NetCDF
    file, igniting a fire at the requested point, and registers the resulting
    time-stepped HazardSystem for use by run_simulation.

    Args:
        landscape_path: Path to the ForeFIRE landscape NetCDF file (fuel, altitude, wind).
        fuels_path: Path to the fuels table CSV matching the landscape fuel indices.
        ignition_lon: Ignition longitude (WGS84).
        ignition_lat: Ignition latitude (WGS84).
        ignition_time: ISO-8601 ignition time (default 2025-01-01T00:00:00).
        duration_seconds: Total simulation duration in seconds (default 82800).
        step_seconds: Perimeter extraction step in seconds (default 10800).
        domain_bbox: Optional [west, south, east, north] bounds metadata.
        wind_u: Optional constant eastward wind m/s (0 uses landscape wind).
        wind_v: Optional constant northward wind m/s (0 uses landscape wind).
        extra_parameters: Optional ForeFIRE setParameter overrides (propagation tuning).

    Returns:
        JSON payload with a hazard system ID and time-stepped fire perimeters.
    """
    try:
        try:
            from erad.plugins import get_plugin, load_plugin

            if get_plugin("forefire") is None:
                raise ImportError("erad-plugin-forefire plugin is not installed")
            forefire_module = load_plugin("forefire")
            if forefire_module is None:
                raise ImportError("erad-plugin-forefire module could not be loaded")
            ForefireConfig = forefire_module.ForefireConfig
            run_forefire_scenario = forefire_module.run_forefire_scenario
            from erad.models.hazard.wild_fire import FireModel
        except ImportError as exc:
            return {
                "error": (
                    "erad-plugin-forefire (and its pyforefire dependency) is not "
                    f"installed in this environment: {exc}"
                )
            }

        parsed = _parse_forefire_args(
            landscape_path=landscape_path,
            fuels_path=fuels_path,
            ignition_lon=ignition_lon,
            ignition_lat=ignition_lat,
            ignition_time=ignition_time,
            duration_seconds=duration_seconds,
            step_seconds=step_seconds,
            domain_bbox=domain_bbox,
            wind_u=wind_u,
            wind_v=wind_v,
            extra_parameters=extra_parameters,
        )
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


async def run_simulation(
    asset_system_id: str,
    hazard_system_id: str,
    curve_set: str = "DEFAULT_CURVES",
    output_path: str | None = None,
    run_id: str | None = None,
) -> dict:
    """Run a hazard simulation using loaded asset and hazard systems.

    Args:
        asset_system_id: ID of loaded asset system.
        hazard_system_id: ID of loaded hazard system.
        curve_set: Fragility curve set name.
        output_path: Output file path for the simulation artifact (a .manifest.json sidecar is written next to it).
        run_id: Optional caller-supplied runstore run_id (minted as ``sim_<hex12>`` when omitted).

    Returns:
        JSON payload with simulation_id and timestep information on success, or an error payload.
    """
    try:
        # Validate systems exist
        if asset_system_id not in state.asset_systems:
            return {"error": f"Asset system not found: {asset_system_id}"}
        if hazard_system_id not in state.hazard_systems:
            return {"error": f"Hazard system not found: {hazard_system_id}"}

        asset_system = state.asset_systems[asset_system_id]
        hazard_system = state.hazard_systems[hazard_system_id]

        # Best-effort runstore wiring (additive; no-op when DIST_STACK_RUNSTORE_DB
        # is unset so today's behavior is preserved exactly).
        run_id = _mint_run_id(run_id)

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
        if run_id:
            state.simulation_results[simulation_id]["run_id"] = run_id

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
        asset_provenance = state.model_provenance.get(asset_system_id, {})
        write_manifest(
            output_path,
            artifact_type="erad_simulation",
            tool="run_simulation",
            tool_version=__version__,
            package="erad",
            package_version=__version__,
            model_id=asset_provenance.get("model_id"),
            model_version=asset_provenance.get("model_version"),
            model_hash=asset_provenance.get("model_hash"),
            config={
                "hazard_type": ",".join(hazard_types) if hazard_types else "unknown",
                "scenario_count": 1,
            },
        )

        if run_id:
            _create_run_best_effort(
                run_id,
                asset_system_id=asset_system_id,
                hazard_system_id=hazard_system_id,
                curve_set=curve_set,
                simulation_id=simulation_id,
                timestamps=[ts.isoformat() for ts in simulator.timestamps],
            )
            _attach_artifact_best_effort(run_id, output_path)

        logger.info(
            f"Simulation {simulation_id} completed with {len(simulator.timestamps)} timesteps; "
            f"wrote manifest sidecar for {output_path}"
        )

        response = {
            "success": True,
            "simulation_id": simulation_id,
            "asset_count": len(simulator.assets),
            "timesteps": len(simulator.timestamps),
            "timestamps": [ts.isoformat() for ts in simulator.timestamps],
            "output_path": str(output_path),
        }
        if run_id:
            response["run_id"] = run_id
        return response

    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        return {"error": str(e)}


async def generate_scenarios(
    simulation_id: str,
    num_samples: int = 1,
    seed: int = 0,
) -> dict:
    """Generate Monte Carlo failure scenarios from simulation results.

    Args:
        simulation_id: ID of completed simulation.
        num_samples: Number of scenarios to generate.
        seed: Random seed for reproducibility.

    Returns:
        JSON payload with generated scenario summaries, or an error payload.
    """
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

        # Best-effort: record the scenario count on the runstore run row.
        run_id = sim_info.get("run_id")
        if run_id:
            _update_run_best_effort(
                run_id,
                payload={
                    "asset_system_id": sim_info["asset_system_id"],
                    "hazard_system_id": sim_info["hazard_system_id"],
                    "curve_set": sim_info["curve_set"],
                    "timestamps": sim_info["timestamps"],
                    "simulation_id": simulation_id,
                    "tracked_changes": len(tracked_changes),
                },
            )

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


async def apply_scenario_to_system(
    system_path: str,
    simulation_id: str,
    output_path: str,
    scenario_name: str | None = None,
) -> dict:
    """Apply a Monte Carlo scenario's tracked changes to a distribution system.

    Loads the original DistributionSystem from ``system_path``, applies the
    tracked changes stored for ``simulation_id`` (optionally filtered to a single
    ``scenario_name``), and writes the updated system to ``output_path``.

    Args:
        system_path: Path to the original DistributionSystem JSON file.
        simulation_id: ID of simulation with tracked changes.
        scenario_name: Optional scenario name to apply (e.g., 'sample_0').
        output_path: Output file path for the updated system JSON.

    Returns:
        JSON payload with the output path and applied change count, or an error payload.
    """
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


def register(mcp: MCPServer) -> None:
    """Register simulation tools with the MCP server."""
    mcp.tool()(load_distribution_model)
    mcp.tool()(load_hazard_model)
    mcp.tool()(create_hazard_system)
    mcp.tool()(create_forefire_hazard)
    mcp.tool()(run_simulation)
    mcp.tool()(generate_scenarios)
    mcp.tool()(apply_scenario_to_system)
