from pathlib import Path

import pytest

from pleiades.nuclear.isotopes.manager import IsotopeManager
from pleiades.nuclear.isotopes.models import FileCategory


@pytest.fixture
def manager():
    return IsotopeManager()


def test_initialize_cache(manager):
    manager._initialize_cache()
    print("Cached files:", manager._cached_files)
    cached_files = {file.name for file in manager._cached_files[FileCategory.ISOTOPES]}  # Extract filenames as strings
    assert "isotopes.info" in cached_files
    assert "mass.mas20" in cached_files
    assert "neutrons.list" in cached_files


def test_get_category_path():
    assert IsotopeManager._get_category_path(FileCategory.ISOTOPES) == "isotopes"


def test_get_file_path_valid(manager):
    # Grab the path to the actual files directory
    files_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "src/pleiades/nuclear/isotopes/files"
    test_file = files_dir / "isotopes.info"

    # Ensure the test file exists
    assert test_file.exists(), f"Test file {test_file} does not exist."

    # Debug: Print cached files
    print("Cached files:", manager._cached_files)

    # Call the method under test
    path = manager.get_file_path(FileCategory.ISOTOPES, "isotopes.info")

    # Assert that the returned path matches the actual file path
    assert path == test_file


def test_get_file_path_invalid_extension(manager):
    with pytest.raises(ValueError, match="Invalid file extension"):
        manager.get_file_path(FileCategory.ISOTOPES, "test.invalid")


def test_get_file_path_not_found(manager):
    with pytest.raises(FileNotFoundError, match="File test.info not found"):
        manager.get_file_path(FileCategory.ISOTOPES, "test.info")


def test_list_files(manager):
    manager._initialize_cache()
    files = manager.list_files()

    # Ensure the category exists in the returned files
    assert FileCategory.ISOTOPES in files

    # Extract filenames from the returned Path objects
    filenames = [file.name for file in files[FileCategory.ISOTOPES]]

    # Assert that the filenames match the expected list
    assert sorted(filenames) == ["isotopes.info", "mass.mas20", "neutrons.list"]


def test_list_files_invalid_category(manager):
    with pytest.raises(ValueError, match="Invalid category"):
        manager.list_files("invalid_category")


def test_validate_file(manager):
    manager._initialize_cache()
    assert manager.validate_file(FileCategory.ISOTOPES, "isotopes.info") is True
    assert manager.validate_file(FileCategory.ISOTOPES, "test.invalid") is False
