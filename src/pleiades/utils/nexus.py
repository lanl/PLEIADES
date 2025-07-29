import h5py

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="nexus")


def get_proton_charge(nexus: str, units="pc") -> float:
    """
    Get the proton charge from the nexus file"""

    if nexus is None:
        return None

    try:
        with h5py.File(nexus, "r") as hdf5_data:
            proton_charge = hdf5_data["entry"]["proton_charge"][0]
            if units == "c":
                return proton_charge / 1e12
            return proton_charge
    except FileNotFoundError:
        return None


def get_proton_charge_dict(
    list_sample_nexus: list, list_nexus_obs: list, nbr_sample_folders: int, nbr_obs_folders: int
) -> dict:
    """
    Check if all the conditions are met to normalize by proton charge
    and  return the state as well as the proton charge value.

    - the number of sample nexus must match the number of sample folders
    and
    - the number of open beam nexus must match the number of open beam folders

    then check if the proton charge value is present in the nexus file

    if those 2 conditions are met, then the normalization by proton charge can be used

    Returns:
        bool: True if normalization is by proton charge, False otherwise.
    """
    logger.info("Checking if normalization by proton charge is possible")

    proton_charge_dict = {"state": False, "sample": None, "ob": None}

    if len(list_sample_nexus) != nbr_sample_folders:
        logger.info(
            f"Number of sample nexus files ({len(list_sample_nexus)}) does not match the number of sample folders ({nbr_sample_folders})"
        )
        return proton_charge_dict

    if len(list_nexus_obs) != nbr_obs_folders:
        logger.info(
            f"Number of open beam nexus files ({len(list_nexus_obs)}) does not match the number of open beam folders ({nbr_obs_folders})"
        )
        return proton_charge_dict

    sample_list_proton_charge = [get_proton_charge(nexus) for nexus in list_sample_nexus]
    if None in sample_list_proton_charge:
        logger.info("Some of the proton charge are missing from the sample nexus files")
        return proton_charge_dict

    ob_list_proton_charge = [get_proton_charge(nexus) for nexus in list_nexus_obs]
    if None in ob_list_proton_charge:
        logger.info("Some of the proton charge are missing from the open beam nexus files")
        return proton_charge_dict

    # If all checks pass, normalization by proton charge is possible

    proton_charge_dict = {"state": True, "sample": sample_list_proton_charge, "ob": ob_list_proton_charge}

    logger.info("Normalization by proton charge is possible")
    logger.info(f"{proton_charge_dict = }")

    return proton_charge_dict
