from enum import IntEnum, StrEnum


class ScenarioTypes(IntEnum):
    flood_m = 0
    wind_m_per_s = 1
    fire_m = 2
    earthquake_pga = 3


class NodeTypes(IntEnum):
    transmission_tower = 5
    distribution_poles = 6
    transmission_junction_box = 11
    distribution_junction_box = 12


class AssetTypes(IntEnum):
    substation = 0
    solar_panels = 1
    distribution_underground_cables = 2
    transmission_underground_cables = 3
    battery_storage = 4
    transmission_tower = 5
    distribution_poles = 6
    transmission_overhead_lines = 7
    distribution_overhead_lines = 8
    transformer_mad_mount = 9
    transformer_pole_mount = 10
    transmission_junction_box = 11
    distribution_junction_box = 12
    switch = 13

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

    @classmethod
    def has_asset(cls, asset):
        return asset in cls.__members__


class PoleClass(StrEnum):
    CLASS_1 = "Class 1"
    CLASS_2 = "Class 2"
    CLASS_3 = "Class 3"
    CLASS_4 = "Class 4"
    CLASS_5 = "Class 5"
    CLASS_6 = "Class 6"
    CLASS_7 = "Class 7"


class PoleConstructionMaterial(StrEnum):
    WOOD = "wood" or "Wood" or "WOOD"
    STEEL = "steel" or "Steel" or "STEEL"
