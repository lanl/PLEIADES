"""
Timepix detector utilities for PLEIADES neutron imaging data processing.

This module provides comprehensive utilities for handling Timepix detector data,
including nexus file processing, proton charge extraction, shutter count management,
and time spectra generation. It supports multiple neutron facilities (ORNL, LANL)
with facility-specific processing workflows.

The module handles:
- Nexus file discovery and processing
- Proton charge extraction for beam normalization
- Shutter count and timing information extraction
- Time-of-flight spectra generation
- Facility-specific data processing workflows

Supported Facilities:
- ORNL (Oak Ridge National Laboratory) - VENUS beamline
- LANL (Los Alamos National Laboratory) - Custom processing

Example:
    Basic workflow for updating master dictionary:

    >>> master_dict = init_master_dict(folders, DataType.sample)
    >>> normalization_status = NormalizationStatus()
    >>>
    >>> update_with_nexus_files(master_dict, normalization_status, "/path/to/nexus")
    >>> update_with_proton_charge(master_dict, normalization_status, Facility.ornl)
    >>> update_with_shutter_counts(master_dict, normalization_status, Facility.ornl)
"""

import glob
import os
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from pleiades.processing import Facility, MasterDictKeys, NormalizationStatus
from pleiades.utils.files import retrieve_number_of_frames_from_file_name, retrieve_time_bin_size_from_file_name
from pleiades.utils.logger import loguru_logger
from pleiades.utils.nexus import get_proton_charge

logger = loguru_logger.bind(name="timepix")


def get_shutter_values_dict(
    list_sample_folders: List[str], list_obs_folders: List[str], timepix: Any
) -> Dict[str, Dict[str, Any]]:
    """
    Extract shutter values from Timepix detector for sample and open beam folders.

    Retrieves shutter timing information from a Timepix detector object for both
    sample and open beam measurements. This information is essential for proper
    normalization of time-of-flight data.

    Args:
        list_sample_folders (List[str]): List of sample folder paths
        list_obs_folders (List[str]): List of open beam folder paths
        timepix (Any): Timepix detector object with get_shutter_values method

    Returns:
        Dict[str, Dict[str, Any]]: Nested dictionary structure with:
            - "sample": {folder_path: shutter_values}
            - "ob": {folder_path: shutter_values}

    Example:
        >>> sample_folders = ["/path/to/sample1", "/path/to/sample2"]
        >>> ob_folders = ["/path/to/ob1"]
        >>> shutter_dict = get_shutter_values_dict(sample_folders, ob_folders, timepix_obj)
        >>> shutter_dict["sample"]["/path/to/sample1"]
        [1.0, 1.2, 0.8, ...]

    Note:
        - Timepix object must implement get_shutter_values(folder) method
        - Shutter values represent timing corrections for each measurement
        - Essential for accurate time-of-flight normalization
    """
    # Input validation
    if not list_sample_folders and not list_obs_folders:
        raise ValueError("At least one of sample or observation folders must be provided")

    shutter_values_dict = {"sample": {}, "ob": {}}

    for folder in list_sample_folders:
        shutter_values_dict["sample"][folder] = timepix.get_shutter_values(folder)

    for folder in list_obs_folders:
        shutter_values_dict["ob"][folder] = timepix.get_shutter_values(folder)

    return shutter_values_dict


