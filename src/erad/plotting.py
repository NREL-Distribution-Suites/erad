"""Plotting helpers for ERAD. Kept separate from model modules so that
plotly is only imported when plotting code is actually used."""

from pathlib import Path

import numpy as np
import plotly.express as px

from erad.models.asset import Asset


def plot_custom_fragility_curves(
    assets: list[Asset],
    asset_state_param: str,
    file_path: Path | None = None,
    x_min: float = 0,
    x_max: float = 60,
    number_of_points: int = 1000,
):
    """Plot fragility curves derived from each asset's custom probability
    distribution, one line per asset.

    Each asset must have its custom-distribution field set (e.g.
    DistributionPole.probability_dist = "Darestani2019") and the
    attributes that distribution requires. The curve is obtained via
    Asset.get_valid_curve(frag_curves=[], field=asset_state_param), which
    routes to the existing asset-side custom-dist path.
    """
    if not assets:
        raise ValueError("No assets to plot")
    if file_path is not None:
        file_path = Path(file_path)
        assert file_path.suffix.lower() == ".html", "File path should be an HTML file"

    sample_curve = assets[0].get_valid_curve(frag_curves=[], field=asset_state_param)
    if sample_curve is None:
        raise ValueError(
            f"Asset {assets[0].name!r} has no curve for '{asset_state_param}'. "
            "Ensure its custom-distribution field (e.g. probability_dist) is set."
        )
    quantity_cls = sample_curve.prob_model.quantity
    units = sample_curve.prob_model.units

    x = np.linspace(x_min, x_max, number_of_points)
    plot_data = {"x": [], "y": [], "Asset": []}

    for asset in assets:
        curve = asset.get_valid_curve(frag_curves=[], field=asset_state_param)
        if curve is None:
            continue
        # Iterate scalar-wise: custom rv_continuous subclasses (e.g. Darestani2019)
        # implement _cdf with Python conditionals that aren't array-safe.
        y = [curve.prob_model.probability(quantity_cls(xi, units)) for xi in x]
        label = asset.name or type(asset).__name__
        plot_data["x"].extend(x)
        plot_data["y"].extend(y)
        plot_data["Asset"].extend([label] * len(x))

    x_label = asset_state_param.replace("_", " ").title()
    fig = px.line(
        plot_data,
        x="x",
        y="y",
        color="Asset",
        labels={"x": f"{x_label} [{units}]", "y": "Probability of Failure"},
        title=f"Custom Fragility Curves for {x_label}",
    )

    fig.show()
    if file_path:
        fig.write_html(file_path)

    return fig
