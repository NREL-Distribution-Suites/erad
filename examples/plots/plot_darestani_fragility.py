from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

matplotlib.rcParams.update({
    "font.size": 14,
    "axes.titlesize": 16,
    "axes.labelsize": 14,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "legend.title_fontsize": 13,
})

from erad.models.custom_distributions import Darestani2019
from erad.enums import PoleClass, PoleConstructionMaterial
from erad.quantities import Speed, WindAngle, ConductorArea, PoleAge
from erad.models.asset import DistributionPole
from erad.probability_builder import ProbabilityFunctionBuilder


# Baseline inputs.
POLE_MATERIAL = PoleConstructionMaterial.WOOD
WIND_ANGLE = WindAngle(90, "degree")
CONDUCTOR_AREA = ConductorArea(2, "m^2")
POLE_AGE = PoleAge(50, "year")

# Sensitivity settings.
AGE_VALUES = list(range(0, 101, 5))  # years
CONDUCTOR_AREA_VALUES = [i / 2 for i in range(0, 17)]  # m^2 from 0 to 8
SUMMARY_WIND_SPEED_MPH = 80

WIND_SPEEDS_MPH = list(range(0, 250, 2))


def _failure_probability_curve(asset: DistributionPole) -> list[float]:
    dist_instance = Darestani2019(asset)
    prob_builder = ProbabilityFunctionBuilder("Darestani2019", [Speed(0, "m/s")], dist_instance)
    return [prob_builder.probability(Speed(ws, "mph")) for ws in WIND_SPEEDS_MPH]


def _failure_probability_at_speed(asset: DistributionPole, wind_speed_mph: float) -> float:
    dist_instance = Darestani2019(asset)
    prob_builder = ProbabilityFunctionBuilder("Darestani2019", [Speed(0, "m/s")], dist_instance)
    return prob_builder.probability(Speed(wind_speed_mph, "mph"))


def _darestani_params(asset: DistributionPole) -> tuple[float, float]:
    dist_instance = Darestani2019(asset)
    return dist_instance.mu, dist_instance.sigma


def _add_fixed_params_label(ax, text: str) -> None:
    ax.text(
        0.02,
        0.98,
        text,
        transform=ax.transAxes,
        verticalalignment="top",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.85},
    )


def _wind_speed_at_probability(
    wind_speeds: list[float], probabilities: list[float], target_probability: float = 0.5
) -> float | None:
    if not wind_speeds or not probabilities or len(wind_speeds) != len(probabilities):
        return None

    if target_probability < probabilities[0] or target_probability > probabilities[-1]:
        return None

    for i in range(1, len(probabilities)):
        p_prev, p_curr = probabilities[i - 1], probabilities[i]
        if p_prev <= target_probability <= p_curr:
            x_prev, x_curr = wind_speeds[i - 1], wind_speeds[i]
            if p_curr == p_prev:
                return x_curr
            frac = (target_probability - p_prev) / (p_curr - p_prev)
            return x_prev + frac * (x_curr - x_prev)

    return None


def _plot_baseline_by_pole_class(asset: DistributionPole, out_dir: Path) -> None:
    fig, ax1 = plt.subplots(figsize=(10, 6))
    class_labels: list[str] = []
    class_indices: list[int] = []
    ws50_values: list[float] = []

    for idx, pole_class in enumerate(PoleClass, start=1):
        asset.pole_class = pole_class
        failure_probability = _failure_probability_curve(asset)
        ax1.plot(WIND_SPEEDS_MPH, failure_probability, label=pole_class.name, linewidth=2)

        ws50 = _wind_speed_at_probability(WIND_SPEEDS_MPH, failure_probability, 0.5)
        if ws50 is not None:
            class_labels.append(pole_class.name)
            class_indices.append(idx)
            ws50_values.append(ws50)

    ax1.set_xlabel("Wind Speed (mph)")
    ax1.set_ylabel("Failure Probability")
    ax1.set_title("Darestani2019 Fragility Curves by Pole Class")
    ax1.grid(True, alpha=0.3)
    ax1.legend(title="Pole Class", loc="lower left")

    ax2 = ax1.twinx()
    ax2.set_ylabel("Pole Class")
    if ws50_values:
        ax2.plot(
            ws50_values,
            class_indices,
            color="black",
            linestyle="--",
            marker="o",
            linewidth=2,
            label="Wind Speed at 50% Failure",
        )
        ax2.set_yticks(class_indices)
        ax2.set_yticklabels(class_labels)
        ax2.legend(loc="lower right")

    fixed_text = (
        f"Fixed: Material={asset.pole_material.name}, "
        f"Wind Angle={asset.wind_angle.magnitude:g} {asset.wind_angle.units}, "
        f"Conductor Area={asset.conductor_area.magnitude:g} {asset.conductor_area.units}, "
        f"Pole Age={asset.pole_age.magnitude:g} {asset.pole_age.units}"
    )
    _add_fixed_params_label(ax1, fixed_text)

    fig.tight_layout()
    out_path = out_dir / "darestani_fragility_curves.png"
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    print(out_path)


