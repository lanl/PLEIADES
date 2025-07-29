import os

import numpy as np

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="normalization_handler")

from pleiades.processing import MasterDictKeys, Roi
from pleiades.utils.files import retrieve_list_of_most_dominant_extension_from_folder
from pleiades.utils.image_processing import crop, rebin
from pleiades.utils.image_processing import remove_outliers as image_processing_remove_outliers
from pleiades.utils.load import load


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
        else:
            raise FileNotFoundError(f"Folder {folder} does not exist")


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
    logger.info(f"Updating master normalization dictionary with crop values {roi}")

    if roi is None:
        logger.info("Crop values are None, skipping crop update")
        return

    for folder in master_dict[MasterDictKeys.sample_data].keys():
        cropped_data = crop(master_dict[MasterDictKeys.sample_data][folder], roi)
        master_dict[MasterDictKeys.sample_data][folder] = cropped_data


def update_with_rebin(master_dict: dict, binning_factor: int) -> None:
    """
    Update the master dictionary with the rebin values.
    """
    logger.info(
        f"Updating {master_dict[MasterDictKeys.data_type]} master dictionary with rebin values {binning_factor}"
    )

    if binning_factor == 1:
        logger.info("Binning factor is 1, skipping rebin update")
        return

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        rebinned_data = rebin(master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data], binning_factor)
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = rebinned_data


def remove_outliers(master_dict: dict, dif: float, num_threads: int) -> None:
    """
    Remove outliers from the data in the master dictionary.
    """
    logger.info(
        f"Removing outliers from {master_dict[MasterDictKeys.data_type]} master dictionary with threshold {dif}"
    )

    for folder in master_dict[MasterDictKeys.list_folders].keys():
        data = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data]
        data = image_processing_remove_outliers(data, dif, num_threads)
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.data] = data


def combine_data(
    master_dict: dict,
    is_normalization_by_proton_charge: bool,
    is_normalization_by_shutter_counts: bool,
    normalization_dict: dict,
) -> None:
    """
    Combine the open beams data.
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


def correct_data_for_proton_charge(master_dict: dict, is_normalization_by_proton_charge: bool) -> None:
    """
    Correct the data for proton charge.
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


def correct_data_for_shutter_counts(master_dict: dict, is_normalization_by_shutter_counts: bool) -> None:
    """
    Correct the data for shutter counts.
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


def performing_normalization(sample_master_dict, normalization_dict, background_roi=None):
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


def get_counts_from_normalized_data(normalized_data: np.ndarray) -> tuple:
    """
    Get counts for each image from the normalized data.
    """
    if not isinstance(normalized_data, np.ndarray):
        raise TypeError("Normalized data must be a numpy array")

    # Assuming normalized_data is a 3D array with shape (num_images, height, width)
    counts_array = np.sum(normalized_data, axis=(1, 2))

    uncertainties = np.sqrt(counts_array)  # Assuming Poisson statistics for counts

    return (counts_array, uncertainties)
