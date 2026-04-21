from infrasys import BaseQuantity
import scipy.stats as stats


class ProbabilityFunctionBuilder:
    """Class containing utility fuctions for sceario definations."""

    def __init__(self, dist, params: list[float | BaseQuantity]):
        """Constructor for BaseScenario class.

        Args:
            dist (str): Name of teh distribution. Should follow Scipy naming convention
            params (list): A list of parameters for the chosen distribution function. See Scipy.stats documentation
        """
        base_quantity = [p for p in params if isinstance(p, BaseQuantity)][0]
        self.quantity = base_quantity.__class__
        self.units = base_quantity.units
        self.dist = getattr(stats, dist)
        self.params = [p.magnitude if isinstance(p, BaseQuantity) else p for p in params]
        return

    def sample(self):
        """Sample the distribution"""
        return self.quantity(self.dist.rvs(*self.params, size=1)[0], self.units)

    def probability(self, value: BaseQuantity) -> float:
        """Calculates survival probability of a given asset.

        Args:
            value (float): value for vetor of interest. Will change with scenarions
        """
        assert isinstance(value, BaseQuantity), "Value must be a BaseQuantity"
        if value.to(self.units).magnitude > 45:
            import pdb; pdb.set_trace()
        cdf = self.dist.cdf
        try:
            return cdf(value.to(self.units).magnitude, *self.params)
        except Exception:
            return cdf(value, *self.params)
