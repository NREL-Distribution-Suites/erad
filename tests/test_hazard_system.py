from infrasys import Component

import pytest

from erad.systems.hazard_system import HazardSystem
from erad.models.hazard import WindModel
from erad.constants import HAZARD_MODELS


def test_component_addition():
    h = HazardSystem(auto_add_composed_components=True)
    for m in HAZARD_MODELS:
        h.add_component(m.example())


def test_component_failure():
    class Testing(Component):
        ...

    test = Testing(name="asdf")

    h = HazardSystem(auto_add_composed_components=True)
    with pytest.raises(AssertionError):
        h.add_component(test)


def test_system_serialization_deserialization(tmp_path):
    h = HazardSystem(auto_add_composed_components=True)
    for m in HAZARD_MODELS:
        h.add_component(m.example())
    h.to_json(tmp_path / "test_hazard_model.json")

    HazardSystem.from_json(tmp_path / "test_hazard_model.json")


def test_earthquake_example():
    HazardSystem.earthquake_example()


def test_fire_example():
    HazardSystem.fire_example()


def test_wind_example():
    HazardSystem.wind_example()


def test_flood_example():
    HazardSystem.flood_example()


def test_wind_plot():
    hazard = WindModel.from_hurricane_sid("2017228N14314")
    system = HazardSystem(auto_add_composed_components=True)
    system.add_components(*hazard)
    system.plot()


def test_earthquake_plot():
    system = HazardSystem.earthquake_example()
    system.plot()


def test_wildfire_plot():
    system = HazardSystem.fire_example()
    system.plot()


def test_flood_plot():
    system = HazardSystem.flood_example()
    system.plot()
