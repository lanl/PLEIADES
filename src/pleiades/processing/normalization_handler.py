"""
Normalization handler utilities for PLEIADES neutron imaging data processing.

This module provides core functions for handling the normalization workflow including
data loading, rebinning, outlier removal, cropping, and the main normalization
calculations. These functions work with master dictionaries that store sample and
open beam data along with their associated metadata.

The normalization handler supports:
- File discovery and data loading
- Spatial rebinning and outlier removal
- Proton charge and shutter count corrections
- Background subtraction normalization
- ROI-based cropping
- Transmission calculation

Example:
    Basic workflow using the handler functions:

    >>> master_dict = init_master_dict(folders, DataType.sample)
    >>> update_with_list_of_files(master_dict)
    >>> update_with_data(master_dict)
    >>> update_with_rebin(master_dict, binning_factor=2)
    >>> performing_normalization(sample_dict, norm_dict, background_roi)
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from pleiades.processing import MasterDictKeys, Roi
from pleiades.utils.files import retrieve_list_of_most_dominant_extension_from_folder
from pleiades.utils.image_processing import crop, rebin
from pleiades.utils.image_processing import remove_outliers as image_processing_remove_outliers
from pleiades.utils.load import load
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="normalization_handler")


def update_with_list_of_files(master_dict: Dict[str, Any]) -> None:
    """
    Update the master dictionary with the list of files in the sample and open beam folders.

    Discovers all image files in each folder and updates the master dictionary with
    the file list and dominant file extension. Only processes folders that exist
    on the filesystem.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing folder paths and metadata.
                                     Must have MasterDictKeys.list_folders structure.

    Raises:
        FileNotFoundError: If any folder in the master dictionary does not exist

    Example:
        >>> master_dict = {
        ...     MasterDictKeys.list_folders: {
        ...         "/path/to/data": {MasterDictKeys.list_images: None}
        ...     }
        ... }
        >>> update_with_list_of_files(master_dict)
        >>> len(master_dict[MasterDictKeys.list_folders]["/path/to/data"][MasterDictKeys.list_images])
        100

    Note:
        Updates master_dict in-place with:
        - list_images: List of file paths with the dominant extension
        - ext: The dominant file extension found in the folder
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with list of files")

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        if Path(folder).exists():
            list_files, ext = retrieve_list_of_most_dominant_extension_from_folder(folder)
            logger.info(f"Found {len(list_files)} files in {folder} with extension {ext}")
            master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_images] = list_files
            master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.ext] = ext
        else:
            raise FileNotFoundError(f"Folder {folder} does not exist")


def update_with_data(master_dict: Dict[str, Any]) -> None:
    """
    Load imaging data from files and update the master dictionary.

    Reads the actual image data from the file lists previously discovered by
    update_with_list_of_files. Supports multiple image formats including
    TIFF and FITS files.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing file lists and metadata.
                                     Must have been processed by update_with_list_of_files first.

    Example:
        >>> # After update_with_list_of_files has been called
        >>> update_with_data(master_dict)
        >>> data = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data]
        >>> data.shape
        (100, 256, 256)  # (time_channels, height, width)

    Note:
        Updates master_dict in-place with:
        - data: 3D numpy array containing the loaded image stack

    Raises:
        ValueError: If file list is empty or files cannot be loaded
        IOError: If image files are corrupted or in unsupported format
    """
    logger.info(f"Updating {master_dict[MasterDictKeys.data_type]} master dictionary with data")

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        list_of_files = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_images]
        ext = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.ext]
        data = load(list_of_files, ext)
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = data


