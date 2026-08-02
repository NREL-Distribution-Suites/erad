"""
Tests for the best-effort ``dist_stack.runstore`` adoption (doc 11 §1.5, erad row).

All runstore wiring is additive: when ``DIST_STACK_RUNSTORE_DB`` is unset the
MCP tools behave exactly as before (no run_id, nothing raised). When it is set,
``run_simulation`` records a ``sim_<hex12>`` run row, attaches the simulation
artifact, and downstream tools mirror the run into the runstore.
"""

from datetime import datetime
from pathlib import Path
from uuid import UUID

import pytest

from erad.mcp.state import state


@pytest.fixture
def clean_state():
    """Clean server state before each test."""
    state.clear()
    yield state
    state.clear()


@pytest.fixture
def runstore_env(tmp_path, monkeypatch):
    """Point DIST_STACK_RUNSTORE_DB at a fresh temporary DB file."""
    db_path = tmp_path / "runstore.sqlite"
    monkeypatch.setenv("DIST_STACK_RUNSTORE_DB", str(db_path))
    return db_path


async def _run_failure_simulation(output_path=None, run_id=None):
    """Build asset/hazard systems in state and run a failing simulation.

    Mirrors ``tests/test_mcp_server.py::_run_failure_simulation``: a single
    distribution pole placed 50 miles from a 150 mph hurricane eye so its
    survival probability drops below the default 0.5 threshold. Returns the
    ``run_simulation`` result dict.
    """
    from geopy.distance import distance as geodist
    from infrasys.quantities import Distance
    from shapely.geometry import Point

    from erad.mcp.simulation import run_simulation
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

    return await run_simulation(
        asset_system_id=asset_system_id,
        hazard_system_id=hazard_system_id,
        output_path=str(output_path) if output_path else None,
        run_id=run_id,
    )


@pytest.mark.asyncio
async def test_run_simulation_records_runstore_run(clean_state, runstore_env, tmp_path):
    """With the runstore env set, a simulation mints sim_<hex12> and records run + artifact."""
    from dist_stack import get_run, list_artifacts
    from dist_stack.manifest import get_manifest_path, has_manifest

    output_path = tmp_path / "simulation.json"
    result = await _run_failure_simulation(output_path=output_path)

    assert result["success"] is True, result
    run_id = result.get("run_id")
    assert run_id and run_id.startswith("sim_")

    # run_id is also mirrored into session state
    assert state.simulation_results[result["simulation_id"]]["run_id"] == run_id

    # The runs row carries the expected tool/run_type/status/payload
    run = get_run(run_id)
    assert run.tool == "run_simulation"
    assert run.run_type == "erad_simulation"
    assert run.status == "succeeded"
    assert run.payload["asset_system_id"] == state.simulation_results[result["simulation_id"]][
        "asset_system_id"
    ]
    assert run.payload["hazard_system_id"] == state.simulation_results[result["simulation_id"]][
        "hazard_system_id"
    ]
    assert run.payload["curve_set"] == "DEFAULT_CURVES"
    assert run.payload["simulation_id"] == result["simulation_id"]
    assert "timestamps" in run.payload

    # attach_artifact created an artifacts row + the manifest sidecar is present
    artifacts = list_artifacts(run_id)
    assert len(artifacts) == 1
    assert Path(artifacts[0].artifact_path) == output_path
    assert artifacts[0].artifact_type == "erad_simulation"
    assert has_manifest(output_path)
    assert get_manifest_path(output_path).exists()


@pytest.mark.asyncio
async def test_runstore_run_survives_scenario_generation_and_export(
    clean_state, runstore_env, tmp_path
):
    """generate_scenarios mirrors tracked_changes onto the run; exports attach artifacts."""
    from dist_stack import get_run, list_artifacts

    from erad.mcp.export import export_tracked_changes
    from erad.mcp.simulation import generate_scenarios

    output_path = tmp_path / "simulation.json"
    result = await _run_failure_simulation(output_path=output_path)
    assert result["success"] is True, result
    run_id = result["run_id"]

    scenarios_result = await generate_scenarios(
        simulation_id=result["simulation_id"], num_samples=2, seed=42
    )
    assert scenarios_result["success"] is True, scenarios_result

    updated = get_run(run_id)
    assert updated.payload["tracked_changes"] == scenarios_result["total_tracked_changes"]

    tracked_path = tmp_path / "tracked_changes.json"
    export_result = await export_tracked_changes(
        simulation_id=result["simulation_id"], output_path=str(tracked_path)
    )
    assert export_result["success"] is True, export_result
    assert tracked_path.exists()

    artifacts = list_artifacts(run_id)
    assert len(artifacts) == 2
    assert any(Path(a.artifact_path) == output_path for a in artifacts)
    assert any(Path(a.artifact_path) == tracked_path for a in artifacts)


@pytest.mark.asyncio
async def test_run_simulation_without_runstore_env(clean_state, monkeypatch, tmp_path):
    """With the runstore env unset, run_simulation returns no run_id and raises nothing."""
    monkeypatch.delenv("DIST_STACK_RUNSTORE_DB", raising=False)

    output_path = tmp_path / "simulation.json"
    result = await _run_failure_simulation(output_path=output_path)

    assert result["success"] is True, result
    assert "run_id" not in result
    assert state.simulation_results[result["simulation_id"]].get("run_id") is None
