import os
import glob
import pandas as pd
import numpy as np

from pleiades.processing import MasterDictKeys, Facility, NormalizationStatus
from pleiades.utils.nexus import get_proton_charge
from pleiades.utils.files import retrieve_number_of_frames_from_file_name
from pleiades.utils.files import retrieve_time_bin_size_from_file_name

from pleiades.utils.logger import loguru_logger
logger = loguru_logger.bind(name="timepix")


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
    

def update_with_nexus_files(master_dict: dict, 
                            normalization_status: NormalizationStatus, 
                            nexus_path: str, 
                            facility=Facility.ornl) -> None:
    """
    Update the master dictionary with the nexus files.
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with nexus files")

    if nexus_path is None:
        return

    if facility == Facility.ornl:
        update_with_nexus_files_at_ornl(master_dict, normalization_status, nexus_path)
    elif facility == Facility.lanl:
        # Implement the logic for LANL if needed
        pass
    else:
        raise ValueError(f"Unknown facility: {facility}. Supported facilities are: {Facility.ornl}, {Facility.lanl}.")


def update_with_nexus_files_at_ornl(master_dict: dict, 
                                    normalization_status: NormalizationStatus, 
                                    nexus_path: str) -> None:

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        run_number = isolate_run_number(folder)
        if run_number == -1:
            return
        
        nexus_file = os.path.join(nexus_path, f"VENUS_{run_number}.nxs.h5")
        if os.path.exists(nexus_file):
            master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.nexus_path] = nexus_file
        else:
            return
        
    normalization_status.all_nexus_file_found = True

def update_with_proton_charge(master_dict: dict, 
                              normalization_status: NormalizationStatus, 
                              facility=Facility.ornl) -> None:
    """
    Update the master dictionary with the proton charge values.
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with proton charge values")

    if facility == Facility.ornl:
        update_with_proton_charge_at_ornl(master_dict, normalization_status)
    elif facility == Facility.lanl:
        # Implement the logic for other facilities if needed
        pass
    else:
        raise ValueError(f"Unknown facility: {facility}. Supported facilities are: {Facility.ornl}, {Facility.lanl}.")


def update_with_proton_charge_at_ornl(master_dict: dict, 
                                      normalization_status: NormalizationStatus) -> None:
    """
    Update the master dictionary with the proton charge values for ORNL.
    """

    for key in master_dict[MasterDictKeys.list_folders].keys():
        nexus = master_dict[MasterDictKeys.list_folders][key][MasterDictKeys.nexus_path]
        proton_charge = get_proton_charge(nexus, units='c')
        if proton_charge is not None:
            master_dict[MasterDictKeys.list_folders][key][MasterDictKeys.proton_charge] = proton_charge
        else:
            pass

    normalization_status.all_proton_charge_value_found = True

def update_with_shutter_counts(master_dict: dict, 
                               normalization_status: NormalizationStatus, 
                               facility=Facility.ornl) -> None:
    """
    Update the master dictionary with the shutter counts.
    """

    if facility == Facility.ornl:
        update_with_shutter_counts_at_ornl(master_dict, normalization_status)
    elif facility == Facility.lanl:
        pass
    else:
        raise ValueError(f"Unknown facility: {facility}. Supported facilities are: {Facility.ornl}, {Facility.lanl}.")
    

def update_with_shutter_counts_at_ornl(master_dict: dict, normalization_status: NormalizationStatus) -> None:
    """
    Update the master dictionary with the shutter counts for ORNL.
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with shutter counts")

    for data_path in master_dict[MasterDictKeys.list_folders].keys():

        logger.info(f"\tUpdating shutter counts for {data_path}")
        _list_files = glob.glob(os.path.join(data_path, "*_ShutterCount.txt"))
        if len(_list_files) == 0:
            logger.info(f"\tNo shutter count file found for {data_path}")
            return
        
        else:
            shutter_count_file = _list_files[0]
            with open(shutter_count_file, 'r') as f:
                lines = f.readlines()
                list_shutter_counts = []
                for _line in lines:
                    _, _value = _line.strip().split("\t")
                    if _value == "0":
                        break
                    list_shutter_counts.append(float(_value))
                logger.info(f"\tShutter counts: {list_shutter_counts}")
                master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.shutter_counts] = list_shutter_counts
    
    normalization_status.all_shutter_counts_file_found = True


def update_with_spectra_files(master_dict: dict, 
                            normalization_status: NormalizationStatus, 
                            facility=Facility.ornl) -> None:
    """
    Update the master dictionary with the spectra files.
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with spectra files")

    if facility == Facility.ornl:
        update_with_spectra_files_at_ornl(master_dict, normalization_status)
    elif facility == Facility.lanl:
        update_with_spectra_files_at_lanl(master_dict, normalization_status)
    else:
        # Implement the logic for other facilities if needed
        pass


