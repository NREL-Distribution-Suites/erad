from datetime import datetime
from typing import Literal
from uuid import UUID

from gdm.distribution import DistributionSystem
from loguru import logger
import numpy as np

from gdm.tracked_changes import (
    TrackedChange,
    PropertyEdit,
)

from erad.default_fragility_curves import DEFAULT_FRAGILITY_CURVES
from erad.models.fragility_curve import HazardFragilityCurves
from erad.systems.hazard_system import HazardSystem
from erad.systems.asset_system import AssetSystem
from erad.constants import HAZARD_TYPES
from erad.models.asset import Asset


class HazardSimulator:
    def __init__(self, asset_system: AssetSystem, engine: Literal["duckdb", "legacy"] = "duckdb"):
        self._asset_system = asset_system
        self._asset_system.auto_add_composed_components = True
        self.assets: list[Asset] = list(asset_system.get_components(Asset))
        self._engine_mode = engine
        self._engine = None

    @classmethod
    def from_gdm(
        cls, dist_system: DistributionSystem, engine: Literal["duckdb", "legacy"] = "duckdb"
    ) -> "HazardSimulator":
        """Create a HazardSimulator from a DistributionSystem."""
        asset_system = AssetSystem.from_gdm(dist_system)
        return cls(asset_system, engine=engine)

    @property
    def asset_system(self) -> AssetSystem:
        """Get the AssetSystem."""
        return self._asset_system

    @property
    def engine(self):
        """Access the DuckDB simulation engine (None if using legacy mode)."""
        return self._engine

    def _get_time_stamps(self) -> list[datetime]:
        timestamps = []
        for model_type in HAZARD_TYPES:
            for model in self.hazard_system.get_components(model_type):
                timestamps.append(model.timestamp)
        return sorted(timestamps)

    def run(
        self, hazard_system: HazardSystem, curve_set: str = "DEFAULT_CURVES", hydrate: bool = True
    ):
        probability_models = list(
            hazard_system.get_components(
                HazardFragilityCurves, filter_func=lambda x: x.name == curve_set
            )
        )

        if not probability_models:
            logger.warning(
                "No HazardFragilityCurves definitions found in the passed HazardSystem, using default curve definitions"
            )
            probability_models = DEFAULT_FRAGILITY_CURVES

        self.hazard_system = hazard_system
        self.timestamps = self._get_time_stamps()

        if self._engine_mode == "duckdb":
            self._run_duckdb(hazard_system, probability_models, hydrate=hydrate)
        else:
            self._run_legacy(probability_models)

    def _run_duckdb(self, hazard_system: HazardSystem, probability_models, hydrate: bool = True):
        """Run simulation using the DuckDB vectorized engine."""
        from erad.engine import SimulationEngine
        import erad.models.hazard as hz

        logger.info(f"Running DuckDB engine with {len(self.assets)} assets")

        self._engine = SimulationEngine()

        # Only compute elevation if flood models exist (expensive pyhigh call)
        has_flood = any(True for _ in hazard_system.get_components(hz.FloodModel))
        self._engine.load_assets(self.assets, compute_elevation=has_flood)
        self._engine.load_hazards(hazard_system)
        self._engine.load_fragility_curves(probability_models)
        self._engine.run()

        # Hydrate results back into Asset objects for API compatibility
        # Skip hydration for scale workloads — use engine.export_*() instead
        if hydrate:
            self._hydrate_results()

    def _hydrate_results(self):
        """Populate Asset.asset_state from DuckDB results for backward compatibility."""
        from infrasys.quantities import Distance

        from erad.models.asset import AssetState
        from erad.models.probability import (
            AccelerationProbability,
            DistanceProbability,
            SpeedProbability,
        )
        from erad.quantities import Acceleration, Speed

        results = self._engine.connection.execute(
            """
            SELECT
                s.asset_id, s.timestamp,
                s.wind_speed_mph, s.flood_depth_m, s.flood_velocity_mps,
                s.fire_distance_km, s.pgv_cms, s.pga_fraction_g,
                s.wind_speed_surv, s.flood_depth_surv, s.flood_velocity_surv,
                s.fire_distance_surv, s.pgv_surv, s.pga_surv
            FROM asset_states s
            ORDER BY s.asset_id, s.timestamp
        """
        ).fetchall()

        # Build lookup: asset_id → list of state rows
        from collections import defaultdict

        states_by_asset = defaultdict(list)
        for row in results:
            states_by_asset[row[0]].append(row)

        # Populate each asset's asset_state list
        for asset in self.assets:
            asset_id = str(asset.distribution_asset)
            rows = states_by_asset.get(asset_id, [])

            for row in rows:
                (
                    _,
                    timestamp,
                    wind_mph,
                    flood_depth_m,
                    flood_vel_mps,
                    fire_dist_km,
                    pgv_cms,
                    pga_g,
                    wind_surv,
                    flood_depth_surv,
                    flood_vel_surv,
                    fire_surv,
                    pgv_surv,
                    pga_surv,
                ) = row

                state = AssetState(timestamp=timestamp)

                if wind_mph is not None:
                    state.wind_speed = SpeedProbability(
                        speed=Speed(wind_mph, "miles/hour"),
                        survival_probability=wind_surv,
                    )
                if flood_depth_m is not None:
                    state.flood_depth = DistanceProbability(
                        distance=Distance(flood_depth_m, "meter"),
                        survival_probability=flood_depth_surv,
                    )
                if flood_vel_mps is not None:
                    state.flood_velocity = SpeedProbability(
                        speed=Speed(flood_vel_mps, "meter/second"),
                        survival_probability=flood_vel_surv,
                    )
                if fire_dist_km is not None:
                    state.fire_boundary_dist = DistanceProbability(
                        distance=Distance(fire_dist_km, "kilometer"),
                        survival_probability=fire_surv,
                    )
                if pgv_cms is not None:
                    state.peak_ground_velocity = SpeedProbability(
                        speed=Speed(pgv_cms, "centimeter/second"),
                        survival_probability=pgv_surv,
                    )
                if pga_g is not None:
                    state.peak_ground_acceleration = AccelerationProbability(
                        acceleration=Acceleration(pga_g / 100.0 * 9.80665, "meter/second**2"),
                        survival_probability=pga_surv,
                    )

                asset.asset_state.append(state)
                if not self._asset_system.has_component(state):
                    self._asset_system.add_component(state)

    def _run_legacy(self, probability_models):
        """Run simulation using the original loop-based approach."""
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
        engine: Literal["duckdb", "legacy"] = "duckdb",
    ):
        self.assets = list(asset_system.get_components(Asset))
        self.hazard_simulator = HazardSimulator(asset_system, engine=engine)
        self.hazard_simulator.run(hazard_system, curve_set)
        self._engine_mode = engine

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

    def _sample_duckdb(self, scenario_name: str) -> list[TrackedChange]:
        """Generate a single sample using the DuckDB engine's scenario generator."""
        engine = self.hazard_simulator.engine
        if engine is None:
            return self._sample(scenario_name)

        failures = engine.generate_scenarios(n_samples=1, seed=None)
        tracked_changes = []
        for failure in failures:
            tracked_changes.append(
                TrackedChange(
                    scenario_name=scenario_name,
                    timestamp=failure["timestamp"],
                    edits=[
                        PropertyEdit(
                            component_uuid=UUID(failure["asset_id"]),
                            name="in_service",
                            value=False,
                        )
                    ],
                )
            )
        return tracked_changes

    def samples(self, number_of_samples: int = 1, seed: int = 0) -> list[TrackedChange]:
        if number_of_samples < 1:
            raise ValueError("number_of_samples should be a positive integer")

        # Use DuckDB fast path for scenario generation when engine is available
        if self._engine_mode == "duckdb" and self.hazard_simulator.engine is not None:
            from erad.engine.scenario import generate_scenarios_fast, generate_scenarios

            engine = self.hazard_simulator.engine
            n_assets = engine.get_asset_count()

            if n_assets > 50_000:
                failures = generate_scenarios_fast(engine.connection, number_of_samples, seed)
            else:
                failures = generate_scenarios(engine.connection, number_of_samples, seed)

            tracked_changes = []
            for failure in failures:
                tracked_changes.append(
                    TrackedChange(
                        scenario_name=failure["scenario_name"],
                        timestamp=failure["timestamp"],
                        edits=[
                            PropertyEdit(
                                component_uuid=UUID(failure["asset_id"]),
                                name="in_service",
                                value=False,
                            )
                        ],
                    )
                )
            return tracked_changes

        # Legacy path
        np.random.seed(seed)
        tracked_changes = []
        for i in range(number_of_samples):
            logger.info(f"Generating sample {i+1}/{number_of_samples}")
            scenario_name = f"sample_{i}"
            tracked_changes.extend(self._sample(scenario_name))
        return tracked_changes
