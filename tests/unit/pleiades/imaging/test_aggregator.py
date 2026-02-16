"""Unit tests for ResultsAggregator and Imaging2DResults.load_hdf5.

These tests are written BEFORE implementation (TDD). They exercise:
  - ResultsAggregator: aggregating per-pixel SAMMY fit results into 2D maps
  - Imaging2DResults.load_hdf5: round-trip HDF5 persistence

Tests use real PLEIADES model classes (not mocks) wherever feasible.
"""

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pytest

from pleiades.imaging.aggregator import ResultsAggregator
from pleiades.imaging.models import HyperspectralData, Imaging2DResults, PixelFitResult
from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
from pleiades.nuclear.models import IsotopeParameters, nuclearParameters
from pleiades.sammy.results.models import FitResults

# ---------------------------------------------------------------------------
# Helper utilities for building realistic test fixtures
# ---------------------------------------------------------------------------


def _make_isotope_info(name: str, atomic_number: int, mass_number: int, atomic_mass: float, spin: float) -> IsotopeInfo:
    """Build a minimal IsotopeInfo with required fields."""
    return IsotopeInfo(
        name=name,
        atomic_number=atomic_number,
        mass_number=mass_number,
        mass_data=IsotopeMassData(atomic_mass=atomic_mass),
        spin=spin,
    )