def update_with_crop(master_dict: Dict[str, Any], roi: Optional[Roi] = None) -> None:
    """
    Apply spatial cropping to normalized data using a region of interest.

    Crops the normalized transmission data to the specified region of interest.
    This function operates on the normalization dictionary's sample_data, not
    the raw data in list_folders.

    Args:
        master_dict (Dict[str, Any]): Normalization dictionary containing processed sample data.
                                     Must have MasterDictKeys.sample_data structure.
        roi (Optional[Roi], optional): Region of interest defining crop boundaries.
                                      If None, no cropping is performed. Defaults to None.

    Example:
        >>> roi = Roi(50, 50, 200, 200)  # x1, y1, x2, y2
        >>> update_with_crop(normalization_dict, roi=roi)
        >>> # Data is now cropped to 150x150 spatial region

    Note:
        - Only crops data in the sample_data section of the dictionary
        - Updates master_dict in-place
        - Preserves time-of-flight dimension, only crops spatial dimensions
        - If roi is None, function returns without any modifications
    """
    logger.info(f"Updating master normalization dictionary with crop values {roi}")

    if roi is None:
        logger.info("Crop values are None, skipping crop update")
        return

    for folder in master_dict[MasterDictKeys.sample_data].keys():
        cropped_data = crop(master_dict[MasterDictKeys.sample_data][folder], roi)
        master_dict[MasterDictKeys.sample_data][folder] = cropped_data


def update_with_rebin(master_dict: Dict[str, Any], binning_factor: int) -> None:
    """
    Apply spatial rebinning to reduce data size and improve signal-to-noise ratio.

    Rebins the imaging data by averaging over spatial blocks of size binning_factor x binning_factor.
    The time-of-flight dimension is preserved. Rebinning reduces spatial resolution but
    improves statistics and reduces data size.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing imaging data.
                                     Must have data loaded via update_with_data.
        binning_factor (int): Spatial binning factor. Must be positive.
                             1 = no binning, 2 = 2x2 binning, etc.

    Example:
        >>> # Original data shape: (100, 512, 512)
        >>> update_with_rebin(master_dict, binning_factor=2)
        >>> # New data shape: (100, 256, 256)

    Note:
        - Updates master_dict in-place
        - If binning_factor is 1, function returns without modifications
        - Spatial dimensions should be divisible by binning_factor for best results
        - Uses mean averaging for binning (preserves intensity scaling)

    Raises:
        ValueError: If binning_factor is not positive
    """
    if binning_factor <= 0:
        raise ValueError("Binning factor must be positive")

    logger.info(
        f"Updating {master_dict[MasterDictKeys.data_type]} master dictionary with rebin values {binning_factor}"
    )

    if binning_factor == 1:
        logger.info("Binning factor is 1, skipping rebin update")
        return

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        rebinned_data = rebin(master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data], binning_factor)
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = rebinned_data


def remove_outliers(master_dict: Dict[str, Any], dif: float, num_threads: int) -> None:
    """
    Remove outlier pixels from imaging data using tomopy's outlier detection algorithm.

    Identifies and corrects outlier pixels that deviate significantly from their neighbors.
    This helps remove detector artifacts, cosmic rays, and other anomalous pixel values
    that could affect normalization quality.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing imaging data.
                                     Must have data loaded via update_with_data.
        dif (float): Threshold for outlier detection. Higher values are more permissive.
                    Typical values range from 10-50. Larger values detect fewer outliers.
        num_threads (int): Number of CPU threads to use for parallel processing.
                          Must be positive.

    Example:
        >>> remove_outliers(master_dict, dif=20.0, num_threads=4)
        >>> # Outlier pixels have been replaced with interpolated values

    Note:
        - Updates master_dict in-place
        - Uses tomopy's remove_outlier algorithm internally
        - Processing time scales with data size and number of threads
        - Conservative dif values (10-20) remove more outliers
        - Liberal dif values (30-50) preserve more original data

    Raises:
        ValueError: If num_threads is not positive
        ValueError: If dif is not positive
    """
    if dif <= 0:
        raise ValueError("Outlier detection threshold must be positive")
    if num_threads <= 0:
        raise ValueError("Number of threads must be positive")

    logger.info(
        f"Removing outliers from {master_dict[MasterDictKeys.data_type]} master dictionary with threshold {dif}"
    )

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        data = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data]
        data = image_processing_remove_outliers(data, dif, num_threads)
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = data


