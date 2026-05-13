"""
Tests for ERAD MCP Server
"""

import os
from datetime import datetime
import pytest
import sqlite3
from unittest.mock import Mock

# Import from new modular structure
from erad.mcp.state import ServerState, state
from erad.mcp.simulation import (
    create_hazard_system_tool,
    _resolve_model_ref_to_path,
    run_simulation_tool,
)
from erad.mcp.assets import (
    query_assets_tool,
    get_asset_statistics_tool,
)
from erad.mcp.utilities import (
    list_asset_types_tool,
    list_loaded_systems_tool,
)
from erad.mcp.cache import get_cache_info_tool
from erad.mcp.fragility import list_fragility_curves_tool
from erad.mcp.hazards import list_historic_hurricanes_tool
from erad.mcp.hazards import load_historic_hurricane_tool
from erad.models.hazard.wind import WindModel


@pytest.fixture
def clean_state():
    """Clean server state before each test."""
    state.clear()
    yield state
    state.clear()


@pytest.fixture
def sample_gdm_model(tmp_path):
    """Create a sample GDM model file."""
    # You would need to create a minimal valid GDM JSON here
    # For now, return None to skip file-based tests
    return None


class TestServerState:
    """Test ServerState class."""

    def test_generate_id(self):
        """Test ID generation."""
        state = ServerState()
        id1 = state.generate_id()
        id2 = state.generate_id()

        assert len(id1) == 8
        assert len(id2) == 8
        assert id1 != id2

    def test_clear(self):
        """Test state clearing."""
        state = ServerState()
        state.asset_systems["test"] = Mock()
        state.hazard_systems["test"] = Mock()
        state.simulation_results["test"] = {}

        state.clear()

        assert len(state.asset_systems) == 0
        assert len(state.hazard_systems) == 0
        assert len(state.simulation_results) == 0


class TestSimulationTools:
    """Test simulation tool functions."""

    @pytest.mark.asyncio
    async def test_create_hazard_system(self, clean_state):
        """Test creating a hazard system."""
        result = await create_hazard_system_tool({})

        assert result["success"] is True
        assert "system_id" in result
        assert result["system_id"] in state.hazard_systems

    @pytest.mark.asyncio
    async def test_run_simulation_missing_systems(self, clean_state):
        """Test simulation with missing systems."""
        result = await run_simulation_tool(
            {"asset_system_id": "nonexistent", "hazard_system_id": "nonexistent"}
        )

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_resolve_model_ref_direct_path(self, tmp_path):
        example = tmp_path / "example.json"
        path = _resolve_model_ref_to_path({"path": str(example)})
        assert str(path) == str(example)

    def test_resolve_model_ref_registry_lookup(self, tmp_path):
        db_path = tmp_path / "registry.sqlite"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE models (
                    model_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    stored_path TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO models (model_id, version, stored_path) VALUES (?, ?, ?)",
                ("erad123", 3, str(tmp_path / "erad_v3.json")),
            )

        os.environ["DIST_STACK_MODEL_REGISTRY_DB"] = str(db_path)
        try:
            path = _resolve_model_ref_to_path({"model_id": "erad123", "version": 3})
        finally:
            os.environ.pop("DIST_STACK_MODEL_REGISTRY_DB", None)

        assert str(path) == str(tmp_path / "erad_v3.json")


class TestAssetQueryTools:
    """Test asset query tools."""

    @pytest.mark.asyncio
    async def test_query_assets_missing_system(self, clean_state):
        """Test querying with missing system."""
        result = await query_assets_tool({"asset_system_id": "nonexistent"})

        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_asset_statistics_missing_system(self, clean_state):
        """Test statistics with missing system."""
        result = await get_asset_statistics_tool({"asset_system_id": "nonexistent"})

        assert "error" in result


