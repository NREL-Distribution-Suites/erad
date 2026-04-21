from pathlib import Path
from math import ceil
import pandas as pd
from datetime import datetime
import glob

from gdm.distribution.distribution_system import DistributionSystem
from gdm.distribution import CatalogSystem
from gdm.distribution.components import MatrixImpedanceBranch, GeometryBranch
from gdm.distribution.equipment import (
    BareConductorEquipment,
    ConcentricCableEquipment,
    GeometryBranchEquipment,
)
from gdm.distribution.enums import WireInsulationType
from gdm.quantities import Distance
from gdmloader.constants import GCS_CASE_SOURCE
from gdmloader.source import SystemLoader
from gdm.tracked_changes import PropertyEdit, TrackedChange, apply_updates_to_system
import json

gdm_loader = SystemLoader()
gdm_loader.add_source(GCS_CASE_SOURCE)


catalog_system: CatalogSystem = gdm_loader.load_dataset(
    system_type=CatalogSystem,
    source_name="gdm_data",
    dataset_name="gdm_catalog",
)
bare_conductors = list(catalog_system.get_components(BareConductorEquipment))
concentric_cables = list(catalog_system.get_components(ConcentricCableEquipment))


root_path = "/Users/mmuralid/Documents/naerm2025/texas/gdm_timeseries_models/"
region = "P49U"
dir_path = Path(root_path) / region

# iterate over .json files in this folder
for file in dir_path.glob("*.json"):
    file_path = str(file)
    print(f"Processing file: {file_path}")
    system = DistributionSystem.from_json(file_path)
    system.auto_add_composed_components = True
    # system.info()

    # Update GDM MatrixImpedanceBranch to GeometryBranch with bare conductors from catalog
    branch_data = []
    for branch in system.get_components(MatrixImpedanceBranch):
        bus_names = [bus.name for bus in branch.buses]
        ampacity = branch.equipment.ampacity.magnitude
        # Find conductor with closest ampacity
        closest_conductor = min(bare_conductors, key=lambda x: abs(x.ampacity.magnitude - ampacity))
        name = branch.name
        uuid = branch.uuid
        branch_data.append((uuid, name, bus_names, ampacity,closest_conductor.name, closest_conductor.ampacity.magnitude))
        df = pd.DataFrame(branch_data, columns=['UUID','Branch Name', 'Buses', 'Ampacity (A)', 'Bare Conductor Name', 'Conductor Ampacity (A)'])

    geometry_branches = []
    for branch in system.get_components(MatrixImpedanceBranch):
        # Get conductor name from branch_data
        conductor_name = df.loc[df['Branch Name'] == branch.name, 'Bare Conductor Name'].values[0]
        conductor = next(c for c in bare_conductors if c.name == conductor_name)

        geometry_branch = GeometryBranch(
            name = branch.name,
            substation=branch.substation,
            feeder=branch.feeder,
            in_service=branch.in_service,
            buses=branch.buses,
            length=branch.length,
            phases=branch.phases,
            equipment=GeometryBranchEquipment(
                name=branch.equipment.name,
                conductors=[conductor],
                horizontal_positions=Distance([1.0], "m"),    
                vertical_positions=Distance([0.0] , "m"),
            )    
        )
        geometry_branches.append(geometry_branch)
        system.remove_component(branch, force = True)
    system.add_components(*geometry_branches)
    system.to_json("/Users/mmuralid/Documents/naerm2025/texas/gdm_timeseries_models/" + region + "/geometry_models/" + Path(file_path).stem + "_base_sys.json", overwrite=True)
    # print("Base system with bare conductors:")
    # system.info()

    # Upgrade GeometryBranch conductors to concentric cables from catalog
    system_changes = []
    for branch in system.get_components(GeometryBranch):
        # Find cable and number of parallel runs needed for conductor upgrade to concentric cable with 150% or higher ampacity from catalog
        ampacity = branch.equipment.conductors[0].ampacity.magnitude
        cables_above_conductor_amp = [c for c in concentric_cables if c.ampacity.magnitude >= 1.5 * ampacity]
        if cables_above_conductor_amp:
            best_cable = sorted(
                cables_above_conductor_amp, key=lambda c: (
                    -c.ampacity.magnitude,                     # Highest ampacity first
                    c.phase_ac_resistance.magnitude,           # Lowest AC resistance
                    0 if c.insulation == WireInsulationType.XLPE else 1,  # XLPE preferred
                    -c.conductor_diameter.magnitude            # Largest conductor diameter
                )
            )[0]
            num_parallel_runs = 1
        else:
            # Find cable with largest ampacity in catalog
            best_cable = max(concentric_cables, key=lambda c: c.ampacity.magnitude)
            num_parallel_runs = ceil(ampacity/best_cable.ampacity.magnitude)
        
        new_equipment = GeometryBranchEquipment(
            name="equipment",
            conductors=[best_cable] * num_parallel_runs,
            horizontal_positions=Distance([i * 0.3 for i in range(num_parallel_runs)], "m"),    
            vertical_positions=Distance([0.0] * num_parallel_runs, "m"),
        )
        new_equipment = new_equipment.model_copy(update={"insulation": best_cable.insulation}) # insulation is frozen field hence needs to be updated this way
        system_changes.append(
            TrackedChange(
            scenario_name="underground_upgrade",
            edits=[
                PropertyEdit(
                component_uuid=branch.uuid,
                name="equipment", 
                value=new_equipment
                )
            ]
            )
        )
        
    mod_system = apply_updates_to_system(tracked_changes=system_changes, system=system, catalog=catalog_system)
    mod_system.to_json("/Users/mmuralid/Documents/naerm2025/texas/gdm_timeseries_models/" + region + "/geometry_models/" + Path(file_path).stem + "_mod_sys.json", overwrite=True)
    # print("Modified system with concentric cables:")
    # mod_system.info()
