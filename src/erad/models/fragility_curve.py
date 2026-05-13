from functools import cached_property
from typing import Literal
from pathlib import Path

from infrasys import Component, BaseQuantity
from scipy.stats import _continuous_distns
from pydantic import field_validator
import plotly.express as px
import numpy as np

from erad.probability_builder import ProbabilityFunctionBuilder
from erad.models.asset import AssetState
from erad.enums import AssetTypes
from erad.quantities import Speed
from erad.models.custom_distributions import CUSTOM_DISTRIBUTIONS


FRAGILITY_CURVE_TYPES = [
    fc for fc in AssetState.model_fields if fc not in ["name", "uuid", "timestamp"]
]
SUPPORTED_CONT_DIST = [name for name in dir(_continuous_distns) if not name.startswith("_")]


class ProbabilityFunction(Component):
    name: str = ""
    distribution: str
    parameters: list[float | BaseQuantity]

    @field_validator("distribution")
    def validate_distribution(cls, value):
        if isinstance(value, str):
            if value not in SUPPORTED_CONT_DIST and value not in CUSTOM_DISTRIBUTIONS:
                raise ValueError(f"Unsupported distribution: {value}")
        return value

    @field_validator("parameters")
    def validate_parameters(cls, value, info):
        if not any(isinstance(v, BaseQuantity) for v in value):
            raise ValueError("There should be atleast one BaseQuantity in the parameters")

        distribution = info.data.get("distribution")
        if distribution in SUPPORTED_CONT_DIST:
            units = set([v.units for v in value if isinstance(v, BaseQuantity)])
            if len(units) > 1:
                raise ValueError("All BaseQuantities should have the same units")
        return value

    @cached_property
    def prob_model(self) -> ProbabilityFunctionBuilder:
        return ProbabilityFunctionBuilder(self.distribution, self.parameters)

    @classmethod
    def example(cls) -> "ProbabilityFunction":
        """Example for a scipy distribution."""
        return ProbabilityFunction(
            distribution="norm",
            parameters=[Speed(1.5, "m/s"), 2],
        )


class FragilityCurve(Component):
    name: str = ""
    asset_type: AssetTypes
    prob_function: ProbabilityFunction

    @classmethod
    def example(cls) -> "FragilityCurve":
        """Example for a fragility curve with a scipy distribution."""
        return FragilityCurve(
            asset_type=AssetTypes.substation,
            prob_function=ProbabilityFunction.example(),
        )


class HazardFragilityCurves(Component):
    name: str = "DEFAULT_CURVES"
    asset_state_param: Literal[*FRAGILITY_CURVE_TYPES]
    curves: list[FragilityCurve]

    @classmethod
    def example(cls) -> "HazardFragilityCurves":
        return HazardFragilityCurves(
            asset_state_param="peak_ground_acceleration",
            curves=[FragilityCurve.example()],
        )

    def plot(
        self,
        file_path: Path | None = None,
        x_min: float = 0,
        x_max: float = 4,
        number_of_points: int = 100,
    ):
        """Plot the fragility curves."""
        if file_path is not None:
            file_path = Path(file_path)
            assert file_path.suffix.lower() == ".html", "File path should be an HTML file"

        if not self.curves:
            raise ValueError("No curves to plot")

        quantities = [
            p for p in self.curves[0].prob_function.parameters if isinstance(p, BaseQuantity)
        ]

        x_label = self.asset_state_param.replace("_", " ").title()
        x = np.linspace(x_min, x_max, number_of_points)

        plot_data = {"x": [], "y": [], "Asset Type": []}

        for curve in self.curves:
            model_class = quantities[0].__class__
            units = quantities[0].units
            prob_model = curve.prob_function.prob_model
            y = prob_model.probability(model_class(x, units))
            label = curve.asset_type.name.replace("_", " ").title()

            plot_data["x"].extend(x)
            plot_data["y"].extend(y)
            plot_data["Asset Type"].extend([label] * len(x))

        fig = px.line(
            plot_data,
            x="x",
            y="y",
            color="Asset Type",
            labels={"x": f"{x_label} [{units}]", "y": "Probability of Failure"},
            title=f"Fragility Curves for {x_label}",
        )

        fig.show()
        if file_path:
            fig.write_html(file_path)

        return fig
