from erad.default_fragility_curves import DEFAULT_FRAGILITY_CURVES


def test_plotting(tmp_path):
    """Test plotting of fragility curves."""

    for i, hazard_curves in enumerate(DEFAULT_FRAGILITY_CURVES):
        img = tmp_path / f"test_plotting_{i}.html"
        hazard_curves.plot(img, 0, 80, 1000)

        assert img.exists(), "Plotting failed, image not created."
