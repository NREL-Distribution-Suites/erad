"""
Asset query tools for ERAD MCP Server.
"""

import statistics

from loguru import logger

from erad.models.asset import Asset

from .state import state
from .helpers import serialize_asset


async def query_assets_tool(args: dict) -> dict:
    """Query assets with filters."""
    asset_system_id = args["asset_system_id"]

    try:
        if asset_system_id not in state.asset_systems:
            return {"error": f"Asset system not found: {asset_system_id}"}

        asset_system = state.asset_systems[asset_system_id]
        assets = list(asset_system.get_components(Asset))

        # Apply filters
        filtered_assets = assets

        # Filter by asset type
        if "asset_type" in args and args["asset_type"]:
            asset_type_str = args["asset_type"]
            filtered_assets = [
                a
                for a in filtered_assets
                if (hasattr(a.asset_type, "value") and a.asset_type.value == asset_type_str)
                or str(a.asset_type) == asset_type_str
            ]

        # Filter by location bounds
        if "latitude_min" in args and args["latitude_min"] is not None:
            filtered_assets = [a for a in filtered_assets if a.latitude >= args["latitude_min"]]
        if "latitude_max" in args and args["latitude_max"] is not None:
            filtered_assets = [a for a in filtered_assets if a.latitude <= args["latitude_max"]]
        if "longitude_min" in args and args["longitude_min"] is not None:
            filtered_assets = [a for a in filtered_assets if a.longitude >= args["longitude_min"]]
        if "longitude_max" in args and args["longitude_max"] is not None:
            filtered_assets = [a for a in filtered_assets if a.longitude <= args["longitude_max"]]

        # Filter by survival probability
        if "min_survival_probability" in args or "max_survival_probability" in args:
            min_prob = args.get("min_survival_probability", 0.0)
            max_prob = args.get("max_survival_probability", 1.0)

            filtered_assets = [
                a
                for a in filtered_assets
                if a.asset_state
                and any(
                    min_prob <= state.survival_probability <= max_prob for state in a.asset_state
                )
            ]

        # Serialize results
        results = [serialize_asset(asset) for asset in filtered_assets]

        logger.info(f"Query returned {len(results)} assets from system {asset_system_id}")

        return {
            "success": True,
            "asset_system_id": asset_system_id,
            "total_assets": len(assets),
            "filtered_count": len(results),
            "assets": results,
        }

    except Exception as e:
        logger.error(f"Error querying assets: {e}")
        return {"error": str(e)}


async def get_asset_details_tool(args: dict) -> dict:
    """Get details for a specific asset."""
    asset_system_id = args["asset_system_id"]
    asset_name = args["asset_name"]

    try:
        if asset_system_id not in state.asset_systems:
            return {"error": f"Asset system not found: {asset_system_id}"}

        asset_system = state.asset_systems[asset_system_id]
        assets = list(
            asset_system.get_components(Asset, filter_func=lambda a: a.name == asset_name)
        )

        if not assets:
            return {"error": f"Asset not found: {asset_name}"}

        asset = assets[0]
        result = serialize_asset(asset)

        logger.info(f"Retrieved details for asset {asset_name}")

        return {"success": True, "asset": result}

    except Exception as e:
        logger.error(f"Error getting asset details: {e}")
        return {"error": str(e)}


async def get_asset_statistics_tool(args: dict) -> dict:
    """Calculate asset statistics."""
    asset_system_id = args["asset_system_id"]

    try:
        if asset_system_id not in state.asset_systems:
            return {"error": f"Asset system not found: {asset_system_id}"}

        asset_system = state.asset_systems[asset_system_id]
        assets = list(asset_system.get_components(Asset))

        # Count by type
        type_counts = {}
        for asset in assets:
            asset_type = (
                asset.asset_type.value
                if hasattr(asset.asset_type, "value")
                else str(asset.asset_type)
            )
            type_counts[asset_type] = type_counts.get(asset_type, 0) + 1

        # Survival probability statistics
        survival_probs = []
        for asset in assets:
            if asset.asset_state:
                for asset_state in asset.asset_state:
                    survival_probs.append(asset_state.survival_probability)

        stats = {
            "total_assets": len(assets),
            "asset_types": type_counts,
            "has_simulation_results": len(survival_probs) > 0,
        }

        if survival_probs:
            stats["survival_probability"] = {
                "min": min(survival_probs),
                "max": max(survival_probs),
                "mean": statistics.mean(survival_probs),
                "median": statistics.median(survival_probs),
                "stdev": statistics.stdev(survival_probs) if len(survival_probs) > 1 else 0,
            }

        logger.info(f"Calculated statistics for system {asset_system_id}")

        return {"success": True, "statistics": stats}

    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        return {"error": str(e)}


async def get_network_topology_tool(args: dict) -> dict:
    """Get network topology."""
    asset_system_id = args["asset_system_id"]

    try:
        if asset_system_id not in state.asset_systems:
            return {"error": f"Asset system not found: {asset_system_id}"}

        asset_system = state.asset_systems[asset_system_id]
        graph = asset_system.get_undirected_graph()

        # Convert to node/edge lists
        nodes = [{"id": str(node), "name": str(node)} for node in graph.nodes()]

        edges = [
            {"source": str(source), "target": str(target)} for source, target in graph.edges()
        ]

        logger.info(f"Retrieved topology: {len(nodes)} nodes, {len(edges)} edges")

        return {
            "success": True,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    except Exception as e:
        logger.error(f"Error getting topology: {e}")
        return {"error": str(e)}
