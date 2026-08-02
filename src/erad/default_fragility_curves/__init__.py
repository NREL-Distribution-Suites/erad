from erad.default_fragility_curves.default_peak_ground_acceleration import (
    DEFAULT_PEAK_GROUND_ACCELERATION_FRAGILITY_CURVES,
)
from erad.default_fragility_curves.default_peak_ground_velocity import (
    DEFAULT_PEAK_GROUND_VELOCITY_FRAGILITY_CURVES,
)
from erad.default_fragility_curves.default_fire_boundary_dist import (
    DEFAULT_FIRE_BOUNDARY_FRAGILITY_CURVES,
)
from erad.default_fragility_curves.default_flood_velocity import (
    DEFAULT_FLOOD_VELOCITY_FRAGILITY_CURVES,
)
from erad.default_fragility_curves.default_flood_depth import DEFAULT_FLOOD_DEPTH_FRAGILITY_CURVES
from erad.default_fragility_curves.default_wind_speed import DEFAULT_WIND_SPEED_FRAGILITY_CURVES
from erad.default_fragility_curves.default_fragility_curves import DEFAULT_FRAGILITY_CURVES


def __getattr__(name: str):
    """Resolve deprecated names at package level.

    ``DEFAULT_FRAGILTY_CURVES`` (misspelled) is deprecated in favor of
    ``DEFAULT_FRAGILITY_CURVES``; accessing it emits a ``DeprecationWarning``.
    """
    if name == "DEFAULT_FRAGILTY_CURVES":
        import warnings

        warnings.warn(
            "DEFAULT_FRAGILTY_CURVES is deprecated; use DEFAULT_FRAGILITY_CURVES instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return DEFAULT_FRAGILITY_CURVES
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
