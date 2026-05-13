from random import random
from uuid import uuid4

from infrasys import Location
from gdm.distribution.equipment.inverter_equipment import InverterEquipment
from gdm.distribution.equipment.solar_equipment import SolarEquipment
from gdm.distribution.controllers.distribution_inverter_controller import (
    InverterController,
)
from gdm.distribution.common import SequencePair
from gdm.distribution import DistributionSystem


from gdm.distribution.enums import (
    ConnectionType,
    VoltageTypes,
    Phase,
)

from gdm.distribution.components import (
    DistributionVoltageSource,
    DistributionTransformer,
    DistributionCapacitor,
    MatrixImpedanceBranch,
    DistributionSolar,
    DistributionLoad,
    DistributionBus,
)

from gdm.distribution.equipment import (
    DistributionTransformerEquipment,
    MatrixImpedanceBranchEquipment,
    PhaseCapacitorEquipment,
    CapacitorEquipment,
    PhaseLoadEquipment,
    WindingEquipment,
    LoadEquipment,
)

from gdm.quantities import (
    ReactivePower,
    ApparentPower,
    CapacitancePULength,
    Resistance,
    Reactance,
    ResistancePULength,
    ActivePowerOverTime,
    ReactancePULength,
    Distance,
    Current,
    Voltage,
    ActivePower,
    Irradiance,
)


def build_distribution_buses():
    return [
        DistributionBus.example().model_copy(
            update={
                "uuid": uuid4(),
                "name": f"bus_{i}",
                "coordinate": Location(
                    x=(28.30551 - 28.29454) * random() + 28.29454,
                    y=(-97.26956 - (-97.28051)) * random() + (-97.28051),
                ),
            }
        )
        for i in range(10)
    ]


def build_distribution_load(bus: DistributionBus, bus_number: int):
    return DistributionLoad.example().model_copy(
        update={
            "uuid": uuid4(),
            "name": f"load_{bus_number}",
            "bus": bus,
            "equipment": LoadEquipment.example().model_copy(
                update={
                    "uuid": uuid4(),
                    "name": f"load_equipment_{bus_number}",
                    "phase_loads": [
                        PhaseLoadEquipment.example().model_copy(
                            update={
                                "uuid": uuid4(),
                                "name": f"phase_load_{i}_{bus_number}",
                                "real_power": ActivePower(bus_number + 1, "kilowatt"),
                                "reactive_power": ReactivePower(
                                    (bus_number + 1) * 0.44, "kilovar"
                                ),
                            }
                        )
                        for i in range(3)
                    ],
                }
            ),
        }
    )


def build_distribution_solar(bus: DistributionBus, bus_number: int):
    return DistributionSolar.example().model_copy(
        update={
            "uuid": uuid4(),
            "name": f"solar_{bus_number}",
            "bus": bus,
            "inverter": InverterEquipment.example().model_copy(
                update={
                    "uuid": uuid4(),
                    "name": f"inverter_equipment_{bus_number}",
                    "rated_apparent_power": ApparentPower(bus_number + 1, "kilowatt"),
                }
            ),
            "equipment": SolarEquipment.example().model_copy(
                update={
                    "uuid": uuid4(),
                    "name": f"solar_equipment_{bus_number}",
                    "rated_power": ActivePower(1000, "kilowatt"),
                    "resistance": 1,
                    "reactance": 1,
                }
            ),
            "controller": InverterController.example().model_copy(
                update={
                    "uuid": uuid4(),
                    "name": f"inverter_controller_{bus_number}",
                }
            ),
            "array_power": ActivePower(1001, "watt"),
            "active_power": ActivePower(1001, "watt"),
            "reactive_power": ReactivePower(1001, "watt"),
            "irradiance": Irradiance(1000, "watt/m^2"),
        }
    )


def build_distribution_line(bus1: DistributionBus, bus2: DistributionBus):
    return MatrixImpedanceBranch.example().model_copy(
        update={
            "name": f"line_{bus1.name}_{bus2.name}",
            "uuid": uuid4(),
            "buses": [bus1, bus2],
        }
    )


def build_distribution_capacitor(bus: DistributionBus, bus_number: int):
    return DistributionCapacitor.example().model_copy(
        update={
            "name": f"capacitor_{bus.name}",
            "uuid": uuid4(),
            "bus": bus,
            "equipment": CapacitorEquipment.example().model_copy(
                update={
                    "uuid": uuid4(),
                    "name": f"capacitor_equipment_{bus_number}",
                    "rated_voltage": Voltage(120, "volt"),
                    "voltage_type": VoltageTypes.LINE_TO_GROUND,
                    "phase_capacitors": [
                        PhaseCapacitorEquipment.example().model_copy(
                            update={
                                "uuid": uuid4(),
                                "name": f"phase_capacitor_{i}_{bus_number}",
                                "rated_reactive_power": ReactivePower(bus_number + 1, "kvar"),
                                "resistance": Resistance(1, "ohm"),
                                "reactance": Reactance(1, "ohm"),
                            }
                        )
                        for i in range(3)
                    ],
                }
            ),
        }
    )


