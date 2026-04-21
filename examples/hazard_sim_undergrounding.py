import pandas as pd
import numpy as np
from shapely.geometry import Point
from scipy.interpolate import interp1d

from gdm.distribution.distribution_system import DistributionSystem
from gdm.tracked_changes import PropertyEdit, TrackedChange
from gdm.quantities import Distance


from infrasys.quantities import Distance

from erad.systems import AssetSystem, HazardSystem
from erad.systems.asset_system import Asset
from erad.enums import AssetTypes
from erad.quantities import Speed, Pressure
from erad.constants import DEFAULT_HEIGHTS_M
from erad.models.hazard import WindModel
from erad.runner import HazardScenarioGenerator
import os
from pathlib import Path


############################ Load hurricane Carla data and create WindModel instances ############################

# # Load CSVs
ibtracs = pd.read_csv("/Users/mmuralid/Documents/naerm2025/carla/ibtracs_hourly.csv", parse_dates=["ISO_TIME"])
rmw = pd.read_csv("/Users/mmuralid/Documents/naerm2025/carla/rmw_nm.csv", header=None, names=["rmw_nm"], skiprows=1)
rs = pd.read_csv("/Users/mmuralid/Documents/naerm2025/carla/rs_nm.csv", header=None, names=["rs_nm"], skiprows=1)

# Convert to numeric, drop NaNs
rmw["rmw_nm"] = pd.to_numeric(rmw["rmw_nm"], errors="coerce").dropna()
rs["rs_nm"] = pd.to_numeric(rs["rs_nm"], errors="coerce").dropna()

# Interpolate RMW and RS to hourly timestamps
rmw_interp = interp1d(np.linspace(0, len(rmw)-1, len(rmw)), rmw["rmw_nm"], fill_value="extrapolate")
rs_interp  = interp1d(np.linspace(0, len(rs)-1, len(rs)), rs["rs_nm"], fill_value="extrapolate")

ibtracs["radius_of_max_wind"] = rmw_interp(np.linspace(0, len(rmw)-1, len(ibtracs)))
ibtracs["radius_of_closest_isobar"] = rs_interp(np.linspace(0, len(rs)-1, len(ibtracs)))


# Shift lon in ibtracs by 1 degree east (Carla track doesn't pass over Houston otherwise)
ibtracs["LON"] = ibtracs["LON"] + 1.95

# Convert to WindModel list
hurricane_carla = []
for _, row in ibtracs.iterrows():
    wm = WindModel(
        name=f"carla",
        timestamp=pd.to_datetime(row["ISO_TIME"]),
        center=Point(row["LON"], row["LAT"]),
        max_wind_speed=Speed(row["USA WIND"], "knots"),
        radius_of_max_wind=Distance(row["radius_of_max_wind"], "nautical_mile"),
        radius_of_closest_isobar=Distance(row["radius_of_closest_isobar"], "nautical_mile"),
        air_pressure=Pressure(row["USA PRES"], "millibar")
    )
    hurricane_carla.append(wm)
hazard = HazardSystem(auto_add_composed_components=True)
hazard.add_components(*hurricane_carla)
hazard.plot(zoom_level=5)

############################ Load GDM distribution system ############################
root_path = "/Users/mmuralid/Documents/naerm2025/texas/gdm_timeseries_models/"
region = "P49U"
dir_path = Path(root_path) / region

# # Iterate through all .json files in the directory
for file_path in dir_path.glob("*.json"):
# file_path = next(dir_path.glob("*.json")) # Test with first file only
    print("Processing file:", file_path.name)

    system = DistributionSystem.from_json(file_path)
    # system.info()

    ############################ Create Base Asset System ############################
    base_asset_system = AssetSystem.from_gdm(system)
    # base_asset_system.info()

    num_overhead_lines = 0
    num_underground_lines = 0
    num_poles = 0
    for asset in base_asset_system.get_components(Asset):
        if asset.asset_type == AssetTypes.distribution_overhead_lines:
            num_overhead_lines += 1         
        if asset.asset_type == AssetTypes.distribution_underground_cables:
            num_underground_lines += 1
        if asset.asset_type == AssetTypes.distribution_poles:
            num_poles += 1
    print(f"Number of overhead lines in base system: {num_overhead_lines}")
    print(f"Number of underground lines in base system: {num_underground_lines}")
    print(f"Number of poles in base system: {num_poles}")

    ############################ Create Modified Asset System with Undergrounded Lines ############################
    modified_asset_system = base_asset_system
    # modified_asset_system.info()

    # Change overhead to underground lines
    for asset in modified_asset_system.get_components(Asset):
        if asset.asset_type == AssetTypes.distribution_overhead_lines:
            asset.asset_type = AssetTypes.distribution_underground_cables
            asset.height = Distance(DEFAULT_HEIGHTS_M[AssetTypes.distribution_underground_cables], "meter")

    num_overhead_lines = 0
    num_underground_lines = 0
    num_poles = 0
    for asset in modified_asset_system.get_components(Asset):
        if asset.asset_type == AssetTypes.distribution_overhead_lines:
            num_overhead_lines += 1         
        if asset.asset_type == AssetTypes.distribution_underground_cables:
            num_underground_lines += 1
        if asset.asset_type == AssetTypes.distribution_poles:
            num_poles += 1
    print(f"Number of overhead lines in modified system: {num_overhead_lines}")
    print(f"Number of underground lines in modified system: {num_underground_lines}")
    print(f"Number of poles in modified system: {num_poles}")
    # breakpoint()

    # Check if total asset count is same in both models
    total_assets_base = len(list(base_asset_system.get_components(Asset)))
    total_assets_modified = len(list(modified_asset_system.get_components(Asset)))
    print(f"Total assets in Base Model: {total_assets_base}")
    print(f"Total assets in Modified Model: {total_assets_modified}")
    breakpoint()


    ############################ Run Hazard Simulation on Base Asset System ############################
    print("Creating simulator for base asset system...")
    base_simulator = HazardScenarioGenerator(hazard_system=hazard, asset_system=base_asset_system)
    base_asset_system.export_results("hazard_sim_base_model_" + str(file_path.stem) + "_results.db")

    ############################ Run Hazard Simulation on Modified Asset System ############################
    print("Creating simulator for modified asset system...")
    mod_simulator = HazardScenarioGenerator(hazard_system=hazard, asset_system=modified_asset_system)
    modified_asset_system.export_results("hazard_sim_ug_" + str(file_path.stem) + "_results.db")