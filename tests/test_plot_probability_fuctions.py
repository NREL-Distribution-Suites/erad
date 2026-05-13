from erad.default_fragility_curves import DEFAULT_FRAGILTY_CURVES
from erad.plotting import plot_custom_fragility_curves
from erad.models.asset import DistributionPole
from erad.enums import PoleClass, PoleConstructionMaterial
from erad.quantities import WindAngle, ConductorArea, PoleAge


def test_plotting(tmp_path):
    """Test plotting of fragility curves."""

    for i, hazard_curves in enumerate(DEFAULT_FRAGILTY_CURVES):
        img = tmp_path / f"test_plotting_{i}.html"
        hazard_curves.plot(img, 0, 80, 1000)

        assert img.exists(), "Plotting failed, image not created."


def test_plot_custom_fragility_curves(tmp_path):
    """Test plotting of per-asset custom fragility curves (Darestani2019)."""
    base = DistributionPole.example()
    assets = [
        base.model_copy(
            update={
                "name": pole_class.name,
                "pole_class": pole_class,
                "pole_material": PoleConstructionMaterial.WOOD,
                "wind_angle": WindAngle(90, "degree"),
                "conductor_area": ConductorArea(2, "m**2"),
                "pole_age": PoleAge(50, "year"),
                "probability_dist": "Darestani2019",
            }
        )
        for pole_class in PoleClass
    ]

    img = tmp_path / "test_plot_custom_fragility.html"
    plot_custom_fragility_curves(
        assets,
        asset_state_param="wind_speed",
        file_path=img,
        x_min=0,
        x_max=60,
        number_of_points=200,
    )
    assert img.exists(), "Plotting failed, image not created."
