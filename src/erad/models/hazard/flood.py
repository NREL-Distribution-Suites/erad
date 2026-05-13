from datetime import datetime

from pydantic import field_serializer, field_validator
from shapely.geometry import Polygon, Point
from gdm.quantities import Distance
import plotly.graph_objects as go
from infrasys import Component

from erad.models.hazard.base_models import BaseDisasterModel
from erad.quantities import Speed, Flow, Ratio


class FloodModelArea(Component):
    name: str = ""
    affected_area: Polygon
    water_velocity: Speed
    water_elevation: Distance
    soil_saturation: Ratio | None = None
    snow_water_equivalent: Distance | None = None
    runoff_volume: Flow | None = None
    groundwater_flow: Flow | None = None

    @field_validator("affected_area", mode="before")
    def deserialize_polygon(cls, value):
        if isinstance(value, dict) and value.get("type") == "Polygon":
            points = [Point(c) for c in value["coordinates"]]
            return Polygon(points)
        return value

    @field_serializer("affected_area")
    def serialize_polygon(self, poly: Polygon, _info):
        return {"type": "Polygon", "coordinates": list(poly.exterior.coords)}

    @classmethod
    def example(cls) -> "FloodModelArea":
        return FloodModelArea(
            affected_area=Polygon(
                [
                    (-120.93036, 36.60144),
                    (-120.91072, 36.60206),
                    (-120.91127, 36.5712),
                    (-120.93405, 36.58100),
                ]
            ),
            water_velocity=Speed(50, "meter/second"),
            water_elevation=Distance(10, "feet"),
        )


class FloodModel(BaseDisasterModel):
    timestamp: datetime
    affected_areas: list[FloodModelArea]

    @classmethod
    def example(cls) -> "FloodModel":
        return FloodModel(
            name="flood 1",
            timestamp=datetime.now(),
            affected_areas=[FloodModelArea.example()],
        )

    def plot(
        self,
        time_index: int = 0,
        figure: go.Figure = go.Figure(),
        map_obj: type[go.Scattergeo | go.Scattermap] = go.Scattermap,
    ) -> int:
        for area in self.affected_areas:
            lon, lat = area.affected_area.exterior.xy  # returns x and y sequences
            figure.add_trace(
                map_obj(
                    lon=lon.tolist(),
                    lat=lat.tolist(),
                    mode="markers+lines+text",
                    fill="toself",
                    marker={
                        "size": 10,
                        "color": [area.water_elevation.magnitude],
                    },
                    hovertemplate=f"""
                        <br> <b>Water velocity:</b> {area.water_velocity}
                        <br> <b>Water elevation:</b> {area.water_elevation}
                        {"<br> <b>Soil saturation:</b> " + str(area.soil_saturation) if area.soil_saturation is not None else ""}
                        {"<br> <b>SWE:</b> " + str(area.snow_water_equivalent) if area.snow_water_equivalent is not None else ""}
                        {"<br> <b>Runoff:</b> " + str(area.runoff_volume) if area.runoff_volume is not None else ""}
                        {"<br> <b>Groundwater flow:</b> " + str(area.groundwater_flow) if area.groundwater_flow is not None else ""}
                        """,
                    visible=(time_index == 0),
                )
            )
        return len(self.affected_areas)