def build_distribution_xfmr(bus1: DistributionBus, bus2: DistributionBus):
    return DistributionTransformer.example().model_copy(
        update={
            "name": "substation_xfmr",
            "uuid": uuid4(),
            "buses": [bus1, bus2],
        }
    )


def build_distribution_voltage_source(bus: DistributionBus):
    return DistributionVoltageSource.example().model_copy(
        update={
            "bus": bus,
        }
    )


def build_source_bus():
    return DistributionBus.example().model_copy(
        update={
            "name": "src_bus",
            "uuid": uuid4(),
            "rated_voltage": Voltage(12.47, "kilovolt"),
            "coordinate": Location(
                x=(28.30551 - 28.29454) * random() + 28.29454,
                y=(-97.26956 - (-97.28051)) * random() + (-97.28051),
            ),
        }
    )


def build_split_phase_distribution_buses():
    return [
        DistributionBus.example().model_copy(
            update={
                "uuid": uuid4(),
                "name": f"split_phase_bus_{i}",
                "phases": [Phase.S1, Phase.S2, Phase.N],
                "rated_voltage": Voltage(120, "volt"),
                "voltage_type": VoltageTypes.LINE_TO_GROUND,
                "coordinate": Location(
                    x=(28.30551 - 28.29454) * random() + 28.29454,
                    y=(-97.26956 - (-97.28051)) * random() + (-97.28051),
                ),
            }
        )
        for i in range(10)
    ]


def build_split_phase_distribution_xfmr(bus1: DistributionBus, bus2: DistributionBus):
    return DistributionTransformer(
        name="split_phase_xfmr",
        buses=[bus1, bus2, bus2],
        winding_phases=[[Phase.A, Phase.B], [Phase.S1, Phase.N], [Phase.S2, Phase.N]],
        equipment=DistributionTransformerEquipment(
            name="split_phase_xfmr_equipment",
            pct_no_load_loss=0.1,
            pct_full_load_loss=1,
            is_center_tapped=True,
            coupling_sequences=[SequencePair(0, 1), SequencePair(0, 2), SequencePair(1, 2)],
            winding_reactances=[2.3] * 3,
            windings=[
                WindingEquipment(
                    resistance=1,
                    is_grounded=False,
                    rated_voltage=Voltage(0.4, "kilovolt"),
                    rated_power=ApparentPower(50, "kilova"),
                    connection_type=ConnectionType.STAR,
                    num_phases=1,
                    tap_positions=[1.0],
                    voltage_type=VoltageTypes.LINE_TO_LINE,
                ),
                WindingEquipment(
                    resistance=1,
                    is_grounded=True,
                    rated_voltage=Voltage(120, "volt"),
                    rated_power=ApparentPower(50, "kilova"),
                    connection_type=ConnectionType.STAR,
                    num_phases=1,
                    tap_positions=[1.0],
                    voltage_type=VoltageTypes.LINE_TO_GROUND,
                ),
                WindingEquipment(
                    resistance=1,
                    is_grounded=True,
                    rated_voltage=Voltage(120, "volt"),
                    rated_power=ApparentPower(50, "kilova"),
                    connection_type=ConnectionType.STAR,
                    num_phases=1,
                    tap_positions=[1.0],
                    voltage_type=VoltageTypes.LINE_TO_GROUND,
                ),
            ],
        ),
    )


def build_split_phase_matrix_impedance():
    return MatrixImpedanceBranchEquipment(
        name="matrix-impedance-branch-1",
        r_matrix=ResistancePULength(
            [
                [0.08820, 0.0312137],
                [0.0312137, 0.0901946],
            ],
            "ohm/mi",
        ),
        x_matrix=ReactancePULength(
            [
                [0.20744, 0.0935314],
                [0.0935314, 0.200783],
            ],
            "ohm/mi",
        ),
        c_matrix=CapacitancePULength(
            [
                [2.90301, -0.679335],
                [-0.679335, 3.15896],
            ],
            "nanofarad/mi",
        ),
        ampacity=Current(90, "ampere"),
    )


