"""
Utility tools for ERAD MCP Server.
"""

from loguru import logger

from erad.enums import AssetTypes
from erad.models.asset import Asset
from erad.constants import HAZARD_TYPES

from .state import state


async def list_asset_types_tool(args: dict) -> dict:
    """List available asset types."""
    try:
        # Get string values from enum
        asset_types = [at.name for at in AssetTypes]

        return {"success": True, "asset_types": asset_types, "count": len(asset_types)}

    except Exception as e:
        logger.error(f"Error listing asset types: {e}")
        return {"error": str(e)}


async def list_loaded_systems_tool(args: dict) -> dict:
    """List all loaded systems."""
    try:
        asset_systems = {}
        for system_id, asset_system in state.asset_systems.items():
            asset_count = len(list(asset_system.get_components(Asset)))
            asset_systems[system_id] = {"asset_count": asset_count}

        hazard_systems = {}
        for system_id, hazard_system in state.hazard_systems.items():
            hazard_count = sum(
                len(list(hazard_system.get_components(hazard_type)))
                for hazard_type in HAZARD_TYPES
            )
            hazard_systems[system_id] = {"hazard_count": hazard_count}

        simulations = {
            sim_id: {
                "timestamp": info["timestamp"],
                "asset_count": info["asset_count"],
                "timesteps": len(info["timestamps"]),
            }
            for sim_id, info in state.simulation_results.items()
        }

        return {
            "success": True,
            "asset_systems": asset_systems,
            "hazard_systems": hazard_systems,
            "simulations": simulations,
        }

    except Exception as e:
        logger.error(f"Error listing loaded systems: {e}")
        return {"error": str(e)}


async def clear_system_tool(args: dict) -> dict:
    """Clear a system from memory."""
    system_id = args["system_id"]
    system_type = args["system_type"]

    try:
        if system_type == "asset":
            if system_id in state.asset_systems:
                del state.asset_systems[system_id]
                logger.info(f"Cleared asset system {system_id}")
                return {"success": True, "message": f"Asset system {system_id} removed"}
            else:
                return {"error": f"Asset system not found: {system_id}"}

        elif system_type == "hazard":
            if system_id in state.hazard_systems:
                del state.hazard_systems[system_id]
                logger.info(f"Cleared hazard system {system_id}")
                return {"success": True, "message": f"Hazard system {system_id} removed"}
            else:
                return {"error": f"Hazard system not found: {system_id}"}

        elif system_type == "simulation":
            if system_id in state.simulation_results:
                del state.simulation_results[system_id]
                if system_id in state.hazard_simulators:
                    del state.hazard_simulators[system_id]
                logger.info(f"Cleared simulation {system_id}")
                return {"success": True, "message": f"Simulation {system_id} removed"}
            else:
                return {"error": f"Simulation not found: {system_id}"}

        else:
            return {"error": f"Invalid system_type: {system_type}"}

    except Exception as e:
        logger.error(f"Error clearing system: {e}")
        return {"error": str(e)}
