"""
Tests for ERAD MCP Server
"""

import os
from datetime import datetime
from pathlib import Path
import pytest
import sqlite3
from unittest.mock import Mock

# Import from new modular structure
from erad.mcp.state import ServerState, state
from erad.mcp.simulation import (
    create_hazard_system_tool,
    _resolve_model_ref_to_path,
    run_simulation_tool,
    generate_scenarios_tool,
    apply_scenario_to_system_tool,
)
from erad.mcp.export import (
    export_csv_tool,
    export_parquet_tool,
    get_failed_assets_tool,
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

    def test_resolve_model_ref_library_registered(self, tmp_path):
        """Register via the dist-stack library, then resolve via model_id/version."""
        from dist_stack.registry import register

        db_path = tmp_path / "registry.sqlite"
        model_file = tmp_path / "registered_v2.json"
        model_file.write_text("{}")

        os.environ["DIST_STACK_MODEL_REGISTRY_DB"] = str(db_path)
        try:
            register(
                model_id="erad-lib",
                version=2,
                stored_path=model_file,
                metadata={"tool": "test"},
            )
            path = _resolve_model_ref_to_path({"model_id": "erad-lib", "version": 2})
        finally:
            os.environ.pop("DIST_STACK_MODEL_REGISTRY_DB", None)

        assert isinstance(path, Path)
        assert str(path) == str(model_file)
        assert path.exists()


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


class TestProvenanceManifest:
    """Provenance manifest sidecar wiring for simulation artifacts."""

    @pytest.mark.asyncio
    async def test_run_simulation_writes_manifest(self, clean_state, tmp_path):
        """A completed simulation should write a .manifest.json sidecar next to its output artifact."""
        from dist_stack.manifest import get_manifest_path, has_manifest, read_manifest
        from erad.models.asset import Asset
        from erad.systems.asset_system import AssetSystem
        from erad.systems.hazard_system import HazardSystem

        # Build a minimal asset system + hazard system in server state
        asset_system = AssetSystem(auto_add_composed_components=True)
        asset_system.add_component(Asset.example())
        asset_system_id = state.generate_id()
        state.asset_systems[asset_system_id] = asset_system

        hazard_system = HazardSystem.wind_example()
        hazard_system_id = state.generate_id()
        state.hazard_systems[hazard_system_id] = hazard_system

        output_path = tmp_path / "simulation.json"
        result = await run_simulation_tool(
            {
                "asset_system_id": asset_system_id,
                "hazard_system_id": hazard_system_id,
                "output_path": str(output_path),
            }
        )

        assert result["success"] is True
        assert result["output_path"] == str(output_path)

        # The output artifact itself should exist...
        assert output_path.exists()
        # ...with a provenance manifest sidecar next to it
        assert get_manifest_path(output_path) == tmp_path / "simulation.json.manifest.json"
        assert has_manifest(output_path)
        assert (tmp_path / "simulation.json.manifest.json").exists()

        manifest = read_manifest(output_path)
        assert manifest.artifact_type == "erad_simulation"
        assert manifest.tool == "run_simulation"
        assert manifest.package == "erad"
        assert manifest.package_version == "0.1.14"
        assert "hazard_type" in manifest.config
        assert manifest.config["hazard_type"] == "WindModel"
        assert manifest.config["scenario_count"] == 1


async def _run_failure_simulation():
    """Set up asset/hazard systems in state and run a simulation where an asset fails.

    Builds a single distribution pole placed 50 miles from a 150 mph hurricane
    eye (the radius of maximum wind), so its survival probability drops well
    below the 0.5 default threshold. Returns the simulation_id.
    """
    from datetime import datetime
    from uuid import UUID

    from geopy.distance import distance as geodist
    from infrasys.quantities import Distance
    from shapely.geometry import Point

    from erad.models.asset import Asset, AssetState, AssetTypes
    from erad.models.hazard.wind import WindModel
    from erad.quantities import Pressure, Speed
    from erad.systems.asset_system import AssetSystem
    from erad.systems.hazard_system import HazardSystem

    center = Point(-121.93036, 36.60144)
    asset_point = geodist(miles=50).destination((36.60144, -121.93036), bearing=0)

    asset_system = AssetSystem(auto_add_composed_components=True)
    asset_system.add_component(
        Asset(
            name="Asset 1",
            asset_type=AssetTypes.distribution_poles,
            distribution_asset=UUID("123e4567-e89b-12d3-a456-426614174000"),
            height=Distance(100, "m"),
            latitude=asset_point.latitude,
            longitude=asset_point.longitude,
            asset_state=[AssetState(timestamp=datetime.now())],
        )
    )
    asset_system_id = state.generate_id()
    state.asset_systems[asset_system_id] = asset_system

    hazard_system = HazardSystem(auto_add_composed_components=True)
    hazard_system.add_component(
        WindModel(
            name="hurricane 1",
            timestamp=datetime.now(),
            center=center,
            max_wind_speed=Speed(150, "miles/hour"),
            air_pressure=Pressure(1013.25, "hPa"),
            radius_of_max_wind=Distance(50, "miles"),
            radius_of_closest_isobar=Distance(300, "miles"),
        )
    )
    hazard_system_id = state.generate_id()
    state.hazard_systems[hazard_system_id] = hazard_system

    result = await run_simulation_tool(
        {
            "asset_system_id": asset_system_id,
            "hazard_system_id": hazard_system_id,
        }
    )
    assert result["success"] is True, result
    return result["simulation_id"]


class TestEngineExportTools:
    """Test DuckDB engine export tools."""

    @pytest.mark.asyncio
    async def test_export_parquet(self, clean_state, tmp_path):
        """Exporting a completed simulation should write a Parquet file."""
        simulation_id = await _run_failure_simulation()
        output_path = tmp_path / "results.parquet"

        result = await export_parquet_tool(
            {"simulation_id": simulation_id, "output_path": str(output_path)}
        )

        assert result["success"] is True
        assert result["output_path"] == str(output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_export_csv(self, clean_state, tmp_path):
        """Exporting a completed simulation should write a CSV file."""
        simulation_id = await _run_failure_simulation()
        output_path = tmp_path / "results.csv"

        result = await export_csv_tool(
            {"simulation_id": simulation_id, "output_path": str(output_path)}
        )

        assert result["success"] is True
        assert result["output_path"] == str(output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_export_parquet_missing_simulation(self, clean_state, tmp_path):
        """Exporting with an unknown simulation should return an error."""
        result = await export_parquet_tool(
            {"simulation_id": "missing", "output_path": str(tmp_path / "x.parquet")}
        )

        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_failed_assets(self, clean_state):
        """Failed asset queries should return assets below the survival threshold."""
        simulation_id = await _run_failure_simulation()

        result = await get_failed_assets_tool({"simulation_id": simulation_id, "threshold": 0.5})

        assert result["success"] is True
        assert result["threshold"] == 0.5
        assert result["failed_asset_count"] == 1
        assert len(result["failed_assets"]) == 1
        record = result["failed_assets"][0]
        assert record["asset_name"] == "Asset 1"
        assert record["survival_probability"] < 0.5
        # Timestamp should be JSON-serializable (ISO string)
        assert "T" in record["timestamp"]

    @pytest.mark.asyncio
    async def test_get_failed_assets_default_threshold(self, clean_state):
        """Threshold should default to 0.5 when not provided."""
        simulation_id = await _run_failure_simulation()

        result = await get_failed_assets_tool({"simulation_id": simulation_id})

        assert result["success"] is True
        assert result["threshold"] == 0.5

    @pytest.mark.asyncio
    async def test_get_failed_assets_missing_simulation(self, clean_state):
        """Failed asset queries with an unknown simulation should return an error."""
        result = await get_failed_assets_tool({"simulation_id": "missing"})

        assert "error" in result
        assert "not found" in result["error"].lower()


class TestApplyScenarioToSystem:
    """Test the apply_scenario_to_system tool."""

    @pytest.mark.asyncio
    async def test_apply_scenario_to_system(self, clean_state, tmp_path, gdm_system):
        """Applying a scenario to a distribution system should write an updated JSON."""
        from gdm.distribution.components import DistributionBus
        from geopy.distance import distance as geodist
        from infrasys.quantities import Distance
        from shapely.geometry import Point

        from erad.models.hazard.wind import WindModel
        from erad.quantities import Pressure, Speed
        from erad.systems.asset_system import AssetSystem
        from erad.systems.hazard_system import HazardSystem

        # Persist the original distribution system
        system_path = tmp_path / "system.json"
        gdm_system.to_json(system_path)

        # Build an asset system from the GDM model
        asset_system = AssetSystem.from_gdm(gdm_system)
        asset_system_id = state.generate_id()
        state.asset_systems[asset_system_id] = asset_system

        # Build a strong storm offset from the feeder so every asset sees
        # hurricane-force winds and fails (survival well below the threshold)
        buses = list(gdm_system.get_components(DistributionBus))
        cx = sum(b.coordinate.x for b in buses) / len(buses)
        cy = sum(b.coordinate.y for b in buses) / len(buses)
        storm_center = geodist(miles=3).destination((cy, cx), bearing=270)

        hazard_system = HazardSystem(auto_add_composed_components=True)
        hazard_system.add_component(
            WindModel(
                name="storm",
                timestamp=datetime.now(),
                center=Point(storm_center.longitude, storm_center.latitude),
                max_wind_speed=Speed(200, "miles/hour"),
                air_pressure=Pressure(1013.25, "hPa"),
                radius_of_max_wind=Distance(5, "miles"),
                radius_of_closest_isobar=Distance(100, "miles"),
            )
        )
        hazard_system_id = state.generate_id()
        state.hazard_systems[hazard_system_id] = hazard_system

        # Run the simulation and generate scenarios
        sim_result = await run_simulation_tool(
            {
                "asset_system_id": asset_system_id,
                "hazard_system_id": hazard_system_id,
            }
        )
        assert sim_result["success"] is True, sim_result
        simulation_id = sim_result["simulation_id"]

        scenarios_result = await generate_scenarios_tool(
            {"simulation_id": simulation_id, "num_samples": 2, "seed": 42}
        )
        assert scenarios_result["success"] is True, scenarios_result
        scenario_name = next(iter(scenarios_result["scenarios"]))

        # Apply the first scenario to the system
        output_path = tmp_path / "updated_system.json"
        result = await apply_scenario_to_system_tool(
            {
                "system_path": str(system_path),
                "simulation_id": simulation_id,
                "scenario_name": scenario_name,
                "output_path": str(output_path),
            }
        )

        assert result["success"] is True, result
        assert result["output_path"] == str(output_path)
        assert result["applied_change_count"] > 0
        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # The updated system should round-trip and be a valid DistributionSystem
        from gdm.distribution import DistributionSystem as GDM_DistributionSystem

        updated = GDM_DistributionSystem.from_json(output_path)
        assert updated is not None

    @pytest.mark.asyncio
    async def test_apply_scenario_missing_simulation(self, clean_state, tmp_path):
        """Applying a scenario with an unknown simulation should return an error."""
        system_path = tmp_path / "system.json"
        system_path.write_text("{}")

        result = await apply_scenario_to_system_tool(
            {
                "system_path": str(system_path),
                "simulation_id": "missing",
                "output_path": str(tmp_path / "out.json"),
            }
        )

        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_apply_scenario_unknown_name(self, clean_state, tmp_path, gdm_system):
        """Applying a nonexistent scenario name should return an error."""
        from erad.systems.asset_system import AssetSystem

        system_path = tmp_path / "system.json"
        gdm_system.to_json(system_path)

        asset_system = AssetSystem.from_gdm(gdm_system)
        asset_system_id = state.generate_id()
        state.asset_systems[asset_system_id] = asset_system

        from erad.systems.hazard_system import HazardSystem

        hazard_system = HazardSystem.wind_example()
        hazard_system_id = state.generate_id()
        state.hazard_systems[hazard_system_id] = hazard_system

        sim_result = await run_simulation_tool(
            {
                "asset_system_id": asset_system_id,
                "hazard_system_id": hazard_system_id,
            }
        )
        assert sim_result["success"] is True, sim_result
        simulation_id = sim_result["simulation_id"]

        scenarios_result = await generate_scenarios_tool(
            {"simulation_id": simulation_id, "num_samples": 2, "seed": 42}
        )
        assert scenarios_result["success"] is True, scenarios_result

        result = await apply_scenario_to_system_tool(
            {
                "system_path": str(system_path),
                "simulation_id": simulation_id,
                "scenario_name": "does_not_exist",
                "output_path": str(tmp_path / "out.json"),
            }
        )

        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