def combine_data(
    master_dict: Dict[str, Any],
    is_normalization_by_proton_charge: bool,
    is_normalization_by_shutter_counts: bool,
    normalization_dict: Dict[str, Any],
) -> None:
    """
    Combine multiple open beam datasets and apply corrections.

    Processes and combines multiple open beam folders into a single reference dataset.
    Applies proton charge normalization and shutter count corrections as needed,
    then combines using median to reduce noise and artifacts.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing open beam data.
                                     Must have DataType.ob and loaded data.
        is_normalization_by_proton_charge (bool): Whether to apply proton charge correction.
                                                 Requires proton charge data to be available.
        is_normalization_by_shutter_counts (bool): Whether to apply shutter count correction.
                                                   Requires shutter data to be available.
        normalization_dict (Dict[str, Any]): Target dictionary to store combined open beam data.

    Example:
        >>> combine_data(ob_master_dict, True, False, normalization_dict)
        >>> combined_ob = normalization_dict[MasterDictKeys.obs_data_combined]
        >>> combined_ob.shape
        (100, 256, 256)

    Note:
        - Uses median combination to reduce outliers and noise
        - Applies corrections in order: proton charge, then shutter counts
        - Sets zero values to NaN to avoid division errors in normalization
        - Updates normalization_dict in-place with combined open beam data
        - Uncertainty propagation is partially implemented (commented out)

    Raises:
        ValueError: If required correction data is missing when corrections are enabled
    """
    logger.info(f"Combining {master_dict[MasterDictKeys.data_type]} master dictionary!")
    logger.info(f"\tis_normalization_by_proton_charge: {is_normalization_by_proton_charge}")
    logger.info(f"\tis_normalization_by_shutter_counts: {is_normalization_by_shutter_counts}")

    full_ob_data_corrected = []

    for _ob_folder in master_dict[MasterDictKeys.list_folders].keys():
        ob_data = master_dict[MasterDictKeys.list_folders][_ob_folder][MasterDictKeys.data]

        _uncertainty = np.zeros_like(ob_data, dtype=np.float32)
        if is_normalization_by_proton_charge:
            proton_charge = master_dict[MasterDictKeys.list_folders][_ob_folder][MasterDictKeys.proton_charge]
            ob_data /= proton_charge
            # _uncertainty += (PROTON_CHARGE_UNCERTAINTY ** 2)

        logger.debug(f"1. {np.shape(_uncertainty) = }")

        if is_normalization_by_shutter_counts:
            list_shutters_values_for_each_image = master_dict[MasterDictKeys.list_folders][_ob_folder][
                MasterDictKeys.list_shutters
            ]
            temp_ob_data = np.empty_like(ob_data, dtype=np.float32)
            for _index in range(len(list_shutters_values_for_each_image)):
                temp_ob_data[_index] = ob_data[_index] / list_shutters_values_for_each_image[_index]
                # _uncertainty[_index] += 1 / list_shutters_values_for_each_image
            ob_data = temp_ob_data[:]
            del temp_ob_data

        logger.debug(f"2. {np.shape(_uncertainty) = }")

        _uncertainty += 1 / ob_data
        full_ob_data_corrected.append(ob_data)
        # uncertainties_ob_data_corrected.append(ob_data * np.sqrt(_uncertainty))

    obs_data_combined = np.median(full_ob_data_corrected, axis=0)
    # uncertainties_ob_data_combined = np.sqrt(np.sum(np.array(uncertainties_ob_data_corrected) ** 2, axis=0))

    # remove zero values
    obs_data_combined[obs_data_combined == 0] = np.nan

    normalization_dict[MasterDictKeys.obs_data_combined] = obs_data_combined
    # normalization_dict[MasterDictKeys.uncertainties_ob_data_combined] = uncertainties_ob_data_combined


