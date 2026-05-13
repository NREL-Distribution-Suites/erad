# Data Models

This page lists the primary ERAD model classes.

## Hazard Models

- `erad.models.hazard.earthquake.EarthQuakeModel`
- `erad.models.hazard.wind.WindModel`
- `erad.models.hazard.flood.FloodModelArea`
- `erad.models.hazard.flood.FloodModel`
- `erad.models.hazard.wild_fire.FireModel`
- `erad.models.hazard.wild_fire.FireModelArea`

## Asset Models

- `erad.models.asset.AssetState`
- `erad.models.asset.Asset`

## Asset Mapping Models

- `erad.models.asset_mapping.ComponentFilterModel`
- `erad.models.asset_mapping.AssetComponentMap`

## Fragility Models

- `erad.models.fragility_curve.ProbabilityFunction`
- `erad.models.fragility_curve.FragilityCurve`
- `erad.models.fragility_curve.HazardFragilityCurves`

## Probability Models

- `erad.models.probability.BaseProbabilityModel`
- `erad.models.probability.SpeedProbability`
- `erad.models.probability.TemperatureProbability`
- `erad.models.probability.DistanceProbability`
- `erad.models.probability.AccelerationProbability`