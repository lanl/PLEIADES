#!/usr/bin/env python
"""Unit tests for the NuclearDataManager class."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from pleiades.nuclear.isotopes.models import IsotopeInfo
from pleiades.nuclear.manager import DataSource, EndfLibrary, NuclearDataManager
from pleiades.utils.config import PleiadesConfig


@pytest.fixture
def mock_config():
    """Create a test configuration."""
    # Create a temporary test configuration
    test_config = PleiadesConfig(
        nuclear_data_cache_dir=Path("/tmp/pleiades_test/nuclear_data"),
        nuclear_data_sources={
            "IAEA": "https://test-iaea.org/download-endf",
            "NNDC": "https://test-nndc.org/endf/data",
        },
    )

    # Patch the global config to use our test config
    with patch("pleiades.nuclear.manager.get_config", return_value=test_config):
        yield test_config


@pytest.fixture
def mock_isotope_info():
    """Create a mock IsotopeInfo instance."""
    isotope = IsotopeInfo(
        name="U-238",
        element="U",
        mass_number=238,
        atomic_number=92,
        material_number=9237,
    )
    return isotope


@pytest.fixture
def mock_isotope_manager():
    """Create a mock IsotopeManager."""
    manager = MagicMock()
    manager.get_isotope_info.return_value = IsotopeInfo(
        name="U-238",
        element="U",
        mass_number=238,
        atomic_number=92,
        material_number=9237,
    )
    manager.get_mat_number.return_value = 9237
    return manager


@pytest.fixture
def data_manager(mock_isotope_manager, mock_config):
    """Create a NuclearDataManager instance with mocked dependencies."""
    with patch("pleiades.nuclear.manager.Path.mkdir") as mock_mkdir:
        manager = NuclearDataManager(isotope_manager=mock_isotope_manager)
        # Ensure cache directories are created
        assert mock_mkdir.called
        return manager


def test_create_isotope_parameters_from_string_valid(data_manager):
    """Test creating IsotopeParameters with a valid isotope string."""
    # Call the method under test with a valid isotope string
    isotope_params = data_manager.create_isotope_parameters_from_string("U-238")

    # Assert that the returned IsotopeParameters instance is correct
    assert isotope_params.isotope_infomation.name == "U-238"
    assert isotope_params.isotope_infomation.mass_number == 238
    assert isotope_params.isotope_infomation.element == "U"
    assert isotope_params.isotope_infomation.material_number == 9237
    assert isotope_params.abundance is None  # Default value
    assert isotope_params.spin_groups == []  # Default empty list
    # New test for default library
    assert isotope_params.endf_library == EndfLibrary.ENDF_B_VIII_0


def test_initialize_cache(mock_config):
    """Test that cache directories are created during initialization."""
    with patch("pleiades.nuclear.manager.Path.mkdir") as mock_mkdir:
        manager = NuclearDataManager()

        # Should create a directory for each combination of source and library
        expected_calls = len(DataSource) * len(EndfLibrary)
        assert mock_mkdir.call_count >= expected_calls


def test_get_cache_dir(data_manager, mock_config):
    """Test getting the cache directory for a specific source and library."""
    # Test for IAEA source and ENDF-B-VIII.0 library
    cache_dir = data_manager._get_cache_dir(DataSource.IAEA, EndfLibrary.ENDF_B_VIII_0)
    expected_path = mock_config.nuclear_data_cache_dir / DataSource.IAEA / EndfLibrary.ENDF_B_VIII_0
    assert cache_dir == expected_path


def test_get_cache_file_path(data_manager, mock_isotope_info):
    """Test getting the cache file path for a specific file."""
    # Test for IAEA source, ENDF-B-VIII.0 library, and U-238 isotope
    cache_file_path = data_manager._get_cache_file_path(
        DataSource.IAEA, EndfLibrary.ENDF_B_VIII_0, mock_isotope_info, 9237
    )
    expected_filename = "n_092-U-238_9237.dat"
    assert cache_file_path.name == expected_filename


def test_download_endf_resonance_file_cache_hit(data_manager, mock_isotope_info, mock_config):
    """Test downloading ENDF resonance file when it exists in cache."""
    # Mock the cache file
    cache_file_path = data_manager._get_cache_file_path(
        DataSource.IAEA, EndfLibrary.ENDF_B_VIII_0, mock_isotope_info, 9237
    )

    # Create mock content with resonance data lines
    mock_content = "Some content\n".encode() + "Line with resonance data  2\n".encode()

    # Patch file exists check and open operations
    with (
        patch("pleiades.nuclear.manager.Path.exists", return_value=True),
        patch("builtins.open", Mock()),
        patch("pleiades.nuclear.manager.Path.write_text") as mock_write,
        patch("builtins.open", mock_open := MagicMock()),
    ):
        # Configure mock to return our content when reading
        mock_open.return_value.__enter__.return_value.read.return_value = mock_content

        # Call the method under test
        output_path = data_manager.download_endf_resonance_file(
            mock_isotope_info, EndfLibrary.ENDF_B_VIII_0, output_dir="/tmp"
        )

        # Verify the output path is correct
        assert output_path.name == "092-U-238.B-VIII.0.par"
        assert output_path.parent == Path("/tmp")

        # Verify we used the cached data
        mock_open.assert_called()


@patch("pleiades.nuclear.manager.requests.get")
def test_download_endf_resonance_file_cache_miss(mock_get, data_manager, mock_isotope_info, mock_config):
    """Test downloading ENDF resonance file when it doesn't exist in cache."""
    # Set up mocks
    mock_response = Mock()
    mock_response.content = b"Mock ZIP content"
    mock_get.return_value = mock_response
    mock_response.raise_for_status = Mock()

    # Set up the mock for _get_data_from_iaea method instead of trying to mock zipfile
    with (
        patch.object(
            data_manager, "_get_data_from_iaea", return_value=(b"Line with resonance data  2\n", "file.dat")
        ) as mock_get_data,
        patch("pleiades.nuclear.manager.Path.exists", return_value=False),
        patch("pleiades.nuclear.manager.Path.write_text") as mock_write,
    ):
        # Call the method under test
        output_path = data_manager.download_endf_resonance_file(
            mock_isotope_info, EndfLibrary.ENDF_B_VIII_0, output_dir="/tmp"
        )

        # Verify the output path is correct
        assert output_path.name == "092-U-238.B-VIII.0.par"
        assert output_path.parent == Path("/tmp")

        # Verify our mock was called
        mock_get_data.assert_called_once()


