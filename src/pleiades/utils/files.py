import glob
import os
from collections import Counter


def retrieve_list_of_most_dominant_extension_from_folder(folder='', files=[]):
    '''
    This will return the list of files from the most dominant file extension found in the folder
    as well as the most dominant extension used
    '''

    if folder:
        list_of_input_files = glob.glob(os.path.join(folder, '*'))
    else:
        list_of_input_files = files

    list_of_input_files.sort()
    list_of_base_name = [os.path.basename(_file) for _file in list_of_input_files]

    # work with the largest common file extension from the folder selected

    counter_extension = Counter()
    for _file in list_of_base_name:
        [_base, _ext] = os.path.splitext(_file)
        counter_extension[_ext] += 1

    dominand_extension = ''
    dominand_number = 0
    for _key in counter_extension.keys():
        if counter_extension[_key] > dominand_number:
            dominand_extension = _key
            dominand_number = counter_extension[_key]

    list_of_input_files = glob.glob(os.path.join(folder, '*' + dominand_extension))
    list_of_input_files.sort()

    list_of_input_files = [os.path.abspath(_file) for _file in list_of_input_files]

    return [list_of_input_files, dominand_extension]


def retrieve_number_of_frames_from_file_name(file_name: str) -> int:
    """
    Retrieve the number of frames from the file name.
    The file name should contain the number of frames in the format image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff
    where the number of frames is after 'T' and before 'p'.
    """
    
    # using regex to find the number of frames in the file name
    if 'T' in file_name and 'p' in file_name:
        try:
            return int(file_name.split('T')[1].split('p')[0])
        except (IndexError, ValueError):
            raise ValueError(f"Could not extract number of frames from file name: {file_name}")
    else:
        raise ValueError(f"File name does not contain 'T' or 'p': {file_name}")
        

def retrieve_time_bin_size_from_file_name(file_name: str) -> float:
    """
    Retrieve the time bin size from the file name.
    The file name should contain the time bin size in the format image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff
    where the time bin size is after 't' and before 'T'.
    """

    if 't' in file_name and 'T' in file_name:
        try:
            _uncorrected_value = file_name.split('t')[1].split('T')[0]
            # add - after "e" to correct the value
            if 'e' in str(_uncorrected_value):
                _corrected_value = str(_uncorrected_value).replace('e', 'e-')
                return float(_corrected_value)
            return float(_uncorrected_value)
        except (IndexError, ValueError):
            raise ValueError(f"Could not extract time bin size from file name: {file_name}")
    else:
        raise ValueError(f"File name does not contain 't' or 'T': {file_name}")