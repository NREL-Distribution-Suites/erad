"""
Main ERAD MCP Server - Tool registration and server setup.
"""

import asyncio
import json
import sys

from loguru import logger
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool
import mcp.types as types

# Import tool handlers
from .simulation import (
    load_distribution_model_tool,
    load_hazard_model_tool,
    create_hazard_system_tool,
    run_simulation_tool,
    generate_scenarios_tool,
)
from .assets import (
    query_assets_tool,
    get_asset_details_tool,
    get_asset_statistics_tool,
    get_network_topology_tool,
)
from .hazards import (
    list_historic_hurricanes_tool,
    list_historic_earthquakes_tool,
    list_historic_wildfires_tool,
    load_historic_hurricane_tool,
    load_historic_earthquake_tool,
    load_historic_wildfire_tool,
)
from .fragility import (
    list_fragility_curves_tool,
    get_fragility_curve_parameters_tool,
)
from .export import (
    export_to_sqlite_tool,
    export_to_json_tool,
    export_tracked_changes_tool,
)
from .cache import (
    list_cached_models_tool,
    get_cache_info_tool,
)
from .documentation import search_documentation_tool
from .utilities import (
    list_asset_types_tool,
    list_loaded_systems_tool,
    clear_system_tool,
)
from .resources import list_resources, read_resource


# Initialize MCP server
app = Server("erad-mcp-server")


@app.list_resources()
async def handle_list_resources() -> list:
    """List available resources."""
    return await list_resources()


