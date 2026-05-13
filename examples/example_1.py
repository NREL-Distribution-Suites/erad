from erad.systems import AssetSystem, HazardSystem
from erad.runner import HazardScenarioGenerator
from erad.models.hazard import WindModel

from sample_gdm_model import sample_distribution_system

# assigned random cooordinates to the distribution buses in sample_gdm_model.py
system = sample_distribution_system()
# Creating a HazardSimulator from the asset system
# Note, the asset system can also be created directly using AssetSystem() and then adding add
# assets to the system using the add_component() or add_components() methods.
asset_system = AssetSystem.from_gdm(system)
# Generating a hurricane scenario (building from the ERAD database)
# Note: This requires an internet connection to download the hurricane data.
# The dataset in downloaded the first time you run ERAD.
hurricane_carla: list[WindModel] = WindModel.from_hurricane_sid("2017228N14314")
# Setting up the hazard system and adding the hurricane components
hazard = HazardSystem(auto_add_composed_components=True)
hazard.add_components(*hurricane_carla)
# Creating a scenario generator for the asset and hazard system
simulator = HazardScenarioGenerator(asset_system, hazard)
# Export results to a database file
asset_system.export_results("example_1_results.db")

# Note: After both asset and hazard system can serialized and deserialized to / from disk using the 'to_json()' and 'from_json()' methods.
# asset_system.to_json("asset_system.json")
# hazard.to_json("hazard.json")

# Plotting the results
hazard.plot()
asset_system.plot()
# Sampling the state of the assets after the simulation (Bernoulli sampling based on survival probability)
tracked_changes = simulator.samples(number_of_samples=3, seed=42)
# Tracked changes can now be applied to the base GDM model to get an updated GDM model. (see GDM documentation for more details)
