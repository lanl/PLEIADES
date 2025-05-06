import numpy as np

from pleiades.processing import Roi
from skimage.measure import block_reduce


def crop(data: np.ndarray, roi: Roi) -> np.ndarray:
    """
    Crop a 2D array using the provided region of interest (ROI).
    The ROI is defined as a Roi object:
        - (x1, y1) is the top-left corner
        - (x2, y2) is the bottom-right corner
    """

    x1, y1, x2, y2 = roi.get_roi()
    tof_dim, y_dim, x_dim = data.shape

    if y2 > y_dim or y1 >= y_dim or x2 > x_dim or x1 > x_dim:
        raise IndexError("ROI exceeds array bounds. Please check the ROI coordinates.")
    
    cropped_data = data[:, y1:y2, x1:x2]
    
    return cropped_data


def rebin(data: np.ndarray, binning_factor: int) -> np.ndarray:
    """
    Rebin a 2D array by averaging over blocks of size binning_factor x binning_factor.
    """

    block_size = (1, binning_factor, binning_factor)

    rebinned_data = block_reduce(data,
                                 block_size=block_size,
                                 func=np.mean,
                                 func_kwargs={'dtype': np.float16})

    return rebinned_data


def combine(data: np.ndarray) -> np.ndarray:
    """
    Combine multiple 2D arrays using np.median
    """
    if data is None or len(data) == 0:
        raise ValueError("No data provided for combination.")
  
    combined_data = np.median(data, axis=0)
    return combined_data
