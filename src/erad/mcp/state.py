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
        # Registry provenance keyed by system_id: {"model_id", "model_version", "model_hash"}.
        self.model_provenance: dict[str, dict[str, Any]] = {}

    def generate_id(self) -> str:
        """Generate a unique ID."""
        return uuid4().hex[:12]

    def clear(self):
        """Clear all state."""
        self.asset_systems.clear()
        self.hazard_systems.clear()
        self.simulation_results.clear()
        self.hazard_simulators.clear()
        self.model_provenance.clear()


# Global state instance
state = ServerState()
