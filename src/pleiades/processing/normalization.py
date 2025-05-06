import os
import numpy as np

from pleiades.utils.files import retrieve_list_of_most_dominant_extension_from_folder
from pleiades.utils.load import load
from pleiades.utils.image_processing import rebin

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

class Roi:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def get_roi(self):
        return (self.x1, self.y1, self.x2, self.y2)

    def set_roi(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2


def normalization(list_sample_folders: list, 
                  list_obs_folders: list, 
                  nexus_sample_file: str = None,
                  nexus_obs_file: str = None,
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
    
    #checking all the inputs
    
    # Check if the input folders are valid
    if not list_sample_folders or not list_obs_folders:
        raise ValueError("Sample and observation folders must be provided.")
    
    if isinstance(list_sample_folders, str):
        list_sample_folders = [list_sample_folders]

    if isinstance(list_obs_folders, str):
        list_obs_folders = [list_obs_folders]

    for sample_folder in list_sample_folders:
        if not os.path.exists(sample_folder):
            raise ValueError(f"Sample folder {sample_folder} does not exist.")

        # retrieve list of files in the sample folder
        list_sample_files = retrieve_list_of_most_dominant_extension_from_folder(sample_folder)

        # load the sample data
        list_sample_data = load(list_sample_files)
        
        # crop the data if requested
        if crop_roi is not None:
            x1, y1, x2, y2 = crop_roi.get_roi()
            list_sample_data = list_sample_data[:, y1:y2, x1:x2]

        # rebin the data if requested
        if pixel_binning > 1:
            list_sample_data = rebin(list_sample_data, pixel_binning)
        
     