def _plot_mu_vs_age_by_class(asset: DistributionPole, out_dir: Path) -> None:
    plt.figure(figsize=(10, 6))

    import math

    for pole_class in PoleClass:
        asset.pole_class = pole_class
        exp_mu_values = []
        for age in AGE_VALUES:
            asset.pole_age = PoleAge(age, "year")
            mu, _ = _darestani_params(asset)
            exp_mu_values.append(math.exp(mu))
        plt.plot(AGE_VALUES, exp_mu_values, label=pole_class.name, linewidth=2)

    plt.xlabel("Pole Age (years)")
    plt.ylabel("exp(μ) (mph)")
    plt.title("Median Failure Wind Speed vs. Pole Age by Pole Class")
    plt.legend(title="Pole Class")
    plt.grid(True, alpha=0.3)

    fixed_text = (
        f"Fixed: Material={asset.pole_material.name}, "
        f"Wind Angle={asset.wind_angle.magnitude:g} {asset.wind_angle.units}, "
        f"Conductor Area={asset.conductor_area.magnitude:g} {asset.conductor_area.units}"
    )
    _add_fixed_params_label(plt.gca(), fixed_text)

    plt.tight_layout()
    out_path = out_dir / "darestani_mu_vs_age_by_class.png"
    plt.savefig(out_path, dpi=180)
    plt.close()
    print(out_path)


def _plot_sigma_vs_age_by_class(asset: DistributionPole, out_dir: Path) -> None:
    plt.figure(figsize=(10, 6))

    for pole_class in PoleClass:
        asset.pole_class = pole_class
        sigma_values = []
        for age in AGE_VALUES:
            asset.pole_age = PoleAge(age, "year")
            _, sigma = _darestani_params(asset)
            sigma_values.append(sigma)
        plt.plot(AGE_VALUES, sigma_values, label=pole_class.name, linewidth=2)

    plt.xlabel("Pole Age (years)")
    plt.ylabel("σ")
    plt.ylim(0, 0.8)
    plt.title("Failure Wind Speed Variability (σ) vs. Pole Age")
    plt.legend(title="Pole Class")
    plt.grid(True, alpha=0.3)

    fixed_text = (
        f"Fixed: Material={asset.pole_material.name}, "
        f"Wind Angle={asset.wind_angle.magnitude:g} {asset.wind_angle.units}, "
        f"Conductor Area={asset.conductor_area.magnitude:g} {asset.conductor_area.units}"
    )
    _add_fixed_params_label(plt.gca(), fixed_text)

    plt.tight_layout()
    out_path = out_dir / "darestani_sigma_vs_age_by_class.png"
    plt.savefig(out_path, dpi=180)
    plt.close()
    print(out_path)


def _plot_failure_vs_conductor_area_by_class(asset: DistributionPole, out_dir: Path) -> None:
    plt.figure(figsize=(10, 6))

    for pole_class in PoleClass:
        asset.pole_class = pole_class
        y_values = []
        for area in CONDUCTOR_AREA_VALUES:
            asset.conductor_area = ConductorArea(area, "m^2")
            y_values.append(_failure_probability_at_speed(asset, SUMMARY_WIND_SPEED_MPH))
        plt.plot(CONDUCTOR_AREA_VALUES, y_values, label=pole_class.name, linewidth=2)

    plt.xlabel("Conductor Area (m^2)")
    plt.ylabel("Failure Probability")
    plt.title(f"Failure Probability vs Conductor Area at {SUMMARY_WIND_SPEED_MPH} mph")
    plt.legend(title="Pole Class")
    plt.grid(True, alpha=0.3)

    fixed_text = (
        f"Fixed: Material={asset.pole_material.name}, "
        f"Wind Angle={asset.wind_angle.magnitude:g} {asset.wind_angle.units}, "
        f"Pole Age={asset.pole_age.magnitude:g} {asset.pole_age.units}, "
        f"Wind Speed={SUMMARY_WIND_SPEED_MPH} mph"
    )
    _add_fixed_params_label(plt.gca(), fixed_text)

    plt.tight_layout()
    out_path = out_dir / "darestani_failure_vs_conductor_area_by_class.png"
    plt.savefig(out_path, dpi=180)
    plt.close()
    print(out_path)


def main() -> None:
    asset = DistributionPole.example()
    asset.pole_material = POLE_MATERIAL
    asset.wind_angle = WIND_ANGLE
    asset.conductor_area = CONDUCTOR_AREA
    asset.pole_age = POLE_AGE

    out_dir = Path("examples/plots")
    out_dir.mkdir(parents=True, exist_ok=True)

    _plot_baseline_by_pole_class(asset, out_dir)

    asset.conductor_area = CONDUCTOR_AREA
    asset.pole_age = POLE_AGE
    _plot_mu_vs_age_by_class(asset, out_dir)

    asset.conductor_area = CONDUCTOR_AREA
    asset.pole_age = POLE_AGE
    _plot_sigma_vs_age_by_class(asset, out_dir)

    asset.conductor_area = CONDUCTOR_AREA
    asset.pole_age = POLE_AGE
    _plot_failure_vs_conductor_area_by_class(asset, out_dir)


if __name__ == "__main__":
    main()
