# Data Models

## Hazard Models

### Earthquake Models
```{eval-rst}
.. autopydantic_model:: erad.models.hazard.earthquake.EarthQuakeModel
    :exclude-members: example, validate_fields
```

### Wind Models

```{eval-rst}
.. autopydantic_model:: erad.models.hazard.wind.WindModel
```

### Flood Models

```{eval-rst}
.. autopydantic_model:: erad.models.hazard.flood.FloodModelArea
```

```{eval-rst}
.. autopydantic_model:: erad.models.hazard.flood.FloodModel
```

### Fire Models

```{eval-rst}
.. autopydantic_model:: erad.models.hazard.wild_fire.FireModel
```

```{eval-rst}
.. autopydantic_model:: erad.models.hazard.wild_fire.FireModelArea
```

## Asset Model

```{eval-rst}
.. autopydantic_model:: erad.models.asset.AssetState

.. autopydantic_model:: erad.models.asset.Asset
```

## Asset Mapping Model

```{eval-rst}

.. autopydantic_model:: erad.models.asset_mapping.ComponentFilterModel

.. autopydantic_model:: erad.models.asset_mapping.AssetComponentMap
```


## Fragility Model

```{eval-rst}
.. autopydantic_model:: erad.models.fragility_curve.ProbabilityFunction

.. autopydantic_model:: erad.models.fragility_curve.FragilityCurve

.. autopydantic_model:: erad.models.fragility_curve.HazardFragilityCurves

```

## Probabaility Model

```{eval-rst}
.. autopydantic_model:: erad.models.probability.BaseProbabilityModel
```
### Speed Model
```{eval-rst}
.. autopydantic_model:: erad.models.probability.SpeedProbability
```

### Temperature Model
```{eval-rst}
.. autopydantic_model:: erad.models.probability.TemperatureProbability
```

### Distance Model
```{eval-rst}
.. autopydantic_model:: erad.models.probability.DistanceProbability
```

### Acceleration Model
```{eval-rst}
.. autopydantic_model:: erad.models.probability.AccelerationProbability
```