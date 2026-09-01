import gdm.distribution.components as gdc
import gdm.distribution.equipment as gde
from gdm.distribution.enums import LineType

from erad.enums import AssetTypes
from erad.models.asset_mapping import ComponentFilterModel

USE_CONSTRUCTION_ATTRIBUTE = False

asset_to_gdm_mapping = {
    AssetTypes.switch: [
        ComponentFilterModel(
            component_type=gdc.DistributionSwitchBase,
        ),
    ],
    AssetTypes.switch: [
        ComponentFilterModel(
            component_type=gdc.DistributionSwitchBase,
        ),
    ],
    AssetTypes.substation: [
        ComponentFilterModel(
            component_type=gdc.DistributionVoltageSource,
        ),
    ],
    AssetTypes.solar_panels: [
        ComponentFilterModel(
            component_type=gdc.DistributionSolar,
        ),
    ],
    AssetTypes.battery_storage: [
        ComponentFilterModel(
            component_type=gdc.DistributionBattery,
        ),
    ],
    AssetTypes.distribution_underground_cables: [
        ComponentFilterModel(
            component_type=gdc.GeometryBranch,
            component_filter=lambda x: x.equipment.conductors[0].__class__
            == gde.ConcentricCableEquipment
            and x.buses[0].rated_voltage.to("kilovolt").magnitude < 35.0,
        ),
        ComponentFilterModel(
            component_type=gdc.MatrixImpedanceBranch,
            component_filter=lambda x: (
                x.equipment.construction == LineType.UNDERGROUND
                if USE_CONSTRUCTION_ATTRIBUTE
                else x.equipment.c_matrix[0, 0].to("microfarad/kilometer").magnitude > 0.05
            )
            and x.buses[0].rated_voltage.to("kilovolt").magnitude < 35.0,
        ),
    ],
    AssetTypes.distribution_overhead_lines: [
        ComponentFilterModel(
            component_type=gdc.GeometryBranch,
            component_filter=lambda x: (
                x.equipment.conductors[0].__class__ == gde.BareConductorEquipment
            )
            and x.buses[0].rated_voltage.to("kilovolt").magnitude < 35.0,
        ),
        ComponentFilterModel(
            component_type=gdc.MatrixImpedanceBranch,
            component_filter=lambda x: (
                x.equipment.construction == LineType.OVERHEAD
                if USE_CONSTRUCTION_ATTRIBUTE
                else x.equipment.c_matrix[0, 0].to("microfarad/kilometer").magnitude < 0.05
            )
            and x.buses[0].rated_voltage.to("kilovolt").magnitude < 35.0,
        ),
    ],
    AssetTypes.transmission_underground_cables: [
        ComponentFilterModel(
            component_type=gdc.GeometryBranch,
            component_filter=lambda x: x.equipment.conductors[0].__class__
            == gde.ConcentricCableEquipment
            and x.buses[0].rated_voltage.to("kilovolt").magnitude > 35.0,
        ),
    ],
    AssetTypes.transmission_overhead_lines: [
        ComponentFilterModel(
            component_type=gdc.GeometryBranch,
            component_filter=lambda x: x.equipment.conductors[0].__class__
            == gde.BareConductorEquipment
            and x.buses[0].rated_voltage.to("kilovolt").magnitude > 35.0,
        ),
    ],
}
