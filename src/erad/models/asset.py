from datetime import datetime
from uuid import UUID
import math
from pydantic import computed_field, Field, field_validator
from infrasys.quantities import Distance
from geopy.distance import geodesic
from shapely.geometry import Point
from pyhigh import get_elevation
from infrasys import Component
from loguru import logger
from typing import Literal
from types import SimpleNamespace

from erad.probability_builder import ProbabilityFunctionBuilder
from erad.models.custom_distributions import CUSTOM_DISTRIBUTIONS
from erad.quantities import Acceleration, Speed
from erad.models.probability import (
    AccelerationProbability,
    DistanceProbability,
    FlowProbability,
    RatioProbability,
    SpeedProbability,
)
from erad.enums import AssetTypes, PoleClass, PoleConstructionMaterial
from erad.quantities import WindAngle, ConductorArea, PoleAge
import erad.models.hazard as hz


class AssetState(Component):
    name: str = ""
    timestamp: datetime
    wind_speed: SpeedProbability | None = None
    flood_velocity: SpeedProbability | None = None
    flood_depth: DistanceProbability | None = None
    fire_boundary_dist: DistanceProbability | None = None
    peak_ground_velocity: SpeedProbability | None = None
    peak_ground_acceleration: AccelerationProbability | None = None
    soil_saturation: RatioProbability | None = None
    snow_water_equivalent: DistanceProbability | None = None
    runoff_volume: FlowProbability | None = None
    groundwater_flow: FlowProbability | None = None

    def calculate_earthquake_vectors(
        self, asset_coordinate: Point, hazard_model: hz.EarthQuakeModel
    ):
        """
        Sources:

        Atkinson, G.M., & Wald, D.J. (2007). “Did You Feel It?” intensity data: A surprisingly good
        measure of earthquake ground motion. Seismological Research Letters, 78(3), 362–368.
        """

        epicenter_distance = Distance(
            geodesic(
                (hazard_model.origin.y, hazard_model.origin.x),
                (asset_coordinate.y, asset_coordinate.x),
            ).km,
            "km",
        )

        hypocentral_distance = (hazard_model.depth**2 + epicenter_distance**2) ** 0.5

        mmi = (
            3.31
            + 1.28 * hazard_model.magnitude
            - 1.42 * math.log10(hypocentral_distance.to("km").magnitude)
        )  # Modified Mercalli Intensity

        log_pgv = (mmi - 3.78) / 1.47
        pgv = 10**log_pgv  # cm/s
        self.peak_ground_velocity = SpeedProbability(
            speed=Speed(pgv, "centimeter/second"),
            survival_probability=1,
        )

        log_pga = (mmi - 1.78) / 3.70
        pga_per_g = 10**log_pga  # % of g
        self.peak_ground_acceleration = AccelerationProbability(
            acceleration=Acceleration(pga_per_g / 100.0 * 9.80665, "meter/second**2"),
            survival_probability=1,
        )

    def calculate_fire_vectors(self, asset_coordinate: Point, hazard_model: hz.FireModel):
        """
        Sources:

        “Integrating Wildfire Risk Modeling with Electric Grid Asset Management” (EPRI)
        “Modeling and Mitigating Wildfire Risk to the Power Grid” (PNNL, 2021)
        “A Framework for Assessing Wildfire Ignition Risk on Distribution Systems”
            (IEEE Transactions on Power Systems, 2020)
        Improving Grid Safety and Resilience to Mitigate Ignition Incident and Fire Risks – EPRI
        Wildfire Risk Reduction Methods 2024 – EPRI
        """

        distances_to_wild_fire_boundaries = []
        for wild_fire_area in hazard_model.affected_areas:
            if wild_fire_area.affected_area.contains(asset_coordinate):
                distance = 0
            else:
                distance = wild_fire_area.affected_area.exterior.distance(asset_coordinate)
            distances_to_wild_fire_boundaries.append(distance)
        minimum_distance_km = min(distances_to_wild_fire_boundaries)
        self.fire_boundary_dist = DistanceProbability(
            distance=Distance(minimum_distance_km, "kilometer"),
            survival_probability=1,
        )

        # survival_probability = 1 - 0.95 * math.exp(-k * minimum_distance_km)

    def calculate_wind_vectors(self, asset_coordinate: Point, hazard_model: hz.WindModel):
        r = Distance(
            geodesic(
                (hazard_model.center.y, hazard_model.center.x),
                (asset_coordinate.y, asset_coordinate.x),
            ).km,
            "km",
        )

        r = r.to("nautical_mile")
        r_max = hazard_model.radius_of_closest_isobar.to("nautical_mile")
        r_v_max = hazard_model.radius_of_max_wind.to("nautical_mile")
        v_max = hazard_model.max_wind_speed.to("knot")

        k = 1.14
        b = 10

        a = math.log(b) / (r_max - r_v_max)
        m = (1 / r_v_max) * math.log(k / (k - 1))

        if r >= 0 and r < r_v_max:
            wind_speed = k * v_max * (1 - math.exp(-m * r))
        elif r >= r_v_max and r < r_max:
            wind_speed = v_max * math.exp(-a * (r - r_v_max))
        else:
            wind_speed = Speed(0, "knots")

        self.wind_speed = SpeedProbability(
            speed=wind_speed.to("miles/hour"),
            survival_probability=1,
        )

    def calculate_flood_vectors(
        self, asset_coordinate: Point, hazard_model: hz.FloodModel, asset_total_elevation: Distance
    ):
        for area in hazard_model.affected_areas:
            if area.affected_area.contains(asset_coordinate):
                self.flood_depth = DistanceProbability(
                    distance=area.water_elevation - asset_total_elevation,
                    survival_probability=1,
                )
                self.flood_velocity = SpeedProbability(
                    speed=area.water_velocity,
                    survival_probability=1,
                )
                if area.soil_saturation is not None:
                    self.soil_saturation = RatioProbability(
                        ratio=area.soil_saturation,
                        survival_probability=1,
                    )
                if area.snow_water_equivalent is not None:
                    self.snow_water_equivalent = DistanceProbability(
                        distance=area.snow_water_equivalent,
                        survival_probability=1,
                    )
                if area.runoff_volume is not None:
                    self.runoff_volume = FlowProbability(
                        flow=area.runoff_volume,
                        survival_probability=1,
                    )
                if area.groundwater_flow is not None:
                    self.groundwater_flow = FlowProbability(
                        flow=area.groundwater_flow,
                        survival_probability=1,
                    )

        if self.flood_depth is None and self.flood_velocity is None:
            self.flood_depth = DistanceProbability(
                distance=Distance(-9999, "meter"),
                survival_probability=1,
            )
            self.flood_velocity = SpeedProbability(
                speed=Speed(0, "meter / second"),
                survival_probability=1,
            )

    @computed_field
    @property
    def survival_probability(self) -> float:
        wind_survival_probability = self.wind_speed.survival_probability if self.wind_speed else 1
        water_flow_survival_probability = (
            self.flood_velocity.survival_probability if self.flood_velocity else 1
        )
        water_level_survivial_probability = (
            self.flood_depth.survival_probability if self.flood_depth else 1
        )
        fire_survival_probability = (
            self.fire_boundary_dist.survival_probability if self.fire_boundary_dist else 1
        )
        pgv_survival_probability = (
            self.peak_ground_velocity.survival_probability if self.peak_ground_velocity else 1
        )
        pga_survival_probability = (
            self.peak_ground_acceleration.survival_probability
            if self.peak_ground_acceleration
            else 1
        )
        soil_saturation_survival = (
            self.soil_saturation.survival_probability if self.soil_saturation else 1
        )
        swe_survival = (
            self.snow_water_equivalent.survival_probability if self.snow_water_equivalent else 1
        )
        runoff_survival = self.runoff_volume.survival_probability if self.runoff_volume else 1
        gw_flow_survival = (
            self.groundwater_flow.survival_probability if self.groundwater_flow else 1
        )

        return (
            wind_survival_probability
            * water_flow_survival_probability
            * water_level_survivial_probability
            * fire_survival_probability
            * pgv_survival_probability
            * pga_survival_probability
            * soil_saturation_survival
            * swe_survival
            * runoff_survival
            * gw_flow_survival
        )

    @classmethod
    def example(cls) -> "AssetState":
        return AssetState(
            timestamp=datetime.now(),
            wind_speed=SpeedProbability.example(),
            flood_velocity=SpeedProbability.example(),
            flood_depth=DistanceProbability.example(),
            fire_boundary_dist=DistanceProbability.example(),
            peak_ground_velocity=SpeedProbability.example(),
            peak_ground_acceleration=AccelerationProbability.example(),
        )


