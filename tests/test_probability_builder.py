import pytest
from erad.probability_builder import ProbabilityFunctionBuilder
from erad.quantities import Speed
from erad.models.custom_distributions import CUSTOM_DISTRIBUTIONS
from erad.models.asset import DistributionPole
from scipy.stats._distn_infrastructure import rv_continuous_frozen

# Example scipy distributions to test
SCIPY_DISTS = [
    ("norm", [Speed(1.5, "m/s"), 2], Speed, "meter/second"),
    ("lognorm", [Speed(3, "m/s"), 1], Speed, "meter/second"),
]
CUSTOM_DISTS = [
    ("Darestani2019", [Speed(0, "m/s")], Speed, "meter/second"),
    # Add other custom distributions here when defined
]


@pytest.mark.parametrize("dist_name,params,quantity_cls,units", SCIPY_DISTS)
class TestScipyDistributions:
    def test_init_with_scipy_distribution(self, dist_name, params, quantity_cls, units):
        b = ProbabilityFunctionBuilder(dist_name, params)
        assert isinstance(b.dist, rv_continuous_frozen)
        assert b.params == [p.magnitude if hasattr(p, "magnitude") else p for p in params]
        assert b.quantity == quantity_cls
        assert b.units == units

    def test_probability_for_scipy_distributions(self, dist_name, params, quantity_cls, units):
        b = ProbabilityFunctionBuilder(dist_name, params)
        p = b.probability(params[0])
        assert isinstance(p, float) and 0 <= p <= 1

    def test_sample_returns_quantity_instance(self, dist_name, params, quantity_cls, units):
        b = ProbabilityFunctionBuilder(dist_name, params)
        sample = b.sample()
        assert isinstance(sample, b.quantity) and sample.units == b.units


@pytest.mark.parametrize("custom_dist_name,params,quantity_cls,units", CUSTOM_DISTS)
class TestCustomDistributions:
    def test_init_with_custom_distribution(self, custom_dist_name, params, quantity_cls, units):
        asset = DistributionPole.example()
        dist_instance = CUSTOM_DISTRIBUTIONS[custom_dist_name](asset)
        b = ProbabilityFunctionBuilder(custom_dist_name, params, dist_instance)
        assert b.dist is not None
        assert b.params == [p.magnitude if hasattr(p, "magnitude") else p for p in params]
        assert b.quantity == quantity_cls
        assert b.units == units

    def test_probability_for_custom_distributions(
        self, custom_dist_name, params, quantity_cls, units
    ):
        asset = DistributionPole.example()
        dist_instance = CUSTOM_DISTRIBUTIONS[custom_dist_name](asset)
        b = ProbabilityFunctionBuilder(custom_dist_name, params, dist_instance)
        p = b.probability(params[0])
        assert isinstance(p, float) and 0 <= p <= 1

    def test_custom_distribution_sample(self, custom_dist_name, params, quantity_cls, units):
        asset = DistributionPole.example()
        dist_instance = CUSTOM_DISTRIBUTIONS[custom_dist_name](asset)
        b = ProbabilityFunctionBuilder(custom_dist_name, params, dist_instance)
        sample = b.sample()
        assert isinstance(sample, b.quantity) and sample.units == b.units


def test_unsupported_distribution_raises():
    with pytest.raises(ValueError, match="Unsupported distribution"):
        ProbabilityFunctionBuilder("not_a_real_dist", [Speed(1.0, "m/s")])
