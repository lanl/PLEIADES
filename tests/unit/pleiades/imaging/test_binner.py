"""Unit tests for pleiades.imaging.binner.SpatialBinner.

Tests cover:
  - bin_hyperspectral: correct output shape, values, uncertainty propagation
  - unbin_map: correct upscaling, NaN preservation, shape matching
  - unbin_results: full round-trip, source_hyperspectral restored, bin_size in metadata
  - analyze_imaging integration: bin_size=1 regression, bin_size=2 produces original shape
  - Error handling: invalid bin_size, invalid method, non-2D map
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pleiades.imaging.binner import SpatialBinner
from pleiades.imaging.models import HyperspectralData, Imaging2DResults, PixelFitResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hyperspectral(data: np.ndarray, uncertainty: np.ndarray | None = None) -> HyperspectralData:
    n_e = data.shape[0]
    energy = np.linspace(1.0, 100.0, n_e)
    return HyperspectralData(
        data=data,
        energy=energy,
        uncertainty=uncertainty,
        source_file=Path("/tmp/test.tif"),
    )


def _make_results(
    h: int,
    w: int,
    n_isotopes: int = 1,
    hyperspectral: HyperspectralData | None = None,
) -> Imaging2DResults:
    """Create a minimal Imaging2DResults for a given spatial size."""
    if hyperspectral is None:
        hyperspectral = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, h, w)))
    abundance = np.random.uniform(0.0, 1.0, (n_isotopes, h, w))
    chi2 = np.random.uniform(1.0, 5.0, (h, w))
    success = np.ones((h, w), dtype=bool)
    return Imaging2DResults(
        abundance_maps=abundance,
        isotope_names=[f"iso-{i}" for i in range(n_isotopes)],
        chi_squared_map=chi2,
        success_mask=success,
        source_hyperspectral=hyperspectral,
        pixel_results=[],
        metadata={},
    )


# ---------------------------------------------------------------------------
# TestSpatialBinnerInit
# ---------------------------------------------------------------------------


class TestSpatialBinnerInit:
    def test_valid_bin_size(self):
        b = SpatialBinner(bin_size=2)
        assert b.bin_size == 2
        assert b.method == "mean"

    def test_bin_size_1_valid(self):
        b = SpatialBinner(bin_size=1)
        assert b.bin_size == 1

    def test_median_method(self):
        b = SpatialBinner(bin_size=2, method="median")
        assert b.method == "median"

    def test_invalid_bin_size_zero(self):
        with pytest.raises(ValueError, match="bin_size"):
            SpatialBinner(bin_size=0)

    def test_invalid_bin_size_negative(self):
        with pytest.raises(ValueError, match="bin_size"):
            SpatialBinner(bin_size=-1)

    def test_invalid_method(self):
        with pytest.raises(ValueError, match="method"):
            SpatialBinner(bin_size=2, method="sum")


# ---------------------------------------------------------------------------
# TestBinHyperspectral
# ---------------------------------------------------------------------------


class TestBinHyperspectral:
    def test_output_shape_bin2(self):
        data = np.random.uniform(0.5, 0.9, (20, 8, 8))
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)
        assert binned.shape == (20, 4, 4)

    def test_output_shape_bin4(self):
        data = np.random.uniform(0.5, 0.9, (10, 16, 16))
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=4)
        binned = binner.bin_hyperspectral(hs)
        assert binned.shape == (10, 4, 4)

    def test_bin1_is_identity(self):
        data = np.random.uniform(0.5, 0.9, (10, 8, 8))
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=1)
        binned = binner.bin_hyperspectral(hs)
        assert binned is hs  # Identity returns the same object

    def test_binned_values_are_mean_of_block(self):
        """A uniform 4×4 block of value v should bin to v."""
        data = np.full((5, 4, 4), 0.7)
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)
        np.testing.assert_allclose(binned.data, 0.7)

    def test_binned_values_mean_of_known_block(self):
        """Manual 2×2 block mean check."""
        # (5, 4, 4) array where top-left 2×2 block has a known mean
        data = np.zeros((1, 4, 4))
        data[0, :2, :2] = np.array([[1.0, 3.0], [5.0, 7.0]])  # mean = 4.0
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)
        assert binned.data[0, 0, 0] == pytest.approx(4.0)

    def test_energy_axis_unchanged(self):
        data = np.random.uniform(0.5, 0.9, (15, 8, 8))
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)
        np.testing.assert_array_equal(binned.energy, hs.energy)

    def test_uncertainty_propagation(self):
        """σ_bin = σ_pixel / bin_size for uncorrelated Gaussian noise."""
        sigma_pixel = 0.04
        data = np.full((5, 8, 8), 0.7)
        uncertainty = np.full((5, 8, 8), sigma_pixel)
        hs = _make_hyperspectral(data, uncertainty=uncertainty)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)

        expected_sigma = sigma_pixel / 2.0  # σ_bin = σ_pixel / N
        np.testing.assert_allclose(binned.uncertainty, expected_sigma, rtol=1e-6)

    def test_uncertainty_propagation_bin4(self):
        sigma_pixel = 0.08
        data = np.full((5, 8, 8), 0.7)
        uncertainty = np.full((5, 8, 8), sigma_pixel)
        hs = _make_hyperspectral(data, uncertainty=uncertainty)
        binner = SpatialBinner(bin_size=4)
        binned = binner.bin_hyperspectral(hs)

        expected_sigma = sigma_pixel / 4.0
        np.testing.assert_allclose(binned.uncertainty, expected_sigma, rtol=1e-6)

    def test_uncertainty_none_stays_none(self):
        data = np.random.uniform(0.5, 0.9, (5, 8, 8))
        hs = _make_hyperspectral(data, uncertainty=None)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)
        assert binned.uncertainty is None

    def test_bin_size_in_metadata(self):
        data = np.random.uniform(0.5, 0.9, (5, 8, 8))
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)
        assert binned.metadata["bin_size"] == 2

    def test_source_file_preserved(self):
        data = np.random.uniform(0.5, 0.9, (5, 8, 8))
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)
        assert binned.source_file == hs.source_file

    def test_non_divisible_dimensions_cropped(self):
        """9×9 image with bin_size=2 should produce (4, 4), not (5, 5)."""
        data = np.ones((5, 9, 9))
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)
        assert binned.shape == (5, 4, 4)
        # All ones → binned values should be exactly 1.0 (no zero-padding bias)
        np.testing.assert_allclose(binned.data, 1.0)

    def test_uncertainty_propagation_heterogeneous(self):
        """Verify sqrt(sum(sigma_i^2))/N for non-uniform uncertainties."""
        data = np.full((1, 2, 2), 0.5)
        uncertainty = np.array([[[0.1, 0.2], [0.3, 0.4]]]).astype(np.float64)
        hs = _make_hyperspectral(data, uncertainty=uncertainty)
        binner = SpatialBinner(bin_size=2)
        binned = binner.bin_hyperspectral(hs)
        expected = np.sqrt(0.1**2 + 0.2**2 + 0.3**2 + 0.4**2) / 4
        np.testing.assert_allclose(binned.uncertainty[0, 0, 0], expected, rtol=1e-10)

    def test_bin_size_larger_than_image_raises(self):
        """bin_size > min(height, width) should raise ValueError."""
        data = np.ones((5, 3, 3))
        hs = _make_hyperspectral(data)
        binner = SpatialBinner(bin_size=4)
        with pytest.raises(ValueError, match="zero-sized"):
            binner.bin_hyperspectral(hs)

    def test_median_method_different_from_mean(self):
        data = np.random.uniform(0.2, 0.9, (5, 8, 8))
        hs = _make_hyperspectral(data)
        b_mean = SpatialBinner(bin_size=2, method="mean")
        b_med = SpatialBinner(bin_size=2, method="median")
        m = b_mean.bin_hyperspectral(hs)
        med = b_med.bin_hyperspectral(hs)
        # For non-symmetric blocks, mean ≠ median in general
        assert not np.allclose(m.data, med.data)


# ---------------------------------------------------------------------------
# TestUnbinMap
# ---------------------------------------------------------------------------


class TestUnbinMap:
    def test_output_shape_bin2(self):
        binned = np.ones((4, 4))
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_map(binned, (8, 8))
        assert unbinned.shape == (8, 8)

    def test_output_shape_bin4(self):
        binned = np.ones((3, 3))
        binner = SpatialBinner(bin_size=4)
        unbinned = binner.unbin_map(binned, (12, 12))
        assert unbinned.shape == (12, 12)

    def test_values_are_repeated(self):
        """Each binned value must appear in a bin_size × bin_size tile."""
        binned = np.array([[1.0, 2.0], [3.0, 4.0]])
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_map(binned, (4, 4))
        expected = np.array(
            [
                [1.0, 1.0, 2.0, 2.0],
                [1.0, 1.0, 2.0, 2.0],
                [3.0, 3.0, 4.0, 4.0],
                [3.0, 3.0, 4.0, 4.0],
            ]
        )
        np.testing.assert_array_equal(unbinned, expected)

    def test_nan_values_preserved(self):
        binned = np.array([[1.0, np.nan], [np.nan, 2.0]])
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_map(binned, (4, 4))
        # NaN tiles should remain NaN
        assert np.all(np.isnan(unbinned[:2, 2:4]))
        assert np.all(np.isnan(unbinned[2:4, :2]))

    def test_bin1_identity(self):
        binned = np.array([[1.0, 2.0], [3.0, 4.0]])
        binner = SpatialBinner(bin_size=1)
        unbinned = binner.unbin_map(binned, (2, 2))
        np.testing.assert_array_equal(unbinned, binned)

    def test_non_2d_raises(self):
        binner = SpatialBinner(bin_size=2)
        with pytest.raises(ValueError, match="2-D"):
            binner.unbin_map(np.ones((2, 2, 2)), (4, 4))

    def test_crop_to_original_shape(self):
        """Upscaling 3-bin map × 2 gives 6, but original was 5 — must crop."""
        binned = np.ones((3, 3))
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_map(binned, (5, 5))
        assert unbinned.shape == (5, 5)


# ---------------------------------------------------------------------------
# TestUnbinResults
# ---------------------------------------------------------------------------


class TestUnbinResults:
    def test_output_shape_abundance_maps(self):
        orig_h, orig_w = 8, 8
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, orig_h, orig_w)))
        bin_h, bin_w = 4, 4
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, bin_h, bin_w)))
        results = _make_results(bin_h, bin_w, n_isotopes=2, hyperspectral=bin_hs)
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        assert unbinned.abundance_maps.shape == (2, orig_h, orig_w)

    def test_output_shape_chi2_map(self):
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 8, 8)))
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 4, 4)))
        results = _make_results(4, 4, hyperspectral=bin_hs)
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        assert unbinned.chi_squared_map.shape == (8, 8)

    def test_output_shape_success_mask(self):
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 8, 8)))
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 4, 4)))
        results = _make_results(4, 4, hyperspectral=bin_hs)
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        assert unbinned.success_mask.shape == (8, 8)

    def test_source_hyperspectral_is_original(self):
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 8, 8)))
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 4, 4)))
        results = _make_results(4, 4, hyperspectral=bin_hs)
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        assert unbinned.source_hyperspectral is orig_hs

    def test_bin_size_in_metadata(self):
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 8, 8)))
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 4, 4)))
        results = _make_results(4, 4, hyperspectral=bin_hs)
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        assert unbinned.metadata["bin_size"] == 2

    def test_fitted_energy_maps_unbinned(self):
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 8, 8)))
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 4, 4)))
        results = _make_results(4, 4, hyperspectral=bin_hs)
        # Add fitted_energy_maps
        results = Imaging2DResults(
            abundance_maps=results.abundance_maps,
            isotope_names=results.isotope_names,
            fitted_energy_maps=np.random.uniform(1.0, 100.0, (2, 4, 4)),
            chi_squared_map=results.chi_squared_map,
            success_mask=results.success_mask,
            source_hyperspectral=bin_hs,
            pixel_results=[],
            metadata={},
        )
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        assert unbinned.fitted_energy_maps is not None
        assert unbinned.fitted_energy_maps.shape == (2, 8, 8)

    def test_no_fitted_energy_maps_stays_none(self):
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 8, 8)))
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 4, 4)))
        results = _make_results(4, 4, hyperspectral=bin_hs)
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        assert unbinned.fitted_energy_maps is None

    def test_isotope_names_preserved(self):
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 8, 8)))
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 4, 4)))
        results = _make_results(4, 4, n_isotopes=2, hyperspectral=bin_hs)
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        assert unbinned.isotope_names == results.isotope_names

    def test_pixel_results_preserved(self):
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 8, 8)))
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 4, 4)))
        pr = [PixelFitResult(row=0, col=0, fit_results=None, success=False, error_message="x")]
        results = _make_results(4, 4, hyperspectral=bin_hs)
        results = Imaging2DResults(
            abundance_maps=results.abundance_maps,
            isotope_names=results.isotope_names,
            chi_squared_map=results.chi_squared_map,
            success_mask=results.success_mask,
            source_hyperspectral=bin_hs,
            pixel_results=pr,
            metadata={},
        )
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        assert unbinned.pixel_results == pr

    def test_success_mask_nan_padded_edges_are_false(self):
        """NaN-padded edge pixels in success_mask must be False, not True."""
        # Original 5×5, binned 2×2 → 2×2 binned result, unbin to 5×5
        orig_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 5, 5)))
        bin_hs = _make_hyperspectral(np.random.uniform(0.5, 0.9, (10, 2, 2)))
        results = Imaging2DResults(
            abundance_maps=np.full((1, 2, 2), 0.5),
            isotope_names=["iso-0"],
            chi_squared_map=np.ones((2, 2)),
            success_mask=np.ones((2, 2), dtype=bool),
            source_hyperspectral=bin_hs,
            pixel_results=[],
            metadata={},
        )
        binner = SpatialBinner(bin_size=2)
        unbinned = binner.unbin_results(results, orig_hs)
        # The 5th row and column are NaN-padded; success_mask should be False there
        assert not unbinned.success_mask[4, 0]
        assert not unbinned.success_mask[0, 4]
        assert not unbinned.success_mask[4, 4]
        # Fitted region should still be True
        assert unbinned.success_mask[0, 0]
        assert unbinned.success_mask[3, 3]


# ---------------------------------------------------------------------------
# TestAnalyzeImagingBinSize
# ---------------------------------------------------------------------------


class TestAnalyzeImagingBinSize:
    """Verify bin_size integration in analyze_imaging."""

    @patch("pleiades.imaging.api.SpatialBinner")
    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_bin_size_1_does_not_create_binner(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        MockBinner,
        tmp_path,
    ):
        """bin_size=1 should not instantiate SpatialBinner."""
        from pleiades.imaging.api import analyze_imaging
        from pleiades.imaging.config import ImagingConfig

        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
            natural_abundances=True,
            min_energy_eV=1.0,
            max_energy_eV=100.0,
        )
        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        data = np.random.uniform(0.5, 0.9, (10, 4, 6))
        energy = np.linspace(1.0, 100.0, 10)
        hs = HyperspectralData(data=data, energy=energy, source_file=tmp_path / "d.tif")

        loader_inst = MockLoader.return_value
        loader_inst.load.return_value = hs
        loader_inst.iter_pixels.return_value = iter([])

        orch_inst = MockOrchestrator.return_value
        orch_inst.fit_pixels.return_value = []

        mock_results = MagicMock(spec=Imaging2DResults)
        agg_inst = MockAggregator.return_value
        agg_inst.aggregate.return_value = mock_results

        src = tmp_path / "data.tif"
        src.touch()
        analyze_imaging(source=src, imaging_config=config, sammy_executable=sammy_exe, bin_size=1)

        MockBinner.assert_not_called()

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_bin_size_2_produces_original_shape(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        tmp_path,
    ):
        """With bin_size=2 on an 8×8 image, the result maps must be 8×8."""
        from pleiades.imaging.api import analyze_imaging
        from pleiades.imaging.config import ImagingConfig

        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
            natural_abundances=True,
            min_energy_eV=1.0,
            max_energy_eV=100.0,
        )
        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        # Original 8×8 data
        data = np.random.uniform(0.5, 0.9, (10, 8, 8))
        energy = np.linspace(1.0, 100.0, 10)
        orig_hs = HyperspectralData(data=data, energy=energy, source_file=tmp_path / "d.tif")

        loader_inst = MockLoader.return_value
        loader_inst.load.return_value = orig_hs
        loader_inst.iter_pixels.return_value = iter([])

        orch_inst = MockOrchestrator.return_value
        # fit_pixels returns empty list; aggregator will build 4×4 maps for binned data
        orch_inst.fit_pixels.return_value = []

        # Aggregator will be called with binned hyperspectral (4×4)
        # We configure it to return a 4×4 result
        bin_hs = HyperspectralData(
            data=np.random.uniform(0.5, 0.9, (10, 4, 4)),
            energy=energy,
            source_file=tmp_path / "d.tif",
        )
        binned_result = Imaging2DResults(
            abundance_maps=np.full((1, 4, 4), 0.5),
            isotope_names=["Ta-181"],
            chi_squared_map=np.ones((4, 4)),
            success_mask=np.ones((4, 4), dtype=bool),
            source_hyperspectral=bin_hs,
            pixel_results=[],
            metadata={},
        )
        agg_inst = MockAggregator.return_value
        agg_inst.aggregate.return_value = binned_result

        src = tmp_path / "data.tif"
        src.touch()
        result = analyze_imaging(source=src, imaging_config=config, sammy_executable=sammy_exe, bin_size=2)

        # After unbinning, maps should be at original 8×8 resolution
        assert result.abundance_maps.shape == (1, 8, 8)
        assert result.chi_squared_map.shape == (8, 8)
        assert result.success_mask.shape == (8, 8)
        assert result.source_hyperspectral is orig_hs

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_bin_size_zero_raises(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        tmp_path,
    ):
        """bin_size=0 must raise ValueError before any IO."""
        from pleiades.imaging.api import analyze_imaging
        from pleiades.imaging.config import ImagingConfig

        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
            natural_abundances=True,
            min_energy_eV=1.0,
            max_energy_eV=100.0,
        )
        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()
        src = tmp_path / "data.tif"
        src.touch()

        with pytest.raises(ValueError, match="bin_size"):
            analyze_imaging(source=src, imaging_config=config, sammy_executable=sammy_exe, bin_size=0)
