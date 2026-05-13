from typing import Optional
from sqlmodel import Field, SQLModel
import logging

logger = logging.getLogger(__name__)


class AssetStateTable(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_name: str
    asset_type: str
    distribution_asset: str
    timestamp: str
    survival_probability: Optional[float] = None
    wind_speed__miles_per_hour: Optional[float] = None
    fire_boundary_dist__feet: Optional[float] = None
    flood_depth__feet: Optional[float] = None
    flood_velocity__feet_per_second: Optional[float] = None
    peak_ground_acceleration__feet_per_second2: Optional[float] = None
    peak_ground_velocity__inch_per_second: Optional[float] = None
