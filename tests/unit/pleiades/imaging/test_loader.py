"""Unit tests for pleiades.imaging.loader."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import tifffile

from pleiades.imaging.loader import HyperspectralLoader
from pleiades.imaging.models import HyperspectralData, PixelSpectrum


@pytest.fixture
def synthetic_tiff():
    """Create synthetic multi-page TIFF for testing."""
    # Create 4×4 image with 10 energy bins
    n_energy, height, width = 10, 4, 4
    data = np.random.uniform(0.5, 1.0, (n_energy, height, width)).astype(np.float32)

    # Save to temp file
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".tif", delete=False) as f:
        tiff_path = Path(f.name)

    tifffile.imwrite(str(tiff_path), data)

    yield tiff_path, data

    # Cleanup
    tiff_path.unlink()


@pytest.fixture
def test_energy():
    """Create test energy array."""
    return np.linspace(1.0, 10.0, 10)


class TestHyperspectralLoader:
    """Test HyperspectralLoader class."""

    def test_loader_init_valid_file(self, synthetic_tiff):
        """Test loader initialization with valid file."""
        tiff_path, _ = synthetic_tiff
        loader = HyperspectralLoader(tiff_path)
        assert loader.filepath == tiff_path

    def test_loader_init_missing_file(self):
        """Test loader initialization with missing file."""
        with pytest.raises(FileNotFoundError):
            HyperspectralLoader(Path("/nonexistent/file.tif"))

    def test_loader_load_without_energy(self, synthetic_tiff):
        """Test loading TIFF without energy axis."""
        tiff_path, expected_data = synthetic_tiff
        loader = HyperspectralLoader(tiff_path)

        hyperspectral = loader.load()

        assert isinstance(hyperspectral, HyperspectralData)
        assert hyperspectral.shape == (10, 4, 4)
        assert len(hyperspectral.energy) == 10
        np.testing.assert_array_almost_equal(hyperspectral.data, expected_data, decimal=4)

    def test_loader_load_with_energy(self, synthetic_tiff, test_energy):
        """Test loading TIFF with provided energy axis."""
        tiff_path, _ = synthetic_tiff
        loader = HyperspectralLoader(tiff_path, energy=test_energy)

        hyperspectral = loader.load()

        assert len(hyperspectral.energy) == 10
        np.testing.assert_array_equal(hyperspectral.energy, test_energy)

    def test_loader_energy_length_mismatch(self, synthetic_tiff):
        """Test loader rejects energy length mismatch."""
        tiff_path, _ = synthetic_tiff
        wrong_energy = np.linspace(1.0, 10.0, 5)  # Wrong length

        loader = HyperspectralLoader(tiff_path, energy=wrong_energy)

        with pytest.raises(ValueError, match="Energy length .* != n_frames"):
            loader.load()

    def test_loader_iter_pixels_all(self, synthetic_tiff, test_energy):
        """Test iterating over all pixels."""
        tiff_path, expected_data = synthetic_tiff
        loader = HyperspectralLoader(tiff_path, energy=test_energy)
        loader.load()

        pixels = list(loader.iter_pixels())

        assert len(pixels) == 16  # 4×4 pixels
        assert all(isinstance(p, PixelSpectrum) for p in pixels)

        # Check first pixel
        first_pixel = pixels[0]
        assert first_pixel.row == 0
        assert first_pixel.col == 0
        assert len(first_pixel.energy) == 10
        np.testing.assert_array_equal(first_pixel.energy, test_energy)

    def test_loader_iter_pixels_roi(self, synthetic_tiff, test_energy):
        """Test iterating over ROI."""
        tiff_path, _ = synthetic_tiff
        loader = HyperspectralLoader(tiff_path, energy=test_energy)
        loader.load()

        # ROI: x=[1,3), y=[1,3) → 2×2 pixels
        roi = (1, 1, 3, 3)
        pixels = list(loader.iter_pixels(roi=roi))

        assert len(pixels) == 4  # 2×2 pixels
        assert all(1 <= p.row < 3 and 1 <= p.col < 3 for p in pixels)

    def test_loader_iter_pixels_invalid_roi(self, synthetic_tiff, test_energy):
        """Test iterating with invalid ROI."""
        tiff_path, _ = synthetic_tiff
        loader = HyperspectralLoader(tiff_path, energy=test_energy)
        loader.load()

        # Invalid ROI: out of bounds
        invalid_roi = (0, 0, 10, 10)  # Exceeds 4×4 image

        with pytest.raises(ValueError, match="Invalid ROI"):
            list(loader.iter_pixels(roi=invalid_roi))

    def test_loader_get_pixel_valid(self, synthetic_tiff, test_energy):
        """Test getting specific pixel."""
        tiff_path, expected_data = synthetic_tiff
        loader = HyperspectralLoader(tiff_path, energy=test_energy)
        loader.load()

        pixel = loader.get_pixel(row=2, col=3)

        assert isinstance(pixel, PixelSpectrum)
        assert pixel.row == 2
        assert pixel.col == 3
        assert len(pixel.transmission) == 10
        np.testing.assert_array_almost_equal(pixel.transmission, expected_data[:, 2, 3], decimal=4)

    def test_loader_get_pixel_out_of_bounds(self, synthetic_tiff, test_energy):
        """Test getting pixel out of bounds."""
        tiff_path, _ = synthetic_tiff
        loader = HyperspectralLoader(tiff_path, energy=test_energy)
        loader.load()

        with pytest.raises(ValueError, match="out of bounds"):
            loader.get_pixel(row=10, col=10)

    def test_loader_iter_before_load(self, synthetic_tiff):
        """Test iterating before loading raises error."""
        tiff_path, _ = synthetic_tiff
        loader = HyperspectralLoader(tiff_path)

        with pytest.raises(ValueError, match="Must call load"):
            list(loader.iter_pixels())

    def test_loader_uncertainty_estimation(self, synthetic_tiff, test_energy):
        """Test uncertainty estimation."""
        tiff_path, _ = synthetic_tiff
        loader = HyperspectralLoader(tiff_path, energy=test_energy)
        hyperspectral = loader.load()

        # Uncertainty should be generated
        assert hyperspectral.uncertainty is not None
        assert hyperspectral.uncertainty.shape == hyperspectral.data.shape

        # Check pixel has uncertainty
        pixel = loader.get_pixel(0, 0)
        assert len(pixel.uncertainty) == 10
        assert np.all(pixel.uncertainty > 0)


class TestLoaderIntegration:
    """Integration tests with real test data."""

    def test_load_lanl_ornl_example(self):
        """Test loading actual LANL-ORNL_example.tif if available."""
        test_file = Path("/Users/8cz/github.com/lanl/PLEIADES/tests/data/pleiades_data/LANL-ORNL_example.tif")

        if not test_file.exists():
            pytest.skip("LANL-ORNL_example.tif not available")

        loader = HyperspectralLoader(test_file)
        hyperspectral = loader.load()

        # Verify expected shape
        assert hyperspectral.shape == (500, 256, 256)
        assert hyperspectral.n_pixels == 256 * 256

        # Test pixel extraction
        center_pixel = loader.get_pixel(row=128, col=128)
        assert center_pixel.row == 128
        assert center_pixel.col == 128
        assert len(center_pixel.transmission) == 500

        # Verify transmission range
        assert 0.0 <= center_pixel.transmission.min() <= 1.0
        assert 0.0 <= center_pixel.transmission.max() <= 1.0
