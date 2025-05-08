import os

from pleiades.utils.logger import loguru_logger
logger = loguru_logger.bind(name="normalization_handler")

from pleiades.processing import NormalizationStatus, MasterDictKeys, Roi
from pleiades.utils.load import load
from pleiades.utils.image_processing import crop, rebin
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
            