def isolate_run_number(run_number_full_path: str) -> Union[str, int]:
    """
    Extract run number from a full file path containing run information.

    Parses folder paths to extract neutron beamline run numbers, typically
    used for identifying corresponding nexus files and metadata. Handles
    standard naming conventions like "Run_1234" or similar patterns.

    Args:
        run_number_full_path (str): Full path to folder containing run information.
                                   Expected format includes underscore-separated run number.

    Returns:
        Union[str, int]: Extracted run number as string, or -1 if parsing fails

    Example:
        >>> path = "/data/VENUS/Run_7820/images"
        >>> run_num = isolate_run_number(path)
        >>> run_num
        '7820'

        >>> path = "/invalid/path/format"
        >>> run_num = isolate_run_number(path)
        >>> run_num
        -1

    Note:
        - Expects basename to contain underscore-separated run number
        - Returns -1 if parsing fails (invalid format)
        - Used primarily for ORNL VENUS beamline data
    """
    run_number = os.path.basename(run_number_full_path)
    try:
        run_number = run_number.split("_")[1]
        return run_number
    except IndexError:
        logger.warning(f"Could not extract run number from path: {run_number_full_path}")
        return -1


def update_with_nexus_files(
    master_dict: Dict[str, Any],
    normalization_status: NormalizationStatus,
    nexus_path: Optional[str],
    facility: Facility = Facility.ornl,
) -> None:
    """
    Update master dictionary with nexus file paths for metadata extraction.

    Discovers and associates nexus files with corresponding data folders.
    Nexus files contain essential metadata including proton charge, beam
    conditions, and experimental parameters required for proper normalization.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing folder information
        normalization_status (NormalizationStatus): Status tracker for normalization workflow
        nexus_path (Optional[str]): Path to directory containing nexus files.
                                   If None, nexus processing is skipped.
        facility (Facility, optional): Neutron facility identifier. Defaults to Facility.ornl.

    Raises:
        ValueError: If facility is not supported (only ORNL and LANL currently supported)

    Example:
        >>> update_with_nexus_files(master_dict, status, "/path/to/nexus", Facility.ornl)
        >>> # master_dict now contains nexus file paths for each folder

    Note:
        - Updates normalization_status.all_nexus_file_found when successful
        - Facility-specific implementations handle different file naming conventions
        - LANL implementation is placeholder for future development
        - Essential prerequisite for proton charge extraction
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with nexus files")

    if nexus_path is None:
        logger.info("Nexus path is None, skipping nexus file processing")
        return

    if facility == Facility.ornl:
        update_with_nexus_files_at_ornl(master_dict, normalization_status, nexus_path)
    elif facility == Facility.lanl:
        # Implement the logic for LANL if needed
        pass
    else:
        raise ValueError(f"Unknown facility: {facility}. Supported facilities are: {Facility.ornl}, {Facility.lanl}.")


def update_with_nexus_files_at_ornl(
    master_dict: Dict[str, Any], normalization_status: NormalizationStatus, nexus_path: str
) -> None:
    """
    Update master dictionary with ORNL VENUS beamline nexus files.

    Handles ORNL-specific nexus file discovery and association. Expects
    nexus files named in VENUS_[run_number].nxs.h5 format and matches
    them to corresponding data folders based on run numbers.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing folder information
        normalization_status (NormalizationStatus): Status tracker for normalization workflow
        nexus_path (str): Path to directory containing ORNL nexus files

    Example:
        >>> # For folder "/data/Run_7820", looks for "/nexus/VENUS_7820.nxs.h5"
        >>> update_with_nexus_files_at_ornl(master_dict, status, "/path/to/nexus")

    Note:
        - Sets normalization_status.all_nexus_file_found = True on success
        - Returns early if any run number cannot be parsed or nexus file not found
        - Updates master_dict with nexus_path for each folder
        - ORNL VENUS-specific file naming convention
    """
    for folder in master_dict[MasterDictKeys.list_folders].keys():
        run_number = isolate_run_number(folder)
        if run_number == -1:
            return

        nexus_file = os.path.join(nexus_path, f"VENUS_{run_number}.nxs.h5")
        if os.path.exists(nexus_file):
            master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.nexus_path] = nexus_file
        else:
            return

    normalization_status.all_nexus_file_found = True


def update_with_proton_charge(
    master_dict: Dict[str, Any], normalization_status: NormalizationStatus, facility: Facility = Facility.ornl
) -> None:
    """
    Extract and store proton charge values for beam intensity normalization.

    Retrieves proton charge measurements from nexus files to enable normalization
    for variations in neutron beam intensity. Proton charge is proportional to
    the number of neutrons produced and is essential for quantitative analysis.

    Args:
        master_dict (Dict[str, Any]): Master dictionary with nexus file paths.
                                     Must have been processed by update_with_nexus_files.
        normalization_status (NormalizationStatus): Status tracker for normalization workflow
        facility (Facility, optional): Neutron facility identifier. Defaults to Facility.ornl.

    Raises:
        ValueError: If facility is not supported

    Example:
        >>> update_with_proton_charge(master_dict, status, Facility.ornl)
        >>> charge = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.proton_charge]
        >>> charge
        1.234e-6  # in Coulombs

    Note:
        - Sets normalization_status.all_proton_charge_value_found = True on success
        - Proton charge typically measured in microampere-hours or Coulombs
        - Essential for correcting beam intensity variations between measurements
        - LANL implementation is placeholder for future development
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with proton charge values")

    if facility == Facility.ornl:
        update_with_proton_charge_at_ornl(master_dict, normalization_status)
    elif facility == Facility.lanl:
        # Implement the logic for other facilities if needed
        pass
    else:
        raise ValueError(f"Unknown facility: {facility}. Supported facilities are: {Facility.ornl}, {Facility.lanl}.")


