import numpy as np
from skimage.measure import block_reduce
from tomopy.misc.corr import remove_outlier as tomopy_remove_outlier

from pleiades.processing import Roi
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="image_processing")


def crop(data: np.ndarray, roi: Roi) -> np.ndarray:
    """
    Crop a 2D array using the provided region of interest (ROI).
    The ROI is defined as a Roi object:
        - (x1, y1) is the top-left corner
        - (x2, y2) is the bottom-right corner
    """
    logger.info(f"Cropping data with shape {data.shape} using ROI: {roi}")

    x1, y1, x2, y2 = roi.get_roi()
    tof_dim, y_dim, x_dim = data.shape

    if y2 > y_dim or y1 >= y_dim or x2 > x_dim or x1 > x_dim:
        logger.error(f"ROI exceeds array bounds: {roi}")
        raise IndexError("ROI exceeds array bounds. Please check the ROI coordinates.")

    cropped_data = data[:, y1:y2, x1:x2]

    logger.info(f"Cropped data shape: {cropped_data.shape}")
    return cropped_data


def rebin(data: np.ndarray, binning_factor: int) -> np.ndarray:
    """
    Rebin a 2D array by averaging over blocks of size binning_factor x binning_factor.
    """
    logger.info(f"Rebinning data with shape {data.shape} using binning factor: {binning_factor}")

    block_size = (1, binning_factor, binning_factor)

    rebinned_data = block_reduce(data, block_size=block_size, func=np.mean, func_kwargs={"dtype": np.float16})

    logger.info(f"Rebinned data shape: {rebinned_data.shape}")
    return rebinned_data


def remove_outliers(data: np.ndarray, dif: float, num_threads: int) -> np.ndarray:
    """
    Remove outliers from a 2D array using tomopy remove_outliers.
    https://tomopy.readthedocs.io/en/stable/api/tomopy.misc.corr.html#tomopy.misc.corr.remove_outlier
    """
    logger.info(f"Removing outliers from data with shape {data.shape} using threshold: {dif}")

    if data is None or len(data) == 0:
        raise ValueError("No data provided for outlier removal.")

    _data = np.array(data, dtype=np.float32)
    cleaned_data = tomopy_remove_outlier(_data, dif=dif, ncore=num_threads)

    logger.info(f"Outliers removed. Data shape: {cleaned_data.shape} and data type: {cleaned_data.dtype}")
    return cleaned_data
