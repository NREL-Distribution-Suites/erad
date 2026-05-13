"""
Export tools for ERAD MCP Server.
"""

import json

from loguru import logger

from .state import state


async def export_to_sqlite_tool(args: dict) -> dict:
    """Export simulation results to SQLite."""
    asset_system_id = args["asset_system_id"]
    output_path = args["output_path"]

    try:
        if asset_system_id not in state.asset_systems:
            return {"error": f"Asset system not found: {asset_system_id}"}

        asset_system = state.asset_systems[asset_system_id]

        logger.info(f"Exporting to SQLite: {output_path}")
        asset_system.export_results(output_path)

        return {
            "success": True,
            "output_path": output_path,
            "message": f"Results exported to {output_path}",
        }

    except Exception as e:
        logger.error(f"Error exporting to SQLite: {e}")
        return {"error": str(e)}


async def export_to_json_tool(args: dict) -> dict:
    """Export system to JSON."""
    system_id = args["system_id"]
    system_type = args["system_type"]
    output_path = args["output_path"]

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

        return {
            "success": True,
            "output_path": output_path,
            "system_type": system_type,
            "message": f"{system_type.capitalize()} system exported to {output_path}",
        }

    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        return {"error": str(e)}


async def export_tracked_changes_tool(args: dict) -> dict:
    """Export tracked changes from Monte Carlo scenarios."""
    simulation_id = args["simulation_id"]
    output_path = args["output_path"]

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
