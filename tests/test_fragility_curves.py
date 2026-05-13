from pydantic import ValidationError
from infrasys import BaseQuantity

from erad.models.fragility_curve import HazardFragilityCurves, FragilityCurve, ProbabilityFunction
from erad.default_fragility_curves import DEFAULT_FRAGILTY_CURVES
from erad.quantities import Speed
from erad.enums import AssetTypes

import pytest


def test_valid_hazard_fragility_model():
    HazardFragilityCurves(
        asset_state_param="peak_ground_velocity",
        curves=[
            FragilityCurve(
                asset_type=AssetTypes.battery_storage,
                prob_function=ProbabilityFunction(
                    distribution="lognorm", parameters=[Speed(35, "cm/s"), 0.5]
                ),
            ),
        ],
    )


def test_invalid_hazard_fragility_model():
    with pytest.raises(ValidationError):
        HazardFragilityCurves(
            asset_state_param="invalid_asset_model_attribute",
            curves=[
                FragilityCurve(
                    asset_type=AssetTypes.battery_storage,
                    prob_function=ProbabilityFunction(
                        distribution="not_valid_dist", parameters=[Speed(35, "cm/s"), 0.5]
                    ),
                ),
            ],
        )


@pytest.mark.parametrize("hazard_curve_set", DEFAULT_FRAGILTY_CURVES)
def test_default_hazard_curves(hazard_curve_set: HazardFragilityCurves):
    for curve in hazard_curve_set.curves:
        prob = curve.prob_function
        prob_model = prob.prob_model
        sample = prob_model.sample()
        assert isinstance(sample, BaseQuantity)
        probability = prob_model.probability(prob.prob_model.quantity(45, prob.prob_model.units))
        assert probability >= 0 and probability <= 1


def test_valid_fragility_curve():
    (ProbabilityFunction(distribution="lognorm", parameters=[Speed(35, "cm/s"), 0.5]),)


def test_invalid_fragility_curve():
    with pytest.raises(ValidationError):
        (ProbabilityFunction(distribution="not_valid_dist", parameters=[Speed(35, "cm/s"), 0.5]),)

    with pytest.raises(ValidationError):
        (ProbabilityFunction(distribution="lognorm", parameters=[35, 0.5]),)

    with pytest.raises(ValidationError):
        (
            ProbabilityFunction(
                distribution="lognorm", parameters=[Speed(35, "cm/s"), Speed(35, "m/s")]
            ),
        )


def test_valid_probability_func_use():
    prob_data_model = ProbabilityFunction(
        distribution="lognorm", parameters=[Speed(35, "cm/s"), 0.5]
    )
    prob_model = prob_data_model.prob_model
    sample = prob_model.sample()
    assert isinstance(sample, BaseQuantity)
    probability = prob_model.probability(Speed(45, "cm/s"))
    assert probability >= 0 and probability <= 1


def test_invalid_probability_func_use():
    with pytest.raises(AssertionError):
        prob_data_model = ProbabilityFunction(
            distribution="lognorm", parameters=[Speed(35, "cm/s"), 0.5]
        )
        prob_model = prob_data_model.prob_model
        prob_model.probability(45)
