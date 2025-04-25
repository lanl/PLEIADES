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


def normalization(list_sample_folders: list, list_obs_folders: list, 
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

    Parameters:
    - list_sample_folders: List of sample folders containing tiff or fits files.
    - list_obs_folders: List of open beam folders containing tiff or fits files.
    - background_roi: Region of interest (optional) used to define the background region in sample data.
    - crop_roi: Region of interest (optional) used to define the crop region
    - timepix: Boolean indicating if timepix data is used.
    - pixel_binning: Pixel binning factor (optional).
    - remove_outliers: Boolean indicating if outliers should be removed (optional).
    - rolling_average: Rolling average window size (optional).
    - output_folder: Folder to save the output (optional).

    Returns:
    - Normalized data.
    """
    pass