def test_clear_cache(data_manager, mock_config):
    """Test clearing the cache."""
    with (
        patch("pleiades.nuclear.manager.Path.exists", return_value=True),
        patch("pleiades.nuclear.manager.Path.glob") as mock_glob,
    ):
        # Create a new test for each case to avoid issues with multiple calls

        # Test 1: Clearing all caches
        mock_file1 = MagicMock()
        mock_file2 = MagicMock()
        mock_glob.return_value = [mock_file1, mock_file2]

        # Test clearing all caches
        data_manager.clear_cache()
        assert mock_glob.call_count > 0

        # Verify each returned mock file had unlink called
        assert mock_file1.unlink.called
        assert mock_file2.unlink.called

    # Test 2: Clearing specific source
    with (
        patch("pleiades.nuclear.manager.Path.exists", return_value=True),
        patch("pleiades.nuclear.manager.Path.glob") as mock_glob,
    ):
        mock_file1 = MagicMock()
        mock_file2 = MagicMock()
        mock_glob.return_value = [mock_file1, mock_file2]

        data_manager.clear_cache(source=DataSource.IAEA)
        assert mock_glob.call_count > 0
        assert mock_file1.unlink.called
        assert mock_file2.unlink.called

    # Test 3: Clearing specific source and library
    with (
        patch("pleiades.nuclear.manager.Path.exists", return_value=True),
        patch("pleiades.nuclear.manager.Path.glob") as mock_glob,
    ):
        mock_file1 = MagicMock()
        mock_file2 = MagicMock()
        mock_glob.return_value = [mock_file1, mock_file2]

        data_manager.clear_cache(source=DataSource.IAEA, library=EndfLibrary.ENDF_B_VIII_0)
        assert mock_glob.call_count > 0
        assert mock_file1.unlink.called
        assert mock_file2.unlink.called


def test_nndc_not_implemented(data_manager, mock_isotope_info):
    """Test that NNDC download raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        # Try to download from NNDC source
        data_manager.download_endf_resonance_file(mock_isotope_info, EndfLibrary.ENDF_B_VIII_0, source=DataSource.NNDC)


# Helper for tests
def mock_open(*args, **kwargs):
    """Mock implementation of built-in open function."""
    m = MagicMock()
    m.__enter__.return_value = m
    m.read.return_value = b"Mock file content"
    return m


if __name__ == "__main__":
    pytest.main(["-v", __file__])