class Asset(Component):
    distribution_asset: UUID = Field(..., description="UUID of the distribution asset")
    connections: list[UUID] = Field([], description="List of UUIDs of connected assets")
    devices: list[UUID] = Field(
        [], description="List of UUIDs of devices associated with the asset"
    )
    asset_type: AssetTypes = Field(..., description="Type of the asset")
    height: Distance = Field(..., description="Height of the asset")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    asset_state: list[AssetState] = Field(
        ..., description="List of asset states associated with the asset"
    )
    _raster_handler: str | None = None

    @computed_field
    @property
    def elevation(self) -> Distance:
        try:
            elev = Distance(get_elevation(lat=self.latitude, lon=self.longitude), "meter")
        except Exception:
            logger.warning(
                f"Error getting elevation information for asset {self.name} with coordinates {self.latitude}, {self.longitude}. Defaulting to 999 meters"
            )
            elev = Distance(999, "meter")
        return elev

    def _get_asset_state_at_timestamp(self, timestamp: datetime) -> AssetState | None:
        for asset_state in self.asset_state:
            if asset_state.timestamp == timestamp:
                return asset_state
        return AssetState(
            timestamp=timestamp,
        )

    def update_survival_probability(
        self, time_stamp: datetime, hazard_model: hz.BaseDisasterModel, frag_curves
    ):
        asset_state = self._get_asset_state_at_timestamp(time_stamp)
        asset_location = Point(self.longitude, self.latitude)

        if isinstance(hazard_model, hz.EarthQuakeModel):
            asset_state.calculate_earthquake_vectors(asset_location, hazard_model)
        elif isinstance(hazard_model, hz.FireModel):
            asset_state.calculate_fire_vectors(asset_location, hazard_model)
        elif isinstance(hazard_model, hz.WindModel):
            asset_state.calculate_wind_vectors(asset_location, hazard_model)
        elif isinstance(hazard_model, hz.FloodModel):
            asset_state.calculate_flood_vectors(
                asset_location, hazard_model, self.elevation + self.height
            )
        else:
            raise Exception(f"Unsupported hazard type {hazard_model.__class__.__name__}")

        self.calculate_probabilities(asset_state, frag_curves)
        if asset_state not in self.asset_state:
            self.asset_state.append(asset_state)
        return asset_state

    def calculate_probabilities(self, asset_state: AssetState, frag_curves):
        fields = [
            model_field
            for model_field in list(asset_state.model_fields.keys())
            if model_field not in ["uuid", "name", "timestamp"]
        ]
        for field in fields:
            prob_model = getattr(asset_state, field)
            if prob_model and prob_model.survival_probability == 1:
                curve = self.get_valid_curve(frag_curves, field)
                if curve is None:
                    raise Exception(
                        f"No fragility curve found for field - {field} for asset type {self.asset_type.name}"
                    )
                prob_inst = curve.prob_model
                quantity_name = [
                    model_field
                    for model_field in list(prob_model.model_fields.keys())
                    if model_field not in ["uuid", "name", "survival_probability"]
                ][0]
                quantity = getattr(prob_model, quantity_name)
                prob_model.survival_probability = 1 - prob_inst.probability(quantity)

    def get_valid_curve(self, frag_curves, field: str):
        for frag_curve in frag_curves:
            if frag_curve.asset_state_param == field:
                for curve in frag_curve.curves:
                    if curve.asset_type == self.asset_type:
                        return curve.prob_function
        return None

    @classmethod
    def example(cls) -> "Asset":
        return Asset(
            name="Asset 1",
            asset_type=AssetTypes.distribution_poles,
            distribution_asset=UUID("123e4567-e89b-12d3-a456-426614174000"),
            height=Distance(100, "m"),
            latitude=37.7749,
            longitude=-122.4194,
            asset_state=[AssetState.example()],
        )


