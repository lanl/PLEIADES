"""Unit tests for AbundanceMapGenerator.

These tests are written BEFORE implementation (TDD). They exercise the
AbundanceMapGenerator class which extracts individual isotope abundance maps
and quality maps from an Imaging2DResults object.

Tests use real PLEIADES model classes and construct Imaging2DResults directly
(not through the ResultsAggregator) for isolation and clarity.
"""

from pathlib import Path
from typing import List, Optional

import numpy as np
import pytest

from pleiades.imaging.generator import AbundanceMapGenerator
from pleiades.imaging.models import HyperspectralData, Imaging2DResults

# ---------------------------------------------------------------------------
# Helper utilities for building test fixtures
# ---------------------------------------------------------------------------


def _make_hyperspectral(height: int, width: int, n_energy: int = 10) -> HyperspectralData:
    """Build a minimal HyperspectralData for testing.

    Args:
        height: Image height in pixels.
        width: Image width in pixels.
        n_energy: Number of energy channels.

    Returns:
        HyperspectralData with random transmission data.
    """
    rng = np.random.default_rng(42)
    data = rng.uniform(0.3, 0.95, (n_energy, height, width)).astype(np.float32)
    energy = np.linspace(1.0, 100.0, n_energy)
    return HyperspectralData(
        data=data,
        energy=energy,
        source_file=Path("/tmp/fake_source.tif"),
    )


def _make_imaging_results(
    height: int = 4,
    width: int = 4,
    isotope_names: Optional[List[str]] = None,
    abundance_values: Optional[np.ndarray] = None,
    chi_squared_values: Optional[np.ndarray] = None,
    success_mask: Optional[np.ndarray] = None,
) -> Imaging2DResults:
    """Build an Imaging2DResults directly from arrays.

    This constructs the object without going through ResultsAggregator,
    giving full control over array contents for precise test assertions.

    Args:
        height: Image height in pixels.
        width: Image width in pixels.
        isotope_names: List of isotope name strings. Defaults to ["Ta-181", "W-182"].
        abundance_values: 3D array (n_isotopes, height, width). Generated randomly if None.
        chi_squared_values: 2D array (height, width). Generated randomly if None.
        success_mask: 2D bool array (height, width). Defaults to all True.

    Returns:
        Imaging2DResults instance.
    """
    if isotope_names is None:
        isotope_names = ["Ta-181", "W-182"]
    n_iso = len(isotope_names)

    rng = np.random.default_rng(99)

    if abundance_values is None:
        abundance_values = rng.uniform(0.1, 0.9, (n_iso, height, width)).astype(np.float64)

    if chi_squared_values is None:
        chi_squared_values = rng.uniform(0.5, 5.0, (height, width)).astype(np.float64)

    if success_mask is None:
        success_mask = np.ones((height, width), dtype=bool)

    source = _make_hyperspectral(height, width)

    return Imaging2DResults(
        abundance_maps=abundance_values,
        isotope_names=isotope_names,
        chi_squared_map=chi_squared_values,
        success_mask=success_mask,
        source_hyperspectral=source,
        pixel_results=[],
        metadata={},
    )


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def two_isotope_results() -> Imaging2DResults:
    """Standard 4x4 image with two isotopes, all pixels successful."""
    return _make_imaging_results(height=4, width=4, isotope_names=["Ta-181", "W-182"])


@pytest.fixture
def single_isotope_results() -> Imaging2DResults:
    """Standard 4x4 image with a single isotope, all pixels successful."""
    return _make_imaging_results(height=4, width=4, isotope_names=["Ta-181"])


@pytest.fixture
def results_with_failures() -> Imaging2DResults:
    """4x4 image with two isotopes, some failed pixels (NaN in maps)."""
    height, width = 4, 4
    isotope_names = ["Ta-181", "W-182"]
    n_iso = len(isotope_names)

    rng = np.random.default_rng(77)
    abundance = rng.uniform(0.1, 0.9, (n_iso, height, width)).astype(np.float64)
    chi2 = rng.uniform(0.5, 5.0, (height, width)).astype(np.float64)
    mask = np.ones((height, width), dtype=bool)

    # Mark some pixels as failed
    failed_positions = [(0, 1), (1, 3), (3, 0)]
    for r, c in failed_positions:
        abundance[:, r, c] = np.nan
        chi2[r, c] = np.nan
        mask[r, c] = False

    return _make_imaging_results(
        height=height,
        width=width,
        isotope_names=isotope_names,
        abundance_values=abundance,
        chi_squared_values=chi2,
        success_mask=mask,
    )


