from collections import defaultdict, Counter
from pathlib import Path

from gdm.distribution.enums import PlotingStyle, MapType
from sqlmodel import SQLModel, Session, create_engine
from gdm.distribution import DistributionSystem
from shapely.geometry import Point, LineString
import gdm.distribution.components as gdc
from gdm.quantities import Distance
import plotly.graph_objects as go
from infrasys import System
from loguru import logger
import geopandas as gpd
import networkx as nx
import pandas as pd
import numpy as np
import elevation


from erad.constants import ASSET_TYPES, DEFAULT_TIME_STAMP, RASTER_DOWNLOAD_PATH, DEFAULT_HEIGHTS_M
from erad.gdm_mapping import asset_to_gdm_mapping
from erad.models.asset import Asset, AssetState
from erad.enums import AssetTypes, NodeTypes
from erad.tables import AssetStateTable


class AssetSystem(System):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_component(self, component, **kwargs):
        assert isinstance(component, ASSET_TYPES), (
            f"Unsupported model type {component.__class__.__name__}"
        )
        return super().add_component(component, **kwargs)

    def add_components(self, *components, **kwargs):
        assert all(isinstance(component, ASSET_TYPES) for component in components), (
            "Unsupported model types in passed component. Valid types are: \n"
            + "\n".join([s.__name__ for s in ASSET_TYPES])
        )
        return super().add_components(*components, **kwargs)

    def get_dircted_graph(self):
        """Get the directed graph of the AssetSystem."""

        graph = self.get_undirected_graph()
        substations = list(
            self.get_components(Asset, filter_func=lambda x: x.asset_type == AssetTypes.substation)
        )

        assert len(substations) <= 1, "There should be at most one substation in the asset system."

        tree = nx.dfs_tree(graph, str(substations[0].connections[0]))
        return tree

    def get_undirected_graph(self):
        """Get the undirected graph of the AssetSystem."""
        g = nx.Graph()
        graph_data = []
        for asset in self.get_components(Asset):
            if len(asset.connections) == 2:
                u, v = asset.connections
                g.add_edge(str(u), str(v), **asset.model_dump())
            else:
                if asset.asset_type in NodeTypes:
                    g.add_node(str(asset.distribution_asset), **asset.model_dump())
                else:
                    graph_data.append(asset.model_dump())

        g.graph["metadata"] = graph_data
        return g

    @classmethod
    def from_gdm(
        cls, dist_system: DistributionSystem, flip_coordinates: bool = False
    ) -> "AssetSystem":
        """Create a AssetSystem from a DistributionSystem."""
        asset_map = AssetSystem.map_asets(dist_system)
        # list_of_assets = AssetSystem._build_assets(asset_map)
        system = AssetSystem(auto_add_composed_components=True)
        list_of_assets = system._build_assets(asset_map, flip_coordinates)
        system.add_components(*list_of_assets)
        return system

    def _add_node_data(
        self, node_data: dict[str, list], asset: Asset, asset_state: AssetState | None = None
    ):
        node_data["name"].append(asset.name)
        node_data["type"].append(asset.asset_type.name)
        node_data["height"].append(asset.height.to("meter").magnitude)
        node_data["elevation"].append(asset.elevation.to("meter").magnitude)
        node_data["latitude"].append(asset.latitude)
        node_data["longitude"].append(asset.longitude)
        node_data["timestamp"].append(asset_state.timestamp if asset_state else DEFAULT_TIME_STAMP)
        node_data["survival_prob"].append(asset_state.survival_probability if asset_state else 1.0)
        node_data["wind_speed"].append(asset_state.wind_speed if asset_state else None)
        node_data["fire_boundary_dist"].append(
            asset_state.fire_boundary_dist if asset_state else None
        )
        node_data["flood_depth"].append(asset_state.flood_depth if asset_state else None)
        node_data["flood_velocity"].append(asset_state.flood_velocity if asset_state else None)
        node_data["peak_ground_acceleration"].append(
            asset_state.peak_ground_acceleration if asset_state else None
        )
        node_data["peak_ground_velocity"].append(
            asset_state.peak_ground_velocity if asset_state else None
        )
        return node_data

    def _add_edge_data(
        self, edge_data: dict[str, list], asset: Asset, asset_state: AssetState | None = None
    ):
        u, v = set(asset.connections)
        buses = list(
            self.get_components(Asset, filter_func=lambda x: x.distribution_asset in [u, v])
        )
        edge_data["name"].append(asset.name)
        edge_data["type"].append(asset.asset_type.name)
        edge_data["height"].append(asset.height.to("meter").magnitude)
        edge_data["elevation"].append(asset.elevation.to("meter").magnitude)
        edge_data["latitude"].append([b.latitude for b in buses])
        edge_data["longitude"].append([b.longitude for b in buses])
        edge_data["timestamp"].append(asset_state.timestamp if asset_state else DEFAULT_TIME_STAMP)
        edge_data["survival_prob"].append(asset_state.survival_probability if asset_state else 1.0)
        edge_data["wind_speed"].append(asset_state.wind_speed if asset_state else None)
        edge_data["fire_boundary_dist"].append(
            asset_state.fire_boundary_dist if asset_state else None
        )
        edge_data["flood_depth"].append(asset_state.flood_depth if asset_state else None)
        edge_data["flood_velocity"].append(asset_state.flood_velocity if asset_state else None)
        edge_data["peak_ground_acceleration"].append(
            asset_state.peak_ground_acceleration if asset_state else None
        )
        edge_data["peak_ground_velocity"].append(
            asset_state.peak_ground_velocity if asset_state else None
        )
        return edge_data

    def to_gdf(self):
        node_data = defaultdict(list)
        edge_data = defaultdict(list)
        assets: list[Asset] = self.get_components(Asset)

        for asset in assets:
            if len(set(asset.connections)) < 2:
                if asset.asset_state:
                    for asset_state in asset.asset_state:
                        node_data = self._add_node_data(node_data, asset, asset_state)
                else:
                    node_data = self._add_node_data(node_data, asset, None)
            else:
                if asset.asset_state:
                    for asset_state in asset.asset_state:
                        edge_data = self._add_edge_data(edge_data, asset, asset_state)
                else:
                    edge_data = self._add_edge_data(edge_data, asset, None)

        nodes_df = pd.DataFrame(node_data)
        gdf_nodes = gpd.GeoDataFrame(
            nodes_df,
            geometry=gpd.points_from_xy(nodes_df.longitude, nodes_df.latitude),
            crs="EPSG:4326",
        )
        edge_df = pd.DataFrame(edge_data)
        if not edge_df.empty:
            edge_df = edge_df[edge_df["longitude"].apply(lambda x: len(x) == 2)]
            geometry = [
                LineString([Point(xy) for xy in zip(*xys)])
                for xys in zip(edge_df["longitude"], edge_df["latitude"])
            ]
            gdf_edges = gpd.GeoDataFrame(edge_df, geometry=geometry, crs="EPSG:4326")
            complete_gdf = pd.concat([gdf_nodes, gdf_edges])
        else:
            complete_gdf = gdf_nodes
        return complete_gdf

    def to_geojson(self) -> str:
        """Create a GeoJSON from an AssetSystem."""
        gdf_nodes = self.to_gdf()
        return gdf_nodes.to_json()

    def _prepopulate_bus_assets(
        self,
        asset_map: dict[AssetTypes : list[gdc.DistributionComponentBase]],
        list_of_assets: dict[str, Asset],
        flip_coordinates: bool = False,
    ):
        for asset_type, components in asset_map.items():
            for component in components:
                if flip_coordinates:
                    long, lat = AssetSystem._get_component_coordinate(component)
                else:
                    lat, long = AssetSystem._get_component_coordinate(component)
                if isinstance(component, gdc.DistributionBus):
                    list_of_assets[str(component.uuid)] = Asset(
                        name=component.name,
                        connections=[],
                        asset_type=asset_type,
                        distribution_asset=component.uuid,
                        height=Distance(DEFAULT_HEIGHTS_M[asset_type], "meter"),
                        latitude=lat,
                        longitude=long,
                        asset_state=[],
                    )
        return list_of_assets

    def _build_assets(
        self,
        asset_map: dict[AssetTypes : list[gdc.DistributionComponentBase]],
        flip_coordinates: bool = False,
    ) -> list[Asset]:
        list_of_assets: dict[str, Asset] = {}

        self._prepopulate_bus_assets(asset_map, list_of_assets, flip_coordinates)

        for asset_type, components in asset_map.items():
            for component in components:
                if not isinstance(component, gdc.DistributionBus):
                    if flip_coordinates:
                        long, lat = AssetSystem._get_component_coordinate(component)
                    else:
                        lat, long = AssetSystem._get_component_coordinate(component)
                    if hasattr(component, "buses"):
                        connections = [c.uuid for c in component.buses]
                    elif hasattr(component, "bus"):
                        connections = [component.bus.uuid]
                    else:
                        connections = []

                    list_of_assets[str(component.uuid)] = Asset(
                        name=component.name,
                        connections=connections,
                        asset_type=asset_type,
                        distribution_asset=component.uuid,
                        height=Distance(DEFAULT_HEIGHTS_M[asset_type], "meter"),
                        latitude=lat,
                        longitude=long,
                        asset_state=[],
                    )

                    if len(connections) == 1:
                        if str(connections[0]) in list_of_assets:
                            asset = list_of_assets[str(connections[0])]
                            asset.devices.append(component.uuid)

        return list_of_assets.values()

    @staticmethod
    def _get_component_coordinate(component: gdc.DistributionComponentBase):
        if hasattr(component, "buses"):
            xs = [bus.coordinate.x for bus in component.buses]
            ys = [bus.coordinate.y for bus in component.buses]
            if 0 not in xs and 0 not in ys:
                return (sum(xs) / len(xs), sum(ys) / len(ys))
            else:
                return (0, 0)
        elif hasattr(component, "bus"):
            return (component.bus.coordinate.x, component.bus.coordinate.y)
        elif isinstance(component, gdc.DistributionBus):
            return (component.coordinate.x, component.coordinate.y)

    @staticmethod
    def map_asets(
        dist_system: DistributionSystem,
    ) -> dict[AssetTypes : list[gdc.DistributionComponentBase]]:
        asset_dict = defaultdict(list)
        for asset, filters in asset_to_gdm_mapping.items():
            for filter_info in filters:
                models = dist_system.get_components(
                    filter_info.component_type, filter_func=filter_info.component_filter
                )
                asset_dict[asset].extend(list(models))

        AssetSystem._maps_buses(asset_dict, dist_system)
        AssetSystem._map_transformers(asset_dict, dist_system)
        return asset_dict

    @staticmethod
    def _maps_buses(
        asset_dict: dict[AssetTypes : list[gdc.DistributionComponentBase]],
        dist_system: DistributionSystem,
    ):
        for bus in dist_system.get_components(gdc.DistributionBus):
            asset_type = AssetSystem._get_bus_type(bus, asset_dict, dist_system)
            if asset_type:
                asset_dict[asset_type].append(bus)

    @staticmethod
    def _map_transformers(
        asset_dict: dict[AssetTypes : list[gdc.DistributionComponentBase]],
        dist_system: DistributionSystem,
    ):
        for transformer in dist_system.get_components(gdc.DistributionTransformerBase):
            bus_types = [
                AssetSystem._get_bus_type(b, asset_dict, dist_system) for b in transformer.buses
            ]
            if (
                AssetTypes.transmission_junction_box in bus_types
                or AssetTypes.transmission_tower in bus_types
            ):
                asset_dict[AssetTypes.transformer_mad_mount].append(transformer)
            elif all(bus_type == AssetTypes.distribution_junction_box for bus_type in bus_types):
                asset_dict[AssetTypes.transformer_mad_mount].append(transformer)
            else:
                asset_dict[AssetTypes.transformer_mad_mount].append(transformer)

    @staticmethod
    def _get_bus_type(
        bus: gdc.DistributionBus,
        asset_dict: dict[AssetTypes : list[gdc.DistributionComponentBase]],
        dist_system: DistributionSystem,
    ):
        components = dist_system.get_bus_connected_components(bus.name, gdc.DistributionBranchBase)
        connected_types = []
        for component in components:
            if component in asset_dict[AssetTypes.distribution_overhead_lines]:
                connected_types.append(AssetTypes.distribution_poles)
            elif component in asset_dict[AssetTypes.transmission_overhead_lines]:
                connected_types.append(AssetTypes.transmission_tower)
            elif component in asset_dict[AssetTypes.transmission_underground_cables]:
                connected_types.append(AssetTypes.transmission_junction_box)
            elif component in asset_dict[AssetTypes.distribution_underground_cables]:
                connected_types.append(AssetTypes.distribution_junction_box)
            else:
                ...
        if connected_types:
            counter = Counter(connected_types)
            return counter.most_common(1)[0][0]

    def _add_node_traces(
        self,
        time_index: int,
        fig: go.Figure,
        df_ts: gpd.GeoDataFrame,
        plotting_object: go.Scattermap | go.Scattergeo,
    ):
        points_only = df_ts[df_ts.geometry.geom_type == "Point"]
        for asset_type in set(points_only["type"]):
            df_filt = points_only[points_only["type"] == asset_type]
            text = [
                "<br>".join([f"<b>{kk}:</b> {vv}" for kk, vv in rr.to_dict().items()][:-1])
                for __, rr in df_filt.iterrows()
            ]
            trace = plotting_object(
                lat=df_filt.geometry.y,
                lon=df_filt.geometry.x,
                mode="markers",
                marker=dict(size=10),
                name=asset_type,
                hovertext=text,
                visible=(time_index == 0),
            )
            fig.add_trace(trace)
        return fig

    def _add_edge_traces(
        self,
        time_index: int,
        fig: go.Figure,
        df_ts: gpd.GeoDataFrame,
        plotting_object: go.Scattermap | go.Scattergeo,
    ):
        points_only = df_ts[df_ts.geometry.geom_type == "LineString"]
        for asset_type in set(points_only["type"]):
            df_filt = points_only[points_only["type"] == asset_type]
            features = {k: [] for k in list(df_filt.columns) + ["text"]}
            for _, row in df_filt.iterrows():
                for c in df_filt.columns:
                    features[c] = np.append(features[c], row[c])
                features["text"] = np.append(
                    features["text"],
                    "<br> ".join([f"<b>{kk}:</b> {vv}" for kk, vv in row.to_dict().items()][:-1]),
                )
                for c in df_filt.columns:
                    features[c] = np.append(features[c], None)
                features["text"] = np.append(features["text"], None)

            trace = plotting_object(
                name=asset_type,
                lat=features["latitude"],
                lon=features["longitude"],
                mode="lines",
                hovertext=features["text"],
                visible=(time_index == 0),
            )
            fig.add_trace(trace)
        return fig

    def _has_zero_zero_coords(self, geom):
        if geom.is_empty or geom is None:
            return False
        if geom.geom_type == "Point":
            return geom.x == 0 and geom.y == 0
        elif geom.geom_type in ["Polygon", "MultiPolygon"]:
            return any(x == 0 and y == 0 for x, y in geom.exterior.coords)
        elif geom.geom_type == "LineString":
            return any(x == 0 and y == 0 for x, y in geom.coords)
        elif geom.geom_type.startswith("Multi") or geom.geom_type == "GeometryCollection":
            return any(self._has_zero_zero_coords(g) for g in geom.geoms)
        return False

    def get_elevation_raster(self) -> Path:
        """Download and clip elevation raster for the AssetSystem."""
        if RASTER_DOWNLOAD_PATH.exists():
            RASTER_DOWNLOAD_PATH.unlink()

        coordinates = np.array(
            [
                (asset.latitude, asset.longitude)
                for asset in self.get_components(Asset)
                if asset.latitude and asset.latitude
            ]
        )

        if len(coordinates):
            lat_min, lat_max = float(coordinates[:, 0].min()), float(coordinates[:, 0].max())
            lon_min, lon_max = float(coordinates[:, 1].min()), float(coordinates[:, 1].max())
            bounds = (lon_min, lat_min, lon_max, lat_max)
            logger.info(f"Downloading raster file to path: {RASTER_DOWNLOAD_PATH}")
            logger.info(f"Clipping raster for bounds: {bounds}")
            elevation.clip(bounds=bounds, output=str(RASTER_DOWNLOAD_PATH.name))
            if not RASTER_DOWNLOAD_PATH.exists():
                raise FileNotFoundError(f"File path {RASTER_DOWNLOAD_PATH} does not exist")
        else:
            logger.info(
                "No assets found in the AssetSystem, no elevation raster will be downloaded."
            )
            return None

    def plot(
        self,
        show: bool = True,
        show_legend: bool = True,
        map_type: MapType = MapType.SCATTER_MAP,
        style: PlotingStyle = PlotingStyle.CARTO_POSITRON,
        zoom_level: int = 11,
        figure=go.Figure(),
    ):
        """Plot the AssetSystem."""
        plotting_object = getattr(go, map_type.value)
        gdf = self.to_gdf()
        gdf["timestamp"] = pd.to_datetime(gdf["timestamp"])
        gdf = gdf[~gdf.geometry.apply(self._has_zero_zero_coords)]
        timestamps = sorted(gdf["timestamp"].unique())

        steps = []

        for i, ts in enumerate(timestamps):
            df_ts = gdf[gdf["timestamp"] == ts]

            figure = self._add_node_traces(i, figure, df_ts, plotting_object)
            figure = self._add_edge_traces(i, figure, df_ts, plotting_object)

            steps.append(
                dict(
                    method="update",
                    label=str(ts.date()),
                    args=[{"visible": [j == i for j in range(len(timestamps))]}],
                )
            )

        sliders = [dict(active=0, pad={"t": 50}, steps=steps)]

        figure.update_layout(
            mapbox=dict(
                style=style.value,
                zoom=zoom_level,
                # center=dict(lat=gdf.geometry.y.mean(), lon=gdf.geometry.x.mean()),
            ),
            sliders=sliders,
            showlegend=True if show_legend else False,
        )

        if show:
            figure.show()

        return figure

    def export_results(self, db_path: str):
        """Export the AssetSystem results to a SQLite database using SQLModel."""

        engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            for asset in self.get_components(Asset):
                for state in asset.asset_state:
                    record = AssetStateTable(
                        asset_name=asset.name,
                        asset_type=asset.asset_type.name,
                        distribution_asset=str(asset.distribution_asset),
                        timestamp=state.timestamp.isoformat(),
                        survival_probability=state.survival_probability,
                        wind_speed__miles_per_hour=state.wind_speed.speed.to(
                            "miles/hour"
                        ).magnitude
                        if state.wind_speed
                        else None,
                        fire_boundary_dist__feet=state.fire_boundary_dist.distance.to(
                            "feet"
                        ).magnitude
                        if state.fire_boundary_dist
                        else None,
                        flood_depth__feet=state.flood_depth.distance.to("feet").magnitude
                        if state.flood_depth
                        else None,
                        flood_velocity__feet_per_second=state.flood_velocity.speed.to(
                            "feet/second"
                        ).magnitude
                        if state.flood_velocity
                        else None,
                        peak_ground_acceleration__feet_per_second2=state.peak_ground_acceleration.acceleration.to(
                            "feet/second**2"
                        ).magnitude
                        if state.peak_ground_acceleration
                        else None,
                        peak_ground_velocity__inch_per_second=state.peak_ground_velocity.speed.to(
                            "inches/second"
                        ).magnitude
                        if state.peak_ground_velocity
                        else None,
                    )
                    session.add(record)

            session.commit()

        logger.info(f"Asset system results exported to {db_path}")
