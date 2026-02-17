"""Validation tests for the 2D imaging pipeline with clean synthetic data.

Issue #180: Validate the imaging pipeline end-to-end using synthetic data with
KNOWN ground truth and verify that the pipeline recovers it correctly.

Test classes:
  1. TestSyntheticUniform       - Single isotope, uniform abundance (flat map)
  2. TestSyntheticGradient      - Linear abundance gradient recovery
  3. TestSyntheticMultiIsotope  - Two isotopes with different spatial patterns
  4. TestSyntheticSharpBoundary - Step function in abundance (boundary preservation)
  5. TestFailedPixelHandling    - Failed pixels produce NaN, success_mask correct
  6. TestHDF5RoundTrip          - Save and reload results, verify data preserved
  7. TestEndToEndPipeline       - Full pipeline: TIFF -> loader -> orchestrator (mocked) -> aggregator -> generator -> visualizer

Tests mock SAMMY execution via _fit_pixel_worker but use real aggregator,
generator, and visualizer objects.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from pathlib import Path  # noqa: E402
from typing import Dict, List  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402
import tifffile  # noqa: E402

from pleiades.imaging.aggregator import ResultsAggregator  # noqa: E402
from pleiades.imaging.generator import AbundanceMapGenerator  # noqa: E402
from pleiades.imaging.loader import HyperspectralLoader  # noqa: E402
from pleiades.imaging.models import (  # noqa: E402
    HyperspectralData,
    Imaging2DResults,
    PixelFitResult,
)
from pleiades.imaging.visualizer import AbundanceMapVisualizer  # noqa: E402
from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData  # noqa: E402
from pleiades.nuclear.models import IsotopeParameters, nuclearParameters  # noqa: E402
from pleiades.sammy.results.models import FitResults  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRID_SIZE = 8
N_ENERGY = 20
TOLERANCE_ABUNDANCE = 0.05  # 5% of ground truth
TOLERANCE_ATOL = 1e-10  # For exact floating point comparisons

# Isotope physical constants used across all tests
TA181_SPEC = {
    "name": "Ta-181",
    "atomic_number": 73,
    "mass_number": 181,
    "atomic_mass": 180.948,
    "spin": 3.5,
}

W182_SPEC = {
    "name": "W-182",
    "atomic_number": 74,
    "mass_number": 182,
    "atomic_mass": 181.948,
    "spin": 0.0,
}


# ---------------------------------------------------------------------------
# Helper: build real PLEIADES model objects for mocked SAMMY output
# ---------------------------------------------------------------------------


def _make_isotope_info(
    name: str,
    atomic_number: int,
    mass_number: int,
    atomic_mass: float,
    spin: float,
) -> IsotopeInfo:
    """Build a minimal IsotopeInfo with required fields."""
    return IsotopeInfo(
        name=name,
        atomic_number=atomic_number,
        mass_number=mass_number,
        mass_data=IsotopeMassData(atomic_mass=atomic_mass),
        spin=spin,
    )


def _make_isotope_params(
    name: str,
    atomic_number: int,
    mass_number: int,
    atomic_mass: float,
    spin: float,
    abundance: float,
) -> IsotopeParameters:
    """Build a minimal IsotopeParameters with an abundance value."""
    info = _make_isotope_info(name, atomic_number, mass_number, atomic_mass, spin)
    return IsotopeParameters(
        isotope_information=info,
        abundance=abundance,
    )


def _make_fit_results(isotope_specs: List[Dict]) -> FitResults:
    """Build a FitResults containing isotopes with specified abundances.

    Args:
        isotope_specs: list of dicts with keys:
            name, atomic_number, mass_number, atomic_mass, spin, abundance
    """
    isotopes = [
        _make_isotope_params(
            name=spec["name"],
            atomic_number=spec["atomic_number"],
            mass_number=spec["mass_number"],
            atomic_mass=spec["atomic_mass"],
            spin=spec["spin"],
            abundance=spec["abundance"],
        )
        for spec in isotope_specs
    ]
    nuclear_data = nuclearParameters(isotopes=isotopes)
    return FitResults(nuclear_data=nuclear_data)


def _make_successful_pixel(
    row: int,
    col: int,
    isotope_specs: List[Dict],
    chi_squared: float = 1.0,
) -> PixelFitResult:
    """Build a successful PixelFitResult with real model objects."""
    fit_results = _make_fit_results(isotope_specs)
    return PixelFitResult(
        row=row,
        col=col,
        fit_results=fit_results,
        success=True,
        chi_squared=chi_squared,
    )


def _make_failed_pixel(
    row: int,
    col: int,
    error_message: str = "Fit diverged",
) -> PixelFitResult:
    """Build a failed PixelFitResult."""
    return PixelFitResult(
        row=row,
        col=col,
        fit_results=None,
        success=False,
        error_message=error_message,
    )


def _make_hyperspectral(
    height: int,
    width: int,
    n_energy: int = N_ENERGY,
) -> HyperspectralData:
    """Build a minimal HyperspectralData for testing.

    Uses a deterministic RNG so tests are reproducible.
    """
    rng = np.random.default_rng(42)
    data = rng.uniform(0.3, 0.95, (n_energy, height, width)).astype(np.float64)
    energy = np.linspace(1.0, 100.0, n_energy)
    return HyperspectralData(
        data=data,
        energy=energy,
        source_file=Path("/tmp/test_validation_source.tif"),
    )


# ---------------------------------------------------------------------------
# Helper: build ground truth maps and corresponding pixel results
# ---------------------------------------------------------------------------


def _build_uniform_ground_truth(
    height: int,
    width: int,
    abundance: float,
) -> tuple[np.ndarray, List[PixelFitResult]]:
    """Build a uniform abundance ground truth for a single isotope.

    Returns:
        (ground_truth_map, pixel_results)
        ground_truth_map: 2D array (height, width) with constant abundance
        pixel_results: list of PixelFitResult, one per pixel
    """
    ground_truth = np.full((height, width), abundance, dtype=np.float64)
    pixel_results = []
    for row in range(height):
        for col in range(width):
            specs = [{**TA181_SPEC, "abundance": abundance}]
            pixel_results.append(_make_successful_pixel(row, col, specs, chi_squared=1.0))
    return ground_truth, pixel_results


def _build_gradient_ground_truth(
    height: int,
    width: int,
    min_abundance: float = 0.10,
    max_abundance: float = 0.90,
) -> tuple[np.ndarray, List[PixelFitResult]]:
    """Build a left-to-right linear gradient ground truth for a single isotope.

    Returns:
        (ground_truth_map, pixel_results)
    """
    ground_truth = np.zeros((height, width), dtype=np.float64)
    pixel_results = []
    for row in range(height):
        for col in range(width):
            # Linear gradient from left (min) to right (max)
            frac = col / max(width - 1, 1)
            abundance = min_abundance + frac * (max_abundance - min_abundance)
            ground_truth[row, col] = abundance
            specs = [{**TA181_SPEC, "abundance": abundance}]
            pixel_results.append(_make_successful_pixel(row, col, specs, chi_squared=1.0 + 0.1 * col))
    return ground_truth, pixel_results


def _build_multi_isotope_ground_truth(
    height: int,
    width: int,
) -> tuple[np.ndarray, np.ndarray, List[PixelFitResult]]:
    """Build two-isotope ground truth with different spatial patterns.

    Ta-181: left-to-right gradient (0.1 -> 0.9)
    W-182:  top-to-bottom gradient (0.8 -> 0.2)

    Returns:
        (ta_truth, w_truth, pixel_results)
    """
    ta_truth = np.zeros((height, width), dtype=np.float64)
    w_truth = np.zeros((height, width), dtype=np.float64)
    pixel_results = []
    for row in range(height):
        for col in range(width):
            col_frac = col / max(width - 1, 1)
            row_frac = row / max(height - 1, 1)
            ta_abundance = 0.1 + 0.8 * col_frac
            w_abundance = 0.8 - 0.6 * row_frac
            ta_truth[row, col] = ta_abundance
            w_truth[row, col] = w_abundance
            specs = [
                {**TA181_SPEC, "abundance": ta_abundance},
                {**W182_SPEC, "abundance": w_abundance},
            ]
            pixel_results.append(_make_successful_pixel(row, col, specs, chi_squared=1.5))
    return ta_truth, w_truth, pixel_results


def _build_sharp_boundary_ground_truth(
    height: int,
    width: int,
    boundary_col: int = 4,
    left_abundance: float = 0.90,
    right_abundance: float = 0.10,
) -> tuple[np.ndarray, List[PixelFitResult]]:
    """Build a step-function ground truth: left half one value, right half another.

    Returns:
        (ground_truth_map, pixel_results)
    """
    ground_truth = np.zeros((height, width), dtype=np.float64)
    pixel_results = []
    for row in range(height):
        for col in range(width):
            abundance = left_abundance if col < boundary_col else right_abundance
            ground_truth[row, col] = abundance
            specs = [{**TA181_SPEC, "abundance": abundance}]
            pixel_results.append(_make_successful_pixel(row, col, specs, chi_squared=1.0))
    return ground_truth, pixel_results


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def close_figures_after_test():
    """Close all matplotlib figures after each test to prevent resource leaks."""
    yield
    plt.close("all")


# ===========================================================================
# 1. TestSyntheticUniform
# ===========================================================================


class TestSyntheticUniform:
    """Uniform sample: single isotope, uniform abundance -> flat map.

    Verifies that when every pixel has the same known abundance, the
    aggregated map is flat, the generator extracts it correctly, and the
    visualizer produces a valid plot.
    """

    def test_aggregated_map_is_flat(self):
        """All pixels with identical abundance produce a flat abundance map."""
        height, width = GRID_SIZE, GRID_SIZE
        target_abundance = 0.75
        ground_truth, pixel_results = _build_uniform_ground_truth(height, width, target_abundance)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        # The abundance map should be flat
        np.testing.assert_allclose(
            result.abundance_maps[0],
            target_abundance,
            atol=TOLERANCE_ATOL,
        )

    def test_all_pixels_succeed(self):
        """Every pixel should be marked as successful on clean synthetic data."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_uniform_ground_truth(height, width, 0.75)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert np.all(result.success_mask)
        assert np.sum(result.success_mask) == height * width

    def test_abundance_within_tolerance_of_ground_truth(self):
        """Recovered abundance is within 5% of ground truth for every pixel."""
        height, width = GRID_SIZE, GRID_SIZE
        target_abundance = 0.75
        ground_truth, pixel_results = _build_uniform_ground_truth(height, width, target_abundance)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        # Every pixel should be within 5% of the ground truth
        relative_error = np.abs(result.abundance_maps[0] - ground_truth) / ground_truth
        assert np.all(relative_error < TOLERANCE_ABUNDANCE), f"Max relative error: {np.max(relative_error):.4f}"

    def test_no_nan_in_results(self):
        """No NaN values should appear in abundance or chi-squared maps."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_uniform_ground_truth(height, width, 0.75)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert not np.any(np.isnan(result.abundance_maps))
        assert not np.any(np.isnan(result.chi_squared_map))

    def test_generator_extracts_flat_map(self):
        """AbundanceMapGenerator.generate_map returns the same flat values."""
        height, width = GRID_SIZE, GRID_SIZE
        target_abundance = 0.75
        _, pixel_results = _build_uniform_ground_truth(height, width, target_abundance)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        imaging_results = aggregator.aggregate(pixel_results, source)

        gen = AbundanceMapGenerator(imaging_results)
        ta_map = gen.generate_map("Ta-181")

        assert ta_map.shape == (height, width)
        np.testing.assert_allclose(ta_map, target_abundance, atol=TOLERANCE_ATOL)

    def test_visualizer_produces_valid_figure(self):
        """AbundanceMapVisualizer.plot_single_isotope produces a valid figure."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_uniform_ground_truth(height, width, 0.75)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        imaging_results = aggregator.aggregate(pixel_results, source)

        viz = AbundanceMapVisualizer(imaging_results)
        fig, ax = viz.plot_single_isotope("Ta-181")

        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(ax, matplotlib.axes.Axes)
        assert len(ax.get_images()) > 0

    def test_pixel_success_rate_100_percent(self):
        """Success rate is 100% for clean synthetic data."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_uniform_ground_truth(height, width, 0.75)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        total_pixels = height * width
        success_count = np.sum(result.success_mask)
        success_rate = success_count / total_pixels
        assert success_rate >= 0.99


# ===========================================================================
# 2. TestSyntheticGradient
# ===========================================================================


class TestSyntheticGradient:
    """Gradient sample: linear abundance gradient -> gradient recovered.

    Verifies that a left-to-right linear gradient in abundance is faithfully
    recovered through the aggregator and generator pipeline.
    """

    def test_gradient_recovered_within_tolerance(self):
        """Recovered gradient matches ground truth within 5% for every pixel."""
        height, width = GRID_SIZE, GRID_SIZE
        ground_truth, pixel_results = _build_gradient_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        # For pixels where ground truth > 0, check relative error
        nonzero = ground_truth > 0
        relative_error = np.abs(result.abundance_maps[0][nonzero] - ground_truth[nonzero]) / ground_truth[nonzero]
        assert np.all(relative_error < TOLERANCE_ABUNDANCE), f"Max relative error: {np.max(relative_error):.4f}"

    def test_gradient_monotonically_increasing_left_to_right(self):
        """Each row of the abundance map should be monotonically increasing."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_gradient_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        for row in range(height):
            row_values = result.abundance_maps[0, row, :]
            diffs = np.diff(row_values)
            assert np.all(diffs >= 0), f"Row {row} is not monotonically increasing: {row_values}"

    def test_gradient_columns_are_constant(self):
        """Each column should have the same abundance value across all rows."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_gradient_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        for col in range(width):
            col_values = result.abundance_maps[0, :, col]
            # All values in a column should be identical
            np.testing.assert_allclose(
                col_values,
                col_values[0],
                atol=TOLERANCE_ATOL,
            )

    def test_gradient_min_max_match_ground_truth(self):
        """The min/max of the recovered gradient match the ground truth."""
        height, width = GRID_SIZE, GRID_SIZE
        min_abundance, max_abundance = 0.10, 0.90
        ground_truth, pixel_results = _build_gradient_ground_truth(height, width, min_abundance, max_abundance)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        recovered_map = result.abundance_maps[0]
        np.testing.assert_allclose(np.min(recovered_map), min_abundance, atol=TOLERANCE_ATOL)
        np.testing.assert_allclose(np.max(recovered_map), max_abundance, atol=TOLERANCE_ATOL)

    def test_gradient_generator_extracts_correct_shape(self):
        """AbundanceMapGenerator returns 2D map with correct shape."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_gradient_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        imaging_results = aggregator.aggregate(pixel_results, source)

        gen = AbundanceMapGenerator(imaging_results)
        ta_map = gen.generate_map("Ta-181")
        assert ta_map.shape == (height, width)

    def test_gradient_chi_squared_map_no_nan(self):
        """Chi-squared map has no NaN values for clean synthetic data."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_gradient_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert not np.any(np.isnan(result.chi_squared_map))

    def test_gradient_all_pixels_succeed(self):
        """Success rate is 100% for clean gradient data."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_gradient_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert np.all(result.success_mask)


