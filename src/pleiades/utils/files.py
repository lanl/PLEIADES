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
