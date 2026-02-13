"""Unit tests for pleiades.imaging.models."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from pleiades.imaging.models import HyperspectralData, Imaging2DResults, PixelFitResult, PixelSpectrum


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

    def test_pixel_spectrum_transmission_tolerance(self):
        """Test PixelSpectrum accepts slight overshoot/undershoot in transmission."""
        energy = np.linspace(1, 100, 10)
        uncertainty = np.full(10, 0.01)

        # Should accept slight overshoot (up to 1.05)
        transmission_overshoot = np.array([0.5, 0.8, 1.0, 1.02, 1.04, 0.9, 0.7, 0.85, 0.95, 1.03])
        pixel_overshoot = PixelSpectrum(
            row=0, col=0, energy=energy, transmission=transmission_overshoot, uncertainty=uncertainty
        )
        assert pixel_overshoot.row == 0

        # Should accept slight undershoot (down to -0.05)
        transmission_undershoot = np.array([0.5, 0.8, 1.0, -0.02, -0.04, 0.9, 0.7, 0.85, 0.95, 0.1])
        pixel_undershoot = PixelSpectrum(
            row=1, col=1, energy=energy, transmission=transmission_undershoot, uncertainty=uncertainty
        )
        assert pixel_undershoot.row == 1

    def test_pixel_spectrum_transmission_out_of_tolerance(self):
        """Test PixelSpectrum rejects transmission values outside tolerance."""
        energy = np.linspace(1, 100, 10)
        uncertainty = np.full(10, 0.01)

        # Should reject overshoot > 1.05
        transmission_too_high = np.array([0.5, 0.8, 1.0, 1.1, 0.9, 0.7, 0.85, 0.95, 1.0, 0.8])
        with pytest.raises(ValueError, match="transmission must be in \\[-0.05, 1.05\\]"):
            PixelSpectrum(row=0, col=0, energy=energy, transmission=transmission_too_high, uncertainty=uncertainty)

        # Should reject undershoot < -0.05
        transmission_too_low = np.array([0.5, 0.8, 1.0, -0.1, 0.9, 0.7, 0.85, 0.95, 1.0, 0.8])
        with pytest.raises(ValueError, match="transmission must be in \\[-0.05, 1.05\\]"):
            PixelSpectrum(row=0, col=0, energy=energy, transmission=transmission_too_low, uncertainty=uncertainty)


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


class TestPixelFitResult:
    """Test PixelFitResult model."""

    def test_create_pixel_fit_result_without_fit_results(self):
        """Test creating PixelFitResult with fit_results=None (runtime type resolution)."""
        # This test verifies that FitResults type annotation is resolvable at runtime
        # Previously failed with PydanticUserError due to TYPE_CHECKING-only import
        pixel_result = PixelFitResult(row=10, col=20, fit_results=None, success=False, error_message="Test failed")

        assert pixel_result.row == 10
        assert pixel_result.col == 20
        assert pixel_result.fit_results is None
        assert pixel_result.success is False
        assert pixel_result.error_message == "Test failed"
        assert pixel_result.chi_squared is None

    def test_create_pixel_fit_result_failed(self):
        """Test creating failed PixelFitResult (success=False with no fit_results)."""
        pixel_result = PixelFitResult(row=5, col=15, fit_results=None, success=False, chi_squared=None)

        assert pixel_result.row == 5
        assert pixel_result.col == 15
        assert pixel_result.success is False
        assert pixel_result.chi_squared is None
        assert pixel_result.get_abundances() == []

    def test_create_pixel_fit_result_validation(self):
        """Test PixelFitResult validates success/fit_results consistency."""
        # success=True requires fit_results
        with pytest.raises(ValueError, match="success=True, fit_results must be provided"):
            PixelFitResult(row=0, col=0, fit_results=None, success=True)

        # success=False requires fit_results=None
        # (We can't test with real FitResults without complex setup, so just verify the validation exists)


class TestImaging2DResults:
    """Test Imaging2DResults model."""

    def test_create_imaging_2d_results(self):
        """Test creating Imaging2DResults with PixelFitResult list (runtime type resolution)."""
        # Create source hyperspectral data
        source_data = HyperspectralData(
            data=np.random.uniform(0.5, 1.0, (10, 2, 2)),
            energy=np.linspace(1, 10, 10),
            source_file=Path("/tmp/test.tif"),
        )

        # Create pixel results (all failed for simplicity - testing runtime type resolution, not success)
        pixel_results = [
            PixelFitResult(row=0, col=0, fit_results=None, success=False, error_message="Test"),
            PixelFitResult(row=0, col=1, fit_results=None, success=False, error_message="Test"),
            PixelFitResult(row=1, col=0, fit_results=None, success=False, error_message="Test"),
        ]

        # Create imaging results
        imaging_results = Imaging2DResults(
            isotope_names=["Ta-181"],
            abundance_maps=np.random.uniform(0.9, 1.0, (1, 2, 2)),
            chi_squared_map=np.array([[np.nan, np.nan], [np.nan, np.nan]]),
            success_mask=np.array([[False, False], [False, False]]),
            pixel_results=pixel_results,
            source_hyperspectral=source_data,
        )

        assert imaging_results.isotope_names == ["Ta-181"]
        assert imaging_results.abundance_maps.shape == (1, 2, 2)
        assert len(imaging_results.pixel_results) == 3
        assert imaging_results.pixel_results[0].row == 0
        assert imaging_results.pixel_results[0].col == 0

    def test_imaging_2d_results_spatial_shape_consistency(self):
        """Test Imaging2DResults validates consistent spatial shapes."""
        # Create source with shape (10, 4, 4)
        source_data = HyperspectralData(
            data=np.random.uniform(0.5, 1.0, (10, 4, 4)),
            energy=np.linspace(1, 10, 10),
            source_file=Path("/tmp/test.tif"),
        )

        # Valid case: all maps have matching (4, 4) spatial shape
        valid_results = Imaging2DResults(
            isotope_names=["Ta-181"],
            abundance_maps=np.random.uniform(0.9, 1.0, (1, 4, 4)),
            chi_squared_map=np.ones((4, 4)),
            success_mask=np.ones((4, 4), dtype=bool),
            pixel_results=[],
            source_hyperspectral=source_data,
        )
        assert valid_results.abundance_maps.shape == (1, 4, 4)

    def test_imaging_2d_results_spatial_shape_mismatch_chi_squared(self):
        """Test Imaging2DResults rejects mismatched chi_squared_map shape."""
        source_data = HyperspectralData(
            data=np.random.uniform(0.5, 1.0, (10, 4, 4)),
            energy=np.linspace(1, 10, 10),
            source_file=Path("/tmp/test.tif"),
        )

        # chi_squared_map has wrong shape (3, 3) instead of (4, 4)
        with pytest.raises(ValueError, match="Spatial shape mismatch"):
            Imaging2DResults(
                isotope_names=["Ta-181"],
                abundance_maps=np.random.uniform(0.9, 1.0, (1, 4, 4)),
                chi_squared_map=np.ones((3, 3)),  # Wrong shape
                success_mask=np.ones((4, 4), dtype=bool),
                pixel_results=[],
                source_hyperspectral=source_data,
            )

    def test_imaging_2d_results_spatial_shape_mismatch_success_mask(self):
        """Test Imaging2DResults rejects mismatched success_mask shape."""
        source_data = HyperspectralData(
            data=np.random.uniform(0.5, 1.0, (10, 4, 4)),
            energy=np.linspace(1, 10, 10),
            source_file=Path("/tmp/test.tif"),
        )

        # success_mask has wrong shape (4, 5) instead of (4, 4)
        with pytest.raises(ValueError, match="Spatial shape mismatch"):
            Imaging2DResults(
                isotope_names=["Ta-181"],
                abundance_maps=np.random.uniform(0.9, 1.0, (1, 4, 4)),
                chi_squared_map=np.ones((4, 4)),
                success_mask=np.ones((4, 5), dtype=bool),  # Wrong shape
                pixel_results=[],
                source_hyperspectral=source_data,
            )

    def test_imaging_2d_results_spatial_shape_mismatch_abundance_maps(self):
        """Test Imaging2DResults rejects mismatched abundance_maps shape."""
        source_data = HyperspectralData(
            data=np.random.uniform(0.5, 1.0, (10, 4, 4)),
            energy=np.linspace(1, 10, 10),
            source_file=Path("/tmp/test.tif"),
        )

        # abundance_maps has wrong spatial shape (1, 3, 4) instead of (1, 4, 4)
        with pytest.raises(ValueError, match="Spatial shape mismatch"):
            Imaging2DResults(
                isotope_names=["Ta-181"],
                abundance_maps=np.random.uniform(0.9, 1.0, (1, 3, 4)),  # Wrong spatial shape
                chi_squared_map=np.ones((4, 4)),
                success_mask=np.ones((4, 4), dtype=bool),
                pixel_results=[],
                source_hyperspectral=source_data,
            )