def _make_isotope_params(
    name: str, atomic_number: int, mass_number: int, atomic_mass: float, spin: float, abundance: float
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
        isotope_specs: List of dicts, each with keys:
            name, atomic_number, mass_number, atomic_mass, spin, abundance

    Returns:
        FitResults with nuclear_data containing the requested isotopes.
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
    """Build a successful PixelFitResult with real model objects.

    Args:
        row: Pixel row coordinate.
        col: Pixel column coordinate.
        isotope_specs: Isotope specifications (see _make_fit_results).
        chi_squared: Chi-squared value for the fit.

    Returns:
        PixelFitResult with success=True and populated fit_results.
    """
    fit_results = _make_fit_results(isotope_specs)
    return PixelFitResult(
        row=row,
        col=col,
        fit_results=fit_results,
        success=True,
        chi_squared=chi_squared,
    )


def _make_failed_pixel(row: int, col: int, error_message: str = "Fit diverged") -> PixelFitResult:
    """Build a failed PixelFitResult."""
    return PixelFitResult(
        row=row,
        col=col,
        fit_results=None,
        success=False,
        error_message=error_message,
    )


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
    data = rng.uniform(0.3, 0.95, (n_energy, height, width))
    energy = np.linspace(1.0, 100.0, n_energy)
    return HyperspectralData(
        data=data,
        energy=energy,
        source_file=Path("/tmp/test_source.tif"),
    )


# Standard isotope specs reusable across many tests
SINGLE_ISOTOPE_SPECS = [
    {"name": "Ta-181", "atomic_number": 73, "mass_number": 181, "atomic_mass": 180.948, "spin": 3.5, "abundance": 0.95},
]

TWO_ISOTOPE_SPECS = [
    {"name": "Ta-181", "atomic_number": 73, "mass_number": 181, "atomic_mass": 180.948, "spin": 3.5, "abundance": 0.60},
    {"name": "W-182", "atomic_number": 74, "mass_number": 182, "atomic_mass": 181.948, "spin": 0.0, "abundance": 0.40},
]

THREE_ISOTOPE_SPECS = [
    {"name": "Ta-181", "atomic_number": 73, "mass_number": 181, "atomic_mass": 180.948, "spin": 3.5, "abundance": 0.50},
    {"name": "W-182", "atomic_number": 74, "mass_number": 182, "atomic_mass": 181.948, "spin": 0.0, "abundance": 0.30},
    {"name": "W-184", "atomic_number": 74, "mass_number": 184, "atomic_mass": 183.951, "spin": 0.0, "abundance": 0.20},
]


# ===========================================================================
# TestResultsAggregator
# ===========================================================================


class TestResultsAggregator:
    """Tests for ResultsAggregator.aggregate()."""

    # -----------------------------------------------------------------------
    # 1. Happy path: all pixels successful, single isotope
    # -----------------------------------------------------------------------
    def test_all_pixels_successful_single_isotope(self):
        """All pixels succeed with one isotope -- maps should be fully populated."""
        height, width = 3, 4
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = []
        for r in range(height):
            for c in range(width):
                specs = [
                    {**SINGLE_ISOTOPE_SPECS[0], "abundance": 0.90 + 0.001 * (r * width + c)},
                ]
                pixel_results.append(_make_successful_pixel(r, c, specs, chi_squared=1.0 + 0.1 * (r * width + c)))

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert isinstance(result, Imaging2DResults)
        assert result.abundance_maps.shape == (1, height, width)
        assert result.chi_squared_map.shape == (height, width)
        assert result.success_mask.shape == (height, width)
        # Every pixel should be successful
        assert np.all(result.success_mask)
        # No NaNs in abundance or chi-squared
        assert not np.any(np.isnan(result.abundance_maps))
        assert not np.any(np.isnan(result.chi_squared_map))
        assert result.isotope_names == ["Ta-181"]

    # -----------------------------------------------------------------------
    # 2. Happy path: all pixels successful, multiple isotopes (2)
    # -----------------------------------------------------------------------
    def test_all_pixels_successful_two_isotopes(self):
        """All pixels succeed with two isotopes -- abundance_maps has shape (2, H, W)."""
        height, width = 2, 3
        isotope_names = ["Ta-181", "W-182"]
        source = _make_hyperspectral(height, width)

        pixel_results = []
        for r in range(height):
            for c in range(width):
                specs = [
                    {**TWO_ISOTOPE_SPECS[0], "abundance": 0.6},
                    {**TWO_ISOTOPE_SPECS[1], "abundance": 0.4},
                ]
                pixel_results.append(_make_successful_pixel(r, c, specs, chi_squared=1.5))

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert result.abundance_maps.shape == (2, height, width)
        assert result.isotope_names == ["Ta-181", "W-182"]
        # All pixels succeeded
        assert np.all(result.success_mask)
        # First isotope layer should all be 0.6
        np.testing.assert_allclose(result.abundance_maps[0], 0.6)
        # Second isotope layer should all be 0.4
        np.testing.assert_allclose(result.abundance_maps[1], 0.4)

    # -----------------------------------------------------------------------
    # 3. Happy path: all pixels successful, three isotopes
    # -----------------------------------------------------------------------
    def test_all_pixels_successful_three_isotopes(self):
        """All pixels succeed with three isotopes."""
        height, width = 2, 2
        isotope_names = ["Ta-181", "W-182", "W-184"]
        source = _make_hyperspectral(height, width)

        pixel_results = []
        for r in range(height):
            for c in range(width):
                pixel_results.append(_make_successful_pixel(r, c, THREE_ISOTOPE_SPECS, chi_squared=2.0))

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert result.abundance_maps.shape == (3, height, width)
        np.testing.assert_allclose(result.abundance_maps[0], 0.50)
        np.testing.assert_allclose(result.abundance_maps[1], 0.30)
        np.testing.assert_allclose(result.abundance_maps[2], 0.20)

    # -----------------------------------------------------------------------
    # 4. Mixed results: some pixels failed, some succeeded
    # -----------------------------------------------------------------------
    def test_mixed_success_and_failure(self):
        """Mixed success/failure -- failed pixels get NaN, success_mask reflects correctly."""
        height, width = 2, 2
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_successful_pixel(0, 0, SINGLE_ISOTOPE_SPECS, chi_squared=1.0),
            _make_failed_pixel(0, 1, error_message="Diverged"),
            _make_successful_pixel(1, 0, SINGLE_ISOTOPE_SPECS, chi_squared=2.0),
            _make_failed_pixel(1, 1, error_message="Timeout"),
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        # Success mask should be True/False in the correct positions
        assert result.success_mask[0, 0] is np.True_
        assert result.success_mask[0, 1] is np.False_
        assert result.success_mask[1, 0] is np.True_
        assert result.success_mask[1, 1] is np.False_

        # Failed pixels should have NaN abundance
        assert np.isnan(result.abundance_maps[0, 0, 1])
        assert np.isnan(result.abundance_maps[0, 1, 1])

        # Succeeded pixels should have the expected abundance
        assert not np.isnan(result.abundance_maps[0, 0, 0])
        assert not np.isnan(result.abundance_maps[0, 1, 0])

        # Failed pixels should have NaN chi-squared
        assert np.isnan(result.chi_squared_map[0, 1])
        assert np.isnan(result.chi_squared_map[1, 1])

        # Succeeded pixels should have correct chi-squared
        np.testing.assert_allclose(result.chi_squared_map[0, 0], 1.0)
        np.testing.assert_allclose(result.chi_squared_map[1, 0], 2.0)

    # -----------------------------------------------------------------------
    # 5. All failures
    # -----------------------------------------------------------------------
    def test_all_pixels_failed(self):
        """Every pixel failed -- all maps should be NaN, success_mask all False."""
        height, width = 2, 3
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [_make_failed_pixel(r, c) for r in range(height) for c in range(width)]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert not np.any(result.success_mask)
        assert np.all(np.isnan(result.abundance_maps))
        assert np.all(np.isnan(result.chi_squared_map))

    # -----------------------------------------------------------------------
    # 6. Sparse results: only a subset of pixels provided
    # -----------------------------------------------------------------------
    def test_sparse_pixel_results(self):
        """Only some pixels provided -- unmentioned pixels should be NaN/False."""
        height, width = 4, 4
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        # Only provide results for a few pixels
        pixel_results = [
            _make_successful_pixel(0, 0, SINGLE_ISOTOPE_SPECS, chi_squared=1.0),
            _make_successful_pixel(2, 3, SINGLE_ISOTOPE_SPECS, chi_squared=2.5),
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        # Provided pixels
        assert result.success_mask[0, 0]
        assert result.success_mask[2, 3]
        assert not np.isnan(result.abundance_maps[0, 0, 0])
        assert not np.isnan(result.abundance_maps[0, 2, 3])

        # Unprovided pixels should be NaN / False
        assert not result.success_mask[1, 1]
        assert np.isnan(result.abundance_maps[0, 1, 1])
        assert np.isnan(result.chi_squared_map[1, 1])

        # Total success count: 2
        assert np.sum(result.success_mask) == 2

    # -----------------------------------------------------------------------
    # 7. Edge case: single pixel image (1x1)
    # -----------------------------------------------------------------------
    def test_single_pixel_image(self):
        """1x1 image with one successful pixel."""
        height, width = 1, 1
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_successful_pixel(0, 0, SINGLE_ISOTOPE_SPECS, chi_squared=0.5),
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert result.abundance_maps.shape == (1, 1, 1)
        assert result.chi_squared_map.shape == (1, 1)
        assert result.success_mask.shape == (1, 1)
        assert result.success_mask[0, 0]
        np.testing.assert_allclose(result.chi_squared_map[0, 0], 0.5)

    # -----------------------------------------------------------------------
    # 8. Edge case: single row image
    # -----------------------------------------------------------------------
    def test_single_row_image(self):
        """Image with height=1, width=5."""
        height, width = 1, 5
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [_make_successful_pixel(0, c, SINGLE_ISOTOPE_SPECS, chi_squared=float(c)) for c in range(width)]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert result.abundance_maps.shape == (1, 1, 5)
        assert np.all(result.success_mask)
        for c in range(width):
            np.testing.assert_allclose(result.chi_squared_map[0, c], float(c))

    # -----------------------------------------------------------------------
    # 9. Edge case: single column image
    # -----------------------------------------------------------------------
    def test_single_column_image(self):
        """Image with height=5, width=1."""
        height, width = 5, 1
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_successful_pixel(r, 0, SINGLE_ISOTOPE_SPECS, chi_squared=float(r)) for r in range(height)
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert result.abundance_maps.shape == (1, 5, 1)
        assert np.all(result.success_mask)
        for r in range(height):
            np.testing.assert_allclose(result.chi_squared_map[r, 0], float(r))

    # -----------------------------------------------------------------------
    # 10. Validation: pixel coordinates out of bounds
    # -----------------------------------------------------------------------
    def test_pixel_row_out_of_bounds(self):
        """Pixel with row >= height should raise ValueError."""
        height, width = 3, 3
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_successful_pixel(5, 0, SINGLE_ISOTOPE_SPECS),  # row 5 > height 3
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        with pytest.raises(ValueError, match="[Oo]ut of bounds|[Cc]oordinate|[Rr]ow"):
            aggregator.aggregate(pixel_results, source)

    def test_pixel_col_out_of_bounds(self):
        """Pixel with col >= width should raise ValueError."""
        height, width = 3, 3
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_successful_pixel(0, 10, SINGLE_ISOTOPE_SPECS),  # col 10 > width 3
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        with pytest.raises(ValueError, match="[Oo]ut of bounds|[Cc]oordinate|[Cc]ol"):
            aggregator.aggregate(pixel_results, source)

    # -----------------------------------------------------------------------
    # 11. Validation: empty pixel_results list
    # -----------------------------------------------------------------------
    def test_empty_pixel_results(self):
        """Empty pixel_results list -- should produce all-NaN/False result without error."""
        height, width = 2, 2
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate([], source)

        assert isinstance(result, Imaging2DResults)
        assert not np.any(result.success_mask)
        assert np.all(np.isnan(result.abundance_maps))
        assert np.all(np.isnan(result.chi_squared_map))

    # -----------------------------------------------------------------------
    # 12. Validation: inconsistent isotope count across pixels
    # -----------------------------------------------------------------------
    def test_inconsistent_isotope_count_raises(self):
        """Pixel returning wrong number of abundances should raise ValueError."""
        height, width = 2, 2
        isotope_names = ["Ta-181", "W-182"]
        source = _make_hyperspectral(height, width)

        # First pixel has 2 isotopes (correct), second has 1 (wrong)
        pixel_results = [
            _make_successful_pixel(0, 0, TWO_ISOTOPE_SPECS, chi_squared=1.0),
            _make_successful_pixel(0, 1, SINGLE_ISOTOPE_SPECS, chi_squared=1.0),  # Only 1 isotope!
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        with pytest.raises(ValueError, match="[Ii]sotope|abundance|count|mismatch"):
            aggregator.aggregate(pixel_results, source)

    # -----------------------------------------------------------------------
    # 13. Correctness: verify specific abundance values at correct positions
    # -----------------------------------------------------------------------
    def test_abundance_values_at_correct_positions(self):
        """Verify that each pixel's abundance ends up at the correct (row, col) in the map."""
        height, width = 3, 3
        isotope_names = ["Ta-181", "W-182"]
        source = _make_hyperspectral(height, width)

        pixel_results = []
        expected_ta = np.full((height, width), np.nan)
        expected_w = np.full((height, width), np.nan)

        for r in range(height):
            for c in range(width):
                ta_abundance = 0.5 + 0.01 * (r * width + c)
                w_abundance = 0.3 + 0.01 * (r * width + c)
                specs = [
                    {**TWO_ISOTOPE_SPECS[0], "abundance": ta_abundance},
                    {**TWO_ISOTOPE_SPECS[1], "abundance": w_abundance},
                ]
                pixel_results.append(_make_successful_pixel(r, c, specs, chi_squared=1.0))
                expected_ta[r, c] = ta_abundance
                expected_w[r, c] = w_abundance

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        np.testing.assert_allclose(result.abundance_maps[0], expected_ta, atol=1e-10)
        np.testing.assert_allclose(result.abundance_maps[1], expected_w, atol=1e-10)

    # -----------------------------------------------------------------------
    # 14. Correctness: verify chi-squared values at correct positions
    # -----------------------------------------------------------------------
    def test_chi_squared_values_at_correct_positions(self):
        """Verify each pixel's chi-squared is placed at correct (row, col)."""
        height, width = 2, 3
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = []
        expected_chi2 = np.full((height, width), np.nan)

        for r in range(height):
            for c in range(width):
                chi2 = 1.0 + r + c * 0.5
                pixel_results.append(_make_successful_pixel(r, c, SINGLE_ISOTOPE_SPECS, chi_squared=chi2))
                expected_chi2[r, c] = chi2

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        np.testing.assert_allclose(result.chi_squared_map, expected_chi2, atol=1e-10)

    # -----------------------------------------------------------------------
    # 15. Correctness: verify success_mask matches pixel success flags
    # -----------------------------------------------------------------------
    def test_success_mask_matches_pixel_flags(self):
        """success_mask[r,c] should be True iff pixel at (r,c) has success=True."""
        height, width = 3, 3
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        # Checkerboard pattern: even (r+c) succeeds, odd (r+c) fails
        pixel_results = []
        expected_mask = np.zeros((height, width), dtype=bool)
        for r in range(height):
            for c in range(width):
                if (r + c) % 2 == 0:
                    pixel_results.append(_make_successful_pixel(r, c, SINGLE_ISOTOPE_SPECS, chi_squared=1.0))
                    expected_mask[r, c] = True
                else:
                    pixel_results.append(_make_failed_pixel(r, c))
                    expected_mask[r, c] = False

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        np.testing.assert_array_equal(result.success_mask, expected_mask)

    # -----------------------------------------------------------------------
    # 16. Metadata passthrough
    # -----------------------------------------------------------------------
    def test_metadata_passed_to_result(self):
        """Metadata dict is forwarded to Imaging2DResults."""
        height, width = 2, 2
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)
        metadata = {"run_id": "test-001", "n_workers": 4, "version": 1.0}

        pixel_results = [
            _make_successful_pixel(r, c, SINGLE_ISOTOPE_SPECS) for r in range(height) for c in range(width)
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source, metadata=metadata)

        assert result.metadata == metadata

    # -----------------------------------------------------------------------
    # 17. Pixel results are stored in the output
    # -----------------------------------------------------------------------
    def test_pixel_results_stored_in_output(self):
        """The original pixel_results list should be stored in the output."""
        height, width = 2, 2
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_successful_pixel(r, c, SINGLE_ISOTOPE_SPECS) for r in range(height) for c in range(width)
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        assert len(result.pixel_results) == len(pixel_results)

    # -----------------------------------------------------------------------
    # 18. Source hyperspectral is stored in the output
    # -----------------------------------------------------------------------
    def test_source_hyperspectral_stored(self):
        """The source HyperspectralData reference should be stored in the output."""
        height, width = 2, 2
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_successful_pixel(r, c, SINGLE_ISOTOPE_SPECS) for r in range(height) for c in range(width)
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        # The source_hyperspectral on the result should reference the same data
        np.testing.assert_array_equal(result.source_hyperspectral.energy, source.energy)
        assert result.source_hyperspectral.source_file == source.source_file

    # -----------------------------------------------------------------------
    # 19. Failed pixel with chi_squared=None produces NaN in chi_squared_map
    # -----------------------------------------------------------------------
    def test_failed_pixel_chi_squared_none_becomes_nan(self):
        """A failed pixel that has chi_squared=None should produce NaN in chi_squared_map."""
        height, width = 1, 2
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_successful_pixel(0, 0, SINGLE_ISOTOPE_SPECS, chi_squared=3.14),
            _make_failed_pixel(0, 1),
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        np.testing.assert_allclose(result.chi_squared_map[0, 0], 3.14)
        assert np.isnan(result.chi_squared_map[0, 1])


# ===========================================================================
# TestImaging2DResultsLoadHdf5
# ===========================================================================


class TestImaging2DResultsLoadHdf5:
    """Tests for Imaging2DResults.load_hdf5() round-trip with save_hdf5()."""

    def _make_imaging_results(
        self,
        height: int = 3,
        width: int = 4,
        n_isotopes: int = 2,
        include_fitted_energy_maps: bool = False,
        include_nan: bool = False,
        metadata: Optional[Dict] = None,
    ) -> Imaging2DResults:
        """Build an Imaging2DResults for save/load testing.

        Args:
            height: Image height.
            width: Image width.
            n_isotopes: Number of isotopes.
            include_fitted_energy_maps: Whether to populate fitted_energy_maps.
            include_nan: Whether to include NaN values in maps (simulating failures).
            metadata: Optional metadata dict.

        Returns:
            Imaging2DResults instance.
        """
        rng = np.random.default_rng(123)

        isotope_names = [f"Iso-{i}" for i in range(n_isotopes)]
        abundance_maps = rng.uniform(0.1, 0.9, (n_isotopes, height, width)).astype(np.float64)
        chi_squared_map = rng.uniform(0.5, 5.0, (height, width)).astype(np.float64)
        success_mask = np.ones((height, width), dtype=bool)

        if include_nan:
            # Set some pixels as failed
            abundance_maps[:, 0, 1] = np.nan
            abundance_maps[:, 1, 0] = np.nan
            chi_squared_map[0, 1] = np.nan
            chi_squared_map[1, 0] = np.nan
            success_mask[0, 1] = False
            success_mask[1, 0] = False

        n_energy = 10
        source = _make_hyperspectral(height, width, n_energy=n_energy)

        fitted_energy_maps = None
        if include_fitted_energy_maps:
            n_resonances = 5
            fitted_energy_maps = rng.uniform(1.0, 100.0, (n_resonances, height, width)).astype(np.float64)

        return Imaging2DResults(
            abundance_maps=abundance_maps,
            isotope_names=isotope_names,
            fitted_energy_maps=fitted_energy_maps,
            chi_squared_map=chi_squared_map,
            success_mask=success_mask,
            source_hyperspectral=source,
            metadata=metadata or {},
        )

    # -----------------------------------------------------------------------
    # 20. Round-trip: basic save and load
    # -----------------------------------------------------------------------
    def test_round_trip_basic(self, tmp_path):
        """save_hdf5 then load_hdf5 -- all core fields should match."""
        original = self._make_imaging_results()
        filepath = tmp_path / "results.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        assert isinstance(loaded, Imaging2DResults)
        np.testing.assert_allclose(loaded.abundance_maps, original.abundance_maps)
        np.testing.assert_allclose(loaded.chi_squared_map, original.chi_squared_map)
        np.testing.assert_array_equal(loaded.success_mask, original.success_mask)
        assert loaded.isotope_names == original.isotope_names

    # -----------------------------------------------------------------------
    # 21. Round-trip with NaN values (failed pixels)
    # -----------------------------------------------------------------------
    def test_round_trip_with_nan(self, tmp_path):
        """NaN values in abundance and chi-squared maps are preserved through save/load."""
        original = self._make_imaging_results(include_nan=True)
        filepath = tmp_path / "results_nan.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        # NaN positions should match
        np.testing.assert_array_equal(
            np.isnan(loaded.abundance_maps),
            np.isnan(original.abundance_maps),
        )
        np.testing.assert_array_equal(
            np.isnan(loaded.chi_squared_map),
            np.isnan(original.chi_squared_map),
        )
        # Non-NaN values should match
        valid_abundance = ~np.isnan(original.abundance_maps)
        np.testing.assert_allclose(
            loaded.abundance_maps[valid_abundance],
            original.abundance_maps[valid_abundance],
        )
        valid_chi2 = ~np.isnan(original.chi_squared_map)
        np.testing.assert_allclose(
            loaded.chi_squared_map[valid_chi2],
            original.chi_squared_map[valid_chi2],
        )
        # Success mask should be preserved
        np.testing.assert_array_equal(loaded.success_mask, original.success_mask)

    # -----------------------------------------------------------------------
    # 22. Round-trip with fitted_energy_maps present
    # -----------------------------------------------------------------------
    def test_round_trip_with_fitted_energy_maps(self, tmp_path):
        """fitted_energy_maps is saved and loaded correctly when present."""
        original = self._make_imaging_results(include_fitted_energy_maps=True)
        filepath = tmp_path / "results_energy.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        assert loaded.fitted_energy_maps is not None
        np.testing.assert_allclose(loaded.fitted_energy_maps, original.fitted_energy_maps)

    # -----------------------------------------------------------------------
    # 23. Round-trip without fitted_energy_maps
    # -----------------------------------------------------------------------
    def test_round_trip_without_fitted_energy_maps(self, tmp_path):
        """fitted_energy_maps=None -- should load as None."""
        original = self._make_imaging_results(include_fitted_energy_maps=False)
        filepath = tmp_path / "results_no_energy.h5"

        assert original.fitted_energy_maps is None

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        assert loaded.fitted_energy_maps is None

    # -----------------------------------------------------------------------
    # 24. Round-trip with metadata
    # -----------------------------------------------------------------------
    def test_round_trip_with_metadata(self, tmp_path):
        """Scalar metadata values (str, int, float, bool) are preserved."""
        metadata = {
            "run_id": "experiment-42",
            "n_workers": 8,
            "threshold": 0.05,
            "converged": True,
        }
        original = self._make_imaging_results(metadata=metadata)
        filepath = tmp_path / "results_meta.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        # Scalar metadata should be preserved (types may differ slightly due to HDF5 serialization)
        for key in metadata:
            assert key in loaded.metadata, f"Metadata key '{key}' missing after load"
            # Check values -- HDF5 may convert bool to numpy bool, etc.
            loaded_val = loaded.metadata[key]
            original_val = metadata[key]
            if isinstance(original_val, float):
                np.testing.assert_allclose(loaded_val, original_val)
            elif isinstance(original_val, bool):
                assert bool(loaded_val) == original_val
            elif isinstance(original_val, int):
                assert int(loaded_val) == original_val
            elif isinstance(original_val, str):
                # HDF5 may return bytes or str
                if isinstance(loaded_val, bytes):
                    assert loaded_val.decode() == original_val
                else:
                    assert str(loaded_val) == original_val

    # -----------------------------------------------------------------------
    # 25. File not found
    # -----------------------------------------------------------------------
    def test_file_not_found(self, tmp_path):
        """load_hdf5 with nonexistent file should raise appropriate error."""
        source = _make_hyperspectral(2, 2)
        nonexistent = tmp_path / "does_not_exist.h5"

        with pytest.raises((FileNotFoundError, OSError)):
            Imaging2DResults.load_hdf5(nonexistent, source_hyperspectral=source)

    # -----------------------------------------------------------------------
    # 26. Corrupt/invalid HDF5: missing required dataset
    # -----------------------------------------------------------------------
    def test_invalid_hdf5_missing_datasets(self, tmp_path):
        """HDF5 file missing required datasets should raise an error."""
        import h5py

        filepath = tmp_path / "corrupt.h5"
        source = _make_hyperspectral(2, 2)

        # Write an HDF5 file with only partial data (missing abundance_maps)
        with h5py.File(filepath, "w") as f:
            f.create_dataset("chi_squared_map", data=np.ones((2, 2)))
            f.create_dataset("success_mask", data=np.ones((2, 2), dtype=bool))
            f.create_dataset("energy", data=np.linspace(1, 100, 10))
            f.create_dataset("isotope_names", data=np.array(["Ta-181"], dtype="S"))
            # abundance_maps is intentionally missing

        with pytest.raises((KeyError, ValueError, OSError)):
            Imaging2DResults.load_hdf5(filepath, source_hyperspectral=source)

    # -----------------------------------------------------------------------
    # 27. Round-trip isotope names encoding
    # -----------------------------------------------------------------------
    def test_isotope_names_encoding_round_trip(self, tmp_path):
        """Isotope names stored as byte strings in HDF5 should decode back to str."""
        original = self._make_imaging_results(n_isotopes=3)
        filepath = tmp_path / "results_names.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        # Isotope names should be Python str, not bytes
        assert all(isinstance(name, str) for name in loaded.isotope_names)
        assert loaded.isotope_names == original.isotope_names

    # -----------------------------------------------------------------------
    # 28. Round-trip preserves shapes
    # -----------------------------------------------------------------------
    def test_round_trip_preserves_shapes(self, tmp_path):
        """All array shapes should be preserved through save/load cycle."""
        height, width = 5, 7
        n_isotopes = 3
        original = self._make_imaging_results(
            height=height, width=width, n_isotopes=n_isotopes, include_fitted_energy_maps=True
        )
        filepath = tmp_path / "results_shapes.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        assert loaded.abundance_maps.shape == (n_isotopes, height, width)
        assert loaded.chi_squared_map.shape == (height, width)
        assert loaded.success_mask.shape == (height, width)
        assert loaded.fitted_energy_maps.shape == original.fitted_energy_maps.shape

    # -----------------------------------------------------------------------
    # 29. Source hyperspectral is used (not loaded from HDF5)
    # -----------------------------------------------------------------------
    def test_source_hyperspectral_comes_from_argument(self, tmp_path):
        """load_hdf5 should use the provided source_hyperspectral, not reconstruct from HDF5."""
        original = self._make_imaging_results()
        filepath = tmp_path / "results_source.h5"
        original.save_hdf5(filepath)

        # Create a different source to verify it is used
        different_source = _make_hyperspectral(
            height=original.source_hyperspectral.shape[1],
            width=original.source_hyperspectral.shape[2],
            n_energy=original.source_hyperspectral.shape[0],
        )

        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=different_source)

        # The loaded result should have the provided source, not the original one
        np.testing.assert_array_equal(
            loaded.source_hyperspectral.data,
            different_source.data,
        )

    # -----------------------------------------------------------------------
    # 30. Round-trip with single isotope
    # -----------------------------------------------------------------------
    def test_round_trip_single_isotope(self, tmp_path):
        """Round-trip with a single isotope."""
        original = self._make_imaging_results(n_isotopes=1)
        filepath = tmp_path / "results_single_iso.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        assert loaded.abundance_maps.shape[0] == 1
        assert len(loaded.isotope_names) == 1
        np.testing.assert_allclose(loaded.abundance_maps, original.abundance_maps)

    # -----------------------------------------------------------------------
    # 31. Round-trip with empty metadata
    # -----------------------------------------------------------------------
    def test_round_trip_empty_metadata(self, tmp_path):
        """Empty metadata dict should survive round-trip."""
        original = self._make_imaging_results(metadata={})
        filepath = tmp_path / "results_empty_meta.h5"

        original.save_hdf5(filepath)
        loaded = Imaging2DResults.load_hdf5(filepath, source_hyperspectral=original.source_hyperspectral)

        assert loaded.metadata == {}


# ===========================================================================
# TestResultsAggregatorValidation
# ===========================================================================


class TestResultsAggregatorValidation:
    """Tests for ResultsAggregator constructor and duplicate-pixel validation."""

    def test_empty_isotope_names_raises(self):
        """Empty isotope_names list should raise ValueError."""
        with pytest.raises(ValueError, match="isotope_names must not be empty"):
            ResultsAggregator(isotope_names=[], height=2, width=2)

    def test_zero_height_raises(self):
        """height=0 should raise ValueError."""
        with pytest.raises(ValueError, match="height must be positive"):
            ResultsAggregator(isotope_names=["Ta-181"], height=0, width=2)

    def test_negative_height_raises(self):
        """Negative height should raise ValueError."""
        with pytest.raises(ValueError, match="height must be positive"):
            ResultsAggregator(isotope_names=["Ta-181"], height=-1, width=2)

    def test_zero_width_raises(self):
        """width=0 should raise ValueError."""
        with pytest.raises(ValueError, match="width must be positive"):
            ResultsAggregator(isotope_names=["Ta-181"], height=2, width=0)

    def test_negative_width_raises(self):
        """Negative width should raise ValueError."""
        with pytest.raises(ValueError, match="width must be positive"):
            ResultsAggregator(isotope_names=["Ta-181"], height=2, width=-3)

    def test_duplicate_pixel_raises(self):
        """Two pixel results at the same (row, col) should raise ValueError."""
        height, width = 3, 3
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_successful_pixel(1, 2, SINGLE_ISOTOPE_SPECS, chi_squared=1.0),
            _make_successful_pixel(1, 2, SINGLE_ISOTOPE_SPECS, chi_squared=2.0),  # duplicate!
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        with pytest.raises(ValueError, match="[Dd]uplicate.*\\(1, 2\\)"):
            aggregator.aggregate(pixel_results, source)

    def test_duplicate_failed_pixel_raises(self):
        """Even duplicated failed pixels should raise ValueError."""
        height, width = 2, 2
        isotope_names = ["Ta-181"]
        source = _make_hyperspectral(height, width)

        pixel_results = [
            _make_failed_pixel(0, 0, error_message="first"),
            _make_failed_pixel(0, 0, error_message="second"),  # duplicate!
        ]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        with pytest.raises(ValueError, match="[Dd]uplicate.*\\(0, 0\\)"):
            aggregator.aggregate(pixel_results, source)

    def test_reordered_isotopes_mapped_by_name(self):
        """Isotopes arriving in different order should be mapped to correct map layers."""
        height, width = 1, 1
        # Aggregator expects Ta-181 first, W-182 second
        isotope_names = ["Ta-181", "W-182"]
        source = _make_hyperspectral(height, width)

        # Build pixel with isotopes in REVERSED order: W-182 first, Ta-181 second
        reversed_specs = [
            {**TWO_ISOTOPE_SPECS[1], "abundance": 0.40},  # W-182
            {**TWO_ISOTOPE_SPECS[0], "abundance": 0.60},  # Ta-181
        ]
        pixel_results = [_make_successful_pixel(0, 0, reversed_specs, chi_squared=1.0)]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        result = aggregator.aggregate(pixel_results, source)

        # Ta-181 (index 0 in isotope_names) should have abundance 0.60
        np.testing.assert_allclose(result.abundance_maps[0, 0, 0], 0.60)
        # W-182 (index 1 in isotope_names) should have abundance 0.40
        np.testing.assert_allclose(result.abundance_maps[1, 0, 0], 0.40)

    def test_isotope_name_mismatch_raises(self):
        """Pixel with unexpected isotope name should raise ValueError."""
        height, width = 2, 2
        isotope_names = ["Ta-181", "W-182"]
        source = _make_hyperspectral(height, width)

        # Build pixel with Hf-180 instead of W-182
        wrong_specs = [
            {**TWO_ISOTOPE_SPECS[0], "abundance": 0.60},  # Ta-181 (correct)
            {
                "name": "Hf-180",
                "atomic_number": 72,
                "mass_number": 180,
                "atomic_mass": 179.947,
                "spin": 0.0,
                "abundance": 0.40,
            },
        ]
        pixel_results = [_make_successful_pixel(0, 0, wrong_specs, chi_squared=1.0)]

        aggregator = ResultsAggregator(isotope_names=isotope_names, height=height, width=width)
        with pytest.raises(ValueError, match="[Ii]sotope name mismatch"):
            aggregator.aggregate(pixel_results, source)
