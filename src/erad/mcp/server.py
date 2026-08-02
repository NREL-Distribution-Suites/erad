"""
Main ERAD MCP Server - Tool registration and server setup.
"""

import asyncio
import sys

from loguru import logger
from mcp.server import MCPServer


def create_server() -> MCPServer:
    """Create and configure the ERAD MCPServer instance."""
    mcp = MCPServer(
        "erad-mcp-server",
        instructions=(
            "ERAD MCP server for energy resilience analysis of distribution "
            "systems. Use the tools to load asset and hazard models, run hazard "
            "simulations, generate failure scenarios, query assets, explore "
            "historic hazards, and export results."
        ),
    )

    # -- Register tool modules -------------------------------------------------
    from .simulation import register as register_simulation
    from .assets import register as register_assets
    from .hazards import register as register_hazards
    from .fragility import register as register_fragility
    from .export import register as register_export
    from .cache import register as register_cache
    from .documentation import register as register_documentation
    from .utilities import register as register_utilities

    register_simulation(mcp)
    register_assets(mcp)
    register_hazards(mcp)
    register_fragility(mcp)
    register_export(mcp)
    register_cache(mcp)
    register_documentation(mcp)
    register_utilities(mcp)

    # -- Register resources ----------------------------------------------------
    from .resources import register as register_resources

    register_resources(mcp)

    # -- Register prompts ------------------------------------------------------
    from .prompts import workflows

    workflows.register(mcp)

    return mcp


async def serve():
    """Run the MCP server."""
    logger.info("Starting ERAD MCP Server")
    create_server().run(transport="stdio")


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