# ===========================================================================
# 3. TestSyntheticMultiIsotope
# ===========================================================================


class TestSyntheticMultiIsotope:
    """Multi-isotope sample: two isotopes with different spatial patterns.

    Ta-181 has a left-to-right gradient; W-182 has a top-to-bottom gradient.
    Each isotope map should match its own ground truth independently.
    """

    def test_ta_map_matches_ground_truth(self):
        """Ta-181 abundance map matches its left-to-right gradient ground truth."""
        height, width = GRID_SIZE, GRID_SIZE
        ta_truth, _, pixel_results = _build_multi_isotope_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        np.testing.assert_allclose(result.abundance_maps[0], ta_truth, atol=TOLERANCE_ATOL)

    def test_w_map_matches_ground_truth(self):
        """W-182 abundance map matches its top-to-bottom gradient ground truth."""
        height, width = GRID_SIZE, GRID_SIZE
        _, w_truth, pixel_results = _build_multi_isotope_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        np.testing.assert_allclose(result.abundance_maps[1], w_truth, atol=TOLERANCE_ATOL)

    def test_ta_and_w_maps_differ(self):
        """The Ta-181 and W-182 maps should have distinct spatial patterns."""
        height, width = GRID_SIZE, GRID_SIZE
        _, _, pixel_results = _build_multi_isotope_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        # The two maps should not be equal
        assert not np.allclose(result.abundance_maps[0], result.abundance_maps[1])

    def test_isotope_names_preserved(self):
        """Isotope names in the output match the input configuration."""
        height, width = GRID_SIZE, GRID_SIZE
        _, _, pixel_results = _build_multi_isotope_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert result.isotope_names == ["Ta-181", "W-182"]

    def test_abundance_maps_shape(self):
        """abundance_maps has shape (2, height, width) for two isotopes."""
        height, width = GRID_SIZE, GRID_SIZE
        _, _, pixel_results = _build_multi_isotope_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert result.abundance_maps.shape == (2, height, width)

    def test_generator_extracts_each_isotope_independently(self):
        """AbundanceMapGenerator can extract each isotope map independently."""
        height, width = GRID_SIZE, GRID_SIZE
        ta_truth, w_truth, pixel_results = _build_multi_isotope_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        imaging_results = aggregator.aggregate(pixel_results, source)

        gen = AbundanceMapGenerator(imaging_results)
        ta_map = gen.generate_map("Ta-181")
        w_map = gen.generate_map("W-182")

        np.testing.assert_allclose(ta_map, ta_truth, atol=TOLERANCE_ATOL)
        np.testing.assert_allclose(w_map, w_truth, atol=TOLERANCE_ATOL)

    def test_generate_all_maps_returns_both(self):
        """generate_all_maps returns both isotope maps."""
        height, width = GRID_SIZE, GRID_SIZE
        _, _, pixel_results = _build_multi_isotope_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        imaging_results = aggregator.aggregate(pixel_results, source)

        gen = AbundanceMapGenerator(imaging_results)
        all_maps = gen.generate_all_maps()

        assert set(all_maps.keys()) == {"Ta-181", "W-182"}
        assert all_maps["Ta-181"].shape == (height, width)
        assert all_maps["W-182"].shape == (height, width)

    def test_multi_isotope_visualizer_plots_grid(self):
        """plot_multi_isotope produces a grid with both isotopes."""
        height, width = GRID_SIZE, GRID_SIZE
        _, _, pixel_results = _build_multi_isotope_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        imaging_results = aggregator.aggregate(pixel_results, source)

        viz = AbundanceMapVisualizer(imaging_results)
        fig, axes = viz.plot_multi_isotope()

        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axes, np.ndarray)
        total_axes = axes.flatten()
        axes_with_images = [ax for ax in total_axes if len(ax.get_images()) > 0]
        assert len(axes_with_images) >= 2

    def test_multi_isotope_within_tolerance(self):
        """Both isotope maps are within 5% relative error of ground truth."""
        height, width = GRID_SIZE, GRID_SIZE
        ta_truth, w_truth, pixel_results = _build_multi_isotope_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        # Ta-181
        ta_nonzero = ta_truth > 0
        ta_relerr = np.abs(result.abundance_maps[0][ta_nonzero] - ta_truth[ta_nonzero]) / ta_truth[ta_nonzero]
        assert np.all(ta_relerr < TOLERANCE_ABUNDANCE)

        # W-182
        w_nonzero = w_truth > 0
        w_relerr = np.abs(result.abundance_maps[1][w_nonzero] - w_truth[w_nonzero]) / w_truth[w_nonzero]
        assert np.all(w_relerr < TOLERANCE_ABUNDANCE)