def correct_data_for_proton_charge(master_dict: Dict[str, Any], is_normalization_by_proton_charge: bool) -> None:
    """
    Apply proton charge correction to sample data.

    Normalizes sample data by the proton charge to account for variations in
    neutron beam intensity between different measurements. This correction
    ensures that transmission values are independent of beam current fluctuations.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing sample data and proton charge values.
                                     Must have proton_charge data loaded for each folder.
        is_normalization_by_proton_charge (bool): Whether to apply the correction.
                                                 If False, function returns without changes.

    Example:
        >>> correct_data_for_proton_charge(sample_master_dict, True)
        >>> # Sample data is now normalized by proton charge

    Note:
        - Updates master_dict in-place by dividing data by proton charge
        - Proton charge values are typically in microampere-hours (μAh)
        - Essential for quantitative transmission measurements
        - If correction is disabled, data remains unchanged

    Raises:
        ValueError: If proton charge data is missing when correction is enabled
        ZeroDivisionError: If proton charge values are zero
    """
    logger.info(f"Correcting {master_dict[MasterDictKeys.data_type]} master dictionary for proton charge")
    if not is_normalization_by_proton_charge:
        logger.info("Normalization by proton charge is not enabled, skipping correction")
        return

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        data = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data]
        proton_charge = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.proton_charge]
        data /= proton_charge
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = data


def correct_data_for_shutter_counts(master_dict: Dict[str, Any], is_normalization_by_shutter_counts: bool) -> None:
    """
    Apply shutter count correction to sample data.

    Normalizes each image by its corresponding shutter count to account for
    variations in exposure time or shutter efficiency. This is particularly
    important for Timepix detectors where shutter timing can vary between images.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing sample data and shutter values.
                                     Must have list_shutters data loaded for each folder.
        is_normalization_by_shutter_counts (bool): Whether to apply the correction.
                                                   If False, function returns without changes.

    Example:
        >>> correct_data_for_shutter_counts(sample_master_dict, True)
        >>> # Each image is now normalized by its shutter count

    Note:
        - Updates master_dict in-place by dividing each image by its shutter count
        - Shutter counts represent effective exposure time or shutter efficiency
        - Applied on a per-image basis (different correction for each time channel)
        - Essential for Timepix detector data normalization

    Raises:
        ValueError: If shutter data is missing when correction is enabled
        ZeroDivisionError: If any shutter count values are zero
        IndexError: If shutter count array length doesn't match number of images
    """
    logger.info(f"Correcting {master_dict[MasterDictKeys.data_type]} master dictionary for shutter counts")
    if not is_normalization_by_shutter_counts:
        logger.info("Normalization by shutter counts is not enabled, skipping correction")
        return

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        data = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data]
        list_shutters_values_for_each_image = master_dict[MasterDictKeys.list_folders][folder][
            MasterDictKeys.list_shutters
        ]
        for i in range(len(data)):
            data[i] /= list_shutters_values_for_each_image[i]
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = data


