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
        assert loader.source == tiff_path

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


class TestLoaderFromDirectory:
    """Test loading from directory with multiple TIFF files."""

    def test_from_directory_valid(self, tmpdir):
        """Test loading multiple TIFF files from directory."""
        # Create temporary directory with multiple TIFFs
        test_dir = Path(tmpdir) / "run_test"
        test_dir.mkdir()

        # Create 10 TIFF files (4×4 each)
        n_files = 10
        height, width = 4, 4
        for i in range(n_files):
            data = np.random.uniform(0.5, 1.0, (height, width)).astype(np.float32)
            tifffile.imwrite(str(test_dir / f"frame_{i:03d}.tif"), data)

        # Load from directory
        loader = HyperspectralLoader.from_directory(test_dir, pattern="*.tif")
        hyperspectral = loader.load()

        # Verify shape
        assert hyperspectral.shape == (n_files, height, width)
        assert len(hyperspectral.energy) == n_files

    def test_from_directory_sorted(self, tmpdir):
        """Test that files are loaded in sorted order."""
        test_dir = Path(tmpdir) / "run_test"
        test_dir.mkdir()

        # Create files with specific values (out of order filenames)
        files_data = [
            ("frame_002.tif", np.full((4, 4), 2.0, dtype=np.float32)),
            ("frame_001.tif", np.full((4, 4), 1.0, dtype=np.float32)),
            ("frame_003.tif", np.full((4, 4), 3.0, dtype=np.float32)),
        ]

        for filename, data in files_data:
            tifffile.imwrite(str(test_dir / filename), data)

        # Load from directory
        loader = HyperspectralLoader.from_directory(test_dir)
        hyperspectral = loader.load()

        # Verify sorted order (001, 002, 003)
        assert hyperspectral.data[0, 0, 0] == pytest.approx(1.0)
        assert hyperspectral.data[1, 0, 0] == pytest.approx(2.0)
        assert hyperspectral.data[2, 0, 0] == pytest.approx(3.0)

    def test_from_directory_no_files(self, tmpdir):
        """Test error when no files match pattern."""
        test_dir = Path(tmpdir) / "empty_dir"
        test_dir.mkdir()

        with pytest.raises(ValueError, match="No files matching pattern"):
            HyperspectralLoader.from_directory(test_dir, pattern="*.tif")

    def test_from_directory_missing(self):
        """Test error when directory doesn't exist."""
        with pytest.raises(FileNotFoundError):
            HyperspectralLoader.from_directory("/nonexistent/directory")


class TestLoaderFromNexus:
    """Test loading from NeXus/HDF5 files."""

    def test_from_nexus_valid(self, tmpdir):
        """Test loading histogram from NeXus file."""
        # Create synthetic NeXus file
        nexus_file = Path(tmpdir) / "test.nxs.h5"
        n_energy, height, width = 50, 8, 8
        data = np.random.uniform(0.5, 1.0, (n_energy, height, width)).astype(np.float32)
        energy = np.linspace(1.0, 50.0, n_energy)

        import h5py

        with h5py.File(nexus_file, "w") as f:
            f.create_group("entry/data")
            f.create_dataset("entry/data/histogram", data=data)
            f.create_dataset("entry/data/energy", data=energy)

        # Load from NeXus
        loader = HyperspectralLoader.from_nexus(
            nexus_file, dataset_path="/entry/data/histogram", energy_path="/entry/data/energy"
        )
        hyperspectral = loader.load()

        # Verify shape and energy
        assert hyperspectral.shape == (n_energy, height, width)
        np.testing.assert_array_almost_equal(hyperspectral.energy, energy)

    def test_from_nexus_no_energy(self, tmpdir):
        """Test loading NeXus without energy axis."""
        # Create NeXus file without energy
        nexus_file = Path(tmpdir) / "test_no_energy.nxs.h5"
        data = np.random.uniform(0.5, 1.0, (10, 4, 4)).astype(np.float32)

        import h5py

        with h5py.File(nexus_file, "w") as f:
            f.create_group("entry/data")
            f.create_dataset("entry/data/histogram", data=data)

        # Load from NeXus
        loader = HyperspectralLoader.from_nexus(nexus_file)
        hyperspectral = loader.load()

        # Should use placeholder energy
        assert len(hyperspectral.energy) == 10

    def test_from_nexus_missing_dataset(self, tmpdir):
        """Test error when dataset path doesn't exist."""
        nexus_file = Path(tmpdir) / "test_invalid.nxs.h5"

        import h5py

        with h5py.File(nexus_file, "w") as f:
            f.create_group("entry")

        loader = HyperspectralLoader.from_nexus(nexus_file, dataset_path="/nonexistent/path")

        with pytest.raises(ValueError, match="Dataset path .* not found"):
            loader.load()


class TestLoaderIntegration:
    """Integration tests with real test data."""

    def test_load_lanl_ornl_example(self):
        """Test loading actual LANL-ORNL_example.tif if available."""
        # Resolve path relative to test file location (works on any machine/CI)
        test_file = Path(__file__).parent.parent.parent.parent.parent / "tests/data/pleiades_data/LANL-ORNL_example.tif"

        if not test_file.exists():
            pytest.skip("LANL-ORNL_example.tif not available")

        loader = HyperspectralLoader(test_file)
        hyperspectral = loader.load()

        # Verify expected shape
        assert hyperspectral.shape == (500, 256, 256)
        assert hyperspectral.n_pixels == 256 * 256
        assert hyperspectral.metadata["load_mode"] == "single_tiff"

        # Test pixel extraction
        center_pixel = loader.get_pixel(row=128, col=128)
        assert center_pixel.row == 128
        assert center_pixel.col == 128
        assert len(center_pixel.transmission) == 500

        # Verify transmission range
        assert 0.0 <= center_pixel.transmission.min() <= 1.0
        assert 0.0 <= center_pixel.transmission.max() <= 1.0