def update_with_spectra_files_at_ornl(master_dict: dict, normalization_status: NormalizationStatus) -> None:
    """
    Update the master dictionary with the spectra files for ORNL.
    """
    for data_path in master_dict[MasterDictKeys.list_folders].keys():
        spectra_files = glob.glob(os.path.join(data_path, "*_Spectra.txt"))
        if len(spectra_files) == 0:
            logger.info(f"\tNo spectra file found for {data_path}")
            return

        else:
            spectra_file = spectra_files[0]
            pd_spectra = pd.read_csv(spectra_file, sep=",", header=0)
            shutter_time = pd_spectra["shutter_time"].values
            master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.list_spectra] = shutter_time

    normalization_status.all_spectra_file_found = True


def update_with_spectra_files_at_lanl(master_dict: dict, normalization_status: NormalizationStatus) -> None:
    """
    Update the master dictionary with the spectra files for LANL.
    for LANL, the time spectra can be build up using the metadata contained in the files name.

    for example:
    file_name = image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff
    where T2000 is the number of time bins
          t1e6 is the time bin size in microseconds (1e6 -> 1e-6)
    """
    for folder in master_dict[MasterDictKeys.list_folders].keys():
        list_files = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_images]

        # extract number of time bins and time bin size from the first file name
        if len(list_files) == 0:
            logger.info(f"\tNo spectra file found for {folder}")
            return
        
        first_file_name = os.path.basename(list_files[0])
        number_of_frames = retrieve_number_of_frames_from_file_name(first_file_name)
        bin_size = retrieve_time_bin_size_from_file_name(first_file_name)

        # create the time spectra
        time_spectra = np.arange(0, number_of_frames * bin_size, bin_size)
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_spectra] = time_spectra
     
    
def update_with_shutter_values(master_dict: dict,
                               normalization_status: NormalizationStatus, 
                               facility=Facility.ornl) -> None:
     """
     Update the master dictionary with the shutter values.
     """
     logger.info(f"Updating {master_dict[MasterDictKeys.data_type]} master dictionary with shutter values")
     if facility == Facility.ornl:
          update_with_shutter_values_at_ornl(master_dict, normalization_status)
     else:
          # Implement the logic for other facilities if needed
          pass
     

def update_with_shutter_values_at_ornl(master_dict: dict, 
                                       normalization_status: NormalizationStatus) -> None:
    """
    Update the master dictionary with the shutter values for ORNL.
    """
    if normalization_status.all_shutter_counts_file_found and normalization_status.all_spectra_file_found:
        for data_path in master_dict[MasterDictKeys.list_folders].keys():
            list_time_spectra = master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.list_spectra]
            # delta_time_spectra = list_time_spectra[1] - list_time_spectra[0]
            list_index_jump = np.where(np.diff(list_time_spectra) > 0.0001)[0]

            list_shutter_counts = master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.shutter_counts]
            list_shutter_values_for_each_image = np.zeros(len(list_time_spectra), dtype=np.float32)
            list_shutter_values_for_each_image[0: list_index_jump[0]+1].fill(list_shutter_counts[0])
            for _index in range(1, len(list_index_jump)):
                _start = list_index_jump[_index - 1]
                _end = list_index_jump[_index]
                list_shutter_values_for_each_image[_start+1: _end+1].fill(list_shutter_counts[_index])

            list_shutter_values_for_each_image[list_index_jump[-1]+1:] = list_shutter_counts[-1]

            master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.list_shutters] = list_shutter_values_for_each_image

        normalization_status.all_list_shutter_values_for_each_image_found = True
