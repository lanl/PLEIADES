import pytest
import tempfile
import os

from pleiades.utils.files import (
    retrieve_list_of_most_dominant_extension_from_folder,
    retrieve_number_of_frames_from_file_name,
    retrieve_time_bin_size_from_file_name,
)


def test_retrieve_list_of_most_dominant_extension_from_folder():

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a temporary directory
        temp_dir = tmpdir + "/test_dir"
        os.makedirs(temp_dir)

        # Create test files with different extensions
        file1 = os.path.join(temp_dir, "file1.txt")
        with open(file1, "w") as f:
            f.write("This is a test file.")

        file2 = os.path.join(temp_dir, "file2.txt")
        with open(file2, "w") as f:
            f.write("This is another test file.")

        file3 = os.path.join(temp_dir, "file3.csv")
        with open(file3, "w") as f:
            f.write("This is a CSV file.")

        # Test the function
        result, dominant_extension = retrieve_list_of_most_dominant_extension_from_folder(temp_dir)

        assert len(result) == 2
        assert dominant_extension == ".txt"


def test_retrieve_number_of_frames_from_file_name():
    # Test with a valid file name
    file_name = "image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff"
    frames = retrieve_number_of_frames_from_file_name(file_name)
    assert frames == 2000

    # Test with an invalid file name that does not contain 'T' or 'p'
    invalid_file_name = "image_m2M9997Ex512y512.tiff"
    with pytest.raises(ValueError):
        retrieve_number_of_frames_from_file_name(invalid_file_name)

    # Test with a file name that has an incorrect format
    incorrect_format_file_name = "image_m2M9997Ex512y512T2000ap1e6P100.tiff"
    with pytest.raises(ValueError):
        retrieve_number_of_frames_from_file_name(incorrect_format_file_name)


def test_retrieve_time_bin_size_from_file_name():
    # Test with a valid file name
    file_name = "image_m2M9997Ex512y512t1e6T2000p1e6P100.tiff"
    time_bin_size = retrieve_time_bin_size_from_file_name(file_name)
    assert time_bin_size == 1e-6

    # Test with an invalid file name that does not contain 't' or 'T'
    invalid_file_name = "image_m2M9997Ex512y512.tiff"
    with pytest.raises(ValueError):
        retrieve_time_bin_size_from_file_name(invalid_file_name)

    # Test with a file name that has an incorrect format
    incorrect_format_file_name = "image_m2M9997Ex512y512T2000p1e6P100.tiff"
    with pytest.raises(ValueError):
        retrieve_time_bin_size_from_file_name(incorrect_format_file_name)


if __name__ == "__main__":
    pytest.main()