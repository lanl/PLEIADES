import os
import numpy as np

from pleiades.utils.logger import loguru_logger
logger = loguru_logger.bind(name="normalization_handler")

from pleiades.processing import NormalizationStatus, MasterDictKeys, Roi
from pleiades.utils.load import load
from pleiades.utils.image_processing import crop, rebin
from pleiades.utils.image_processing import  remove_outliers as image_processing_remove_outliers 
from pleiades.utils.files import retrieve_list_of_most_dominant_extension_from_folder


def update_with_list_of_files(master_dict: dict) -> None:
    """
    Update the master dictionary with the list of files in the sample and open beam folders.
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with list of files")
    
    for folder in master_dict[MasterDictKeys.list_folders].keys():
        if os.path.exists(folder):
            list_files, ext = retrieve_list_of_most_dominant_extension_from_folder(folder)
            logger.info(f"Found {len(list_files)} files in {folder} with extension {ext}")
            master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_images] = list_files
            master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.ext] = ext


def update_with_data(master_dict: dict):
    logger.info(f"Updating {master_dict[MasterDictKeys.data_type]} master dictionary with data")

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        list_of_files = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_images]
        ext = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.ext]
        data = load(list_of_files, ext)
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = data


def update_with_crop(master_dict: dict, roi=Roi) -> None:
    """
    Update the master dictionary with the crop values.
    """
    logger.info(f"Updating {master_dict[MasterDictKeys.data_type]} master dictionary with crop values {roi}")

    if roi is None:
        logger.info(f"Crop values are None, skipping crop update")
        return

    for folder in master_dict[MasterDictKeys.list_folders].keys():
            cropped_data = crop(master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data], roi) 
            master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = cropped_data


def update_with_rebin(master_dict: dict, binning_factor: int) -> None:
    """
    Update the master dictionary with the rebin values.
    """
    logger.info(f"Updating {master_dict[MasterDictKeys.data_type]} master dictionary with rebin values {binning_factor}")

    if binning_factor == 1:
        logger.info(f"Binning factor is 1, skipping rebin update")
        return

    for folder in master_dict[MasterDictKeys.list_folders].keys():
            rebinned_data = rebin(master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data], binning_factor)
            master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = rebinned_data


def remove_outliers(master_dict: dict, dif: float, num_threads: int) -> None:
    """
    Remove outliers from the data in the master dictionary.
    """
    logger.info(f"Removing outliers from {master_dict[MasterDictKeys.data_type]} master dictionary with threshold {dif}")

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        data = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data]
        data = image_processing_remove_outliers(data, dif, num_threads)
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = data


def combine_data(master_dict: dict, 
                sample_normalization_status: NormalizationStatus,
                ob_normalization_status: NormalizationStatus,
                normalization_dict: dict,
                ) -> None :
                
    """
    Combine the open beams data.
    """
    logger.info(f"Combining {master_dict[MasterDictKeys.data_type]} master dictionary!")
    is_normalization_by_proton_charge = sample_normalization_status.all_proton_charge_value_found and ob_normalization_status.all_proton_charge_value_found
    is_normalization_by_shutter_counts = sample_normalization_status.all_shutter_counts_file_found and ob_normalization_status.all_shutter_counts_file_found
    logger.info(f"\tis_normalization_by_proton_charge: {is_normalization_by_proton_charge}")
    logger.info(f"\tis_normalization_by_shutter_counts: {is_normalization_by_shutter_counts}")

    full_ob_data_corrected = []
    for _ob_folder in master_dict[MasterDictKeys.list_folders].keys():
        ob_data = master_dict[MasterDictKeys.list_folders][_ob_folder][MasterDictKeys.data]
        
        if is_normalization_by_proton_charge:
            proton_charge = master_dict[MasterDictKeys.list_folders][_ob_folder][MasterDictKeys.proton_charge]
            ob_data /= proton_charge

        if is_normalization_by_shutter_counts:
            list_shutters_values_for_each_image = master_dict[MasterDictKeys.list_folders][_ob_folder][MasterDictKeys.list_shutters]
            temp_ob_data = np.empty_like(ob_data, dtype=np.float32)
            for _index in range(len(list_shutters_values_for_each_image)):
                temp_ob_data[_index] = ob_data[_index] / list_shutters_values_for_each_image[_index]
            ob_data = temp_ob_data[:]
            del temp_ob_data

        full_ob_data_corrected.append(ob_data)

    obs_data_combined = np.median(full_ob_data_corrected, axis=0)

    # remove zero values
    obs_data_combined[obs_data_combined == 0] = np.nan

    normalization_dict[MasterDictKeys.obs_data_combined] = obs_data_combined
    