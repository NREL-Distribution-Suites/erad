"""
Fragility curve tools for ERAD MCP Server.
"""

from loguru import logger

from erad.default_fragility_curves import DEFAULT_FRAGILTY_CURVES


async def list_fragility_curves_tool(args: dict) -> dict:
    """List available fragility curves."""
    try:
        # Get default curve sets
        curve_info = {}
        for curve_set in DEFAULT_FRAGILTY_CURVES:
            hazard_param = curve_set.asset_state_param
            if hazard_param not in curve_info:
                curve_info[hazard_param] = {"asset_types": [], "curve_count": 0}

            for curve in curve_set.curves:
                asset_type = (
                    curve.asset_type.value
                    if hasattr(curve.asset_type, "value")
                    else str(curve.asset_type)
                )
                if asset_type not in curve_info[hazard_param]["asset_types"]:
                    curve_info[hazard_param]["asset_types"].append(asset_type)
                curve_info[hazard_param]["curve_count"] += 1

        return {"success": True, "curve_sets": ["DEFAULT_CURVES"], "hazard_types": curve_info}

    except Exception as e:
        logger.error(f"Error listing fragility curves: {e}")
        return {"error": str(e)}


async def get_fragility_curve_parameters_tool(args: dict) -> dict:
    """Get fragility curve parameters."""
    hazard_type = args["hazard_type"]
    asset_type_str = args["asset_type"]

    try:
        # Find matching curves
        matching_curves = []

        for curve_set in DEFAULT_FRAGILTY_CURVES:
            if curve_set.asset_state_param == hazard_type:
                for curve in curve_set.curves:
                    curve_asset_type = (
                        curve.asset_type.value
                        if hasattr(curve.asset_type, "value")
                        else str(curve.asset_type)
                    )
                    if curve_asset_type == asset_type_str:
                        matching_curves.append(
                            {
                                "asset_type": curve_asset_type,
                                "hazard_parameter": hazard_type,
                                "distribution": curve.prob_function.distribution,
                                "parameters": [str(p) for p in curve.prob_function.parameters],
                            }
                        )

        if not matching_curves:
            return {
                "success": False,
                "message": f"No curves found for hazard_type={hazard_type}, asset_type={asset_type_str}",
            }

        return {"success": True, "curves": matching_curves}

    except Exception as e:
        logger.error(f"Error getting curve parameters: {e}")
        return {"error": str(e)}
