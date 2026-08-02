"""
Export tools for ERAD MCP Server.
"""

import json

from dist_stack import RunstoreError, attach_artifact
from loguru import logger
from mcp.server import MCPServer

from .state import state


def _get_run_id(simulation_id: str) -> str | None:
    """Best-effort: the runstore run_id recorded for a simulation, if any."""
    sim_info = state.simulation_results.get(simulation_id)
    if sim_info:
        return sim_info.get("run_id")
    return None


def _get_run_id_for_system(system_id: str, *, system_type: str | None = None) -> str | None:
    """Best-effort: the runstore run_id recorded for a simulation involving system_id."""
    for sim_info in state.simulation_results.values():
        if system_type != "hazard" and sim_info.get("asset_system_id") == system_id:
            return sim_info.get("run_id")
        if system_type != "asset" and sim_info.get("hazard_system_id") == system_id:
            return sim_info.get("run_id")
    return None


def _attach_artifact_best_effort(run_id: str | None, output_path: str) -> None:
    """Best-effort runstore attach_artifact; never raises."""
    if not run_id:
        return
    try:
        attach_artifact(run_id, output_path)
    except RunstoreError as exc:
        logger.warning(f"runstore attach_artifact skipped for run_id={run_id}: {exc}")


async def export_to_sqlite(asset_system_id: str, output_path: str) -> dict:
    """Export simulation results to SQLite database.

    Args:
        asset_system_id: ID of asset system with results.
        output_path: Output file path for SQLite database.

    Returns:
        JSON payload with the output path, or an error payload.
    """
    try:
        if asset_system_id not in state.asset_systems:
            return {"error": f"Asset system not found: {asset_system_id}"}

        asset_system = state.asset_systems[asset_system_id]

        logger.info(f"Exporting to SQLite: {output_path}")
        asset_system.export_results(output_path)

        # Best-effort: attach the export artifact to the simulation's runstore run.
        _attach_artifact_best_effort(
            _get_run_id_for_system(asset_system_id, system_type="asset"), output_path
        )

        return {
            "success": True,
            "output_path": output_path,
            "message": f"Results exported to {output_path}",
        }

    except Exception as e:
        logger.error(f"Error exporting to SQLite: {e}")
        return {"error": str(e)}


async def export_to_json(system_id: str, system_type: str, output_path: str) -> dict:
    """Export asset or hazard system to JSON file.

    Args:
        system_id: ID of system to export.
        system_type: Type of system: 'asset' or 'hazard'.
        output_path: Output file path.

    Returns:
        JSON payload with the output path, or an error payload.
    """
    try:
        if system_type == "asset":
            if system_id not in state.asset_systems:
                return {"error": f"Asset system not found: {system_id}"}
            system = state.asset_systems[system_id]
        elif system_type == "hazard":
            if system_id not in state.hazard_systems:
                return {"error": f"Hazard system not found: {system_id}"}
            system = state.hazard_systems[system_id]
        else:
            return {"error": f"Invalid system_type: {system_type}"}

        logger.info(f"Exporting {system_type} system to JSON: {output_path}")
        system.to_json(output_path)

        # Best-effort: attach the export artifact to the simulation's runstore run.
        _attach_artifact_best_effort(
            _get_run_id_for_system(system_id, system_type=system_type), output_path
        )

        return {
            "success": True,
            "output_path": output_path,
            "system_type": system_type,
            "message": f"{system_type.capitalize()} system exported to {output_path}",
        }

    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        return {"error": str(e)}


async def export_tracked_changes(simulation_id: str, output_path: str) -> dict:
    """Export Monte Carlo scenario tracked changes to JSON.

    Args:
        simulation_id: ID of simulation with tracked changes.
        output_path: Output file path.

    Returns:
        JSON payload with the output path and change count, or an error payload.
    """
    try:
        if simulation_id not in state.simulation_results:
            return {"error": f"Simulation not found: {simulation_id}"}

        sim_info = state.simulation_results[simulation_id]

        if "tracked_changes" not in sim_info:
            return {"error": "No tracked changes found. Run generate_scenarios first."}

        tracked_changes = sim_info["tracked_changes"]

        # Serialize tracked changes
        serialized = [
            {
                "scenario_name": tc.scenario_name,
                "timestamp": tc.timestamp.isoformat(),
                "edits": [
                    {
                        "component_uuid": str(edit.component_uuid),
                        "property": edit.name,
                        "value": edit.value,
                    }
                    for edit in tc.edits
                ],
            }
            for tc in tracked_changes
        ]

        with open(output_path, "w") as f:
            json.dump(serialized, f, indent=2)

        # Best-effort: attach the export artifact to the simulation's runstore run.
        _attach_artifact_best_effort(_get_run_id(simulation_id), output_path)

        logger.info(f"Exported {len(tracked_changes)} tracked changes to {output_path}")

        return {
            "success": True,
            "output_path": output_path,
            "tracked_change_count": len(tracked_changes),
            "message": f"Tracked changes exported to {output_path}",
        }

    except Exception as e:
        logger.error(f"Error exporting tracked changes: {e}")
        return {"error": str(e)}


