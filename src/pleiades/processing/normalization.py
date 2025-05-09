import os
import numpy as np

from pleiades.processing import Roi, MasterDictKeys, Facility, NormalizationStatus, DataType
from pleiades.utils.load import load
from pleiades.utils.image_processing import remove_outliers
from pleiades.utils.timepix import update_with_nexus_files
from pleiades.utils.timepix import update_with_shutter_counts
from pleiades.utils.timepix import update_with_proton_charge
from pleiades.utils.timepix import update_with_spectra_files
from pleiades.utils.timepix import update_with_shutter_values
from pleiades.processing.normalization_handler import update_with_list_of_files
from pleiades.processing.normalization_handler import update_with_data
from pleiades.processing.normalization_handler import update_with_crop
from pleiades.processing.normalization_handler import update_with_rebin
from pleiades.processing.normalization_handler import combine_data
from pleiades.processing.normalization_handler import remove_outliers
from pleiades.processing.normalization_handler import correct_data_for_proton_charge
from pleiades.processing.normalization_handler import correct_data_for_shutter_counts

from pleiades.utils.logger import loguru_logger
logger = loguru_logger.bind(name="normalization")

# input: 
#  - list_of_sample folders (tiff, fits)
#  - list_of_obs folders (tiff, fits)
# ROI (optional)

# if timepix
# - time spectra file will be used (.txt)
# - shutter count file will be used (.txt)
# if not timepix
# - need to retrieve the energy spectra file (from file name)

# if more than 1 OBS
# - OBs will be combined (using mean)

# - pixel binning (optional)
# - remove outliers (optional)
# - rolling average (optional) ?

# options:
# - normalization then rolling average
# - rolling average then normalization

# output:
#  - numpy (otional)
#  - output folder (optional)


def init_master_dict(list_folders: list, data_type: DataType = DataType.sample) -> dict:
    """
    Initialize a master dictionary to store the data from each sample and open beam folders.
    """
    master_dict = {MasterDictKeys.data_type: data_type,
                   MasterDictKeys.list_folders: {},
                   }
    for folder in list_folders:
        master_dict[MasterDictKeys.list_folders][folder] = {MasterDictKeys.nexus_path: None, 
                                                            MasterDictKeys.data: None,
                                                            MasterDictKeys.frame_number: None, 
                                                            MasterDictKeys.data_path: None, 
                                                            MasterDictKeys.proton_charge: None,
                                                            MasterDictKeys.matching_ob: [],
                                                            MasterDictKeys.list_images: [],
                                                            MasterDictKeys.ext: None, 
                                                            MasterDictKeys.shutter_counts: None,
                                                            MasterDictKeys.list_spectra: [],
                                                            MasterDictKeys.list_shutters: [],
                                                            MasterDictKeys.data: None}
    return master_dict


def init_normalization_dict(list_folders: list) -> dict:
    """
    Initialize a normalization dictionary to store the normalized data.
    """
    normalization_dict = {}
    for folder in list_folders:
        normalization_dict[folder] = {MasterDictKeys.obs_data_combined: None, 
                                      MasterDictKeys.sample_data: None,
                                    }
    return normalization_dict


