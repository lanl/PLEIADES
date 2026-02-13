"""Unit tests for pleiades.imaging.models."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from pleiades.imaging.models import HyperspectralData, PixelSpectrum


class TestPixelSpectrum:
    """Test PixelSpectrum model."""

    def test_create_valid_pixel_spectrum(self):
        """Test creating valid PixelSpectrum."""
        energy = np.linspace(1, 100, 500)
        transmission = np.random.uniform(0.5, 1.0, 500)
        uncertainty = transmission * 0.01

        pixel = PixelSpectrum(row=10, col=20, energy=energy, transmission=transmission, uncertainty=uncertainty)

        assert pixel.row == 10
        assert pixel.col == 20
        assert len(pixel.energy) == 500
        assert len(pixel.transmission) == 500
        assert len(pixel.uncertainty) == 500

    def test_pixel_spectrum_array_length_mismatch(self):
        """Test PixelSpectrum rejects array length mismatch."""
        energy = np.linspace(1, 100, 500)
        transmission = np.random.uniform(0.5, 1.0, 400)  # Wrong length
        uncertainty = transmission * 0.01

        with pytest.raises(ValueError, match="Array length mismatch"):
            PixelSpectrum(row=0, col=0, energy=energy, transmission=transmission, uncertainty=uncertainty)

    def test_pixel_spectrum_2d_array_rejected(self):
        """Test PixelSpectrum rejects 2D arrays."""
        energy = np.random.rand(500, 2)  # 2D array
        transmission = np.random.rand(500)
        uncertainty = transmission * 0.01

        with pytest.raises(ValueError, match="must be 1D array"):
            PixelSpectrum(row=0, col=0, energy=energy, transmission=transmission, uncertainty=uncertainty)

    def test_pixel_spectrum_negative_coordinates(self):
        """Test PixelSpectrum rejects negative coordinates."""
        energy = np.linspace(1, 100, 500)
        transmission = np.random.uniform(0.5, 1.0, 500)
        uncertainty = transmission * 0.01

        with pytest.raises(ValueError):
            PixelSpectrum(row=-1, col=0, energy=energy, transmission=transmission, uncertainty=uncertainty)

    def test_pixel_spectrum_to_csv(self):
        """Test PixelSpectrum.to_csv() export."""
        energy = np.linspace(1, 100, 10)
        transmission = np.random.uniform(0.5, 1.0, 10)
        uncertainty = transmission * 0.01

        pixel = PixelSpectrum(row=5, col=10, energy=energy, transmission=transmission, uncertainty=uncertainty)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            csv_path = Path(f.name)

        try:
            pixel.to_csv(csv_path)
            assert csv_path.exists()

            # Read and verify
            data = np.loadtxt(csv_path, skiprows=1)
            assert data.shape == (10, 3)  # 10 rows, 3 columns (energy, transmission, uncertainty)
            np.testing.assert_array_almost_equal(data[:, 0], energy)
        finally:
            csv_path.unlink()


class TestHyperspectralData:
    """Test HyperspectralData model."""

    def test_create_valid_hyperspectral_data(self):
        """Test creating valid HyperspectralData."""
        data = np.random.uniform(0.5, 1.0, (500, 256, 256))
        energy = np.linspace(1, 100, 500)
        source_file = Path("/tmp/test.tif")

        hyperspectral = HyperspectralData(data=data, energy=energy, source_file=source_file)

        assert hyperspectral.shape == (500, 256, 256)
        assert hyperspectral.n_pixels == 256 * 256
        assert len(hyperspectral.energy) == 500

    def test_hyperspectral_data_shape_validation(self):
        """Test HyperspectralData validates data shape."""
        data_2d = np.random.rand(500, 256)  # 2D instead of 3D
        energy = np.linspace(1, 100, 500)
        source_file = Path("/tmp/test.tif")

        with pytest.raises(ValueError, match="must be 3D array"):
            HyperspectralData(data=data_2d, energy=energy, source_file=source_file)

    def test_hyperspectral_energy_length_mismatch(self):
        """Test HyperspectralData rejects energy length mismatch."""
        data = np.random.uniform(0.5, 1.0, (500, 256, 256))
        energy = np.linspace(1, 100, 400)  # Wrong length
        source_file = Path("/tmp/test.tif")

        with pytest.raises(ValueError, match="Energy length .* != n_energy"):
            HyperspectralData(data=data, energy=energy, source_file=source_file)

    def test_hyperspectral_uncertainty_shape_mismatch(self):
        """Test HyperspectralData rejects uncertainty shape mismatch."""
        data = np.random.uniform(0.5, 1.0, (500, 256, 256))
        energy = np.linspace(1, 100, 500)
        uncertainty = np.random.rand(500, 128, 128)  # Wrong shape
        source_file = Path("/tmp/test.tif")

        with pytest.raises(ValueError, match="Uncertainty shape .* != data shape"):
            HyperspectralData(data=data, energy=energy, uncertainty=uncertainty, source_file=source_file)

    def test_hyperspectral_with_valid_uncertainty(self):
        """Test HyperspectralData with valid uncertainty."""
        data = np.random.uniform(0.5, 1.0, (500, 256, 256))
        energy = np.linspace(1, 100, 500)
        uncertainty = data * 0.01
        source_file = Path("/tmp/test.tif")

        hyperspectral = HyperspectralData(data=data, energy=energy, uncertainty=uncertainty, source_file=source_file)

        assert hyperspectral.uncertainty is not None
        assert hyperspectral.uncertainty.shape == hyperspectral.data.shape
