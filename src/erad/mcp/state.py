"""
State management for ERAD MCP Server.
"""

from typing import Any
from uuid import uuid4

from erad.runner import HazardSimulator
from erad.systems.asset_system import AssetSystem
from erad.systems.hazard_system import HazardSystem


class ServerState:
    """Manages server state for loaded systems and simulation results."""

    def __init__(self):
        self.asset_systems: dict[str, AssetSystem] = {}
        self.hazard_systems: dict[str, HazardSystem] = {}
        self.simulation_results: dict[str, dict[str, Any]] = {}
        self.hazard_simulators: dict[str, HazardSimulator] = {}

    def generate_id(self) -> str:
        """Generate a unique ID."""
        return str(uuid4())[:8]

    def clear(self):
        """Clear all state."""
        self.asset_systems.clear()
        self.hazard_systems.clear()
        self.simulation_results.clear()
        self.hazard_simulators.clear()


# Global state instance
state = ServerState()
