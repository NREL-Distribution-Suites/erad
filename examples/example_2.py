from random import random, choice
from datetime import datetime
from uuid import uuid4

from infrasys.quantities import Distance
from shapely import Point

from erad.systems import AssetSystem, HazardSystem
from erad.runner import HazardScenarioGenerator
from erad.models.hazard import EarthQuakeModel
from erad.models.asset import Asset
from erad.enums import AssetTypes


asset_system = AssetSystem(auto_add_composed_components=True)
for i in range(100):
    asset = Asset(
        name=f"asset_{i}",
        asset_type=choice(list(AssetTypes)),
        distribution_asset=uuid4(),
        height=Distance(int(random() * 20), "m"),
        latitude=(28.30551 - 28.29454) * random() + 28.29454,
        longitude=(-97.26956 - (-97.28051)) * random() + (-97.28051),
        asset_state=[],
    )
    asset_system.add_component(asset)

asset_system.export_results("pre_simulation_run_example_2.db")

earthquake = EarthQuakeModel(
    name="earthquake_1",
    timestamp=datetime.now(),
    origin=Point((-97.26956 - 97.28051) / 2, (28.30551 + 28.29454) / 2),
    depth=Distance(100, "km"),
    magnitude=8.0,
)
# Setting up the hazard system and adding the hurricane components
hazard = HazardSystem(auto_add_composed_components=True)
hazard.add_component(earthquake)
# Creating a scenario generator for the asset and hazard system
simulator = HazardScenarioGenerator(asset_system, hazard)
# Export results to a database file
asset_system.export_results("post_simulation_run_example_2.db")
# Plotting the results
hazard.plot()
asset_system.plot()
# Sampling the state of the assets after the simulation (Bernoulli sampling based on survival probability)
tracked_changes = simulator.samples(number_of_samples=3, seed=42)
# Tracked changes can now be applied to the base GDM model to get an updated GDM model. (see GDM documentation for more details)
