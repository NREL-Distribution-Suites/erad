from gdm.quantities import Distance

import erad.models.fragility_curve as frag
from erad.enums import AssetTypes

DEFAULT_FIRE_BOUNDARY_FRAGILITY_CURVES = frag.HazardFragilityCurves(
    asset_state_param="fire_boundary_dist",
    curves=[
        frag.FragilityCurve(
            asset_type=AssetTypes.switch,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.2, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.battery_storage,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.2, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.distribution_junction_box,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.2, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.distribution_overhead_lines,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.3, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.distribution_poles,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.3, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.distribution_underground_cables,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.05, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.solar_panels,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.2, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.substation,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.25, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.transformer_mad_mount,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.25, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.transformer_pole_mount,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.3, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.transmission_junction_box,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.2, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.transmission_overhead_lines,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.3, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.transmission_tower,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.25, "km"), 0.95]
            ),
        ),
        frag.FragilityCurve(
            asset_type=AssetTypes.transmission_underground_cables,
            prob_function=frag.ProbabilityFunction(
                distribution="expon", parameters=[Distance(0.05, "km"), 0.95]
            ),
        ),
    ],
)
