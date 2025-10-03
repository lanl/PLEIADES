"""
NeXus file utilities for PLEIADES neutron imaging data processing.

This module provides utilities for reading and processing NeXus HDF5 files commonly
used at neutron scattering facilities. It focuses on extracting proton charge
information essential for beam intensity normalization in neutron imaging experiments.

NeXus is a common data format for neutron, X-ray, and muon science that provides
standardized file structures for experimental data and metadata. This module
handles the facility-specific implementations for accessing beam monitoring data.

The module supports:
- Proton charge extraction from NeXus files
- Unit conversion (picocoulombs to coulombs)
- Validation of proton charge data availability
- Batch processing of multiple NeXus files

Example:
    Basic proton charge extraction:

    >>> charge_pc = get_proton_charge("/path/to/nexus.h5", units="pc")
    >>> charge_c = get_proton_charge("/path/to/nexus.h5", units="c")
    >>> print(f"Charge: {charge_pc} pC = {charge_c} C")

    Batch validation:
    >>> result = get_proton_charge_dict(sample_files, ob_files, 2, 1)
    >>> if result["state"]:
    ...     print("Proton charge normalization available")
"""

from typing import Dict, List, Optional, Union

import h5py

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="nexus")


def get_proton_charge(nexus: Optional[str], units: str = "pc") -> Optional[float]:
    """
    Extract proton charge from a NeXus HDF5 file.

    Reads proton charge measurements from NeXus files, which represent the
    total charge delivered to the neutron production target. This value is
    proportional to the neutron flux and is essential for normalizing
    beam intensity variations between measurements.

    Args:
        nexus (Optional[str]): Path to NeXus HDF5 file. If None, returns None.
        units (str, optional): Units for the returned value. Defaults to "pc".
                              - "pc": picocoulombs (raw NeXus value)
                              - "c": coulombs (divided by 1e12)

    Returns:
        Optional[float]: Proton charge value in requested units, or None if:
            - nexus path is None
            - file cannot be opened
            - proton charge data is missing

    Example:
        >>> # Get proton charge in picocoulombs (default)
        >>> charge_pc = get_proton_charge("VENUS_7820.nxs.h5")
        >>> charge_pc
        1.234567e+12

        >>> # Get proton charge in coulombs
        >>> charge_c = get_proton_charge("VENUS_7820.nxs.h5", units="c")
        >>> charge_c
        1.234567

        >>> # Handle missing file
        >>> charge = get_proton_charge(None)
        >>> charge is None
        True

    Note:
        - NeXus files store proton charge at path: /entry/proton_charge[0]
        - Conversion factor: 1 Coulomb = 1e12 picocoulombs
        - Function handles file access errors gracefully
        - Essential for quantitative neutron imaging analysis

    Raises:
        KeyError: If NeXus file structure is unexpected (logged but returns None)
        OSError: If file access fails (logged but returns None)
    """

    if nexus is None:
        logger.debug("Nexus path is None, returning None")
        return None

    try:
        with h5py.File(nexus, "r") as hdf5_data:
            proton_charge = hdf5_data["entry"]["proton_charge"][0]
            if units == "c":
                return float(proton_charge / 1e12)
            elif units == "pc":
                return float(proton_charge)
            else:
                logger.warning(f"Unknown units '{units}', defaulting to picocoulombs")
                return float(proton_charge)
    except (FileNotFoundError, OSError) as e:
        logger.error(f"Could not open NeXus file {nexus}: {e}")
        return None
    except (KeyError, IndexError) as e:
        logger.error(f"Proton charge data not found in NeXus file {nexus}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading NeXus file {nexus}: {e}")
        return None


