from infrasys.base_quantity import BaseQuantity


class Speed(BaseQuantity):
    """Quantity representing speed."""

    __base_unit__ = "m/second"


class Acceleration(BaseQuantity):
    """Quantity representing acceleration."""

    __base_unit__ = "m/second**2"


class Temperature(BaseQuantity):
    """Quantity representing temperature."""

    __base_unit__ = "degC"


class Pressure(BaseQuantity):
    """Quantity representing pressure."""

    __base_unit__ = "millibar"


class Flow(BaseQuantity):
    """Quantity representing flow."""

    __base_unit__ = "feet**3/second"


class WindAngle(BaseQuantity):
    """Quantity representing angle between wind and conductor."""

    __base_unit__ = "degree"


class ConductorArea(BaseQuantity):
    """Quantity representing cross-sectional area of a conductor."""

    __base_unit__ = "m**2"


class PoleAge(BaseQuantity):
    """Quantity representing age of a pole."""

    __base_unit__ = "year"