class DistributionPole(Asset):
    pole_class: PoleClass | None = Field(
        description="Class of the pole (only for distribution poles)"
    )
    pole_material: PoleConstructionMaterial | None = Field(
        description="Construction material of the pole (only for distribution poles)"
    )
    wind_angle: WindAngle | None = Field(
        description="Angle between wind direction and pole"
    )  # Hazard property?
    conductor_area: ConductorArea | None = Field(description="Conductor area in m^2")
    pole_age: PoleAge | None = Field(description="Age of the pole in years")
    probability_dist: Literal[*CUSTOM_DISTRIBUTIONS] | None = Field(
        description="Custom distribution function to model pole failure probability. Run list_custom_distributions() for available options."
    )

    @field_validator("asset_type")
    @classmethod
    def validate_asset_type(cls, v):
        if v != AssetTypes.distribution_poles:
            raise ValueError("Invalid asset type for DistributionPole, must be distribution_poles")
        return v

    def get_valid_curve(self, frag_curves, field: str):
        if self.probability_dist and field == "wind_speed":
            custom_dist_instance = CUSTOM_DISTRIBUTIONS[self.probability_dist](self)
            prob_builder = ProbabilityFunctionBuilder(
                dist=self.probability_dist,
                params=[Speed(0, "m/s")],  # Only to set output type
                custom_dist_instance=custom_dist_instance,
            )
            wrapper = SimpleNamespace()
            wrapper.prob_model = prob_builder
            return wrapper
        return super().get_valid_curve(frag_curves, field)

    @classmethod
    def example(cls) -> "DistributionPole":
        return DistributionPole(
            name="Asset 1",
            asset_type=AssetTypes.distribution_poles,
            distribution_asset=UUID("123e4567-e89b-12d3-a456-426614174000"),
            height=Distance(100, "m"),
            latitude=37.7749,
            longitude=-122.4194,
            asset_state=[AssetState.example()],
            pole_class=PoleClass.CLASS_5,
            pole_material=PoleConstructionMaterial.WOOD,
            wind_angle=WindAngle(90, "degree"),
            conductor_area=ConductorArea(0.0005, "m**2"),
            pole_age=PoleAge(30, "year"),
            probability_dist="Darestani2019",
        )
