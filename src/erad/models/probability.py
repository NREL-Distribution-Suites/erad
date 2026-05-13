from typing import Annotated

from gdm.quantities import Distance
from infrasys import Component
from pydantic import Field
from abc import ABC

from erad.quantities import Speed, Acceleration, Temperature, Flow, Ratio


class BaseProbabilityModel(Component, ABC):
    name: str = ""
    survival_probability: Annotated[
        float,
        Field(1.0, ge=0, le=1, description="Asset survival probability"),
    ]


class SpeedProbability(BaseProbabilityModel):
    speed: Annotated[
        Speed,
        Field(
            ...,
            description="Represents the speed of a scenario parameter experienced by the asset e.g speed of wind",
        ),
    ]

    @classmethod
    def example(cls) -> "SpeedProbability":
        return SpeedProbability(
            speed=Speed(50, "m/s"),
            survival_probability=1.0,
        )


class TemperatureProbability(BaseProbabilityModel):
    temperature: Annotated[
        Temperature,
        Field(..., description="Temperature of the asset"),
    ]

    @classmethod
    def example(cls) -> "TemperatureProbability":
        return TemperatureProbability(
            temperature=Temperature(0, "degC"),
            survival_probability=1.0,
        )


class DistanceProbability(BaseProbabilityModel):
    distance: Annotated[
        Distance,
        Field(
            Distance(-9999, "m"),
            description="Distance of asset from the source / boundary of a disaster event",
        ),
    ]

    @classmethod
    def example(cls) -> "DistanceProbability":
        return DistanceProbability(
            distance=Distance(0, "m"),
            survival_probability=1.0,
        )


class AccelerationProbability(BaseProbabilityModel):
    name: str = ""
    acceleration: Acceleration = Acceleration(0, "m/s**2")

    @classmethod
    def example(cls) -> "AccelerationProbability":
        return AccelerationProbability(
            acceleration=Acceleration(0, "m/s**2"),
            survival_probability=1.0,
        )


class FlowProbability(BaseProbabilityModel):
    flow: Annotated[
        Flow,
        Field(
            ...,
            description="Flow rate experienced by the asset e.g. streamflow, runoff discharge",
        ),
    ]

    @classmethod
    def example(cls) -> "FlowProbability":
        return FlowProbability(
            flow=Flow(0, "feet**3/second"),
            survival_probability=1.0,
        )


class RatioProbability(BaseProbabilityModel):
    ratio: Annotated[
        Ratio,
        Field(
            ...,
            description="Dimensionless ratio e.g. soil saturation fraction",
        ),
    ]

    @classmethod
    def example(cls) -> "RatioProbability":
        return RatioProbability(
            ratio=Ratio(0, "percent"),
            survival_probability=1.0,
        )