def normalization(list_sample_folders: list, 
                  list_obs_folders: list, 
                  nexus_path: str = None,
                  background_roi: Roi = None, 
                  crop_roi: Roi = None,
                  timepix: bool = True, 
                  pixel_binning: int = 1, 
                  remove_outliers_flag: bool = False, 
                  rolling_average: bool = False, 
                  output_folder: str = None, 
                  output_numpy: bool = True,
                  facility=Facility.ornl,
                  num_threads: int = 1):
    """
    Normalize the data from the sample and observation folders.

    if more than 1 ob folder is provided, the data will be combined using the mean
    if more than 1 sample folder is provided, each folder will be processed separately

    if the nexus_path is provided, the proton charge will be retrieved from the nexus file
    if the timepix flag is True, the data will be normalized using the shutter values
    if the background_roi is provided, the data will be normalized using the background region
    if the crop_roi is provided, the data will be cropped to the region of interest
    if the pixel_binning is provided, the data will be binned using the binning factor
    if the remove_outliers_flag flag is True, the data will be filtered using the outlier removal method
    if the rolling_average flag is True, the data will be smoothed using the rolling average method
    if the output_folder is provided, the data will be saved in the folder
    if the output_numpy flag is True, the data will be saved as numpy arrays
    
    Parameters:
    - list_sample_folders: List of sample folders containing tiff or fits files.
    - list_obs_folders: List of open beam folders containing tiff or fits files.
    - nexus_path: Path to the nexus file (optional).
    - background_roi: Region of interest (optional) used to define the background region in sample data.
    - crop_roi: Region of interest (optional) used to define the crop region
    - timepix: Boolean indicating if timepix data is used.
    - pixel_binning: Pixel binning factor (1 means no binning).
    - output_numpy: Boolean indicating if the output should be saved as numpy arrays.
    - remove_outliers: Boolean indicating if outliers should be removed.
    - rolling_average: should a rolling average be applied.
    - output_folder: Folder to save the output (optional).
    - num_threads: Number of threads to use for processing (default is 1).

    Returns:
    - Normalized data.
    """
    
    logger.info("Starting normalization process...")
    logger.info(f"##############################")
    logger.info(f"\tSample folders: {list_sample_folders}")
    logger.info(f"\tOpen beam folders: {list_obs_folders}")
    logger.info(f"\tnexus path: {nexus_path}")
    logger.info(f"\tBackground ROI: {background_roi}")
    logger.info(f"\tCrop ROI: {crop_roi}")
    logger.info(f"\tTimepix: {timepix}")
    logger.info(f"\tPixel binning: {pixel_binning}")
    logger.info(f"\tRemove outliers flag: {remove_outliers_flag}")
    logger.info(f"\tRolling average: {rolling_average}")
    logger.info(f"\tOutput folder: {output_folder}")
    logger.info(f"\tOutput numpy: {output_numpy}")
    logger.info(f"\tNumber of threads: {num_threads}")
    logger.info(f"\tFacility: {facility}")
    logger.info(f"##############################")

    sample_normalization_status = NormalizationStatus()
    ob_normalization_status = NormalizationStatus()

    #checking all the inputs
    
    # Check if the input folders are valid
    if not list_sample_folders or not list_obs_folders:
        raise ValueError("Sample and observation folders must be provided.")
    
    if isinstance(list_sample_folders, str):
        list_sample_folders = [list_sample_folders]

    if isinstance(list_obs_folders, str):
        list_obs_folders = [list_obs_folders]

    sample_master_dict = init_master_dict(list_sample_folders, data_type=DataType.sample)
    ob_master_dict = init_master_dict(list_obs_folders, data_type=DataType.ob)
    normalization_dict = init_normalization_dict(list_sample_folders)

    # update with the nexus files
    update_with_nexus_files(sample_master_dict, sample_normalization_status, nexus_path, facility=facility)
    update_with_nexus_files(ob_master_dict, ob_normalization_status, nexus_path, facility=facility)

    # update with list of files in sample and open beam folders
    update_with_list_of_files(sample_master_dict)
    update_with_list_of_files(ob_master_dict)

    # update with proton charge
    update_with_proton_charge(sample_master_dict, sample_normalization_status, facility=facility)
    update_with_proton_charge(ob_master_dict, ob_normalization_status, facility=facility)

    # update with the shutter counts
    update_with_shutter_counts(sample_master_dict, sample_normalization_status, facility=facility)
    update_with_shutter_counts(ob_master_dict, ob_normalization_status, facility=facility)
    
    # update with spectra files
    update_with_spectra_files(sample_master_dict, sample_normalization_status, facility=facility)
    update_with_spectra_files(ob_master_dict, ob_normalization_status, facility=facility)

    # update with list of shutter values for each image
    update_with_shutter_values(sample_master_dict, sample_normalization_status, facility=facility)
    update_with_shutter_values(ob_master_dict, ob_normalization_status, facility=facility)

    # load data
    update_with_data(sample_master_dict)
    update_with_data(ob_master_dict)

    # crop the data if requested
    update_with_crop(sample_master_dict, roi=crop_roi)
    update_with_crop(ob_master_dict, roi=crop_roi)
        
    # rebin if requested
    update_with_rebin(sample_master_dict, binning_factor=pixel_binning)
    update_with_rebin(ob_master_dict, binning_factor=pixel_binning)

    # remove outliers if requested
    remove_outliers(sample_master_dict, dif=20, num_threads=num_threads)
    remove_outliers(ob_master_dict, dif=20, num_threads=num_threads)

    is_normalization_by_proton_charge = sample_normalization_status.all_proton_charge_value_found and ob_normalization_status.all_proton_charge_value_found
    is_normalization_by_shutter_counts = sample_normalization_status.all_shutter_counts_file_found and ob_normalization_status.all_shutter_counts_file_found

    # combine the obs
    combine_data(ob_master_dict, is_normalization_by_proton_charge, is_normalization_by_shutter_counts, normalization_dict)

    # correct the sample by proton charge
    correct_data_for_proton_charge(sample_master_dict, is_normalization_by_proton_charge)

    # correct the sample by shutter counts
    correct_data_for_shutter_counts(sample_master_dict, is_normalization_by_shutter_counts)

    # normalization
    ob_data_combined = normalization_dict[MasterDictKeys.obs_data_combined]
    for sample_folder in sample_master_dict[MasterDictKeys.list_folders].keys():
        logger.info(f"Normalizing sample folder: {sample_folder}")

        sample_data = sample_master_dict[MasterDictKeys.list_folders][sample_folder][MasterDictKeys.data]
    
        normalized_sample = np.empty_like(sample_data, dtype=np.float32)
        for _index, _sample, _ob in zip(np.arange(len(sample_data)), sample_data, ob_data_combined): 

            coeff = 1
            if not (background_roi is None):
                x0, y0, x1, y1 = background_roi.get_roi()
                median_roi_of_ob = np.median(_ob[y0:y1, x0:x1])
                median_roi_of_sample = np.median(_sample[y0:y1, x0:x1])
                coeff = median_roi_of_ob / median_roi_of_sample

            normalized_sample[_index] = (_sample / _ob) * coeff

        normalization_dict[sample_folder][MasterDictKeys.sample_data] = normalized_sample

    logger.info(f"Normalization completed successfully!")

if __name__ == "__main__":
    # Example usage
    normalization(
        list_sample_folders=["/Users/j35/SNS/VENUS/IPTS-35945/autoreduce/Run_7820"],
        list_obs_folders=["/Users/j35/SNS/VENUS/IPTS-35945/autoreduce/Run_7816"],
        nexus_path="/Users/j35/SNS/VENUS/IPTS-35945/nexus",
        background_roi=Roi(0, 0, 10, 10),
        crop_roi=Roi(10, 10, 200, 200),
        timepix=True,
        pixel_binning=2,
        remove_outliers_flag=False,
        rolling_average=False,
        output_folder="/Users/j35/SNS/IPTS-35945/processed",
        output_numpy=True,
        num_threads=4,
    )

