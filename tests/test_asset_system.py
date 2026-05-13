from infrasys import Component

from gdm.distribution.distribution_system import DistributionSystem
import pytest

from erad.systems.asset_system import AssetSystem
from erad.constants import ASSET_TYPES


def test_component_addition():
    h = AssetSystem(auto_add_composed_components=True)
    for m in ASSET_TYPES:
        h.add_component(m.example())


def test_component_failure():
    class Testing(Component):
        ...

    test = Testing(name="asdf")

    h = AssetSystem(auto_add_composed_components=True)
    with pytest.raises(AssertionError):
        h.add_component(test)


def test_from_gdm(gdm_system: DistributionSystem):
    asset_system = AssetSystem.from_gdm(gdm_system)
    asset_system.info()


def test_serialization_deserialization(tmp_path):
    h = AssetSystem(auto_add_composed_components=True)
    for m in ASSET_TYPES:
        h.add_component(m.example())
    h.to_json(tmp_path / "asset_system.json")
    AssetSystem.from_json(tmp_path / "asset_system.json")


def test_plot(gdm_system_2: DistributionSystem):
    asset_system = AssetSystem.from_gdm(gdm_system_2)
    asset_system.plot()