@pytest.fixture
def all_failed_results() -> Imaging2DResults:
    """4x4 image where every pixel failed (all NaN)."""
    height, width = 4, 4
    isotope_names = ["Ta-181", "W-182"]
    n_iso = len(isotope_names)

    abundance = np.full((n_iso, height, width), np.nan, dtype=np.float64)
    chi2 = np.full((height, width), np.nan, dtype=np.float64)
    mask = np.zeros((height, width), dtype=bool)

    return _make_imaging_results(
        height=height,
        width=width,
        isotope_names=isotope_names,
        abundance_values=abundance,
        chi_squared_values=chi2,
        success_mask=mask,
    )


@pytest.fixture
def single_pixel_results() -> Imaging2DResults:
    """1x1 image with one isotope, successful."""
    abundance = np.array([[[0.75]]], dtype=np.float64)
    chi2 = np.array([[1.5]], dtype=np.float64)
    mask = np.array([[True]])

    return _make_imaging_results(
        height=1,
        width=1,
        isotope_names=["Ta-181"],
        abundance_values=abundance,
        chi_squared_values=chi2,
        success_mask=mask,
    )


# ===========================================================================
# TestAbundanceMapGenerator
# ===========================================================================


class TestAbundanceMapGeneratorInit:
    """Tests for AbundanceMapGenerator.__init__."""

    def test_init_stores_results(self, two_isotope_results: Imaging2DResults) -> None:
        """Constructor should store the Imaging2DResults instance."""
        gen = AbundanceMapGenerator(two_isotope_results)
        # The generator should have access to the results data.
        # We verify by checking it can later produce maps (tested elsewhere),
        # but at minimum it should not raise on construction.
        assert gen is not None

    def test_init_with_single_isotope(self, single_isotope_results: Imaging2DResults) -> None:
        """Constructor should accept results with a single isotope."""
        gen = AbundanceMapGenerator(single_isotope_results)
        assert gen is not None