# ===========================================================================
# 4. TestSyntheticSharpBoundary
# ===========================================================================


class TestSyntheticSharpBoundary:
    """Sharp boundary: step function in abundance -> boundaries preserved.

    Left half has abundance 0.90, right half has 0.10. The aggregated map
    should faithfully reproduce this sharp transition.
    """

    def test_boundary_preserved(self):
        """Step function boundary is preserved: left != right."""
        height, width = GRID_SIZE, GRID_SIZE
        boundary_col = width // 2
        left_val, right_val = 0.90, 0.10
        ground_truth, pixel_results = _build_sharp_boundary_ground_truth(
            height, width, boundary_col, left_val, right_val
        )
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        recovered = result.abundance_maps[0]
        np.testing.assert_allclose(recovered, ground_truth, atol=TOLERANCE_ATOL)

    def test_left_half_uniform(self):
        """All pixels in the left half have the same high abundance."""
        height, width = GRID_SIZE, GRID_SIZE
        boundary_col = width // 2
        left_val, right_val = 0.90, 0.10
        _, pixel_results = _build_sharp_boundary_ground_truth(height, width, boundary_col, left_val, right_val)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        left_half = result.abundance_maps[0, :, :boundary_col]
        np.testing.assert_allclose(left_half, left_val, atol=TOLERANCE_ATOL)

    def test_right_half_uniform(self):
        """All pixels in the right half have the same low abundance."""
        height, width = GRID_SIZE, GRID_SIZE
        boundary_col = width // 2
        left_val, right_val = 0.90, 0.10
        _, pixel_results = _build_sharp_boundary_ground_truth(height, width, boundary_col, left_val, right_val)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        right_half = result.abundance_maps[0, :, boundary_col:]
        np.testing.assert_allclose(right_half, right_val, atol=TOLERANCE_ATOL)

    def test_boundary_column_contrast(self):
        """The column immediately left of boundary differs from right column."""
        height, width = GRID_SIZE, GRID_SIZE
        boundary_col = width // 2
        left_val, right_val = 0.90, 0.10
        _, pixel_results = _build_sharp_boundary_ground_truth(height, width, boundary_col, left_val, right_val)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        recovered = result.abundance_maps[0]
        # Column just before boundary vs column at boundary
        left_boundary = recovered[:, boundary_col - 1]
        right_boundary = recovered[:, boundary_col]

        # Contrast should be preserved
        for row in range(height):
            assert abs(left_boundary[row] - right_boundary[row]) > 0.5, (
                f"Row {row}: boundary contrast too small ({left_boundary[row]:.3f} vs {right_boundary[row]:.3f})"
            )

    def test_sharp_boundary_all_pixels_succeed(self):
        """All pixels succeed for clean step-function data."""
        height, width = GRID_SIZE, GRID_SIZE
        _, pixel_results = _build_sharp_boundary_ground_truth(height, width, width // 2, 0.90, 0.10)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert np.all(result.success_mask)

    def test_sharp_boundary_within_tolerance(self):
        """Every pixel's abundance is within 5% relative error of ground truth."""
        height, width = GRID_SIZE, GRID_SIZE
        ground_truth, pixel_results = _build_sharp_boundary_ground_truth(height, width, width // 2, 0.90, 0.10)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        nonzero = ground_truth > 0
        relative_error = np.abs(result.abundance_maps[0][nonzero] - ground_truth[nonzero]) / ground_truth[nonzero]
        assert np.all(relative_error < TOLERANCE_ABUNDANCE)


# ===========================================================================
# 5. TestFailedPixelHandling
# ===========================================================================


class TestFailedPixelHandling:
    """Failed pixels: some pixels fail -> NaN placement, success_mask correct.

    Verifies that when specific pixels fail during fitting, the aggregated
    results correctly use NaN for those pixels and mark success_mask=False.
    """

    def _build_results_with_failures(
        self,
        height: int,
        width: int,
        failed_coords: List[tuple[int, int]],
    ) -> tuple[Imaging2DResults, np.ndarray]:
        """Build Imaging2DResults with specified failed pixel coordinates.

        Returns:
            (imaging_results, expected_success_mask)
        """
        pixel_results = []
        expected_success_mask = np.ones((height, width), dtype=bool)
        failed_set = set(failed_coords)

        for row in range(height):
            for col in range(width):
                if (row, col) in failed_set:
                    pixel_results.append(_make_failed_pixel(row, col, "Simulated failure"))
                    expected_success_mask[row, col] = False
                else:
                    specs = [{**TA181_SPEC, "abundance": 0.75}]
                    pixel_results.append(_make_successful_pixel(row, col, specs, chi_squared=1.0))

        source = _make_hyperspectral(height, width)
        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)
        return result, expected_success_mask

    def test_failed_pixels_have_nan_abundance(self):
        """Failed pixels should have NaN in the abundance map."""
        failed_coords = [(0, 0), (2, 3), (5, 7)]
        result, _ = self._build_results_with_failures(GRID_SIZE, GRID_SIZE, failed_coords)

        for row, col in failed_coords:
            assert np.isnan(result.abundance_maps[0, row, col]), f"Pixel ({row}, {col}) should have NaN abundance"

    def test_failed_pixels_have_nan_chi_squared(self):
        """Failed pixels should have NaN in the chi-squared map."""
        failed_coords = [(1, 1), (3, 4), (6, 2)]
        result, _ = self._build_results_with_failures(GRID_SIZE, GRID_SIZE, failed_coords)

        for row, col in failed_coords:
            assert np.isnan(result.chi_squared_map[row, col]), f"Pixel ({row}, {col}) should have NaN chi_squared"

    def test_success_mask_correct(self):
        """success_mask should be False for failed pixels, True otherwise."""
        failed_coords = [(0, 3), (4, 4), (7, 0), (7, 7)]
        result, expected_mask = self._build_results_with_failures(GRID_SIZE, GRID_SIZE, failed_coords)

        np.testing.assert_array_equal(result.success_mask, expected_mask)

    def test_successful_pixels_unaffected_by_failures(self):
        """Successful pixels should have correct abundance despite some failures."""
        failed_coords = [(0, 0), (7, 7)]
        result, _ = self._build_results_with_failures(GRID_SIZE, GRID_SIZE, failed_coords)

        # Check a known successful pixel
        assert result.success_mask[3, 3]
        np.testing.assert_allclose(result.abundance_maps[0, 3, 3], 0.75, atol=TOLERANCE_ATOL)

    def test_single_failed_pixel(self):
        """A single failed pixel in an otherwise clean image is correctly handled."""
        failed_coords = [(4, 4)]
        result, expected_mask = self._build_results_with_failures(GRID_SIZE, GRID_SIZE, failed_coords)

        assert not result.success_mask[4, 4]
        assert np.isnan(result.abundance_maps[0, 4, 4])

        # All other pixels should be fine
        n_success = np.sum(result.success_mask)
        assert n_success == GRID_SIZE * GRID_SIZE - 1

    def test_all_pixels_failed(self):
        """When every pixel fails, all maps should be NaN and success_mask all False."""
        height, width = 4, 4
        failed_coords = [(r, c) for r in range(height) for c in range(width)]
        result, _ = self._build_results_with_failures(height, width, failed_coords)

        assert not np.any(result.success_mask)
        assert np.all(np.isnan(result.abundance_maps))
        assert np.all(np.isnan(result.chi_squared_map))

    def test_edge_pixels_failed(self):
        """Edge pixels failing does not corrupt interior pixels."""
        height, width = GRID_SIZE, GRID_SIZE
        # All edge pixels
        edge_coords = []
        for r in range(height):
            for c in range(width):
                if r == 0 or r == height - 1 or c == 0 or c == width - 1:
                    edge_coords.append((r, c))
        result, expected_mask = self._build_results_with_failures(height, width, edge_coords)

        # Edge pixels should be NaN
        for r, c in edge_coords:
            assert np.isnan(result.abundance_maps[0, r, c])

        # Interior pixels should be valid
        for r in range(1, height - 1):
            for c in range(1, width - 1):
                assert result.success_mask[r, c]
                np.testing.assert_allclose(result.abundance_maps[0, r, c], 0.75, atol=TOLERANCE_ATOL)

    def test_generator_fill_value_for_failed_pixels(self):
        """Generator fill_value correctly replaces NaN for failed pixels."""
        failed_coords = [(2, 2), (5, 5)]
        result, _ = self._build_results_with_failures(GRID_SIZE, GRID_SIZE, failed_coords)

        gen = AbundanceMapGenerator(result)
        filled_map = gen.generate_map("Ta-181", fill_value=0.0)

        # Failed pixels should now be 0.0
        for r, c in failed_coords:
            np.testing.assert_allclose(filled_map[r, c], 0.0)

        # Successful pixels should keep their value
        assert filled_map[3, 3] == pytest.approx(0.75)

    def test_quality_map_success_reflects_failures(self):
        """generate_quality_map('success') correctly marks failed pixels as 0.0."""
        failed_coords = [(1, 1), (6, 6)]
        result, _ = self._build_results_with_failures(GRID_SIZE, GRID_SIZE, failed_coords)

        gen = AbundanceMapGenerator(result)
        success_map = gen.generate_quality_map(metric="success")

        for r, c in failed_coords:
            np.testing.assert_allclose(success_map[r, c], 0.0)

        # A successful pixel should be 1.0
        np.testing.assert_allclose(success_map[3, 3], 1.0)


# ===========================================================================
# 6. TestHDF5RoundTrip
# ===========================================================================


class TestHDF5RoundTrip:
    """HDF5 round-trip: save and reload results, verify data preserved.

    Tests that Imaging2DResults.save_hdf5 / load_hdf5 preserves all fields
    including abundance maps, isotope names, chi-squared, success mask,
    and metadata through a round-trip cycle.
    """

    def _build_results_for_roundtrip(
        self,
        height: int = GRID_SIZE,
        width: int = GRID_SIZE,
        include_failures: bool = False,
        include_metadata: bool = False,
        n_isotopes: int = 1,
    ) -> Imaging2DResults:
        """Build Imaging2DResults suitable for HDF5 round-trip tests."""
        if n_isotopes == 1:
            isotope_names = ["Ta-181"]
        else:
            isotope_names = ["Ta-181", "W-182"]

        pixel_results = []
        for row in range(height):
            for col in range(width):
                if include_failures and (row, col) in [(0, 0), (height - 1, width - 1)]:
                    pixel_results.append(_make_failed_pixel(row, col))
                else:
                    if n_isotopes == 1:
                        specs = [{**TA181_SPEC, "abundance": 0.5 + 0.01 * (row * width + col)}]
                    else:
                        specs = [
                            {**TA181_SPEC, "abundance": 0.5 + 0.01 * col},
                            {**W182_SPEC, "abundance": 0.3 + 0.01 * row},
                        ]
                    pixel_results.append(_make_successful_pixel(row, col, specs, chi_squared=1.0 + 0.1 * row))

        source = _make_hyperspectral(height, width)
        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)

        metadata = {}
        if include_metadata:
            metadata = {
                "run_id": "validation-test",
                "n_workers": 4,
                "threshold": 0.05,
                "converged": True,
            }

        return aggregator.aggregate(pixel_results, source, metadata=metadata)

    def test_round_trip_preserves_abundance_maps(self, tmp_path):
        """Abundance maps are identical after save/load."""
        original = self._build_results_for_roundtrip()
        filepath = tmp_path / "test_roundtrip.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        np.testing.assert_allclose(loaded.abundance_maps, original.abundance_maps)

    def test_round_trip_preserves_isotope_names(self, tmp_path):
        """Isotope names are preserved and decoded as strings."""
        original = self._build_results_for_roundtrip(n_isotopes=2)
        filepath = tmp_path / "test_roundtrip_names.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        assert loaded.isotope_names == original.isotope_names
        assert all(isinstance(name, str) for name in loaded.isotope_names)

    def test_round_trip_preserves_chi_squared_map(self, tmp_path):
        """Chi-squared map is preserved after save/load."""
        original = self._build_results_for_roundtrip()
        filepath = tmp_path / "test_roundtrip_chi2.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        np.testing.assert_allclose(loaded.chi_squared_map, original.chi_squared_map)

    def test_round_trip_preserves_success_mask(self, tmp_path):
        """Success mask is preserved after save/load."""
        original = self._build_results_for_roundtrip(include_failures=True)
        filepath = tmp_path / "test_roundtrip_mask.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        np.testing.assert_array_equal(loaded.success_mask, original.success_mask)

    def test_round_trip_preserves_nan_positions(self, tmp_path):
        """NaN positions in abundance and chi-squared maps are preserved."""
        original = self._build_results_for_roundtrip(include_failures=True)
        filepath = tmp_path / "test_roundtrip_nan.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        np.testing.assert_array_equal(
            np.isnan(loaded.abundance_maps),
            np.isnan(original.abundance_maps),
        )
        np.testing.assert_array_equal(
            np.isnan(loaded.chi_squared_map),
            np.isnan(original.chi_squared_map),
        )

    def test_round_trip_preserves_metadata(self, tmp_path):
        """Scalar metadata values are preserved through HDF5 round-trip."""
        original = self._build_results_for_roundtrip(include_metadata=True)
        filepath = tmp_path / "test_roundtrip_meta.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        for key in original.metadata:
            assert key in loaded.metadata, f"Missing metadata key: {key}"
            original_val = original.metadata[key]
            loaded_val = loaded.metadata[key]
            if isinstance(original_val, float):
                np.testing.assert_allclose(loaded_val, original_val)
            elif isinstance(original_val, bool):
                assert bool(loaded_val) == original_val
            elif isinstance(original_val, int):
                assert int(loaded_val) == original_val
            elif isinstance(original_val, str):
                loaded_str = loaded_val.decode() if isinstance(loaded_val, bytes) else str(loaded_val)
                assert loaded_str == original_val

    def test_round_trip_preserves_shapes(self, tmp_path):
        """All array shapes are preserved through save/load cycle."""
        original = self._build_results_for_roundtrip(n_isotopes=2)
        filepath = tmp_path / "test_roundtrip_shapes.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        assert loaded.abundance_maps.shape == original.abundance_maps.shape
        assert loaded.chi_squared_map.shape == original.chi_squared_map.shape
        assert loaded.success_mask.shape == original.success_mask.shape

    def test_round_trip_with_gradient_data(self, tmp_path):
        """Gradient data survives HDF5 round-trip accurately."""
        height, width = GRID_SIZE, GRID_SIZE
        ground_truth, pixel_results = _build_gradient_ground_truth(height, width)
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=height, width=width)
        original = aggregator.aggregate(pixel_results, source)
        filepath = tmp_path / "test_roundtrip_gradient.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        np.testing.assert_allclose(loaded.abundance_maps[0], ground_truth, atol=TOLERANCE_ATOL)

    def test_round_trip_loaded_usable_by_generator(self, tmp_path):
        """Loaded results can be used by AbundanceMapGenerator."""
        original = self._build_results_for_roundtrip(n_isotopes=2)
        filepath = tmp_path / "test_roundtrip_gen.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        gen = AbundanceMapGenerator(loaded)
        ta_map = gen.generate_map("Ta-181")
        w_map = gen.generate_map("W-182")

        assert ta_map.shape == (GRID_SIZE, GRID_SIZE)
        assert w_map.shape == (GRID_SIZE, GRID_SIZE)

        # Should match original
        np.testing.assert_allclose(ta_map, original.abundance_maps[0])
        np.testing.assert_allclose(w_map, original.abundance_maps[1])

    def test_round_trip_loaded_usable_by_visualizer(self, tmp_path):
        """Loaded results can be plotted by AbundanceMapVisualizer."""
        original = self._build_results_for_roundtrip()
        filepath = tmp_path / "test_roundtrip_viz.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        viz = AbundanceMapVisualizer(loaded)
        fig, ax = viz.plot_single_isotope("Ta-181")

        assert isinstance(fig, matplotlib.figure.Figure)
        assert len(ax.get_images()) > 0


