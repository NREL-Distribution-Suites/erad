"""
ERAD MCP Server - Model Context Protocol Server for Energy Resilience Analysis.

This package provides a stateful MCP server for running hazard simulations,
querying assets, exploring historic hazards, and analyzing distribution system resilience.

Main Components:
    - server: Main MCP server with tool registration
    - state: Server state management for loaded systems
    - simulation: Simulation and scenario generation tools
    - assets: Asset query and analysis tools
    - hazards: Historic hazard database access
    - fragility: Fragility curve tools
    - export: Data export tools
    - cache: Cache management
    - documentation: Documentation search
    - utilities: Utility tools
    - resources: MCP resource handlers
    - helpers: Helper functions

Usage:
    Start the server from command line:
        $ erad server mcp
        $ erad-mcp

    Or programmatically:
        from erad.mcp import main
        main()
"""

from .server import main, serve
from .state import ServerState, state

__all__ = [
    "main",
    "serve",
    "ServerState",
    "state",
]

__version__ = "1.0.0"
