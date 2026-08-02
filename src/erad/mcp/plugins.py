"""
Plugin discovery tools for ERAD MCP Server.
"""

import json

from mcp.server import MCPServer

from erad.plugins import get_plugin as _get_plugin
from erad.plugins import list_plugins as _list_plugins


async def list_plugins() -> dict:
    """List all discovered ERAD plugins.

    Returns:
        JSON payload with the plugin metadata list, or an error payload.
    """
    try:
        return {"plugins": _list_plugins()}
    except Exception as e:
        return {"error": str(e)}


async def get_plugin(plugin_name: str) -> dict:
    """Get metadata for a single ERAD plugin.

    Args:
        plugin_name: Name of the plugin (e.g., 'forefire').

    Returns:
        JSON payload with the plugin metadata, or an error payload.
    """
    try:
        metadata = _get_plugin(plugin_name)
        if metadata is None:
            return {"error": f"plugin not found: {plugin_name}"}
        return {"plugin": metadata}
    except Exception as e:
        return {"error": str(e)}


def register(mcp: MCPServer) -> None:
    """Register plugin discovery tools and resources with the MCP server."""

    @mcp.resource("erad://plugins")
    def plugins_resource() -> str:
        """List all discovered ERAD plugins (metadata for each)."""
        return json.dumps({"plugins": _list_plugins()}, indent=2)

    mcp.tool()(list_plugins)
    mcp.tool()(get_plugin)
