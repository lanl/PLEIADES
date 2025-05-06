import os
import numpy as np

from pleiades.processing import Roi
from pleiades.utils.files import retrieve_list_of_most_dominant_extension_from_folder
from pleiades.utils.load import load
from pleiades.utils.image_processing import rebin, crop, combine
from pleiades.utils.nexus import is_normalization_by_proton_charge

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


def normalization(list_sample_folders: list, 
                  list_obs_folders: list, 
                  list_nexus_sample_file: str = None,
                  list_nexus_obs_file: str = None,
                  background_roi: Roi = None, 
                  crop_roi: Roi = None,
                  timepix: bool = True, 
                  pixel_binning: int = 1, 
                  remove_outliers: bool = False, 
                  rolling_average: bool = False, 
                  output_folder: str = None, 
                  output_numpy: bool = True):
    """
    Normalize the data from the sample and observation folders.

    if more than 1 ob folder is provided, the data will be combined using the mean
    if more than 1 sample folder is provided, each folder will be processed separately

    if the nexus files (sample and obs) are provided, the data will be normalized using the proton charge value
    if the timepix flag is True, the data will be normalized using the shutter values
    if the background_roi is provided, the data will be normalized using the background region
    if the crop_roi is provided, the data will be cropped to the region of interest
    if the pixel_binning is provided, the data will be binned using the binning factor
    if the remove_outliers flag is True, the data will be filtered using the outlier removal method
    if the rolling_average flag is True, the data will be smoothed using the rolling average method
    if the output_folder is provided, the data will be saved in the folder
    if the output_numpy flag is True, the data will be saved as numpy arrays
    


    Parameters:
    - list_sample_folders: List of sample folders containing tiff or fits files.
    - list_obs_folders: List of open beam folders containing tiff or fits files.
    - list_nexus_sample_file: Nexus sample file (optional) used to retrieve the proton charge value.
    - list_nexus_obs_file: Nexus observation file (optional) used to retrieve the proton charge value.
    - background_roi: Region of interest (optional) used to define the background region in sample data.
    - crop_roi: Region of interest (optional) used to define the crop region
    - timepix: Boolean indicating if timepix data is used.
    - pixel_binning: Pixel binning factor (1 means no binning).
    - output_numpy: Boolean indicating if the output should be saved as numpy arrays.
    - remove_outliers: Boolean indicating if outliers should be removed.
    - rolling_average: should a rolling average be applied.
    - output_folder: Folder to save the output (optional).

    Returns:
    - Normalized data.
    """
    
    logger.info("Starting normalization process...")
    logger.info(f"##############################")
    logger.info(f"\tSample folders: {list_sample_folders}")
    logger.info(f"\tOpen beam folders: {list_obs_folders}")
    logger.info(f"\tNexus sample files: {list_nexus_sample_file}")
    logger.info(f"\tNexus obs files: {list_nexus_obs_file}")
    logger.info(f"\tBackground ROI: {background_roi}")
    logger.info(f"\tCrop ROI: {crop_roi}")
    logger.info(f"\tTimepix: {timepix}")
    logger.info(f"\tPixel binning: {pixel_binning}")
    logger.info(f"\tRemove outliers: {remove_outliers}")
    logger.info(f"\tRolling average: {rolling_average}")
    logger.info(f"\tOutput folder: {output_folder}")
    logger.info(f"\tOutput numpy: {output_numpy}")
    logger.info(f"##############################")

    #checking all the inputs
    
    # Check if the input folders are valid
    if not list_sample_folders or not list_obs_folders:
        raise ValueError("Sample and observation folders must be provided.")
    
    if isinstance(list_sample_folders, str):
        list_sample_folders = [list_sample_folders]

    if isinstance(list_obs_folders, str):
        list_obs_folders = [list_obs_folders]

    proton_charge_dict = get_proton_charge_dict(list_sample_nexus = list_nexus_sample_file,
                                                list_nexus_obs = list_nexus_obs_file,
                                                nbr_sample_folders = len(list_sample_folders),
                                                nbr_obs_folders = len(list_obs_folders))

    # process open beams
    for obs_folder in list_obs_folders:
        if not os.path.exists(obs_folder):
            raise ValueError(f"Observation folder {obs_folder} does not exist.")

        # retrieve list of files in the observation folder
        list_obs_files, ext = retrieve_list_of_most_dominant_extension_from_folder(obs_folder)

        # load the observation data
        list_obs_data = load(list_obs_files, ext)

        # crop the data if requested
        if crop_roi is not None:
            list_obs_data = crop(list_obs_data, crop_roi)

        # rebin the data if requested
        if pixel_binning > 1:
            list_obs_data = rebin(list_obs_data, pixel_binning)

        # combine the normalized data
        if len(list_obs_data) > 1:
            ob_data = combine(list_obs_data)
        else:
            ob_data = list_obs_data[0]

    for sample_folder in list_sample_folders:
        if not os.path.exists(sample_folder):
            raise ValueError(f"Sample folder {sample_folder} does not exist.")

        # retrieve list of files in the sample folder
        list_sample_files, ext = retrieve_list_of_most_dominant_extension_from_folder(sample_folder)

        # load the sample data
        list_sample_data = load(list_sample_files, ext)
        
        # crop the data if requested
        if crop_roi is not None:
            list_sample_data = crop(list_sample_data, crop_roi)

        # rebin the data if requested
        if pixel_binning > 1:
            list_sample_data = rebin(list_sample_data, pixel_binning)

        # 


if __name__ == "__main__":
    # Example usage
    normalization(
        list_sample_folders=["/Users/j35/SNS/VENUS/IPTS-35945/autoreduce/Run_7820"],
        list_obs_folders=["/Users/j35/SNS/VENUS/IPTS-35945/autoreduce/Run_7816"],
        list_nexus_sample_file=["/Users/j35/SNS/VENUS/IPTS-35945/nexus/VENUS_7820.nxs.h5"],
        list_nexus_obs_file=["/Users/j35/SNS/VENUS/IPTS-35945/nexus/VENUS_7816.nxs.h5"],
        # background_roi=Roi(0, 0, 10, 10),
        crop_roi=Roi(10, 10, 200, 200),
        timepix=True,
        pixel_binning=2,
        remove_outliers=True,
        rolling_average=True,
        output_folder="/Users/j35/SNS/IPTS-35945/processed",
        output_numpy=True
    )

