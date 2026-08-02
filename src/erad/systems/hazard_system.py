from infrasys import System

from gdm.distribution.enums import PlotingStyle, MapType
import plotly.graph_objects as go

from erad.default_fragility_curves import DEFAULT_FRAGILITY_CURVES
from erad.constants import HAZARD_MODELS
import erad.models.fragility_curve as fc
import erad.models.hazard as hz


class HazardSystem(System):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_component(self, component, **kwargs):
        assert isinstance(
            component, HAZARD_MODELS
        ), f"Unsupported model type {component.__class__.__name__}"
        return super().add_component(component, **kwargs)

    def add_components(self, *components, **kwargs):
        assert all(isinstance(component, HAZARD_MODELS) for component in components), (
            "Unsupported model types in passed component. Valid types are: \n"
            + "\n".join([s.__name__ for s in HAZARD_MODELS])
            + "\nPassed components: \n"
            + "\n".join(set([component.__class__.__name__ for component in components]))
        )
        return super().add_components(*components, **kwargs)

    def to_json(self, filename, overwrite=False, indent=None, data=None):
        if not list(self.get_components(fc.HazardFragilityCurves)):
            self.add_components(*DEFAULT_FRAGILITY_CURVES)
        return super().to_json(filename, overwrite, indent, data)

    @classmethod
    def fire_example(cls) -> "HazardSystem":
        hazard = hz.FireModel.example()
        system = HazardSystem(auto_add_composed_components=True)
        system.add_component(hazard)
        return system

    @classmethod
    def wind_example(cls) -> "HazardSystem":
        hazard = hz.WindModel.example()
        system = HazardSystem(auto_add_composed_components=True)
        system.add_component(hazard)
        return system

    @classmethod
    def wind_gust_example(cls) -> "HazardSystem":
        hazard = hz.WindGustModel.example()
        system = HazardSystem(auto_add_composed_components=True)
        system.add_component(hazard)
        return system

    @classmethod
    def earthquake_example(cls) -> "HazardSystem":
        hazard = hz.EarthQuakeModel.example()
        system = HazardSystem(auto_add_composed_components=True)
        system.add_component(hazard)
        return system

    @classmethod
    def flood_example(cls) -> "HazardSystem":
        hazard = hz.FloodModel.example()
        system = HazardSystem(auto_add_composed_components=True)
        system.add_component(hazard)
        return system

    @classmethod
    def multihazard_example(cls) -> "HazardSystem":
        wind_hazard = hz.WindModel.example()
        flood_hazard = hz.FloodModel.example()
        system = HazardSystem(auto_add_composed_components=True)
        system.add_component(wind_hazard)
        system.add_component(flood_hazard)
        return system

    def plot(
        self,
        show: bool = True,
        show_legend: bool = True,
        map_type: MapType = MapType.SCATTER_MAP,
        style: PlotingStyle = PlotingStyle.CARTO_POSITRON,
        zoom_level: int = 11,
        figure=go.Figure(),
    ):
        timestamps = sorted(
            [model.timestamp for model in self.get_components(hz.BaseDisasterModel)]
        )

        steps = []
        for i, ts in enumerate(timestamps):
            hazards = self.get_components(
                hz.BaseDisasterModel, filter_func=lambda x: x.timestamp == ts
            )
            map_obj = getattr(go, map_type.value)
            num_traces = 0
            for hazard in hazards:
                num_traces += hazard.plot(i, figure, map_obj)
            vis = [j == i for j in range(len(timestamps))]
            result = [x for x in vis for _ in range(num_traces)]
            steps.append(dict(method="update", label=str(ts), args=[{"visible": result}]))

        sliders = [dict(active=0, pad={"t": 50}, steps=steps)]

        if map_type == MapType.SCATTER_MAP:
            figure.update_layout(
                map={
                    "style": style.value,
                    "zoom": zoom_level,
                },
                sliders=sliders,
                showlegend=True if show_legend else False,
            )
        else:
            figure.update_layout(
                geo=dict(
                    projection_scale=zoom_level,
                ),
                sliders=sliders,
                showlegend=True if show_legend else False,
            )

        if show:
            figure.show()

        return figure
