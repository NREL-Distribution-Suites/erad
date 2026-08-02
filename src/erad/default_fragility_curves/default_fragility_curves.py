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

DEFAULT_FRAGILITY_CURVES = [
    DEFAULT_PEAK_GROUND_ACCELERATION_FRAGILITY_CURVES,
    DEFAULT_PEAK_GROUND_VELOCITY_FRAGILITY_CURVES,
    DEFAULT_FIRE_BOUNDARY_FRAGILITY_CURVES,
    DEFAULT_FLOOD_VELOCITY_FRAGILITY_CURVES,
    DEFAULT_FLOOD_DEPTH_FRAGILITY_CURVES,
    DEFAULT_WIND_SPEED_FRAGILITY_CURVES,
]

# Deprecated alias for backward compatibility. ``DEFAULT_FRAGILTY_CURVES`` was
# a misspelling of ``DEFAULT_FRAGILITY_CURVES``; it is kept importable (with a
# DeprecationWarning on access) so existing external callers keep working.
def __getattr__(name: str):
    if name == "DEFAULT_FRAGILTY_CURVES":
        import warnings

        warnings.warn(
            "DEFAULT_FRAGILTY_CURVES is deprecated; use DEFAULT_FRAGILITY_CURVES instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return DEFAULT_FRAGILITY_CURVES
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