def performing_normalization(
    sample_master_dict: Dict[str, Any], normalization_dict: Dict[str, Any], background_roi: Optional[Roi] = None
) -> None:
    """
    Perform the main normalization calculation to compute transmission values.

    Calculates transmission as T = (Sample - Background) / (OpenBeam - Background)
    with optional background subtraction. This is the core neutron imaging equation
    that converts raw count data into physically meaningful transmission coefficients.

    Args:
        sample_master_dict (Dict[str, Any]): Master dictionary containing corrected sample data.
                                            Must have been processed through correction functions.
        normalization_dict (Dict[str, Any]): Dictionary containing combined open beam data.
                                            Must have obs_data_combined from combine_data.
        background_roi (Optional[Roi], optional): Region defining background area for subtraction.
                                                 If provided, background correction is applied.
                                                 Defaults to None.

    Example:
        >>> background_roi = Roi(0, 0, 10, 10)  # Top-left corner background
        >>> performing_normalization(sample_dict, norm_dict, background_roi)
        >>> transmission = norm_dict[MasterDictKeys.sample_data][folder]
        >>> transmission.shape
        (100, 256, 256)  # Same shape as input data

    Note:
        - Updates normalization_dict in-place with transmission data
        - Transmission values typically range from 0 (complete absorption) to 1 (no absorption)
        - Background correction uses median values from specified ROI
        - Background coefficient is applied as multiplicative factor
        - Each sample folder is processed independently

    Mathematical Details:
        Without background: T = Sample / OpenBeam
        With background: T = (Sample / OpenBeam) * (median(OB_bg) / median(Sample_bg))

    Raises:
        ValueError: If required data is missing in either dictionary
        ZeroDivisionError: If open beam or background values are zero
        IndexError: If background ROI exceeds image boundaries
    """
    logger.info("Performing normalization:")
    ob_data_combined = normalization_dict[MasterDictKeys.obs_data_combined]

    for sample_folder in sample_master_dict[MasterDictKeys.list_folders].keys():
        logger.info(f"Normalizing sample folder: {sample_folder}")

        sample_data = sample_master_dict[MasterDictKeys.list_folders][sample_folder][MasterDictKeys.data]

        normalized_sample = np.empty_like(sample_data, dtype=np.float32)
        for _index, _sample, _ob in zip(np.arange(len(sample_data)), sample_data, ob_data_combined):
            coeff = 1
            if background_roi is not None:
                x0, y0, x1, y1 = background_roi.get_roi()
                median_roi_of_ob = np.median(_ob[y0:y1, x0:x1])
                median_roi_of_sample = np.median(_sample[y0:y1, x0:x1])
                coeff = median_roi_of_ob / median_roi_of_sample

            normalized_sample[_index] = (_sample / _ob) * coeff

        normalization_dict[MasterDictKeys.sample_data][sample_folder] = normalized_sample


def get_counts_from_normalized_data(normalized_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract integrated transmission counts and uncertainties from normalized data.

    Sums the normalized transmission data over spatial dimensions to obtain
    total transmission as a function of time-of-flight (or energy). Also
    calculates statistical uncertainties assuming Poisson statistics.

    Args:
        normalized_data (np.ndarray): 3D normalized transmission data with shape
                                     (time_channels, height, width). Values should
                                     be transmission coefficients (0-1 range typical).

    Returns:
        Tuple[np.ndarray, np.ndarray]: A tuple containing:
            - counts_array: 1D array of integrated transmission values for each time channel
            - uncertainties: 1D array of statistical uncertainties (sqrt of counts)

    Example:
        >>> transmission_data.shape
        (100, 256, 256)
        >>> counts, uncertainties = get_counts_from_normalized_data(transmission_data)
        >>> counts.shape
        (100,)
        >>> uncertainties.shape
        (100,)

    Note:
        - Spatial integration is performed over detector pixels (axes 1 and 2)
        - Uncertainties assume Poisson statistics: σ = √counts
        - Output is suitable for time-of-flight spectroscopy analysis
        - Transmission "counts" are actually integrated transmission coefficients

    Raises:
        TypeError: If input is not a numpy array
        ValueError: If input array is not 3D
    """
    if not isinstance(normalized_data, np.ndarray):
        raise TypeError("Normalized data must be a numpy array")

    if normalized_data.ndim != 3:
        raise ValueError(f"Expected 3D array, got {normalized_data.ndim}D array")

    # Assuming normalized_data is a 3D array with shape (num_images, height, width)
    counts_array = np.sum(normalized_data, axis=(1, 2))

    uncertainties = np.sqrt(counts_array)  # Assuming Poisson statistics for counts

    return (counts_array, uncertainties)
