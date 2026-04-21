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
# root_path = "/Users/mmuralid/Documents/naerm2025/texas/gdm_timeseries_models/"
# region = "P49U"
# dir_path = Path(root_path) / region / "geometry_models/"

# # Iterate through all .json files in the directory
# for file_path in dir_path.glob("*.json"):
# find of form 
base_file_path = "/Users/mmuralid/Documents/naerm2025/texas/gdm_timeseries_models/P49U/geometry_models/p49uhs11_1247_base_sys.json"
base_system = DistributionSystem.from_json(base_file_path)
base_asset_system = AssetSystem.from_gdm(base_system)

mod_file_path = "/Users/mmuralid/Documents/naerm2025/texas/gdm_timeseries_models/P49U/geometry_models/p49uhs11_1247_mod_sys.json"
modified_system = DistributionSystem.from_json(mod_file_path)
modified_asset_system = AssetSystem.from_gdm(modified_system)

# Check if total asset count is same in both models
total_assets_base = len(list(base_asset_system.get_components(Asset)))
total_assets_modified = len(list(modified_asset_system.get_components(Asset)))
print(f"Total assets in Base Model: {total_assets_base}")
print(f"Total assets in Modified Model: {total_assets_modified}")
breakpoint()

#### Getting error about UUID ####
# infrasys.exceptions.ISNotStored: No component with uuid=UUID('1e7fbf4e-ad18-4970-aa63-211f38ec2c42') is stored