class TestUtilityTools:
    """Test utility tools."""

    @pytest.mark.asyncio
    async def test_list_asset_types(self):
        """Test listing asset types."""
        result = await list_asset_types_tool({})

        assert result["success"] is True
        assert "asset_types" in result
        assert len(result["asset_types"]) > 0
        assert "distribution_poles" in result["asset_types"]

    @pytest.mark.asyncio
    async def test_list_loaded_systems_empty(self, clean_state):
        """Test listing systems when empty."""
        result = await list_loaded_systems_tool({})

        assert result["success"] is True
        assert len(result["asset_systems"]) == 0
        assert len(result["hazard_systems"]) == 0
        assert len(result["simulations"]) == 0

    @pytest.mark.asyncio
    async def test_get_cache_info(self):
        """Test getting cache information."""
        result = await get_cache_info_tool({})

        assert result["success"] is True
        assert "distribution_cache" in result
        assert "hazard_cache" in result
        assert "directory" in result["distribution_cache"]

    @pytest.mark.asyncio
    async def test_list_fragility_curves(self):
        """Test listing fragility curves."""
        result = await list_fragility_curves_tool({})

        assert result["success"] is True
        assert "curve_sets" in result
        assert "DEFAULT_CURVES" in result["curve_sets"]
        assert "hazard_types" in result

    @pytest.mark.asyncio
    async def test_list_historic_hurricanes_legacy_schema(self, tmp_path, monkeypatch):
        """Historic hurricane listing should work with legacy IBTrACS-style column names."""
        db_path = tmp_path / "erad_data.sqlite"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                'CREATE TABLE historic_hurricanes ("SID " TEXT, "NAME " TEXT, "SEASON (Year)" INTEGER)'
            )
            conn.execute(
                'INSERT INTO historic_hurricanes ("SID ", "NAME ", "SEASON (Year)") VALUES (?, ?, ?)',
                ("2025053S15150", "ALFRED", 2025),
            )

        monkeypatch.setattr("erad.mcp.hazards.get_historic_hazard_db", lambda: db_path)

        result = await list_historic_hurricanes_tool({"year": 2025, "limit": 10})

        assert result["success"] is True
        assert result["count"] == 1
        assert result["hurricanes"][0]["sid"] == "2025053S15150"
        assert result["hurricanes"][0]["name"] == "ALFRED"
        assert result["hurricanes"][0]["season"] == 2025

    def test_wind_model_from_hurricane_sid_legacy_schema(self, tmp_path, monkeypatch):
        """WindModel loading should handle legacy IBTrACS-style column names."""
        db_path = tmp_path / "erad_data.sqlite"
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE historic_hurricanes (
                    "SID " TEXT,
                    "LAT (degrees_north)" REAL,
                    "LON (degrees_east)" REAL,
                    "USA_WIND (kts)" TEXT,
                    "USA_ROCI (nmile)" TEXT,
                    "USA_RMW (nmile)" TEXT,
                    "USA_POCI (mb)" TEXT,
                    "ISO_TIME " TEXT
                )
                """
            )
            conn.execute(
                'INSERT INTO historic_hurricanes ("SID ", "LAT (degrees_north)", '
                '"LON (degrees_east)", "USA_WIND (kts)", "USA_ROCI (nmile)", '
                '"USA_RMW (nmile)", "USA_POCI (mb)", "ISO_TIME ") '
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("TESTSID", 10.0, -20.0, "75", "120", "20", "980", "2025-01-01 00:00:00"),
            )

        monkeypatch.setattr("erad.models.hazard.wind.ERAD_DB", db_path)

        track = WindModel.from_hurricane_sid("TESTSID")

        assert len(track) == 1
        assert track[0].name == "TESTSID"

    @pytest.mark.asyncio
    async def test_load_historic_hurricane_adds_track_points(self, clean_state, monkeypatch):
        """Historic hurricane load should add each track point to the hazard system."""

        class _WindPoint:
            def __init__(self, hour: int):
                self.timestamp = datetime(2025, 1, 1, hour, 0, 0)
                self.max_wind_speed = f"{70 + hour} knots"

        hazard_system = Mock()
        state.hazard_systems["hz1"] = hazard_system
        monkeypatch.setattr(
            "erad.mcp.hazards.WindModel.from_hurricane_sid",
            lambda _sid: [_WindPoint(0), _WindPoint(1)],
        )

        result = await load_historic_hurricane_tool(
            {"hazard_system_id": "hz1", "hurricane_sid": "2017106N36310"}
        )

        assert result["success"] is True
        assert result["points_loaded"] == 2
        assert hazard_system.add_component.call_count == 2


class TestFragilityCurveTools:
    """Test fragility curve tools."""

    @pytest.mark.asyncio
    async def test_list_curves(self):
        """Test listing available curves."""
        result = await list_fragility_curves_tool({})

        assert result["success"] is True
        assert len(result["hazard_types"]) > 0


class TestStatefulBehavior:
    """Test stateful server behavior."""

    @pytest.mark.asyncio
    async def test_create_and_list_hazard_system(self, clean_state):
        """Test creating system and then listing it."""
        # Create system
        create_result = await create_hazard_system_tool({})
        assert create_result["success"] is True
        system_id = create_result["system_id"]

        # List systems
        list_result = await list_loaded_systems_tool({})
        assert list_result["success"] is True
        assert system_id in list_result["hazard_systems"]


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_invalid_system_id(self, clean_state):
        """Test handling of invalid system IDs."""
        result = await query_assets_tool({"asset_system_id": "invalid-id-12345"})

        assert "error" in result
        assert "not found" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