def build_split_phase_distribution_line(
    bus1: DistributionBus, bus2: DistributionBus, matrix: MatrixImpedanceBranchEquipment
):
    return MatrixImpedanceBranch(
        buses=[bus1, bus2],
        length=Distance(130.2, "meter"),
        phases=[Phase.S1, Phase.S2],
        name="DistBranch_{}_{}".format(bus1.name, bus2.name),
        equipment=matrix,
    )


def build_split_phase_loads(bus: DistributionBus, bus_number: int):
    return [
        DistributionLoad(
            name=f"load_{bus_number}_{phase}",
            bus=bus,
            phases=[phase],
            equipment=LoadEquipment(
                name=f"load_equipment_{bus_number}_{phase}",
                connection_type=ConnectionType.STAR,
                phase_loads=[
                    PhaseLoadEquipment(
                        name=f"phase_load_{bus_number}_{phase}",
                        real_power=ActivePower(bus_number + 1, "kilowatt"),
                        reactive_power=ReactivePower((bus_number + 1) * 0.44, "kilovar"),
                        z_real=0.75,
                        z_imag=1.0,
                        i_real=0.1,
                        i_imag=0.0,
                        p_real=0.15,
                        p_imag=0.0,
                    )
                ],
            ),
        )
        for phase in bus.phases
        if phase != Phase.N
    ]


def build_split_phase_solar(bus: DistributionBus, bus_number: int):
    return DistributionSolar(
        name=f"pv_{bus_number}",
        bus=bus,
        phases=[Phase.S1, Phase.S2],
        equipment=SolarEquipment(
            name=f"pv_equipment_{bus_number}",
            rated_power=ActivePower(bus_number + 1, "kilowatt"),
            resistance=1,
            reactance=1,
            rated_voltage=bus.rated_voltage,
            voltage_type=bus.voltage_type,
        ),
        inverter=InverterEquipment(
            rated_apparent_power=ApparentPower(3.8, "kva"),
            rise_limit=ActivePowerOverTime(1.1, "kW/second"),
            fall_limit=ActivePowerOverTime(1.1, "kW/second"),
            dc_to_ac_efficiency=100,
            cutin_percent=10,
            cutout_percent=10,
        ),
        controller=None,
        active_power=ActivePower(bus_number + 1, "kilowatt"),
        reactive_power=ReactivePower(bus_number + 1, "kilowatt"),
        irradiance=Irradiance(1000, "watt/m^2"),
    )


def sample_distribution_system() -> DistributionSystem:
    """Tests the DistributionSystem class."""

    # building primary
    system = DistributionSystem(auto_add_composed_components=True)
    buses = build_distribution_buses()
    load_bus_numbers = [5, 7, 9]
    solar_bus_numbers = [3, 9]
    capacity_bus_numbers = [4, 8]

    for bus_number, bus in enumerate(buses):
        system.add_component(bus)
        if bus_number in load_bus_numbers:
            load = build_distribution_load(bus, bus_number)
            system.add_component(load)
        if bus_number in solar_bus_numbers:
            solar = build_distribution_solar(bus, bus_number)
            system.add_component(solar)
        if bus_number in capacity_bus_numbers:
            capacitor = build_distribution_capacitor(bus, bus_number)
            system.add_component(capacitor)
        if bus_number != 0:
            line = build_distribution_line(buses[bus_number - 1], bus)
            system.add_component(line)

    # building substation
    src_bus = build_source_bus()
    substation_xfmr = build_distribution_xfmr(src_bus, buses[0])
    system.add_component(substation_xfmr)
    vsource = build_distribution_voltage_source(src_bus)
    system.add_component(vsource)

    # building secondary
    split_phase_buses = build_split_phase_distribution_buses()
    system.add_components(*split_phase_buses)
    split_phase_xfmr = build_split_phase_distribution_xfmr(buses[-1], split_phase_buses[0])
    system.add_component(split_phase_xfmr)

    split_phase_load_bus_numbers = [5, 7, 9]
    split_phase_solar_bus_numbers = [3, 9]
    matrix = build_split_phase_matrix_impedance()
    for bus_number, bus in enumerate(split_phase_buses):
        if bus_number != 0:
            split_phase_line = build_split_phase_distribution_line(
                split_phase_buses[bus_number - 1], bus, matrix
            )
            system.add_component(split_phase_line)
        if bus_number in split_phase_load_bus_numbers:
            split_phase_loads = build_split_phase_loads(bus, bus_number)
            system.add_components(*split_phase_loads)
        if bus_number in split_phase_solar_bus_numbers:
            distribution_solar = build_split_phase_solar(bus, bus_number)
            system.add_component(distribution_solar)

    return system
