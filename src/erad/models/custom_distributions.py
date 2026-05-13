import numpy as np
from scipy.stats import norm, rv_continuous
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erad.models.asset import DistributionPole

from erad.data import pole_coefficients_data


def validate_range(param: float, min_value: float, max_value: float, param_name: str):
    """Common validation function to check if a parameter is within a specified range."""
    if not (min_value <= param <= max_value):
        raise ValueError(f"{param_name} out of range [{min_value}, {max_value}]")


class Darestani2019(rv_continuous):
    """Custom distribution based on Darestani et al. (2019) model."""

    def __init__(self, asset: "DistributionPole"):
        super().__init__(name="Darestani2019")  # Initialize the base class
        for attr in ["wind_angle", "conductor_area", "pole_age", "pole_class", "pole_material"]:
            if getattr(asset, attr) is None:
                raise ValueError(f"{attr} must be provided for Darestani2019 distribution")

        self.wind_angle = asset.wind_angle
        self.conductor_area = asset.conductor_area
        self.pole_age = asset.pole_age
        self.pole_class = asset.pole_class
        self.pole_material = asset.pole_material

        validate_range(self.wind_angle.magnitude, 0, 90, "Wind angle")
        validate_range(self.conductor_area.magnitude, 0, 8, "Conductor area")
        validate_range(self.pole_age.magnitude, 0, 100, "Pole age")

        self.mu, self.sigma = self._calculate_params()

    def _cdf(self, x):
        """Cumulative distribution function."""
        if x < 2:
            return 0
        if x > 112:
            return 1
        log_x = np.log(2.23694 * x)
        return norm.cdf((log_x - self.mu) / self.sigma)

    def _rvs(self, size=1, random_state=None):
        """Random variates."""
        rng = np.random.default_rng(random_state)
        log_transformed_speed = rng.normal(self.mu, self.sigma, size)
        sampled_wind_speed = np.exp(log_transformed_speed) / 2.23694
        sampled_wind_speed = np.clip(sampled_wind_speed, 2, 112)
        return sampled_wind_speed

    def _calculate_params(self) -> tuple[float, float]:
        """Calculate mu and sigma params for Darestani et al. (2019) distribution."""

        key = (self.pole_material, self.pole_class)
        if key not in pole_coefficients_data.Darestani2019_PoleCoefficients:
            raise ValueError("No coefficients found")

        coeff_data = pole_coefficients_data.Darestani2019_PoleCoefficients[key]

        params = [
            1,
            self.wind_angle.magnitude,
            self.conductor_area.magnitude,
            self.pole_age.magnitude,
            self.wind_angle.magnitude**2,
            self.wind_angle.magnitude * self.conductor_area.magnitude,
            self.conductor_area.magnitude**2,
            self.wind_angle.magnitude * self.pole_age.magnitude,
            self.conductor_area.magnitude * self.pole_age.magnitude,
            self.pole_age.magnitude**2,
        ]

        mu = np.dot(coeff_data["mu_coefficients"], params)
        sigma = np.dot(coeff_data["sigma_coefficients"], params)

        if sigma <= 0:
            raise ValueError("Sigma must be positive")

        return mu, sigma


CUSTOM_DISTRIBUTIONS = {
    "Darestani2019": Darestani2019,  # Add other custom distributions here as needed
}


# Helper functions
def list_custom_distributions():
    """List available custom functions."""
    return list(CUSTOM_DISTRIBUTIONS.keys())
