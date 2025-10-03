"""
File utilities for PLEIADES neutron imaging data processing.

This module provides utilities for file discovery, metadata extraction, and data export
operations. It includes functions for finding image files with dominant extensions,
extracting timing information from filenames, and exporting processed data to ASCII format.

The module supports:
- Automatic file discovery with extension filtering
- Filename-based metadata extraction for neutron imaging files
- ASCII data export with proper formatting
- Robust error handling for file operations

Example:
    Basic file discovery and export:

    >>> files, ext = retrieve_list_of_most_dominant_extension_from_folder("/path/to/data")
    >>> print(f"Found {len(files)} {ext} files")
    >>>
    >>> data_dict = {"energy": [1, 2, 3], "transmission": [0.8, 0.6, 0.4]}
    >>> export_ascii(data_dict, "output.txt")
"""

import glob
import os
from collections import Counter
from typing import Any, Dict, List, Tuple, Union

import pandas as pd

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="files")


def retrieve_list_of_most_dominant_extension_from_folder(
    folder: str = "", files: List[str] = None
) -> Tuple[List[str], str]:
    """
    Find and return files with the most common extension from a folder or file list.

    Analyzes a folder or list of files to determine the most frequently occurring
    file extension, then returns all files with that extension. This is useful
    for automatically detecting the primary data format in imaging directories.

    Args:
        folder (str, optional): Path to folder to search for files. If provided,
                              files parameter is ignored. Defaults to "".
        files (List[str], optional): List of file paths to analyze. Only used
                                   if folder is empty. Defaults to None.

    Returns:
        Tuple[List[str], str]: A tuple containing:
            - List of absolute file paths with the dominant extension, sorted alphabetically
            - The dominant file extension (e.g., '.tiff', '.fits')

    Example:
        From folder:
        >>> files, ext = retrieve_list_of_most_dominant_extension_from_folder("/path/to/data")
        >>> print(f"Found {len(files)} files with extension {ext}")
        Found 100 files with extension .tiff

        From file list:
        >>> file_list = ["/path/file1.tiff", "/path/file2.tiff", "/path/file3.fits"]
        >>> files, ext = retrieve_list_of_most_dominant_extension_from_folder(files=file_list)
        >>> ext
        '.tiff'

    Note:
        - If folder is provided, it takes precedence over files parameter
        - Files are returned as absolute paths and sorted alphabetically
        - Extension counting is case-sensitive
        - Hidden files (starting with '.') are included in the search

    Raises:
        FileNotFoundError: If folder doesn't exist
        ValueError: If no files are found or all files lack extensions
    """

    # Handle default mutable argument
    if files is None:
        files = []

    if folder:
        if not os.path.exists(folder):
            raise FileNotFoundError(f"Folder does not exist: {folder}")
        list_of_input_files = glob.glob(os.path.join(folder, "*"))
    else:
        list_of_input_files = files

    if not list_of_input_files:
        raise ValueError("No files found to analyze")

    list_of_input_files.sort()
    list_of_base_name = [os.path.basename(_file) for _file in list_of_input_files]

    # work with the largest common file extension from the folder selected

    counter_extension = Counter()
    for _file in list_of_base_name:
        [_base, _ext] = os.path.splitext(_file)
        if _ext:  # Only count files with extensions
            counter_extension[_ext] += 1

    if not counter_extension:
        raise ValueError("No files with extensions found")

    dominand_extension = ""
    dominand_number = 0
    for _key in counter_extension.keys():
        if counter_extension[_key] > dominand_number:
            dominand_extension = _key
            dominand_number = counter_extension[_key]

    list_of_input_files = glob.glob(os.path.join(folder, "*" + dominand_extension))
    list_of_input_files.sort()

    list_of_input_files = [os.path.abspath(_file) for _file in list_of_input_files]

    return (list_of_input_files, dominand_extension)


def retrieve_number_of_frames_from_file_name(file_name: str) -> int:
    """
    Extract the number of time-of-flight frames from a neutron imaging filename.

    Parses specially formatted filenames to extract the number of time frames.
    The expected format includes 'T' followed by the frame count, then 'p'.
    This is commonly used in neutron imaging file naming conventions.

    Args:
        file_name (str): Filename containing frame information in the format
                        '...T{frame_count}p...'. Example:
                        'image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff'

    Returns:
        int: Number of time-of-flight frames extracted from the filename

    Example:
        >>> filename = "image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff"
        >>> frames = retrieve_number_of_frames_from_file_name(filename)
        >>> frames
        2000

        >>> filename = "data_T500p.fits"
        >>> frames = retrieve_number_of_frames_from_file_name(filename)
        >>> frames
        500

    Raises:
        ValueError: If the filename doesn't contain required 'T' and 'p' markers
        ValueError: If the extracted value cannot be converted to an integer

    Note:
        - The function looks for the pattern 'T{number}p' in the filename
        - Only the basename of the file is considered (path is ignored)
        - The number must be a valid integer
    """

    # Extract basename to work with filename only
    base_name = os.path.basename(file_name)

    # using regex-like string parsing to find the number of frames in the file name
    if "T" in base_name and "p" in base_name:
        try:
            return int(base_name.split("T")[1].split("p")[0])
        except (IndexError, ValueError) as e:
            raise ValueError(f"Could not extract number of frames from file name: {file_name}") from e
    else:
        raise ValueError(f"File name does not contain required 'T' and 'p' markers: {file_name}")