@app.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a resource by URI."""
    return await read_resource(uri)


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        # Simulation Tools
        Tool(
            name="load_distribution_model",
            description="Load a distribution system model from file or cache. Returns a system ID for use in other tools.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "File path or cached model name"},
                    "model_ref": {
                        "type": "object",
                        "description": "Optional model reference ({model_id/version} or direct stored_path/path)",
                    },
                    "from_cache": {
                        "type": "boolean",
                        "description": "Whether to load from cache (true) or file path (false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="load_hazard_model",
            description="Load a hazard system model from JSON file. Returns a system ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to hazard model JSON file",
                    },
                    "model_ref": {
                        "type": "object",
                        "description": "Optional model reference ({model_id/version} or direct stored_path/path)",
                    },
                },
            },
        ),
        Tool(
            name="create_hazard_system",
            description="Create a new empty hazard system. Returns a system ID.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="run_simulation",
            description="Run a hazard simulation using loaded asset and hazard systems.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_system_id": {
                        "type": "string",
                        "description": "ID of loaded asset system",
                    },
                    "hazard_system_id": {
                        "type": "string",
                        "description": "ID of loaded hazard system",
                    },
                    "curve_set": {
                        "type": "string",
                        "description": "Fragility curve set name",
                        "default": "DEFAULT_CURVES",
                    },
                },
                "required": ["asset_system_id", "hazard_system_id"],
            },
        ),
        Tool(
            name="generate_scenarios",
            description="Generate Monte Carlo failure scenarios from simulation results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "simulation_id": {
                        "type": "string",
                        "description": "ID of completed simulation",
                    },
                    "num_samples": {
                        "type": "integer",
                        "description": "Number of scenarios to generate",
                        "default": 1,
                    },
                    "seed": {
                        "type": "integer",
                        "description": "Random seed for reproducibility",
                        "default": 0,
                    },
                },
                "required": ["simulation_id"],
            },
        ),
        # Asset Query Tools
        Tool(
            name="query_assets",
            description="Query and filter assets from a loaded asset system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_system_id": {
                        "type": "string",
                        "description": "ID of loaded asset system",
                    },
                    "asset_type": {
                        "type": "string",
                        "description": "Filter by asset type (optional)",
                    },
                    "min_survival_probability": {
                        "type": "number",
                        "description": "Minimum survival probability threshold (optional)",
                    },
                    "max_survival_probability": {
                        "type": "number",
                        "description": "Maximum survival probability threshold (optional)",
                    },
                    "latitude_min": {
                        "type": "number",
                        "description": "Minimum latitude for bounding box (optional)",
                    },
                    "latitude_max": {
                        "type": "number",
                        "description": "Maximum latitude for bounding box (optional)",
                    },
                    "longitude_min": {
                        "type": "number",
                        "description": "Minimum longitude for bounding box (optional)",
                    },
                    "longitude_max": {
                        "type": "number",
                        "description": "Maximum longitude for bounding box (optional)",
                    },
                },
                "required": ["asset_system_id"],
            },
        ),
        Tool(
            name="get_asset_details",
            description="Get detailed information about a specific asset.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_system_id": {
                        "type": "string",
                        "description": "ID of loaded asset system",
                    },
                    "asset_name": {"type": "string", "description": "Name of the asset"},
                },
                "required": ["asset_system_id", "asset_name"],
            },
        ),
        Tool(
            name="get_asset_statistics",
            description="Calculate statistics about assets in the system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_system_id": {
                        "type": "string",
                        "description": "ID of loaded asset system",
                    }
                },
                "required": ["asset_system_id"],
            },
        ),
        Tool(
            name="get_network_topology",
            description="Get network topology as node and edge lists.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_system_id": {
                        "type": "string",
                        "description": "ID of loaded asset system",
                    }
                },
                "required": ["asset_system_id"],
            },
        ),
        # Historic Hazard Tools
        Tool(
            name="list_historic_hurricanes",
            description="List available historic hurricanes from the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Filter by year (optional)"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="list_historic_earthquakes",
            description="List available historic earthquakes from the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_magnitude": {
                        "type": "number",
                        "description": "Minimum magnitude filter (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="list_historic_wildfires",
            description="List available historic wildfires from the database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Filter by year (optional)"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="load_historic_hurricane",
            description="Load a historic hurricane and add to hazard system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hazard_system_id": {
                        "type": "string",
                        "description": "ID of hazard system to add to",
                    },
                    "hurricane_sid": {
                        "type": "string",
                        "description": "Hurricane SID (e.g., '2017228N14314')",
                    },
                },
                "required": ["hazard_system_id", "hurricane_sid"],
            },
        ),
        Tool(
            name="load_historic_earthquake",
            description="Load a historic earthquake and add to hazard system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hazard_system_id": {
                        "type": "string",
                        "description": "ID of hazard system to add to",
                    },
                    "earthquake_code": {
                        "type": "string",
                        "description": "Earthquake code (e.g., 'ISCGEM851547')",
                    },
                },
                "required": ["hazard_system_id", "earthquake_code"],
            },
        ),
        Tool(
            name="load_historic_wildfire",
            description="Load a historic wildfire and add to hazard system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hazard_system_id": {
                        "type": "string",
                        "description": "ID of hazard system to add to",
                    },
                    "wildfire_name": {
                        "type": "string",
                        "description": "Wildfire name (e.g., 'GREAT LAKES FIRE')",
                    },
                },
                "required": ["hazard_system_id", "wildfire_name"],
            },
        ),
        # Fragility Curve Tools
        Tool(
            name="list_fragility_curves",
            description="List available fragility curve sets and hazard types.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_fragility_curve_parameters",
            description="Get fragility curve parameters for specific asset type and hazard.",
            inputSchema={
                "type": "object",
                "properties": {
                    "hazard_type": {
                        "type": "string",
                        "description": "Hazard type (wind_speed, flood_depth, etc.)",
                    },
                    "asset_type": {"type": "string", "description": "Asset type"},
                },
                "required": ["hazard_type", "asset_type"],
            },
        ),
        # Export Tools
        Tool(
            name="export_to_sqlite",
            description="Export simulation results to SQLite database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "asset_system_id": {
                        "type": "string",
                        "description": "ID of asset system with results",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output file path for SQLite database",
                    },
                },
                "required": ["asset_system_id", "output_path"],
            },
        ),
        Tool(
            name="export_to_json",
            description="Export asset or hazard system to JSON file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {"type": "string", "description": "ID of system to export"},
                    "system_type": {
                        "type": "string",
                        "description": "Type of system: 'asset' or 'hazard'",
                    },
                    "output_path": {"type": "string", "description": "Output file path"},
                },
                "required": ["system_id", "system_type", "output_path"],
            },
        ),
        Tool(
            name="export_tracked_changes",
            description="Export Monte Carlo scenario tracked changes to JSON.",
            inputSchema={
                "type": "object",
                "properties": {
                    "simulation_id": {
                        "type": "string",
                        "description": "ID of simulation with tracked changes",
                    },
                    "output_path": {"type": "string", "description": "Output file path"},
                },
                "required": ["simulation_id", "output_path"],
            },
        ),
        # Cache Management
        Tool(
            name="list_cached_models",
            description="List all cached distribution and hazard models.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model_type": {
                        "type": "string",
                        "description": "'distribution' or 'hazard' or 'both'",
                        "default": "both",
                    }
                },
            },
        ),
        Tool(
            name="get_cache_info",
            description="Get information about cache directories and usage.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # Documentation Tools
        Tool(
            name="search_documentation",
            description="Search ERAD documentation for specific topics.",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        ),
        # Utility Tools
        Tool(
            name="list_asset_types",
            description="List all available asset types in ERAD.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_loaded_systems",
            description="List all currently loaded asset and hazard systems.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="clear_system",
            description="Remove a loaded system from memory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {"type": "string", "description": "ID of system to remove"},
                    "system_type": {
                        "type": "string",
                        "description": "'asset', 'hazard', or 'simulation'",
                    },
                },
                "required": ["system_id", "system_type"],
            },
        ),
    ]


# Tool dispatch registry
_TOOL_HANDLERS = {
    "load_distribution_model": load_distribution_model_tool,
    "load_hazard_model": load_hazard_model_tool,
    "create_hazard_system": create_hazard_system_tool,
    "run_simulation": run_simulation_tool,
    "generate_scenarios": generate_scenarios_tool,
    "query_assets": query_assets_tool,
    "get_asset_details": get_asset_details_tool,
    "get_asset_statistics": get_asset_statistics_tool,
    "get_network_topology": get_network_topology_tool,
    "list_historic_hurricanes": list_historic_hurricanes_tool,
    "list_historic_earthquakes": list_historic_earthquakes_tool,
    "list_historic_wildfires": list_historic_wildfires_tool,
    "load_historic_hurricane": load_historic_hurricane_tool,
    "load_historic_earthquake": load_historic_earthquake_tool,
    "load_historic_wildfire": load_historic_wildfire_tool,
    "list_fragility_curves": list_fragility_curves_tool,
    "get_fragility_curve_parameters": get_fragility_curve_parameters_tool,
    "export_to_sqlite": export_to_sqlite_tool,
    "export_to_json": export_to_json_tool,
    "export_tracked_changes": export_tracked_changes_tool,
    "list_cached_models": list_cached_models_tool,
    "get_cache_info": get_cache_info_tool,
    "search_documentation": search_documentation_tool,
    "list_asset_types": list_asset_types_tool,
    "list_loaded_systems": list_loaded_systems_tool,
    "clear_system": clear_system_tool,
}


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls."""
    try:
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            result = {"error": f"Unknown tool: {name}"}
        else:
            result = await handler(arguments)

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [types.TextContent(type="text", text=json.dumps({"error": str(e), "tool": name}))]


async def serve():
    """Run the MCP server."""
    logger.info("Starting ERAD MCP Server")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Main entry point with logging configuration."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    asyncio.run(serve())