def _get_engine(simulation_id: str):
    """Return the DuckDB SimulationEngine for a simulation, or raise if unavailable."""
    if simulation_id not in state.hazard_simulators:
        raise ValueError(f"Simulation not found: {simulation_id}")
    engine = state.hazard_simulators[simulation_id].engine
    if engine is None:
        raise ValueError("Simulation has no DuckDB engine available")
    return engine


async def export_parquet(simulation_id: str, output_path: str) -> dict:
    """Export simulation results to Parquet format.

    Args:
        simulation_id: ID of completed simulation.
        output_path: Output file path for the Parquet file.

    Returns:
        JSON payload with the output path, or an error payload.
    """
    try:
        engine = _get_engine(simulation_id)

        logger.info(f"Exporting simulation {simulation_id} to Parquet: {output_path}")
        engine.export_to_parquet(output_path)

        # Best-effort: attach the export artifact to the simulation's runstore run.
        _attach_artifact_best_effort(_get_run_id(simulation_id), output_path)

        return {
            "success": True,
            "output_path": output_path,
            "message": f"Simulation results exported to Parquet at {output_path}",
        }

    except Exception as e:
        logger.error(f"Error exporting simulation to Parquet: {e}")
        return {"error": str(e)}


async def export_csv(simulation_id: str, output_path: str) -> dict:
    """Export simulation results to CSV format.

    Args:
        simulation_id: ID of completed simulation.
        output_path: Output file path for the CSV file.

    Returns:
        JSON payload with the output path, or an error payload.
    """
    try:
        engine = _get_engine(simulation_id)

        logger.info(f"Exporting simulation {simulation_id} to CSV: {output_path}")
        engine.export_to_csv(output_path)

        # Best-effort: attach the export artifact to the simulation's runstore run.
        _attach_artifact_best_effort(_get_run_id(simulation_id), output_path)

        return {
            "success": True,
            "output_path": output_path,
            "message": f"Simulation results exported to CSV at {output_path}",
        }

    except Exception as e:
        logger.error(f"Error exporting simulation to CSV: {e}")
        return {"error": str(e)}


async def get_failed_assets(simulation_id: str, threshold: float = 0.5) -> dict:
    """Get assets with survival probability below a threshold from a simulation.

    Args:
        simulation_id: ID of completed simulation.
        threshold: Survival probability threshold (default 0.5).

    Returns:
        JSON payload with the failed asset list, or an error payload.
    """
    try:
        engine = _get_engine(simulation_id)

        logger.info(
            f"Getting failed assets for simulation {simulation_id} (threshold={threshold})"
        )
        df = engine.get_failed_assets(threshold)

        # Convert to JSON-serializable records (timestamps -> ISO strings)
        failed_assets = []
        for record in df.to_dict(orient="records"):
            serializable = dict(record)
            timestamp = serializable.get("timestamp")
            if hasattr(timestamp, "isoformat"):
                serializable["timestamp"] = timestamp.isoformat()
            failed_assets.append(serializable)

        return {
            "success": True,
            "failed_asset_count": len(failed_assets),
            "failed_assets": failed_assets,
            "threshold": threshold,
        }

    except Exception as e:
        logger.error(f"Error getting failed assets: {e}")
        return {"error": str(e)}


def register(mcp: MCPServer) -> None:
    """Register export tools with the MCP server."""
    mcp.tool()(export_to_sqlite)
    mcp.tool()(export_to_json)
    mcp.tool()(export_tracked_changes)
    mcp.tool()(export_parquet)
    mcp.tool()(export_csv)
    mcp.tool()(get_failed_assets)
