import os

from pleiades.processing import MasterDictKeys, Facility
from pleiades.utils.nexus import get_proton_charge


def get_shutter_values_dict(list_sample_folders: list, list_obs_folders: list, timepix: object) -> dict:
    """
    Get the shutter values from the timepix object for the given sample and observation folders.
    """
    shutter_values_dict = {
        'sample': {},
        'ob': {}
    }

    for folder in list_sample_folders:
        shutter_values_dict['sample'][folder] = timepix.get_shutter_values(folder)

    for folder in list_obs_folders:
        shutter_values_dict['ob'][folder] = timepix.get_shutter_values(folder)

    return shutter_values_dict


def isolate_run_number(run_number_full_path: str) -> int:
    run_number = os.path.basename(run_number_full_path)
    try:
        run_number = run_number.split("_")[1]
        return run_number
    except IndexError:
        return -1
    

def update_with_nexus_files(master_dict: dict, nexus_path: str, facility=Facility.ornl) -> None:
    """
    Update the master dictionary with the nexus files.
    """
    if nexus_path is None:
        return

    if facility == Facility.ornl:
        update_with_nexus_files_at_ornl(master_dict, nexus_path)
    elif facility == Facility.lanl:
        # Implement the logic for LANL if needed
        pass
    else:
        raise ValueError(f"Unknown facility: {facility}. Supported facilities are: {Facility.ornl}, {Facility.lanl}.")


def update_with_nexus_files_at_ornl(master_dict: dict, nexus_path: str) -> None:

    for folder in master_dict.keys():
        run_number = isolate_run_number(folder)
        if run_number == -1:
            return
        
        nexus_file = os.path.join(nexus_path, f"VENUS_{run_number}.nxs.h5")
        if os.path.exists(nexus_file):
            master_dict[folder][MasterDictKeys.nexus_path] = nexus_file
        else:
            return

def update_with_proton_charge(master_dict: dict, facility=Facility.ornl) -> None:
    """
    Update the master dictionary with the proton charge values.
    """

    if facility == Facility.ornl:
        update_with_proton_charge_at_ornl(master_dict)
    else:
        # Implement the logic for other facilities if needed
        pass


def update_with_proton_charge_at_ornl(master_dict: dict) -> None:
    """
    Update the master dictionary with the proton charge values for ORNL.
    """

    for key in master_dict.keys():
        nexus = master_dict[key][MasterDictKeys.nexus_path]
        proton_charge = get_proton_charge(nexus, units='c')
        if proton_charge is not None:
            master_dict[key][MasterDictKeys.proton_charge] = proton_charge
        else:
            pass
