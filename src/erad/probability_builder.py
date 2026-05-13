from infrasys import BaseQuantity
import scipy.stats as stats


class ProbabilityFunctionBuilder:
    """Class containing utility fuctions for scenario definations."""

    def __init__(self, dist: str, params: list[float | BaseQuantity], custom_dist_instance=None):
        """Constructor for BaseScenario class.

        Args:
            dist (str or custom distribution instance):
                - String name for scipy.stats distributions (See Scipy.stats documentation)
                - String name for custom distributions (Call list_custom_distributions() to see available functions)
            params (list): Parameters for the distribution or custom function.
        """
        base_quantities = [p for p in params if isinstance(p, BaseQuantity)]
        self.quantity = base_quantities[0].__class__
        self.units = base_quantities[0].units
        self.params = [p.magnitude if isinstance(p, BaseQuantity) else p for p in params]

        if hasattr(stats, dist):
            dist_class = getattr(stats, dist)
            self.dist = dist_class(*self.params)  # Create a frozen scipy distribution instance
        elif custom_dist_instance:
            self.dist = custom_dist_instance  # Use the provided custom distribution instance
        else:
            raise ValueError(f"Unsupported distribution: {dist}.")

        return

    def sample(self):
        """Sample the distribution"""
        return self.quantity(self.dist.rvs(size=1)[0], self.units)

    def probability(self, value: BaseQuantity) -> float:
        """Calculates survival probability of a given asset.

        Args:
            value (float): value for vector of interest. Will change with scenarios
        """
        assert isinstance(value, BaseQuantity), "Value must be a BaseQuantity"
        val = value.to(self.units).magnitude
        return self.dist.cdf(val)
