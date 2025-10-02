"""Comprehensive unit tests for utils/load.py module."""

from unittest.mock import patch

import astropy.io.fits as fits
import numpy as np
import pytest
import tifffile

from pleiades.utils.load import load, load_fits, load_tiff


@pytest.fixture(scope="function")
def data_fixture(tmpdir):
    """Create temporary test files for testing."""
    # dummy tiff image data
    data = np.ones((3, 3))

    # TIFF files
    # -- valid tiff with generic name, no metadata
    generic = tmpdir / "generic_dir"
    generic.mkdir()

    tiff_file_name = generic / "generic.tiff"
    tifffile.imwrite(str(tiff_file_name), data)

    # Fits files
    fits_file_name = generic / "generic.fits"
    hdu = fits.PrimaryHDU(data)
    hdu.writeto(str(fits_file_name))

    # return the tmp files
    return tiff_file_name, fits_file_name


class TestLoadFunction:
    """Test the main load function."""

    @patch("pleiades.utils.load.load_tiff")
    def test_load_tiff_files(self, mock_load_tiff):
        """Test loading TIFF files through main load function."""
        mock_load_tiff.return_value = np.array([[[1, 2], [3, 4]]])

        files = ["file1.tiff", "file2.tiff"]
        result = load(files, ".tiff")

        mock_load_tiff.assert_called_once_with(files)
        assert result.shape == (1, 2, 2)

    @patch("pleiades.utils.load.load_tiff")
    def test_load_tif_files(self, mock_load_tiff):
        """Test loading TIF files (alternative extension)."""
        mock_load_tiff.return_value = np.array([[[1, 2], [3, 4]]])

        files = ["file1.tif", "file2.tif"]
        result = load(files, ".tif")

        mock_load_tiff.assert_called_once_with(files)
        assert result.shape == (1, 2, 2)

    @patch("pleiades.utils.load.load_fits")
    def test_load_fits_files(self, mock_load_fits):
        """Test loading FITS files through main load function."""
        mock_load_fits.return_value = np.array([[[5, 6], [7, 8]]])

        files = ["file1.fits", "file2.fits"]
        result = load(files, ".fits")

        mock_load_fits.assert_called_once_with(files)
        assert result.shape == (1, 2, 2)

    def test_load_empty_list(self):
        """Test that empty file list raises ValueError."""
        with pytest.raises(ValueError, match="List of files must be provided"):
            load([], ".tiff")

    def test_load_unsupported_extension(self):
        """Test that unsupported file extension raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported file extension"):
            load(["file.jpg"], ".jpg")

    @patch("pleiades.utils.load.logger")
    @patch("pleiades.utils.load.load_tiff")
    def test_load_logs_info(self, mock_load_tiff, mock_logger):
        """Test that load function logs information."""
        mock_load_tiff.return_value = np.zeros((2, 3, 3))

        files = ["file1.tiff", "file2.tiff", "file3.tiff"]
        load(files, ".tiff")

        mock_logger.info.assert_called_once_with("loading 3 files with extension .tiff")


class TestLoadTiff:
    """Test the load_tiff function."""

    @patch("pleiades.utils.load.read_tiff")
    def test_load_single_tiff(self, mock_read_tiff):
        """Test loading a single TIFF file."""
        mock_image = np.array([[1, 2, 3], [4, 5, 6]])
        mock_read_tiff.return_value = mock_image

        files = ["file1.tiff"]
        result = load_tiff(files)

        assert result.shape == (1, 2, 3)
        assert np.array_equal(result[0], mock_image)
        # Called twice - once for shape, once for loading
        assert mock_read_tiff.call_count == 2

    @patch("pleiades.utils.load.read_tiff")
    def test_load_multiple_tiff(self, mock_read_tiff):
        """Test loading multiple TIFF files."""
        mock_image1 = np.array([[1, 2], [3, 4]])
        mock_image2 = np.array([[5, 6], [7, 8]])
        mock_image3 = np.array([[9, 10], [11, 12]])

        mock_read_tiff.side_effect = [mock_image1, mock_image1, mock_image2, mock_image3]

        files = ["file1.tiff", "file2.tiff", "file3.tiff"]
        result = load_tiff(files)

        assert result.shape == (3, 2, 2)
        assert np.array_equal(result[0], mock_image1)
        assert np.array_equal(result[1], mock_image2)
        assert np.array_equal(result[2], mock_image3)

    @patch("pleiades.utils.load.read_tiff")
    def test_load_tiff_with_dtype(self, mock_read_tiff):
        """Test loading TIFF files with specified dtype."""
        mock_image = np.array([[1.5, 2.5], [3.5, 4.5]])
        mock_read_tiff.return_value = mock_image

        files = ["file1.tiff"]
        result = load_tiff(files, dtype=np.float32)

        assert result.dtype == np.float32
        assert result.shape == (1, 2, 2)

    @patch("pleiades.utils.load.read_tiff")
    def test_load_tiff_default_dtype(self, mock_read_tiff):
        """Test that default dtype is uint16."""
        mock_image = np.array([[1, 2], [3, 4]])
        mock_read_tiff.return_value = mock_image

        files = ["file1.tiff"]
        result = load_tiff(files)

        assert result.dtype == np.uint16

    def test_load_tiff_real_file(self, data_fixture):
        """Test loading a real TIFF file."""
        tiff_file, _ = data_fixture

        result = load_tiff([str(tiff_file)])

        assert result.shape == (1, 3, 3)
        assert np.array_equal(result[0], np.ones((3, 3)))


class TestLoadFits:
    """Test the load_fits function."""

    @patch("pleiades.utils.load.read_fits")
    def test_load_single_fits(self, mock_read_fits):
        """Test loading a single FITS file."""
        mock_image = np.array([[10, 20, 30], [40, 50, 60]])
        mock_read_fits.return_value = mock_image

        files = ["file1.fits"]
        result = load_fits(files)

        assert result.shape == (1, 2, 3)
        assert np.array_equal(result[0], mock_image)
        # Called twice - once for shape, once for loading
        assert mock_read_fits.call_count == 2

    @patch("pleiades.utils.load.read_fits")
    def test_load_multiple_fits(self, mock_read_fits):
        """Test loading multiple FITS files."""
        mock_image1 = np.array([[1, 2], [3, 4]])
        mock_image2 = np.array([[5, 6], [7, 8]])
        mock_image3 = np.array([[9, 10], [11, 12]])

        mock_read_fits.side_effect = [mock_image1, mock_image1, mock_image2, mock_image3]

        files = ["file1.fits", "file2.fits", "file3.fits"]
        result = load_fits(files)

        assert result.shape == (3, 2, 2)
        assert np.array_equal(result[0], mock_image1)
        assert np.array_equal(result[1], mock_image2)
        assert np.array_equal(result[2], mock_image3)

    @patch("pleiades.utils.load.read_fits")
    def test_load_fits_with_dtype(self, mock_read_fits):
        """Test loading FITS files with specified dtype."""
        mock_image = np.array([[1.5, 2.5], [3.5, 4.5]])
        mock_read_fits.return_value = mock_image

        files = ["file1.fits"]
        result = load_fits(files, dtype=np.float64)

        assert result.dtype == np.float64
        assert result.shape == (1, 2, 2)

    @patch("pleiades.utils.load.read_fits")
    def test_load_fits_default_dtype(self, mock_read_fits):
        """Test that default dtype is uint16."""
        mock_image = np.array([[1, 2], [3, 4]])
        mock_read_fits.return_value = mock_image

        files = ["file1.fits"]
        result = load_fits(files)

        assert result.dtype == np.uint16

    def test_load_fits_real_file(self, data_fixture):
        """Test loading a real FITS file."""
        _, fits_file = data_fixture

        result = load_fits([str(fits_file)])

        assert result.shape == (1, 3, 3)
        assert np.array_equal(result[0], np.ones((3, 3)))


class TestIntegrationScenarios:
    """Test integration scenarios with actual file operations."""

    def test_load_workflow_with_tiff(self, data_fixture):
        """Test complete workflow with TIFF files."""
        tiff_file, _ = data_fixture

        # Test through main load function
        result = load([str(tiff_file)], ".tiff")

        assert result.shape == (1, 3, 3)
        assert np.array_equal(result[0], np.ones((3, 3)))

    def test_load_workflow_with_fits(self, data_fixture):
        """Test complete workflow with FITS files."""
        _, fits_file = data_fixture

        # Test through main load function
        result = load([str(fits_file)], ".fits")

        assert result.shape == (1, 3, 3)
        assert np.array_equal(result[0], np.ones((3, 3)))

    @patch("pleiades.utils.load.read_tiff")
    def test_load_tiff_memory_error(self, mock_read_tiff):
        """Test handling of memory error during loading."""
        mock_read_tiff.side_effect = MemoryError("Out of memory")

        files = ["file1.tiff"]

        with pytest.raises(MemoryError, match="Out of memory"):
            load_tiff(files)

    @patch("pleiades.utils.load.read_fits")
    def test_load_fits_io_error(self, mock_read_fits):
        """Test handling of IO error during loading."""
        mock_read_fits.side_effect = IOError("Cannot read file")

        files = ["file1.fits"]

        with pytest.raises(IOError, match="Cannot read file"):
            load_fits(files)

    @patch("pleiades.utils.load.read_tiff")
    def test_load_large_stack(self, mock_read_tiff):
        """Test loading a large stack of images."""
        mock_image = np.ones((100, 100))
        mock_read_tiff.return_value = mock_image

        # Create list of 100 files
        files = [f"file{i}.tiff" for i in range(100)]
        result = load_tiff(files)

        assert result.shape == (100, 100, 100)
        assert mock_read_tiff.call_count == 101  # First call for shape, then 100 for loading


# Keep the original tests for backward compatibility
def test_load_tiff(data_fixture):
    """Original test: loading tiff files with tifffile directly."""
    generic_tiff, generic_fits = list(map(str, data_fixture))

    # Load the tiff files
    loaded_generic_tiff = tifffile.imread(str(generic_tiff))

    # Check the loaded data
    assert np.array_equal(loaded_generic_tiff, np.ones((3, 3)))


def test_load_fits(data_fixture):
    """Original test: loading fits files with astropy directly."""
    generic_tiff, generic_fits = data_fixture

    # Load the fits files
    loaded_generic_fits = fits.getdata(str(generic_fits))

    # Check the loaded data
    assert np.array_equal(loaded_generic_fits, np.ones((3, 3)))


if __name__ == "__main__":
    pytest.main(["-v", __file__])
