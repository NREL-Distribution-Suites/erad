from datetime import datetime

from gdm.distribution.components.distribution_bus import DistributionBus
from gdm.distribution.distribution_system import DistributionSystem
from gdm.quantities import Distance
from shapely.geometry import Point

from erad.systems.hazard_system import HazardSystem
from erad.models.hazard import EarthQuakeModel
from erad.runner import HazardSimulator


def test_gdm_model_earthquake(gdm_system: DistributionSystem):
    hazard_scenario = HazardSimulator.from_gdm(gdm_system)
    buses: list[DistributionBus] = list(gdm_system.get_components(DistributionBus))
    buses = sorted(buses, key=lambda b: b.name)
    earthquake = EarthQuakeModel(
        name="earthquake_1",
        timestamp=datetime.now(),
        origin=Point(buses[0].coordinate.y, buses[0].coordinate.x),
        depth=Distance(100, "kilometer"),
        magnitude=5.8,
    )
    hazard_system = HazardSystem(auto_add_composed_components=True)
    hazard_system.add_component(earthquake)
    hazard_scenario.run(hazard_system)


def test_asset_graph_undirected(gdm_system: DistributionSystem):
    dist_graph = gdm_system.get_undirected_graph()
    hazard_scenario = HazardSimulator.from_gdm(gdm_system)
    graph = hazard_scenario.asset_system.get_undirected_graph()
    assert (
        dist_graph.number_of_edges() == graph.number_of_edges()
    ), f"The number of edges in the asset graph ({graph.number_of_edges()}) should match the distribution system graph ({dist_graph.number_of_edges()})."
    assert (
        dist_graph.number_of_nodes() == graph.number_of_nodes()
    ), f"The number of nodes in the asset graph ({graph.number_of_nodes()}) should match the distribution system graph. ({dist_graph.number_of_nodes()})"


def test_asset_graph_directed(gdm_system: DistributionSystem):
    dist_graph = gdm_system.get_directed_graph()
    hazard_scenario = HazardSimulator.from_gdm(gdm_system)
    graph = hazard_scenario.asset_system.get_dircted_graph()

    assert (
        dist_graph.number_of_edges() == graph.number_of_edges()
    ), f"The number of edges in the asset graph ({graph.number_of_edges()}) should match the distribution system graph ({dist_graph.number_of_edges()})."
    assert (
        dist_graph.number_of_nodes() == graph.number_of_nodes()
    ), f"The number of nodes in the asset graph ({graph.number_of_nodes()}) should match the distribution system graph. ({dist_graph.number_of_nodes()})"
