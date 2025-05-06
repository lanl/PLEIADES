def get_shutter_values_dict(list_sample_folders: list, list_obs_folders: list, timepix: object) -> dict:
    """
    Get the shutter values from the timepix object for the given sample and observation folders.
    """
    shutter_values_dict = {
        'sample': {},
        'ob': {}
    }

    for folder in list_sample_folders:
        shutter_values_dict['sample'][folder] = timepix.get_shutter_values(folder)

    for folder in list_obs_folders:
        shutter_values_dict['ob'][folder] = timepix.get_shutter_values(folder)

    return shutter_values_dict