def update_with_proton_charge_at_ornl(master_dict: Dict[str, Any], normalization_status: NormalizationStatus) -> None:
    """
    Extract proton charge values from ORNL VENUS nexus files.

    Reads proton charge data from ORNL nexus files using the nexus utility
    functions. Proton charge is stored in Coulombs and represents the total
    charge delivered to the neutron production target.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing nexus file paths
        normalization_status (NormalizationStatus): Status tracker for normalization workflow

    Example:
        >>> update_with_proton_charge_at_ornl(master_dict, status)
        >>> # Proton charge values now available in master_dict

    Note:
        - Requires nexus files to be already associated via update_with_nexus_files_at_ornl
        - Sets normalization_status.all_proton_charge_value_found = True
        - Uses get_proton_charge utility with units="c" (Coulombs)
        - Skips folders where proton charge extraction fails
    """

    for key in master_dict[MasterDictKeys.list_folders].keys():
        nexus = master_dict[MasterDictKeys.list_folders][key][MasterDictKeys.nexus_path]
        proton_charge = get_proton_charge(nexus, units="c")
        if proton_charge is not None:
            master_dict[MasterDictKeys.list_folders][key][MasterDictKeys.proton_charge] = proton_charge
        else:
            pass

    normalization_status.all_proton_charge_value_found = True


def update_with_shutter_counts(
    master_dict: Dict[str, Any], normalization_status: NormalizationStatus, facility: Facility = Facility.ornl
) -> None:
    """
    Extract shutter count information for exposure time normalization.

    Reads shutter count data from facility-specific files. Shutter counts
    represent the effective exposure time or number of neutron pulses for
    each measurement, essential for time-of-flight normalization.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing folder information
        normalization_status (NormalizationStatus): Status tracker for normalization workflow
        facility (Facility, optional): Neutron facility identifier. Defaults to Facility.ornl.

    Raises:
        ValueError: If facility is not supported

    Example:
        >>> update_with_shutter_counts(master_dict, status, Facility.ornl)
        >>> counts = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.shutter_counts]
        >>> counts
        [1000, 1200, 980, ...]  # counts per time bin

    Note:
        - Sets normalization_status.all_shutter_counts_file_found = True on success
        - ORNL implementation reads from *_ShutterCount.txt files
        - LANL implementation is placeholder for future development
        - Essential for Timepix detector normalization
    """

    if facility == Facility.ornl:
        update_with_shutter_counts_at_ornl(master_dict, normalization_status)
    elif facility == Facility.lanl:
        pass
    else:
        raise ValueError(f"Unknown facility: {facility}. Supported facilities are: {Facility.ornl}, {Facility.lanl}.")