def retrieve_time_bin_size_from_file_name(file_name: str) -> float:
    """
    Extract the time bin size from a neutron imaging filename.

    Parses specially formatted filenames to extract the time bin size used
    for time-of-flight measurements. The expected format includes 't' followed
    by the bin size, then 'T'. Handles scientific notation with automatic
    correction for common formatting issues.

    Args:
        file_name (str): Filename containing time bin information in the format
                        '...t{bin_size}T...'. Example:
                        'image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff'
                        Scientific notation like '1e6' is supported and corrected to '1e-6'.

    Returns:
        float: Time bin size in seconds (typically microseconds as 1e-6)

    Example:
        >>> filename = "image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff"
        >>> bin_size = retrieve_time_bin_size_from_file_name(filename)
        >>> bin_size
        1e-06

        >>> filename = "data_t0.001T500p.fits"
        >>> bin_size = retrieve_time_bin_size_from_file_name(filename)
        >>> bin_size
        0.001

    Raises:
        ValueError: If the filename doesn't contain required 't' and 'T' markers
        ValueError: If the extracted value cannot be converted to a float

    Note:
        - The function looks for the pattern 't{number}T' in the filename
        - Automatically corrects 'e' to 'e-' in scientific notation (common formatting)
        - Only the basename of the file is considered (path is ignored)
        - Supports both decimal and scientific notation
    """

    # Extract basename to work with filename only
    base_name = os.path.basename(file_name)

    if "t" in base_name and "T" in base_name:
        try:
            _uncorrected_value = base_name.split("t")[1].split("T")[0]
            # add - after "e" to correct the value for scientific notation
            if "e" in str(_uncorrected_value):
                _corrected_value = str(_uncorrected_value).replace("e", "e-")
                return float(_corrected_value)
            return float(_uncorrected_value)
        except (IndexError, ValueError) as e:
            raise ValueError(f"Could not extract time bin size from file name: {file_name}") from e
    else:
        raise ValueError(f"File name does not contain required 't' and 'T' markers: {file_name}")


def export_ascii(data_dict: Dict[str, Union[List, Any]], file_path: str) -> None:
    """
    Export processed data to a tab-separated ASCII file.

    Converts a dictionary of data arrays to a formatted ASCII file suitable
    for analysis in external tools. The output uses tab separation with
    column headers for easy import into spreadsheet or analysis software.

    Args:
        data_dict (Dict[str, Union[List, Any]]): Dictionary containing data to export.
                                               Keys become column headers, values become data columns.
                                               All values should be array-like with the same length.
        file_path (str): Path to the output ASCII file. Parent directories will be
                        created if they don't exist.

    Example:
        Basic export:
        >>> data = {
        ...     "energy_eV": [1.0, 2.0, 3.0],
        ...     "transmission": [0.8, 0.6, 0.4],
        ...     "uncertainties": [0.1, 0.08, 0.06]
        ... }
        >>> export_ascii(data, "transmission_results.txt")
        Data exported to transmission_results.txt

        Output file format:
        energy_eV	transmission	uncertainties
        1.0	0.8	0.1
        2.0	0.6	0.08
        3.0	0.4	0.06

    Raises:
        ValueError: If data_dict is empty or contains mismatched array lengths
        IOError: If file cannot be written (permissions, disk space, etc.)
        KeyError: If data_dict contains invalid data types

    Note:
        - Uses tab separation for easy import into analysis software
        - Includes column headers in the first row
        - Creates parent directories if they don't exist
        - Overwrites existing files without warning
        - All data columns must have the same length
    """
    # Validate input
    if not data_dict:
        raise ValueError("Data dictionary cannot be empty")

    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try:
        df = pd.DataFrame(data_dict)
        df.to_csv(file_path, sep="\t", index=False, header=True)
        print(f"Data exported to {file_path}")
        logger.info(f"Data exported to {file_path}")
    except Exception as e:
        error_msg = f"Failed to export data to {file_path}: {str(e)}"
        logger.error(error_msg)
        raise IOError(error_msg) from e
