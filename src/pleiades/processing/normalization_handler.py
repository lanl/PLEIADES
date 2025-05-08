import os

from pleiades.processing import NormalizationStatus, MasterDictKeys
from pleiades.utils.logger import loguru_logger
logger = loguru_logger.bind(name="normalization_handler")

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
     
