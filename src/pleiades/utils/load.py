import numpy as np
from dxchange.reader import read_fits, read_tiff

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="load")


def load(list_of_files: list, file_extension: str) -> np.ndarray:
    """
    Load the data from the list of files.

    Parameters:
    - list_of_files: List of files to load.
    - file_extension: File extension to determine the file type (e.g., 'tiff', 'fits').

    Returns:
    - Loaded data.
    """

    logger.info(f"loading {len(list_of_files)} files with extension {file_extension}")

    # Check if the input files are valid
    if not list_of_files:
        raise ValueError("List of files must be provided.")

    # get file extension
    if file_extension == ".tiff" or file_extension == ".tif":
        # Load TIFF files
        data = load_tiff(list_of_files)
    elif file_extension == ".fits":
        # Load FITS files
        data = load_fits(list_of_files)
    else:
        raise ValueError(f"Unsupported file extension: {file_extension}")

    return data


def load_tiff(list_of_tiff: list, dtype=np.uint16) -> np.ndarray:
    """
    Load TIFF files.

    Parameters:
    - list_of_tiff: List of TIFF files to load.
    - dtype: Data type to convert the loaded data (optional).

    Returns:
    - Loaded data.
    """

    # init array
    first_image = read_tiff(list_of_tiff[0])
    size_3d = [len(list_of_tiff), np.shape(first_image)[0], np.shape(first_image)[1]]
    data_3d_array = np.empty(size_3d, dtype=dtype)

    # load stack of tiff
    for _index, _file in enumerate(list_of_tiff):
        _array = read_tiff(_file)
        data_3d_array[_index] = _array

    return data_3d_array


def load_fits(list_of_fits: list, dtype=np.uint16) -> np.ndarray:
    """
    Load FITS files.

    Parameters:
    - list_of_fits: List of FITS files to load.
    - dtype: Data type to convert the loaded data (optional).

    Returns:
    - Loaded data.
    """

    # init array
    first_image = read_fits(list_of_fits[0])
    size_3d = [len(list_of_fits), np.shape(first_image)[0], np.shape(first_image)[1]]
    data_3d_array = np.empty(size_3d, dtype=dtype)

    # load stack of fits
    for _index, _file in enumerate(list_of_fits):
        _array = read_fits(_file)
        data_3d_array[_index] = _array

    return data_3d_array
