from datetime import datetime

from gdm.distribution import DistributionSystem
from loguru import logger
import numpy as np

from gdm.tracked_changes import (
    TrackedChange,
    PropertyEdit,
)

from erad.default_fragility_curves import DEFAULT_FRAGILTY_CURVES
from erad.models.fragility_curve import HazardFragilityCurves
from erad.systems.hazard_system import HazardSystem
from erad.systems.asset_system import AssetSystem
from erad.constants import HAZARD_TYPES
from erad.models.asset import Asset


class HazardSimulator:
    def __init__(self, asset_system: AssetSystem):
        self._asset_system = asset_system
        self._asset_system.auto_add_composed_components = True
        self.assets: list[Asset] = list(asset_system.get_components(Asset))

    @classmethod
    def from_gdm(cls, dist_system: DistributionSystem) -> "HazardSimulator":
        """Create a HazardSimulator from a DistributionSystem."""
        asset_system = AssetSystem.from_gdm(dist_system)
        return cls(asset_system)

    @property
    def asset_system(self) -> AssetSystem:
        """Get the AssetSystem."""
        return self._asset_system

    def _get_time_stamps(self) -> list[datetime]:
        timestamps = []
        for model_type in HAZARD_TYPES:
            for model in self.hazard_system.get_components(model_type):
                timestamps.append(model.timestamp)
        return sorted(timestamps)

    def run(self, hazard_system: HazardSystem, curve_set: str = "DEFAULT_CURVES"):
        probability_models = list(
            hazard_system.get_components(
                HazardFragilityCurves, filter_func=lambda x: x.name == curve_set
            )
        )

        if not probability_models:
            logger.warning(
                "No HazardFragilityCurves definitions found in the passed HazardSystem, using default curve definitions"
            )
            probability_models = DEFAULT_FRAGILTY_CURVES

        self.hazard_system = hazard_system
        self.timestamps = self._get_time_stamps()
        for timestamp in self.timestamps:
            logger.info(f"Simulating hazard at {timestamp}")
            for hazard_type in HAZARD_TYPES:
                for hazard_model in self.hazard_system.get_components(
                    hazard_type, filter_func=lambda x: x.timestamp == timestamp
                ):
                    for asset in self.assets:
                        assset_state = asset.update_survival_probability(
                            timestamp, hazard_model, probability_models
                        )
                        if not self._asset_system.has_component(assset_state):
                            self._asset_system.add_component(assset_state)


class HazardScenarioGenerator:
    def __init__(
        self,
        asset_system: AssetSystem,
        hazard_system: HazardSystem,
        curve_set: str = "DEFAULT_CURVES",
    ):
        self.assets = list(asset_system.get_components(Asset))
        self.hazard_simulator = HazardSimulator(asset_system)
        self.hazard_simulator.run(hazard_system, curve_set)

    def _sample(self, scenario_name: str) -> list[TrackedChange]:
        outaged_assets = []
        tracked_changes = []

        n_assets = len(self.assets)
        n_timestamps = len(self.assets[0].asset_state)

        ramdom_samples = np.random.random((n_assets, n_timestamps))

        for ii, asset in enumerate(self.assets):
            for jj, state in enumerate(
                sorted(asset.asset_state, key=lambda asset_state: asset_state.timestamp)
            ):
                if (
                    ramdom_samples[ii, jj] > state.survival_probability
                    and asset.name not in outaged_assets
                ):
                    tracked_changes.append(
                        TrackedChange(
                            scenario_name=scenario_name,
                            timestamp=state.timestamp,
                            edits=[
                                PropertyEdit(
                                    component_uuid=asset.distribution_asset,
                                    name="in_service",
                                    value=False,
                                )
                            ],
                        ),
                    )
                    outaged_assets.append(asset.name)

        return tracked_changes

    def samples(self, number_of_samples: int = 1, seed: int = 0) -> list[TrackedChange]:
        if number_of_samples < 1:
            raise ValueError("number_of_samples should be a positive integer")
        np.random.seed(seed)
        tracked_changes = []
        for i in range(number_of_samples):
            logger.info(f"Generating sample {i+1}/{number_of_samples}")
            scenario_name = f"sample_{i}"
            tracked_changes.extend(self._sample(scenario_name))
        return tracked_changes
