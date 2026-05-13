"""Module for managing constants in ERAD package.

_Do not change this constants in your code._
"""

from datetime import datetime
from pathlib import Path

import elevation

import erad.models.fragility_curve as frag
import erad.models.probability as prob
import erad.models.hazard as hazard
import erad.models.asset as asset

from erad.enums import AssetTypes

# Get list of continuous distributions

RASTER_DOWNLOAD_PATH = Path(elevation.CACHE_DIR) / "SRTM1" / "raster.tif"
ROOT_PATH = Path(__file__).parent.parent.parent
TEST_PATH = Path(__file__).parent.parent.parent / "tests"
DATA_FOLDER_NAME = "data"
DATA_FOLDER = TEST_PATH / DATA_FOLDER_NAME

DEFAULT_TIME_STAMP = datetime(1970, 1, 1, 0, 0, 0)

DEFAULT_HEIGHTS_M = {
    AssetTypes.substation: 0.0,
    AssetTypes.solar_panels: 3.0,
    AssetTypes.distribution_underground_cables: -1.0,
    AssetTypes.transmission_underground_cables: -1.0,
    AssetTypes.battery_storage: 1.0,
    AssetTypes.transmission_tower: 0.0,
    AssetTypes.distribution_poles: 0.0,
    AssetTypes.transmission_overhead_lines: 30.0,
    AssetTypes.distribution_overhead_lines: 0.0,
    AssetTypes.transformer_mad_mount: 0.3,
    AssetTypes.transformer_pole_mount: 4.0,
    AssetTypes.transmission_junction_box: -1.0,
    AssetTypes.distribution_junction_box: -1.0,
    AssetTypes.switch: 4.0,
}

ASSET_TYPES = (
    asset.AssetState,
    asset.Asset,
    prob.AccelerationProbability,
    prob.TemperatureProbability,
    prob.DistanceProbability,
    prob.SpeedProbability,
    prob.FlowProbability,
    prob.RatioProbability,
)

HAZARD_TYPES = (
    hazard.EarthQuakeModel,
    hazard.FloodModel,
    hazard.FireModel,
    hazard.WindModel,
)

HAZARD_MODELS = (
    hazard.EarthQuakeModel,
    hazard.FloodModelArea,
    hazard.FireModelArea,
    hazard.FloodModel,
    hazard.FireModel,
    hazard.WindModel,
    frag.ProbabilityFunction,
    frag.FragilityCurve,
    frag.HazardFragilityCurves,
)

SUPPORTED_MODELS = [
    hazard.EarthQuakeModel,
    hazard.FloodModelArea,
    hazard.FireModelArea,
    hazard.FloodModel,
    hazard.FireModel,
    hazard.WindModel,
    prob.AccelerationProbability,
    prob.TemperatureProbability,
    prob.DistanceProbability,
    prob.SpeedProbability,
    prob.FlowProbability,
    prob.RatioProbability,
    frag.ProbabilityFunction,
    frag.FragilityCurve,
    frag.HazardFragilityCurves,
    asset.AssetState,
    asset.Asset,
]
