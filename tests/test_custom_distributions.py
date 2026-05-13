import pytest
from erad.models.custom_distributions import (
    Darestani2019,
    CUSTOM_DISTRIBUTIONS,
    list_custom_distributions,
)
from erad.models.asset import DistributionPole
from erad.enums import PoleConstructionMaterial, PoleClass
import re
import tempfile
import json


@pytest.mark.parametrize(
    "distribution_name,distribution_class",
    [
        ("Darestani2019", Darestani2019),
    ],
)
def test_custom_distributions_registry(distribution_name, distribution_class):
    assert distribution_name in CUSTOM_DISTRIBUTIONS
    assert CUSTOM_DISTRIBUTIONS[distribution_name] is distribution_class


@pytest.mark.parametrize("distribution_name", ["Darestani2019"])
def test_list_custom_distributions(distribution_name):
    available_custom_distributions = list_custom_distributions()
    assert distribution_name in available_custom_distributions
    assert isinstance(available_custom_distributions, list)
    assert (
        len(available_custom_distributions) > 0
    ), "Should have at least one custom distribution listed"
    assert all(
        isinstance(name, str) for name in available_custom_distributions
    ), "All names should be strings"


@pytest.mark.parametrize(
    "attr,value,err_msg",
    [
        ("wind_angle", None, "wind_angle must be provided for Darestani2019 distribution"),
        ("pole_age", None, "pole_age must be provided for Darestani2019 distribution"),
    ],
)
def test_darestani2019_invalid_single_parameter(attr, value, err_msg):
    asset = DistributionPole.example()
    setattr(asset, attr, value)
    with pytest.raises(ValueError, match=err_msg):
        Darestani2019(asset)


def test_darestani2019_invalid_material_and_class():
    asset = DistributionPole.example()
    asset.pole_material = "steel"
    asset.pole_class = "Class 3"
    with pytest.raises(ValueError, match="No coefficients found"):
        Darestani2019(asset)


@pytest.mark.parametrize(
    "attr,value,err_msg",
    [
        ("wind_angle", -10, "Wind angle out of range [0, 90]"),
        ("conductor_area", 10, "Conductor area out of range [0, 8]"),
        ("pole_age", 150, "Pole age out of range [0, 100]"),
    ],
)
def test_invalid_range_parameters(attr, value, err_msg):
    asset = DistributionPole.example()
    setattr(asset, attr, value)
    with pytest.raises(ValueError, match=re.escape(err_msg)):
        Darestani2019(asset)


def test_darestani2019_sampling():
    asset = DistributionPole.example()
    custom_dist = Darestani2019(asset)

    # Test sampling and CDF
    samples = custom_dist.rvs(size=1000)
    assert len(samples) == 1000
    assert all(2 <= s <= 112 for s in samples)
    cdf_points = [1, 2, 50, 112, 113]
    cdf_values = [custom_dist.cdf(x) for x in cdf_points]
    assert cdf_values[0] == 0
    assert cdf_values[4] == 1
    assert all(0 <= cdf <= 1 for cdf in cdf_values)
    assert all(
        cdf_values[i] <= cdf_values[i + 1] for i in range(len(cdf_values) - 1)
    )  # non-decreasing

def test_darestani2019_calculate_params():
    asset = DistributionPole.example()
    custom_dist = Darestani2019(asset)
    mu, sigma = custom_dist._calculate_params()
    assert isinstance(mu, float)
    assert isinstance(sigma, float)
    assert sigma > 0

    # Test with different valid attributes
    asset.pole_material = PoleConstructionMaterial.WOOD
    asset.pole_class = PoleClass.CLASS_2
    mu2, sigma2 = Darestani2019(asset)._calculate_params()
    assert isinstance(mu2, float)
    assert isinstance(sigma2, float)
    assert sigma2 > 0
    assert (mu, sigma) != (mu2, sigma2)
