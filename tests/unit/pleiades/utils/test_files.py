import pytest
import tempfile
import os

from pleiades.utils.files import (
    retrieve_list_of_most_dominant_extension_from_folder,
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


if __name__ == "__main__":
    pytest.main()