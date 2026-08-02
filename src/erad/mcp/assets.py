"""
Asset query tools for ERAD MCP Server.
"""

import statistics

from loguru import logger
from mcp.server import MCPServer

from erad.models.asset import Asset

from .state import state
from .helpers import serialize_asset


async def query_assets(
    asset_system_id: str,
    asset_type: str | None = None,
    min_survival_probability: float | None = None,
    max_survival_probability: float | None = None,
    latitude_min: float | None = None,
    latitude_max: float | None = None,
    longitude_min: float | None = None,
    longitude_max: float | None = None,
) -> dict:
    """Query and filter assets from a loaded asset system.

    Args:
        asset_system_id: ID of loaded asset system.
        asset_type: Filter by asset type (optional).
        min_survival_probability: Minimum survival probability threshold (optional).
        max_survival_probability: Maximum survival probability threshold (optional).
        latitude_min: Minimum latitude for bounding box (optional).
        latitude_max: Maximum latitude for bounding box (optional).
        longitude_min: Minimum longitude for bounding box (optional).
        longitude_max: Maximum longitude for bounding box (optional).

    Returns:
        JSON payload with the filtered asset list, or an error payload.
    """
    try:
        if asset_system_id not in state.asset_systems:
            return {"error": f"Asset system not found: {asset_system_id}"}

        asset_system = state.asset_systems[asset_system_id]
        assets = list(asset_system.get_components(Asset))

        # Apply filters
        filtered_assets = assets

        # Filter by asset type
        if asset_type:
            filtered_assets = [
                a
                for a in filtered_assets
                if (hasattr(a.asset_type, "value") and a.asset_type.value == asset_type)
                or str(a.asset_type) == asset_type
            ]

        # Filter by location bounds
        if latitude_min is not None:
            filtered_assets = [a for a in filtered_assets if a.latitude >= latitude_min]
        if latitude_max is not None:
            filtered_assets = [a for a in filtered_assets if a.latitude <= latitude_max]
        if longitude_min is not None:
            filtered_assets = [a for a in filtered_assets if a.longitude >= longitude_min]
        if longitude_max is not None:
            filtered_assets = [a for a in filtered_assets if a.longitude <= longitude_max]

        # Filter by survival probability
        if min_survival_probability is not None or max_survival_probability is not None:
            min_prob = min_survival_probability if min_survival_probability is not None else 0.0
            max_prob = max_survival_probability if max_survival_probability is not None else 1.0

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


async def get_asset_details(asset_system_id: str, asset_name: str) -> dict:
    """Get detailed information about a specific asset.

    Args:
        asset_system_id: ID of loaded asset system.
        asset_name: Name of the asset.

    Returns:
        JSON payload with the asset details, or an error payload.
    """
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


async def get_asset_statistics(asset_system_id: str) -> dict:
    """Calculate statistics about assets in the system.

    Args:
        asset_system_id: ID of loaded asset system.

    Returns:
        JSON payload with asset statistics, or an error payload.
    """
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


async def get_network_topology(asset_system_id: str) -> dict:
    """Get network topology as node and edge lists.

    Args:
        asset_system_id: ID of loaded asset system.

    Returns:
        JSON payload with node and edge lists, or an error payload.
    """
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


def register(mcp: MCPServer) -> None:
    """Register asset query tools with the MCP server."""
    mcp.tool()(query_assets)
    mcp.tool()(get_asset_details)
    mcp.tool()(get_asset_statistics)
    mcp.tool()(get_network_topology)
