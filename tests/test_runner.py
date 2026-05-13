from erad.models.asset import Asset
from erad.runner import HazardSimulator
from erad.systems.asset_system import AssetSystem
from erad.systems.hazard_system import HazardSystem


def get_asset_system() -> AssetSystem:
    asset = Asset.example()
    asset_system = AssetSystem(auto_add_composed_components=True)
    asset_system.add_component(asset.example())
    return asset_system


def test_earthquake_simulation(tmp_path):
    hazard_scenario = HazardSimulator(asset_system=get_asset_system())
    hazard_scenario.run(hazard_system=HazardSystem.earthquake_example())
    hazard_scenario.asset_system.export_results(tmp_path / "test_earthquake_simulation.db")
    assert (tmp_path / "test_earthquake_simulation.db").exists()


def test_fire_simulation(tmp_path):
    hazard_scenario = HazardSimulator(asset_system=get_asset_system())
    hazard_scenario.run(hazard_system=HazardSystem.fire_example())
    hazard_scenario.asset_system.export_results(tmp_path / "test_fire_simulation.db")
    assert (tmp_path / "test_fire_simulation.db").exists()


def test_wind_simulation(tmp_path):
    hazard_scenario = HazardSimulator(asset_system=get_asset_system())
    hazard_scenario.run(hazard_system=HazardSystem.wind_example())
    hazard_scenario.asset_system.export_results(tmp_path / "test_wind_simulation.db")
    assert (tmp_path / "test_wind_simulation.db").exists()


def test_flood_simulation(tmp_path):
    hazard_scenario = HazardSimulator(asset_system=get_asset_system())
    hazard_scenario.run(hazard_system=HazardSystem.flood_example())
    hazard_scenario.asset_system.export_results(tmp_path / "test_flood_simulation.db")
    assert (tmp_path / "test_flood_simulation.db").exists()