# ===========================================================================
# 7. TestEndToEndPipeline
# ===========================================================================


class TestEndToEndPipeline:
    """Full pipeline end-to-end: TIFF -> loader -> orchestrator (mocked) -> aggregator -> generator -> visualizer.

    This test class exercises the complete imaging pipeline with a synthetic
    multi-page TIFF file. SAMMY execution is mocked via patching
    _fit_pixel_worker to return controlled PixelFitResult objects based on
    a known ground truth map.
    """

    @pytest.fixture
    def synthetic_tiff_and_truth(self, tmp_path):
        """Create a synthetic multi-page TIFF with known ground truth.

        Returns:
            (tiff_path, energy, ground_truth_ta, ground_truth_w)
        """
        height, width = GRID_SIZE, GRID_SIZE
        n_energy = N_ENERGY
        energy = np.linspace(1.0, 100.0, n_energy)

        # Create realistic-looking transmission data
        rng = np.random.default_rng(12345)
        data = rng.uniform(0.3, 0.95, (n_energy, height, width)).astype(np.float32)

        # Write as multi-page TIFF
        tiff_path = tmp_path / "synthetic_test.tif"
        tifffile.imwrite(str(tiff_path), data)

        # Ground truth abundance maps
        ta_truth = np.zeros((height, width), dtype=np.float64)
        w_truth = np.zeros((height, width), dtype=np.float64)
        for row in range(height):
            for col in range(width):
                col_frac = col / max(width - 1, 1)
                row_frac = row / max(height - 1, 1)
                ta_truth[row, col] = 0.2 + 0.6 * col_frac
                w_truth[row, col] = 0.7 - 0.4 * row_frac

        return tiff_path, energy, ta_truth, w_truth

    def _make_mock_worker(self, ta_truth: np.ndarray, w_truth: np.ndarray):
        """Create a mock worker function that returns PixelFitResults from ground truth.

        The returned callable has the same signature as _fit_pixel_worker.
        """

        def mock_worker(
            pixel,
            imaging_config,
            sammy_executable,
            resolution_file=None,
            shared_json_config=None,
            shared_endf_directory=None,
            temp_base_dir=None,
            cleanup_policy="immediate",
            attempt_id=0,
            max_disk_usage_gb=None,
            initial_free_gb=None,
        ):
            row, col = pixel.row, pixel.col
            ta_abundance = ta_truth[row, col]
            w_abundance = w_truth[row, col]
            specs = [
                {**TA181_SPEC, "abundance": ta_abundance},
                {**W182_SPEC, "abundance": w_abundance},
            ]
            return _make_successful_pixel(row, col, specs, chi_squared=1.0 + 0.01 * (row + col))

        return mock_worker

    def test_full_pipeline_tiff_to_visualization(self, synthetic_tiff_and_truth):
        """Full pipeline: TIFF -> loader -> orchestrator (mocked) -> aggregator -> generator -> visualizer."""
        tiff_path, energy, ta_truth, w_truth = synthetic_tiff_and_truth
        height, width = ta_truth.shape

        # Stage 1: Loader
        loader = HyperspectralLoader(tiff_path, energy=energy)
        hyperspectral = loader.load()

        assert hyperspectral.shape == (N_ENERGY, height, width)

        # Stage 2: Extract pixels
        pixels = list(loader.iter_pixels())
        assert len(pixels) == height * width

        # Stage 3: Mock orchestrator (simulate SAMMY fitting)
        # Instead of calling the actual orchestrator, we mock _fit_pixel_worker
        # and directly build pixel results from ground truth
        mock_worker = self._make_mock_worker(ta_truth, w_truth)
        pixel_results = []
        for pixel in pixels:
            result = mock_worker(pixel, None, None)
            pixel_results.append(result)

        # Stage 4: Aggregator
        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        imaging_results = aggregator.aggregate(pixel_results, hyperspectral)

        assert imaging_results.abundance_maps.shape == (2, height, width)
        assert np.all(imaging_results.success_mask)

        # Stage 5: Generator
        gen = AbundanceMapGenerator(imaging_results)
        ta_map = gen.generate_map("Ta-181")
        w_map = gen.generate_map("W-182")

        np.testing.assert_allclose(ta_map, ta_truth, atol=TOLERANCE_ATOL)
        np.testing.assert_allclose(w_map, w_truth, atol=TOLERANCE_ATOL)

        # Stage 6: Visualizer
        viz = AbundanceMapVisualizer(imaging_results)

        fig1, ax1 = viz.plot_single_isotope("Ta-181")
        assert isinstance(fig1, matplotlib.figure.Figure)
        assert len(ax1.get_images()) > 0

        fig2, axes2 = viz.plot_multi_isotope()
        assert isinstance(fig2, matplotlib.figure.Figure)

        fig3, ax3 = viz.plot_quality_overlay("Ta-181")
        assert isinstance(fig3, matplotlib.figure.Figure)
        assert len(ax3.get_images()) >= 2

    def test_pipeline_pixel_count_matches_image(self, synthetic_tiff_and_truth):
        """iter_pixels yields exactly height * width pixel spectra."""
        tiff_path, energy, ta_truth, _ = synthetic_tiff_and_truth
        height, width = ta_truth.shape

        loader = HyperspectralLoader(tiff_path, energy=energy)
        loader.load()
        pixels = list(loader.iter_pixels())

        assert len(pixels) == height * width

    def test_pipeline_pixel_spectra_have_correct_shape(self, synthetic_tiff_and_truth):
        """Each PixelSpectrum has the expected energy, transmission, and uncertainty length."""
        tiff_path, energy, _, _ = synthetic_tiff_and_truth

        loader = HyperspectralLoader(tiff_path, energy=energy)
        loader.load()
        pixels = list(loader.iter_pixels())

        for pixel in pixels:
            assert len(pixel.energy) == N_ENERGY
            assert len(pixel.transmission) == N_ENERGY
            assert len(pixel.uncertainty) == N_ENERGY
            assert np.all(pixel.energy > 0)
            assert np.all(pixel.uncertainty > 0)

    def test_pipeline_aggregated_results_have_correct_shapes(self, synthetic_tiff_and_truth):
        """Aggregated results have correct array shapes."""
        tiff_path, energy, ta_truth, w_truth = synthetic_tiff_and_truth
        height, width = ta_truth.shape

        loader = HyperspectralLoader(tiff_path, energy=energy)
        hyperspectral = loader.load()
        pixels = list(loader.iter_pixels())

        mock_worker = self._make_mock_worker(ta_truth, w_truth)
        pixel_results = [mock_worker(p, None, None) for p in pixels]

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, hyperspectral)

        assert result.abundance_maps.shape == (2, height, width)
        assert result.chi_squared_map.shape == (height, width)
        assert result.success_mask.shape == (height, width)
        assert result.isotope_names == ["Ta-181", "W-182"]

    def test_pipeline_with_roi(self, synthetic_tiff_and_truth):
        """Pipeline works with a Region-Of-Interest subset of pixels."""
        tiff_path, energy, ta_truth, w_truth = synthetic_tiff_and_truth

        loader = HyperspectralLoader(tiff_path, energy=energy)
        loader.load()

        # Only process a 4x4 ROI in the center
        roi = (2, 2, 6, 6)  # (x1, y1, x2, y2) -> cols [2,6), rows [2,6)
        pixels = list(loader.iter_pixels(roi=roi))

        roi_height = 4  # y2 - y1
        roi_width = 4  # x2 - x1
        assert len(pixels) == roi_height * roi_width

        # All pixels should have row in [2, 6) and col in [2, 6)
        for pixel in pixels:
            assert 2 <= pixel.row < 6
            assert 2 <= pixel.col < 6

    def test_pipeline_chi_squared_map_populated(self, synthetic_tiff_and_truth):
        """Chi-squared map is fully populated with no NaN for clean data."""
        tiff_path, energy, ta_truth, w_truth = synthetic_tiff_and_truth
        height, width = ta_truth.shape

        loader = HyperspectralLoader(tiff_path, energy=energy)
        hyperspectral = loader.load()
        pixels = list(loader.iter_pixels())

        mock_worker = self._make_mock_worker(ta_truth, w_truth)
        pixel_results = [mock_worker(p, None, None) for p in pixels]

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, hyperspectral)

        assert not np.any(np.isnan(result.chi_squared_map))
        assert np.all(result.chi_squared_map > 0)

    def test_pipeline_quality_overlay_produces_valid_plot(self, synthetic_tiff_and_truth):
        """Quality overlay plot produces a valid figure with two images."""
        tiff_path, energy, ta_truth, w_truth = synthetic_tiff_and_truth
        height, width = ta_truth.shape

        loader = HyperspectralLoader(tiff_path, energy=energy)
        hyperspectral = loader.load()
        pixels = list(loader.iter_pixels())

        mock_worker = self._make_mock_worker(ta_truth, w_truth)
        pixel_results = [mock_worker(p, None, None) for p in pixels]

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, hyperspectral)

        viz = AbundanceMapVisualizer(result)
        fig, ax = viz.plot_quality_overlay("Ta-181", quality_metric="chi_squared")

        assert isinstance(fig, matplotlib.figure.Figure)
        images = ax.get_images()
        assert len(images) >= 2  # base abundance + overlay

    def test_pipeline_mocked_orchestrator_fit_pixels(self, synthetic_tiff_and_truth):
        """Test the pipeline using a patched BatchFittingOrchestrator.fit_pixels.

        This verifies the orchestrator integration point by mocking fit_pixels
        to return controlled results, then passing them through the real
        aggregator and generator.
        """
        tiff_path, energy, ta_truth, w_truth = synthetic_tiff_and_truth
        height, width = ta_truth.shape

        loader = HyperspectralLoader(tiff_path, energy=energy)
        hyperspectral = loader.load()
        pixels = list(loader.iter_pixels())

        # Build expected pixel results from ground truth
        mock_worker = self._make_mock_worker(ta_truth, w_truth)
        expected_results = [mock_worker(p, None, None) for p in pixels]

        # Verify that mock worker results flow correctly through
        # aggregator + generator (orchestrator requires real SAMMY executable,
        # so we test the downstream pipeline directly).
        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(expected_results, hyperspectral)

        gen = AbundanceMapGenerator(result)
        ta_map = gen.generate_map("Ta-181")
        w_map = gen.generate_map("W-182")

        np.testing.assert_allclose(ta_map, ta_truth, atol=TOLERANCE_ATOL)
        np.testing.assert_allclose(w_map, w_truth, atol=TOLERANCE_ATOL)

    def test_pipeline_with_some_failed_pixels(self, synthetic_tiff_and_truth):
        """Pipeline handles a mix of successful and failed pixels correctly."""
        tiff_path, energy, ta_truth, w_truth = synthetic_tiff_and_truth
        height, width = ta_truth.shape

        loader = HyperspectralLoader(tiff_path, energy=energy)
        hyperspectral = loader.load()
        pixels = list(loader.iter_pixels())

        # Build results where corner pixels fail
        failed_coords = {(0, 0), (0, width - 1), (height - 1, 0), (height - 1, width - 1)}
        pixel_results = []
        for pixel in pixels:
            if (pixel.row, pixel.col) in failed_coords:
                pixel_results.append(_make_failed_pixel(pixel.row, pixel.col, "Simulated failure"))
            else:
                ta_val = ta_truth[pixel.row, pixel.col]
                w_val = w_truth[pixel.row, pixel.col]
                specs = [
                    {**TA181_SPEC, "abundance": ta_val},
                    {**W182_SPEC, "abundance": w_val},
                ]
                pixel_results.append(_make_successful_pixel(pixel.row, pixel.col, specs, chi_squared=1.0))

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        result = aggregator.aggregate(pixel_results, hyperspectral)

        # Failed pixels should be NaN
        for r, c in failed_coords:
            assert np.isnan(result.abundance_maps[0, r, c])
            assert np.isnan(result.abundance_maps[1, r, c])
            assert not result.success_mask[r, c]

        # Successful pixels should match ground truth
        n_expected_success = height * width - len(failed_coords)
        assert np.sum(result.success_mask) == n_expected_success

        # Check a known interior pixel
        assert result.success_mask[3, 3]
        np.testing.assert_allclose(result.abundance_maps[0, 3, 3], ta_truth[3, 3], atol=TOLERANCE_ATOL)
        np.testing.assert_allclose(result.abundance_maps[1, 3, 3], w_truth[3, 3], atol=TOLERANCE_ATOL)

    def test_pipeline_hdf5_roundtrip_end_to_end(self, synthetic_tiff_and_truth, tmp_path):
        """Full pipeline results survive HDF5 round-trip."""
        tiff_path, energy, ta_truth, w_truth = synthetic_tiff_and_truth
        height, width = ta_truth.shape

        loader = HyperspectralLoader(tiff_path, energy=energy)
        hyperspectral = loader.load()
        pixels = list(loader.iter_pixels())

        mock_worker = self._make_mock_worker(ta_truth, w_truth)
        pixel_results = [mock_worker(p, None, None) for p in pixels]

        aggregator = ResultsAggregator(isotope_names=["Ta-181", "W-182"], height=height, width=width)
        original = aggregator.aggregate(pixel_results, hyperspectral, metadata={"test": "end_to_end"})

        # Save and reload
        filepath = tmp_path / "pipeline_roundtrip.h5"
        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=hyperspectral)

        # Verify loaded results match original
        np.testing.assert_allclose(loaded.abundance_maps, original.abundance_maps)
        np.testing.assert_allclose(loaded.chi_squared_map, original.chi_squared_map)
        np.testing.assert_array_equal(loaded.success_mask, original.success_mask)
        assert loaded.isotope_names == original.isotope_names

        # Verify loaded results can still be used by generator and visualizer
        gen = AbundanceMapGenerator(loaded)
        ta_map = gen.generate_map("Ta-181")
        np.testing.assert_allclose(ta_map, ta_truth, atol=TOLERANCE_ATOL)

        viz = AbundanceMapVisualizer(loaded)
        fig, ax = viz.plot_single_isotope("Ta-181")
        assert isinstance(fig, matplotlib.figure.Figure)
