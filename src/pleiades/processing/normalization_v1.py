"""
Neutron imaging data normalization module for PLEIADES.

This module provides comprehensive normalization functionality for neutron imaging data,
including sample and open beam data processing, outlier removal, rebinning, and
transmission calculation. Supports both Timepix and traditional detector data formats.

The normalization process includes:
- Data loading and validation
- Proton charge correction
- Shutter count correction
- Background subtraction
- Open beam normalization
- Cropping and rebinning
- Transmission calculation
- Data export

Example:
    Basic normalization workflow:

    >>> from pleiades.processing.normalization_v1 import normalization
    >>> from pleiades.processing import Roi, Facility
    >>>
    >>> result = normalization(
    ...     list_sample_folders=["/path/to/sample"],
    ...     list_obs_folders=["/path/to/openbeam"],
    ...     background_roi=Roi(0, 0, 10, 10),
    ...     crop_roi=Roi(10, 10, 200, 200),
    ...     facility=Facility.ornl
    ... )
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from pleiades.processing import DataType, Facility, MasterDictKeys, NormalizationStatus, Roi
from pleiades.processing.normalization_handler import (
    combine_data,
    correct_data_for_proton_charge,
    correct_data_for_shutter_counts,
    get_counts_from_normalized_data,
    performing_normalization,
    remove_outliers,
    update_with_crop,
    update_with_data,
    update_with_list_of_files,
    update_with_rebin,
)
from pleiades.utils.files import export_ascii
from pleiades.utils.logger import loguru_logger
from pleiades.utils.timepix import (
    update_with_nexus_files,
    update_with_proton_charge,
    update_with_shutter_counts,
    update_with_shutter_values,
    update_with_spectra_files,
)
from pleiades.utils.units import (
    DistanceUnitOptions,
    EnergyUnitOptions,
    TimeUnitOptions,
    convert_array_from_time_to_energy,
)

logger = loguru_logger.bind(name="normalization")


def init_master_dict(list_folders: List[str], data_type: DataType = DataType.sample) -> Dict[str, Any]:
    """
    Initialize a master dictionary to store data from sample and open beam folders.

    Creates a hierarchical dictionary structure that will hold all metadata and
    processed data for each folder in the normalization workflow.

    Args:
        list_folders (List[str]): List of folder paths containing imaging data files
        data_type (DataType, optional): Type of data (sample or open beam).
                                       Defaults to DataType.sample.

    Returns:
        Dict[str, Any]: Master dictionary with initialized structure containing:
            - data_type: The type of data being processed
            - list_folders: Nested dict with folder-specific metadata placeholders

    Example:
        >>> folders = ["/path/to/sample1", "/path/to/sample2"]
        >>> master_dict = init_master_dict(folders, DataType.sample)
        >>> print(master_dict.keys())
        dict_keys(['data_type', 'list_folders'])

    Note:
        Each folder entry is initialized with None values for:
        nexus_path, data, frame_number, data_path, proton_charge,
        matching_ob, list_images, ext, shutter_counts, list_spectra,
        list_shutters
    """
    master_dict: Dict[str, Any] = {
        MasterDictKeys.data_type: data_type,
        MasterDictKeys.list_folders: {},
    }

    for folder in list_folders:
        master_dict[MasterDictKeys.list_folders][folder] = {
            MasterDictKeys.nexus_path: None,
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
            MasterDictKeys.data: None,
        }
    return master_dict


def init_normalization_dict(list_folders: List[str]) -> Dict[str, Any]:
    """
    Initialize a normalization dictionary to store processed and normalized data.

    Creates the data structure that will hold the final normalized transmission
    data and associated uncertainties for each sample folder.

    Args:
        list_folders (List[str]): List of sample folder paths

    Returns:
        Dict[str, Any]: Normalization dictionary with structure for:
            - obs_data_combined: Combined open beam data
            - sample_data: Sample data for each folder
            - uncertainties_obs_data_combined: Open beam uncertainties
            - uncertainties_sample_data: Sample uncertainties

    Example:
        >>> folders = ["/path/to/sample1", "/path/to/sample2"]
        >>> norm_dict = init_normalization_dict(folders)
        >>> print(len(norm_dict['sample_data']))
        2
    """
    normalization_dict: Dict[str, Any] = {
        MasterDictKeys.obs_data_combined: None,
        MasterDictKeys.sample_data: {},
        MasterDictKeys.uncertainties_obs_data_combined: None,
        MasterDictKeys.uncertainties_sample_data: None,
    }

    for folder in list_folders:
        normalization_dict[MasterDictKeys.sample_data][folder] = None

    return normalization_dict


def normalization(
    list_sample_folders: Union[List[str], str],
    list_obs_folders: Union[List[str], str],
    nexus_path: Optional[str] = None,
    background_roi: Optional[Roi] = None,
    crop_roi: Optional[Roi] = None,
    timepix: bool = True,
    pixel_binning: int = 1,
    remove_outliers_flag: bool = False,
    rolling_average: bool = False,
    distance_source_detector_m: float = 25,
    detector_offset_micros: float = 0,
    output_folder: Optional[str] = None,
    output_numpy: bool = True,
    facility: Facility = Facility.ornl,
    num_threads: int = 1,
) -> None:
    """
    Perform comprehensive neutron imaging data normalization.

    This is the main normalization function that processes sample and open beam data
    to calculate transmission values. The function handles multiple processing steps
    including data loading, corrections, background subtraction, and normalization.

    Processing workflow:
    1. Initialize data structures
    2. Load and validate nexus files
    3. Extract proton charge and shutter information
    4. Load imaging data
    5. Apply rebinning and outlier removal (if requested)
    6. Combine open beam data
    7. Apply corrections (proton charge, shutter counts)
    8. Perform normalization and background subtraction
    9. Crop data (if requested)
    10. Convert to energy units and export results

    Args:
        list_sample_folders (Union[List[str], str]): Sample folder(s) containing
            TIFF or FITS files. If string, will be converted to single-item list.
        list_obs_folders (Union[List[str], str]): Open beam folder(s) containing
            TIFF or FITS files. Multiple folders will be combined using mean.
        nexus_path (Optional[str], optional): Path to nexus file for proton charge
            retrieval. Defaults to None.
        background_roi (Optional[Roi], optional): Region of interest defining
            background region in sample data for subtraction. Defaults to None.
        crop_roi (Optional[Roi], optional): Region of interest for final data
            cropping. Defaults to None.
        timepix (bool, optional): Whether Timepix detector data format is used.
            Affects shutter value normalization. Defaults to True.
        pixel_binning (int, optional): Spatial binning factor. 1 means no binning,
            2 means 2x2 binning, etc. Must be positive. Defaults to 1.
        remove_outliers_flag (bool, optional): Whether to apply outlier removal
            filtering. Defaults to False.
        rolling_average (bool, optional): Whether to apply rolling average smoothing.
            Currently not implemented. Defaults to False.
        distance_source_detector_m (float, optional): Distance from neutron source
            to detector in meters. Used for time-to-energy conversion. Defaults to 25.
        detector_offset_micros (float, optional): Detector timing offset in
            microseconds. Used for time-to-energy conversion. Defaults to 0.
        output_folder (Optional[str], optional): Directory to save output files.
            If None, no files are saved. Defaults to None.
        output_numpy (bool, optional): Whether to save output as numpy arrays.
            Currently affects ASCII export format. Defaults to True.
        facility (Facility, optional): Neutron facility (ORNL, etc.) for
            facility-specific processing. Defaults to Facility.ornl.
        num_threads (int, optional): Number of CPU threads for parallel processing.
            Must be positive. Defaults to 1.

    Returns:
        None: Results are saved to output_folder if specified.

    Raises:
        ValueError: If sample or open beam folders are not provided
        ValueError: If pixel_binning is not positive
        ValueError: If num_threads is not positive
        FileNotFoundError: If specified folders do not exist
        RuntimeError: If normalization process fails

    Example:
        Basic normalization:

        >>> normalization(
        ...     list_sample_folders="/path/to/sample",
        ...     list_obs_folders="/path/to/openbeam",
        ...     output_folder="/path/to/output"
        ... )

        Advanced normalization with ROIs and processing options:

        >>> from pleiades.processing import Roi, Facility
        >>> normalization(
        ...     list_sample_folders=["/sample1", "/sample2"],
        ...     list_obs_folders=["/ob1", "/ob2"],
        ...     nexus_path="/path/to/nexus",
        ...     background_roi=Roi(0, 0, 10, 10),
        ...     crop_roi=Roi(50, 50, 200, 200),
        ...     pixel_binning=2,
        ...     remove_outliers_flag=True,
        ...     distance_source_detector_m=25.5,
        ...     detector_offset_micros=100,
        ...     output_folder="/path/to/output",
        ...     facility=Facility.ornl,
        ...     num_threads=8
        ... )

    Note:
        - Multiple open beam folders are automatically combined using mean values
        - Each sample folder is processed separately if multiple are provided
        - Energy conversion assumes neutron time-of-flight geometry
        - Output files are named as "{folder_basename}_transmission.txt"
        - Transmission values are calculated as: T = (Sample - Background) / (OpenBeam - Background)
    """
    logger.info("Starting normalization process...")
    logger.info("##############################")
    logger.info(f"\tSample folders: {list_sample_folders}")
    logger.info(f"\tOpen beam folders: {list_obs_folders}")
    logger.info(f"\tnexus path: {nexus_path}")
    logger.info(f"\tBackground ROI: {background_roi}")
    logger.info(f"\tCrop ROI: {crop_roi}")
    logger.info(f"\tTimepix: {timepix}")
    logger.info(f"\tPixel binning: {pixel_binning}")
    logger.info(f"\tRemove outliers flag: {remove_outliers_flag}")
    logger.info(f"\tRolling average: {rolling_average}")
    logger.info(f"\tDistance source to detector (m): {distance_source_detector_m}")
    logger.info(f"\tDetector offset (micros): {detector_offset_micros}")
    logger.info(f"\tOutput folder: {output_folder}")
    logger.info(f"\tOutput numpy: {output_numpy}")
    logger.info(f"\tNumber of threads: {num_threads}")
    logger.info(f"\tFacility: {facility}")
    logger.info("##############################")

    # Input validation
    if not list_sample_folders or not list_obs_folders:
        raise ValueError("Sample and open beam folders must be provided.")

    if pixel_binning <= 0:
        raise ValueError("Pixel binning factor must be positive")

    if num_threads <= 0:
        raise ValueError("Number of threads must be positive")

    # Convert string inputs to lists
    if isinstance(list_sample_folders, str):
        list_sample_folders = [list_sample_folders]

    if isinstance(list_obs_folders, str):
        list_obs_folders = [list_obs_folders]

    # Initialize data structures
    sample_normalization_status = NormalizationStatus()
    ob_normalization_status = NormalizationStatus()

    sample_master_dict = init_master_dict(list_sample_folders, data_type=DataType.sample)
    ob_master_dict = init_master_dict(list_obs_folders, data_type=DataType.ob)
    normalization_dict = init_normalization_dict(list_sample_folders)

    # Update with nexus files for metadata extraction
    update_with_nexus_files(sample_master_dict, sample_normalization_status, nexus_path, facility=facility)
    update_with_nexus_files(ob_master_dict, ob_normalization_status, nexus_path, facility=facility)

    # Update with list of data files in folders
    update_with_list_of_files(sample_master_dict)
    update_with_list_of_files(ob_master_dict)

    # Extract proton charge information for normalization
    update_with_proton_charge(sample_master_dict, sample_normalization_status, facility=facility)
    update_with_proton_charge(ob_master_dict, ob_normalization_status, facility=facility)

    # Extract shutter count information
    update_with_shutter_counts(sample_master_dict, sample_normalization_status, facility=facility)
    update_with_shutter_counts(ob_master_dict, ob_normalization_status, facility=facility)

    # Extract time spectra files for energy conversion
    update_with_spectra_files(sample_master_dict, sample_normalization_status, facility=facility)
    update_with_spectra_files(ob_master_dict, ob_normalization_status, facility=facility)

    # Extract shutter values for each image
    update_with_shutter_values(sample_master_dict, sample_normalization_status, facility=facility)
    update_with_shutter_values(ob_master_dict, ob_normalization_status, facility=facility)

    # Load actual imaging data
    update_with_data(sample_master_dict)
    update_with_data(ob_master_dict)

    # Apply spatial rebinning if requested
    update_with_rebin(sample_master_dict, binning_factor=pixel_binning)
    update_with_rebin(ob_master_dict, binning_factor=pixel_binning)

    # Remove outlier pixels if requested
    remove_outliers(sample_master_dict, dif=20, num_threads=num_threads)
    remove_outliers(ob_master_dict, dif=20, num_threads=num_threads)

    # Determine normalization method based on available data
    is_normalization_by_proton_charge = (
        sample_normalization_status.all_proton_charge_value_found
        and ob_normalization_status.all_proton_charge_value_found
    )
    is_normalization_by_shutter_counts = (
        sample_normalization_status.all_shutter_counts_file_found
        and ob_normalization_status.all_shutter_counts_file_found
    )

    # Combine multiple open beam datasets using mean
    combine_data(
        ob_master_dict, is_normalization_by_proton_charge, is_normalization_by_shutter_counts, normalization_dict
    )

    # Apply proton charge corrections to sample data
    correct_data_for_proton_charge(sample_master_dict, is_normalization_by_proton_charge)

    # Apply shutter count corrections to sample data
    correct_data_for_shutter_counts(sample_master_dict, is_normalization_by_shutter_counts)

    # Perform the main normalization calculation
    performing_normalization(sample_master_dict, normalization_dict, background_roi=background_roi)
    logger.info("Normalization completed successfully!")

    # Crop the normalized data to region of interest
    update_with_crop(normalization_dict, roi=crop_roi)

    # Format and export results
    if output_folder:
        sample_folders = list(normalization_dict[MasterDictKeys.sample_data].keys())

        if len(sample_folders) == 1:
            # Single run - use original logic
            folder = sample_folders[0]
            logger.info(f"Exporting data for single folder: {folder}")

            # Get time spectra for energy conversion
            spectra_array = sample_master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_spectra]

            # Convert time-of-flight to energy
            energy_array = convert_array_from_time_to_energy(
                spectra_array,
                time_unit=TimeUnitOptions.s,
                distance_source_detector=distance_source_detector_m,
                distance_source_detector_unit=DistanceUnitOptions.m,
                detector_offset=detector_offset_micros,
                detector_offset_unit=TimeUnitOptions.us,
                energy_unit=EnergyUnitOptions.eV,
            )

            # Extract transmission counts and uncertainties
            counts_array, uncertainties = get_counts_from_normalized_data(
                normalization_dict[MasterDictKeys.sample_data][folder]
            )

            # Prepare export data (reverse arrays for ascending energy)
            data_dict = {
                "energy_eV": energy_array[::-1],
                "transmission": counts_array[::-1],
                "uncertainties": uncertainties[::-1],
            }

            # Generate output filename and export
            output_file_name = Path(output_folder) / f"{Path(folder).name}_transmission.txt"
            export_ascii(data_dict, str(output_file_name))

        else:
            # Multiple runs - export individual runs AND combined result
            logger.info(f"Processing {len(sample_folders)} sample runs individually and combining")

            # Get energy array from first folder (all should be the same)
            first_folder = sample_folders[0]
            spectra_array = sample_master_dict[MasterDictKeys.list_folders][first_folder][MasterDictKeys.list_spectra]

            # Convert time-of-flight to energy
            energy_array = convert_array_from_time_to_energy(
                spectra_array,
                time_unit=TimeUnitOptions.s,
                distance_source_detector=distance_source_detector_m,
                distance_source_detector_unit=DistanceUnitOptions.m,
                detector_offset=detector_offset_micros,
                detector_offset_unit=TimeUnitOptions.us,
                energy_unit=EnergyUnitOptions.eV,
            )

            # Step 1: Export individual runs
            run_transmissions = []
            run_uncertainties = []

            for folder in sample_folders:
                logger.info(f"Processing and exporting individual run: {Path(folder).name}")

                # Extract transmission and uncertainties for this run
                counts_array, uncertainties = get_counts_from_normalized_data(
                    normalization_dict[MasterDictKeys.sample_data][folder]
                )

                # Export individual run
                individual_data_dict = {
                    "energy_eV": energy_array[::-1],
                    "transmission": counts_array[::-1],
                    "uncertainties": uncertainties[::-1],
                }

                individual_output_file = Path(output_folder) / f"{Path(folder).name}_transmission.txt"
                export_ascii(individual_data_dict, str(individual_output_file))
                logger.info(f"  Individual run exported to: {individual_output_file}")

                # Collect for combination
                run_transmissions.append(counts_array)
                run_uncertainties.append(uncertainties)

            # Step 2: Create combined result
            logger.info("Creating weighted combination of all runs...")

            # Convert to numpy arrays for easier calculation
            run_transmissions = np.array(run_transmissions)  # Shape: (n_runs, n_energy_bins)
            run_uncertainties = np.array(run_uncertainties)

            # Calculate weights: w_i = 1/σ_i²
            with np.errstate(divide="ignore", invalid="ignore"):
                weights = 1.0 / (run_uncertainties**2)
                weights[~np.isfinite(weights)] = 0  # Set invalid weights to 0

            # Weighted average: T_combined = Σ(w_i * T_i) / Σ(w_i)
            total_weights = np.sum(weights, axis=0)

            with np.errstate(divide="ignore", invalid="ignore"):
                combined_transmission = np.sum(weights * run_transmissions, axis=0) / total_weights
                combined_uncertainties = 1.0 / np.sqrt(total_weights)

                # Handle edge cases
                combined_transmission[total_weights == 0] = 0.001
                combined_uncertainties[total_weights == 0] = 0.1

            # Log statistics
            avg_improvement = np.sqrt(len(sample_folders))
            actual_improvement = np.mean(run_uncertainties.mean(axis=0) / combined_uncertainties)
            logger.info(
                f"Combined transmission range: {combined_transmission.min():.3f} to {combined_transmission.max():.3f}"
            )
            logger.info(f"Expected uncertainty improvement: {avg_improvement:.2f}x")
            logger.info(f"Actual uncertainty improvement: {actual_improvement:.2f}x")

            # Export combined result
            combined_data_dict = {
                "energy_eV": energy_array[::-1],
                "transmission": combined_transmission[::-1],
                "uncertainties": combined_uncertainties[::-1],
            }

            # Generate combined output filename
            run_numbers = [Path(folder).name.split("_")[1] for folder in sample_folders]
            combined_output_file = Path(output_folder) / f"Combined_Runs_{'_'.join(run_numbers)}_transmission.txt"
            export_ascii(combined_data_dict, str(combined_output_file))

            logger.info(f"Combined transmission data exported to: {combined_output_file}")
            logger.info(f"Summary: {len(sample_folders)} individual files + 1 combined file exported")


if __name__ == "__main__":
    # Example usage
    normalization(
        list_sample_folders=["/Users/j35/SNS/VENUS_local/IPTS-35945/autoreduce/Run_7820"],
        list_obs_folders=["/Users/j35/SNS/VENUS_local/IPTS-35945/autoreduce/Run_7816"],
        nexus_path="/Users/j35/SNS/VENUS_local/IPTS-35945/nexus",
        background_roi=Roi(0, 0, 10, 10),
        crop_roi=Roi(10, 10, 200, 200),
        timepix=True,
        pixel_binning=2,
        remove_outliers_flag=False,
        rolling_average=False,
        distance_source_detector_m=25,
        detector_offset_micros=0,
        output_folder="/Users/j35/SNS/VENUS_local/IPTS-35945/processed",
        output_numpy=True,
        facility=Facility.ornl,
        num_threads=4,
    )

# how to run it
# pixi run python src/pleiades/processing/normalization.py