def get_proton_charge_dict(
    list_sample_nexus: List[str], list_nexus_obs: List[str], nbr_sample_folders: int, nbr_obs_folders: int
) -> Dict[str, Union[bool, List[float], None]]:
    """
    Validate proton charge availability and extract values for normalization.

    Comprehensive validation function that checks if proton charge normalization
    is feasible by verifying file counts match folder counts and that all
    NeXus files contain valid proton charge data.

    Args:
        list_sample_nexus (List[str]): List of sample NeXus file paths
        list_nexus_obs (List[str]): List of open beam NeXus file paths
        nbr_sample_folders (int): Expected number of sample folders
        nbr_obs_folders (int): Expected number of open beam folders

    Returns:
        Dict[str, Union[bool, List[float], None]]: Dictionary containing:
            - "state" (bool): True if proton charge normalization is possible
            - "sample" (List[float] or None): Sample proton charge values in picocoulombs
            - "ob" (List[float] or None): Open beam proton charge values in picocoulombs

    Validation Criteria:
        1. Number of sample NeXus files must match number of sample folders
        2. Number of open beam NeXus files must match number of open beam folders
        3. All sample NeXus files must contain valid proton charge data
        4. All open beam NeXus files must contain valid proton charge data

    Example:
        Successful validation:
        >>> sample_nexus = ["/path/sample1.h5", "/path/sample2.h5"]
        >>> ob_nexus = ["/path/ob1.h5"]
        >>> result = get_proton_charge_dict(sample_nexus, ob_nexus, 2, 1)
        >>> result
        {
            'state': True,
            'sample': [1.234e12, 1.456e12],
            'ob': [1.389e12]
        }

        Failed validation (missing data):
        >>> result = get_proton_charge_dict([], ob_nexus, 2, 1)
        >>> result
        {
            'state': False,
            'sample': None,
            'ob': None
        }

    Note:
        - Function returns False state on any validation failure
        - Logs detailed information about validation failures
        - Proton charge values returned in picocoulombs (NeXus default)
        - Essential prerequisite for beam intensity normalization

    Raises:
        ValueError: If folder counts are negative
    """
    # Input validation
    if nbr_sample_folders < 0 or nbr_obs_folders < 0:
        raise ValueError("Folder counts cannot be negative")

    logger.info("Checking if normalization by proton charge is possible")
    logger.info(f"Sample NeXus files: {len(list_sample_nexus)}, Expected folders: {nbr_sample_folders}")
    logger.info(f"Open beam NeXus files: {len(list_nexus_obs)}, Expected folders: {nbr_obs_folders}")

    proton_charge_dict: Dict[str, Union[bool, List[float], None]] = {"state": False, "sample": None, "ob": None}

    # Validate file counts match expected folder counts
    if len(list_sample_nexus) != nbr_sample_folders:
        logger.warning(
            f"Number of sample NeXus files ({len(list_sample_nexus)}) does not match "
            f"the number of sample folders ({nbr_sample_folders})"
        )
        return proton_charge_dict

    if len(list_nexus_obs) != nbr_obs_folders:
        logger.warning(
            f"Number of open beam NeXus files ({len(list_nexus_obs)}) does not match "
            f"the number of open beam folders ({nbr_obs_folders})"
        )
        return proton_charge_dict

    # Extract proton charge from all sample NeXus files
    sample_list_proton_charge = [get_proton_charge(nexus) for nexus in list_sample_nexus]
    if None in sample_list_proton_charge:
        logger.warning("Some proton charge values are missing from the sample NeXus files")
        missing_indices = [i for i, val in enumerate(sample_list_proton_charge) if val is None]
        logger.warning(f"Missing proton charge in sample files at indices: {missing_indices}")
        return proton_charge_dict

    # Extract proton charge from all open beam NeXus files
    ob_list_proton_charge = [get_proton_charge(nexus) for nexus in list_nexus_obs]
    if None in ob_list_proton_charge:
        logger.warning("Some proton charge values are missing from the open beam NeXus files")
        missing_indices = [i for i, val in enumerate(ob_list_proton_charge) if val is None]
        logger.warning(f"Missing proton charge in open beam files at indices: {missing_indices}")
        return proton_charge_dict

    # All validation checks passed - normalization by proton charge is possible
    proton_charge_dict = {"state": True, "sample": sample_list_proton_charge, "ob": ob_list_proton_charge}

    logger.info("✓ Normalization by proton charge is possible")
    logger.info(f"Sample proton charges (pC): {sample_list_proton_charge}")
    logger.info(f"Open beam proton charges (pC): {ob_list_proton_charge}")

    return proton_charge_dict