class TestGenerateMap:
    """Tests for AbundanceMapGenerator.generate_map()."""

    def test_returns_correct_shape(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_map should return a 2D array with shape (height, width)."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_map("Ta-181")
        assert result.ndim == 2
        expected_shape = two_isotope_results.abundance_maps.shape[1:]  # (height, width)
        assert result.shape == expected_shape

    def test_returns_correct_values_first_isotope(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_map for the first isotope should return the first layer of abundance_maps."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_map("Ta-181")
        expected = two_isotope_results.abundance_maps[0]
        np.testing.assert_array_equal(result, expected)

    def test_returns_correct_values_second_isotope(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_map for the second isotope should return the second layer of abundance_maps."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_map("W-182")
        expected = two_isotope_results.abundance_maps[1]
        np.testing.assert_array_equal(result, expected)

    def test_fill_value_replaces_nan(self, results_with_failures: Imaging2DResults) -> None:
        """generate_map with fill_value should replace NaN in failed pixels."""
        gen = AbundanceMapGenerator(results_with_failures)
        result = gen.generate_map("Ta-181", fill_value=0.0)

        # The result should contain no NaN values
        assert not np.any(np.isnan(result))

        # Failed pixel positions should now be 0.0
        failed_mask = ~results_with_failures.success_mask
        np.testing.assert_array_equal(result[failed_mask], 0.0)

    def test_fill_value_does_not_affect_successful_pixels(self, results_with_failures: Imaging2DResults) -> None:
        """fill_value should only replace NaN, not change successful pixel values."""
        gen = AbundanceMapGenerator(results_with_failures)
        result = gen.generate_map("Ta-181", fill_value=-999.0)

        # Successful pixels should retain their original values
        success_mask = results_with_failures.success_mask
        original = results_with_failures.abundance_maps[0]
        np.testing.assert_array_equal(result[success_mask], original[success_mask])

    def test_fill_value_default_is_nan(self, results_with_failures: Imaging2DResults) -> None:
        """Default fill_value should be NaN, preserving the original NaN values."""
        gen = AbundanceMapGenerator(results_with_failures)
        result = gen.generate_map("Ta-181")

        # NaN positions should be preserved
        original = results_with_failures.abundance_maps[0]
        np.testing.assert_array_equal(np.isnan(result), np.isnan(original))

    def test_fill_value_negative_one(self, results_with_failures: Imaging2DResults) -> None:
        """fill_value=-1.0 should fill failed pixels with -1.0."""
        gen = AbundanceMapGenerator(results_with_failures)
        result = gen.generate_map("Ta-181", fill_value=-1.0)

        failed_mask = ~results_with_failures.success_mask
        np.testing.assert_array_equal(result[failed_mask], -1.0)

    def test_unknown_isotope_raises_valueerror(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_map for an unknown isotope should raise ValueError."""
        gen = AbundanceMapGenerator(two_isotope_results)
        with pytest.raises(ValueError, match="(?i)isotope|not found|unknown"):
            gen.generate_map("Hf-180")

    def test_unknown_isotope_empty_string_raises(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_map with empty string isotope should raise ValueError."""
        gen = AbundanceMapGenerator(two_isotope_results)
        with pytest.raises(ValueError):
            gen.generate_map("")

    def test_single_isotope(self, single_isotope_results: Imaging2DResults) -> None:
        """generate_map works correctly when there is only one isotope."""
        gen = AbundanceMapGenerator(single_isotope_results)
        result = gen.generate_map("Ta-181")
        assert result.ndim == 2
        expected = single_isotope_results.abundance_maps[0]
        np.testing.assert_array_equal(result, expected)


class TestGenerateMapEdgeCases:
    """Edge case tests for generate_map."""

    def test_single_pixel_image(self, single_pixel_results: Imaging2DResults) -> None:
        """generate_map should work for a 1x1 image."""
        gen = AbundanceMapGenerator(single_pixel_results)
        result = gen.generate_map("Ta-181")
        assert result.shape == (1, 1)
        np.testing.assert_allclose(result[0, 0], 0.75)

    def test_all_pixels_failed(self, all_failed_results: Imaging2DResults) -> None:
        """generate_map with all-NaN map should return all NaN (default fill_value)."""
        gen = AbundanceMapGenerator(all_failed_results)
        result = gen.generate_map("Ta-181")
        assert np.all(np.isnan(result))

    def test_all_pixels_failed_with_fill_value(self, all_failed_results: Imaging2DResults) -> None:
        """generate_map with all-NaN map and fill_value should fill every pixel."""
        gen = AbundanceMapGenerator(all_failed_results)
        result = gen.generate_map("Ta-181", fill_value=0.0)
        np.testing.assert_array_equal(result, 0.0)
        assert not np.any(np.isnan(result))

    def test_all_pixels_succeeded(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_map with no NaN should return the same values regardless of fill_value."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result_default = gen.generate_map("Ta-181")
        result_filled = gen.generate_map("Ta-181", fill_value=0.0)

        # Both should be identical since there are no NaN values to replace
        np.testing.assert_array_equal(result_default, result_filled)

    def test_wide_image(self) -> None:
        """generate_map works for a wide image (1 row, many columns)."""
        results = _make_imaging_results(height=1, width=100, isotope_names=["Ta-181"])
        gen = AbundanceMapGenerator(results)
        result = gen.generate_map("Ta-181")
        assert result.shape == (1, 100)

    def test_tall_image(self) -> None:
        """generate_map works for a tall image (many rows, 1 column)."""
        results = _make_imaging_results(height=100, width=1, isotope_names=["Ta-181"])
        gen = AbundanceMapGenerator(results)
        result = gen.generate_map("Ta-181")
        assert result.shape == (100, 1)


class TestGenerateAllMaps:
    """Tests for AbundanceMapGenerator.generate_all_maps()."""

    def test_returns_dict(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_all_maps should return a dict."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_all_maps()
        assert isinstance(result, dict)

    def test_dict_keys_are_isotope_names(self, two_isotope_results: Imaging2DResults) -> None:
        """Keys of the returned dict should be isotope names."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_all_maps()
        assert set(result.keys()) == {"Ta-181", "W-182"}

    def test_dict_values_are_2d_arrays(self, two_isotope_results: Imaging2DResults) -> None:
        """Values of the returned dict should be 2D numpy arrays."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_all_maps()
        for name, arr in result.items():
            assert isinstance(arr, np.ndarray), f"Value for '{name}' is not ndarray"
            assert arr.ndim == 2, f"Value for '{name}' is not 2D"

    def test_values_match_individual_maps(self, two_isotope_results: Imaging2DResults) -> None:
        """Each map in generate_all_maps should match the corresponding generate_map call."""
        gen = AbundanceMapGenerator(two_isotope_results)
        all_maps = gen.generate_all_maps()

        for isotope_name in two_isotope_results.isotope_names:
            expected = gen.generate_map(isotope_name)
            np.testing.assert_array_equal(all_maps[isotope_name], expected)

    def test_single_isotope(self, single_isotope_results: Imaging2DResults) -> None:
        """generate_all_maps with one isotope returns dict with one entry."""
        gen = AbundanceMapGenerator(single_isotope_results)
        result = gen.generate_all_maps()
        assert len(result) == 1
        assert "Ta-181" in result

    def test_three_isotopes(self) -> None:
        """generate_all_maps with three isotopes returns dict with three entries."""
        results = _make_imaging_results(height=3, width=3, isotope_names=["Ta-181", "W-182", "W-184"])
        gen = AbundanceMapGenerator(results)
        all_maps = gen.generate_all_maps()
        assert len(all_maps) == 3
        assert set(all_maps.keys()) == {"Ta-181", "W-182", "W-184"}

    def test_with_failures_preserves_nan(self, results_with_failures: Imaging2DResults) -> None:
        """generate_all_maps should preserve NaN values for failed pixels."""
        gen = AbundanceMapGenerator(results_with_failures)
        all_maps = gen.generate_all_maps()

        for isotope_name in results_with_failures.isotope_names:
            idx = results_with_failures.isotope_names.index(isotope_name)
            original = results_with_failures.abundance_maps[idx]
            np.testing.assert_array_equal(
                np.isnan(all_maps[isotope_name]),
                np.isnan(original),
            )


class TestGenerateQualityMap:
    """Tests for AbundanceMapGenerator.generate_quality_map()."""

    def test_chi_squared_returns_correct_map(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_quality_map('chi_squared') should return the chi_squared_map."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_quality_map(metric="chi_squared")
        np.testing.assert_array_equal(result, two_isotope_results.chi_squared_map)

    def test_chi_squared_is_default_metric(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_quality_map() with no argument should default to 'chi_squared'."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result_default = gen.generate_quality_map()
        result_explicit = gen.generate_quality_map(metric="chi_squared")
        np.testing.assert_array_equal(result_default, result_explicit)

    def test_chi_squared_shape(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_quality_map('chi_squared') should return a 2D array."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_quality_map(metric="chi_squared")
        assert result.ndim == 2
        assert result.shape == two_isotope_results.chi_squared_map.shape

    def test_chi_squared_preserves_nan(self, results_with_failures: Imaging2DResults) -> None:
        """generate_quality_map('chi_squared') should preserve NaN for failed pixels."""
        gen = AbundanceMapGenerator(results_with_failures)
        result = gen.generate_quality_map(metric="chi_squared")
        np.testing.assert_array_equal(
            np.isnan(result),
            np.isnan(results_with_failures.chi_squared_map),
        )

    def test_success_metric_returns_float_mask(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_quality_map('success') should return success_mask as float (1.0/0.0)."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_quality_map(metric="success")

        # All pixels successful, so all should be 1.0
        expected = np.ones((4, 4), dtype=float)
        np.testing.assert_array_equal(result, expected)

    def test_success_metric_with_failures(self, results_with_failures: Imaging2DResults) -> None:
        """generate_quality_map('success') should return 0.0 for failed pixels, 1.0 for successful."""
        gen = AbundanceMapGenerator(results_with_failures)
        result = gen.generate_quality_map(metric="success")

        expected = results_with_failures.success_mask.astype(float)
        np.testing.assert_array_equal(result, expected)

    def test_success_metric_dtype_is_float(self, results_with_failures: Imaging2DResults) -> None:
        """generate_quality_map('success') should return float array, not bool."""
        gen = AbundanceMapGenerator(results_with_failures)
        result = gen.generate_quality_map(metric="success")
        assert result.dtype in (np.float32, np.float64), f"Expected float dtype, got {result.dtype}"

    def test_success_metric_shape(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_quality_map('success') should return a 2D array."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_quality_map(metric="success")
        assert result.ndim == 2
        assert result.shape == two_isotope_results.success_mask.shape

    def test_invalid_metric_raises_valueerror(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_quality_map with unknown metric should raise ValueError."""
        gen = AbundanceMapGenerator(two_isotope_results)
        with pytest.raises(ValueError, match="(?i)metric|unsupported|unknown|invalid"):
            gen.generate_quality_map(metric="r_squared")

    def test_invalid_metric_empty_string(self, two_isotope_results: Imaging2DResults) -> None:
        """generate_quality_map with empty string metric should raise ValueError."""
        gen = AbundanceMapGenerator(two_isotope_results)
        with pytest.raises(ValueError):
            gen.generate_quality_map(metric="")

    def test_all_failed_chi_squared(self, all_failed_results: Imaging2DResults) -> None:
        """generate_quality_map('chi_squared') with all-failed should return all NaN."""
        gen = AbundanceMapGenerator(all_failed_results)
        result = gen.generate_quality_map(metric="chi_squared")
        assert np.all(np.isnan(result))

    def test_all_failed_success_metric(self, all_failed_results: Imaging2DResults) -> None:
        """generate_quality_map('success') with all-failed should return all 0.0."""
        gen = AbundanceMapGenerator(all_failed_results)
        result = gen.generate_quality_map(metric="success")
        np.testing.assert_array_equal(result, 0.0)

    def test_single_pixel_chi_squared(self, single_pixel_results: Imaging2DResults) -> None:
        """generate_quality_map works for a 1x1 image."""
        gen = AbundanceMapGenerator(single_pixel_results)
        result = gen.generate_quality_map(metric="chi_squared")
        assert result.shape == (1, 1)
        np.testing.assert_allclose(result[0, 0], 1.5)

    def test_single_pixel_success_metric(self, single_pixel_results: Imaging2DResults) -> None:
        """generate_quality_map('success') for 1x1 successful image returns 1.0."""
        gen = AbundanceMapGenerator(single_pixel_results)
        result = gen.generate_quality_map(metric="success")
        assert result.shape == (1, 1)
        np.testing.assert_allclose(result[0, 0], 1.0)


class TestGenerateMapReturnsCopy:
    """Tests to verify that generate_map returns a copy, not a view of the internal data."""

    def test_modifying_result_does_not_affect_internal_data(self, two_isotope_results: Imaging2DResults) -> None:
        """Modifying the returned map should not change the original results."""
        gen = AbundanceMapGenerator(two_isotope_results)
        result = gen.generate_map("Ta-181")
        original_value = result[0, 0]

        # Mutate the returned array
        result[0, 0] = -999.0

        # The generator should still return the original value
        result2 = gen.generate_map("Ta-181")
        np.testing.assert_allclose(result2[0, 0], original_value)

    def test_modifying_all_maps_does_not_affect_internal_data(self, two_isotope_results: Imaging2DResults) -> None:
        """Modifying a map from generate_all_maps should not change the original results."""
        gen = AbundanceMapGenerator(two_isotope_results)
        all_maps = gen.generate_all_maps()
        original_value = all_maps["Ta-181"][0, 0]

        # Mutate the returned array
        all_maps["Ta-181"][0, 0] = -999.0

        # The generator should still return the original value
        all_maps2 = gen.generate_all_maps()
        np.testing.assert_allclose(all_maps2["Ta-181"][0, 0], original_value)