def update_with_shutter_counts_at_ornl(master_dict: Dict[str, Any], normalization_status: NormalizationStatus) -> None:
    """
    Extract shutter count data from ORNL VENUS shutter count files.

    Reads tab-separated shutter count files (*_ShutterCount.txt) containing
    timing information for each neutron pulse. These files are essential for
    proper normalization of time-of-flight data at ORNL facilities.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing folder paths
        normalization_status (NormalizationStatus): Status tracker for normalization workflow

    File Format:
        Tab-separated values with pulse timing information:
        pulse_index    shutter_count
        0              1000.5
        1              1200.3
        ...

    Example:
        >>> update_with_shutter_counts_at_ornl(master_dict, status)
        >>> # Shutter counts now available for each folder

    Note:
        - Sets normalization_status.all_shutter_counts_file_found = True
        - Stops reading when encountering "0" count (end of valid data)
        - Returns early if no shutter count files found in any folder
        - Each folder should contain exactly one *_ShutterCount.txt file
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with shutter counts")

    for data_path in master_dict[MasterDictKeys.list_folders].keys():
        logger.info(f"\tUpdating shutter counts for {data_path}")
        _list_files = glob.glob(os.path.join(data_path, "*_ShutterCount.txt"))
        if len(_list_files) == 0:
            logger.info(f"\tNo shutter count file found for {data_path}")
            return

        else:
            shutter_count_file = _list_files[0]
            with open(shutter_count_file, "r") as f:
                lines = f.readlines()
                list_shutter_counts = []
                for _line in lines:
                    _, _value = _line.strip().split("\t")
                    if _value == "0":
                        break
                    list_shutter_counts.append(float(_value))
                logger.info(f"\tShutter counts: {list_shutter_counts}")
                master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.shutter_counts] = list_shutter_counts

    normalization_status.all_shutter_counts_file_found = True


def update_with_spectra_files(
    master_dict: Dict[str, Any], normalization_status: NormalizationStatus, facility: Facility = Facility.ornl
) -> None:
    """
    Extract time-of-flight spectra information for energy conversion.

    Reads or generates time spectra data needed for converting time-of-flight
    measurements to energy or wavelength scales. Implementation varies by
    facility based on available metadata and file formats.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing folder information
        normalization_status (NormalizationStatus): Status tracker for normalization workflow
        facility (Facility, optional): Neutron facility identifier. Defaults to Facility.ornl.

    Example:
        >>> update_with_spectra_files(master_dict, status, Facility.ornl)
        >>> spectra = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_spectra]
        >>> spectra[:5]
        array([0.000000e+00, 1.000000e-06, 2.000000e-06, 3.000000e-06, 4.000000e-06])

    Note:
        - ORNL: Reads from *_Spectra.txt CSV files containing shutter_time column
        - LANL: Generates time arrays from filename metadata (bin size, frame count)
        - Sets normalization_status.all_spectra_file_found = True on success
        - Time spectra typically in seconds, starting from 0
        - Essential for time-to-energy conversion in neutron spectroscopy
    """
    data_type = master_dict[MasterDictKeys.data_type]
    logger.info(f"Updating {data_type} master dictionary with spectra files")

    if facility == Facility.ornl:
        update_with_spectra_files_at_ornl(master_dict, normalization_status)
    elif facility == Facility.lanl:
        update_with_spectra_files_at_lanl(master_dict, normalization_status)
    else:
        # Implement the logic for other facilities if needed
        pass


def update_with_spectra_files_at_ornl(master_dict: Dict[str, Any], normalization_status: NormalizationStatus) -> None:
    """
    Extract time spectra from ORNL VENUS spectra files.

    Reads CSV-formatted spectra files (*_Spectra.txt) containing shutter timing
    information. These files provide the time axis for time-of-flight measurements
    at the ORNL VENUS beamline.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing folder paths
        normalization_status (NormalizationStatus): Status tracker for normalization workflow

    File Format:
        CSV file with headers including 'shutter_time' column:
        time_index,shutter_time,other_columns...
        0,0.000000e+00,...
        1,1.000000e-06,...

    Example:
        >>> update_with_spectra_files_at_ornl(master_dict, status)
        >>> # Time spectra arrays now available for energy conversion

    Note:
        - Sets normalization_status.all_spectra_file_found = True
        - Returns early if no spectra files found in any folder
        - Uses pandas to read CSV with comma separation
        - Extracts 'shutter_time' column as numpy array
    """
    for data_path in master_dict[MasterDictKeys.list_folders].keys():
        spectra_files = glob.glob(os.path.join(data_path, "*_Spectra.txt"))
        if len(spectra_files) == 0:
            logger.info(f"\tNo spectra file found for {data_path}")
            return

        else:
            spectra_file = spectra_files[0]
            pd_spectra = pd.read_csv(spectra_file, sep=",", header=0)
            shutter_time = pd_spectra["shutter_time"].values
            master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.list_spectra] = shutter_time

    normalization_status.all_spectra_file_found = True


def update_with_spectra_files_at_lanl(master_dict: Dict[str, Any], normalization_status: NormalizationStatus) -> None:
    """
    Generate time spectra from LANL filename metadata.

    Creates time-of-flight arrays by extracting timing parameters directly
    from LANL image filenames. This approach eliminates the need for separate
    spectra files by encoding timing information in the filename structure.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing file lists.
                                     Must have been processed by update_with_list_of_files.
        normalization_status (NormalizationStatus): Status tracker for normalization workflow

    Filename Format:
        image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff
        - T2000: Number of time bins (frames)
        - t1e6: Time bin size in microseconds (1e6 -> 1e-6 seconds)

    Example:
        >>> # For file with T2000 and t1e6:
        >>> update_with_spectra_files_at_lanl(master_dict, status)
        >>> spectra = master_dict[folder][MasterDictKeys.list_spectra]
        >>> len(spectra)
        2000
        >>> spectra[1] - spectra[0]
        1e-06

    Note:
        - Automatically sets normalization_status.all_spectra_file_found = True
        - Uses numpy.arange to generate uniform time arrays
        - Time starts at 0 with uniform bin spacing
        - Returns early if no files found in any folder
        - Extracts metadata from first file in each folder
    """
    for folder in master_dict[MasterDictKeys.list_folders].keys():
        list_files = master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_images]

        # extract number of time bins and time bin size from the first file name
        if len(list_files) == 0:
            logger.info(f"\tNo spectra file found for {folder}")
            return

        first_file_name = os.path.basename(list_files[0])
        number_of_frames = retrieve_number_of_frames_from_file_name(first_file_name)
        bin_size = retrieve_time_bin_size_from_file_name(first_file_name)

        # Generate time spectra array
        time_spectra = np.arange(0, number_of_frames * bin_size, bin_size)
        master_dict[MasterDictKeys.list_folders][folder][MasterDictKeys.list_spectra] = time_spectra

    normalization_status.all_spectra_file_found = True


def update_with_shutter_values(
    master_dict: Dict[str, Any], normalization_status: NormalizationStatus, facility: Facility = Facility.ornl
) -> None:
    """
    Generate per-image shutter values for time-of-flight normalization.

    Combines shutter count and time spectra information to create individual
    shutter values for each time-of-flight image. These values are essential
    for proper normalization of Timepix detector data.

    Args:
        master_dict (Dict[str, Any]): Master dictionary with shutter counts and time spectra.
                                     Must have been processed by update_with_shutter_counts
                                     and update_with_spectra_files.
        normalization_status (NormalizationStatus): Status tracker for normalization workflow
        facility (Facility, optional): Neutron facility identifier. Defaults to Facility.ornl.

    Example:
        >>> update_with_shutter_values(master_dict, status, Facility.ornl)
        >>> shutter_vals = master_dict[folder][MasterDictKeys.list_shutters]
        >>> len(shutter_vals)  # Same as number of time channels
        2000

    Note:
        - Only processes ORNL facility currently
        - Requires both shutter counts and spectra data to be available
        - Sets normalization_status.all_list_shutter_values_for_each_image_found = True
        - Creates per-image correction factors for detector normalization
        - LANL and other facilities: placeholder for future implementation
    """
    logger.info(f"Updating {master_dict[MasterDictKeys.data_type]} master dictionary with shutter values")
    if facility == Facility.ornl:
        update_with_shutter_values_at_ornl(master_dict, normalization_status)
    else:
        # Implement the logic for other facilities if needed
        pass


def update_with_shutter_values_at_ornl(master_dict: Dict[str, Any], normalization_status: NormalizationStatus) -> None:
    """
    Generate ORNL-specific per-image shutter correction values.

    Processes ORNL time spectra and shutter count data to create individual
    shutter correction factors for each time-of-flight image.

    VENUS FIX: For VENUS data with continuous time bins and single-period measurements,
    uses the first non-zero shutter count for the entire spectrum instead of
    attempting time discontinuity segmentation.

    Args:
        master_dict (Dict[str, Any]): Master dictionary containing time spectra and shutter counts
        normalization_status (NormalizationStatus): Status tracker for normalization workflow

    Algorithm:
        1. Check for time discontinuities (gaps > 0.0001 seconds) in time spectra
        2. If discontinuities found: segment and assign shutter counts per segment
        3. If no discontinuities (VENUS case): use first non-zero shutter count for entire spectrum
        4. Create per-image shutter value array

    Example:
        >>> update_with_shutter_values_at_ornl(master_dict, status)
        >>> # Per-image shutter values now available for normalization

    Note:
        - Requires both all_shutter_counts_file_found and all_spectra_file_found to be True
        - Sets normalization_status.all_list_shutter_values_for_each_image_found = True
        - VENUS compatibility: handles continuous time data without discontinuities
        - Creates float32 arrays for memory efficiency
        - Essential for ORNL Timepix detector normalization workflow
    """
    if normalization_status.all_shutter_counts_file_found and normalization_status.all_spectra_file_found:
        for data_path in master_dict[MasterDictKeys.list_folders].keys():
            list_time_spectra = master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.list_spectra]
            list_shutter_counts = master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.shutter_counts]
            list_shutter_values_for_each_image = np.zeros(len(list_time_spectra), dtype=np.float32)

            # Check for time discontinuities (original ORNL logic)
            list_index_jump = np.where(np.diff(list_time_spectra) > 0.0001)[0]

            if len(list_index_jump) > 0:
                # Original multi-segment logic for traditional ORNL data
                list_shutter_values_for_each_image[0 : list_index_jump[0] + 1].fill(list_shutter_counts[0])
                for _index in range(1, len(list_index_jump)):
                    _start = list_index_jump[_index - 1]
                    _end = list_index_jump[_index]
                    list_shutter_values_for_each_image[_start + 1 : _end + 1].fill(list_shutter_counts[_index])
                list_shutter_values_for_each_image[list_index_jump[-1] + 1 :] = list_shutter_counts[-1]
            else:
                # VENUS fix: continuous time data, use first non-zero shutter count for entire spectrum
                first_valid_shutter = next((sc for sc in list_shutter_counts if sc > 0), list_shutter_counts[0])
                list_shutter_values_for_each_image.fill(first_valid_shutter)

            master_dict[MasterDictKeys.list_folders][data_path][MasterDictKeys.list_shutters] = (
                list_shutter_values_for_each_image
            )

        normalization_status.all_list_shutter_values_for_each_image_found = True
