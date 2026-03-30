"""Unit tests for AbundanceMapVisualizer.

These tests are written BEFORE implementation (TDD). They exercise the
AbundanceMapVisualizer class which produces matplotlib visualizations of
isotope abundance maps and quality overlays from an Imaging2DResults object.

Tests use the Agg backend to avoid requiring a display, and check figure
structure (axes, colorbars, titles, shapes) rather than pixel-level rendering.
"""

from pathlib import Path
from typing import List, Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest

# Force non-interactive backend before any other matplotlib imports
matplotlib.use("Agg")

from pleiades.imaging.models import HyperspectralData, Imaging2DResults  # noqa: E402
from pleiades.imaging.visualizer import AbundanceMapVisualizer  # noqa: E402

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


@pytest.fixture(autouse=True)
def close_figures_after_test():
    """Close all matplotlib figures after each test to prevent resource leaks."""
    yield
    plt.close("all")


@pytest.fixture
def two_isotope_results() -> Imaging2DResults:
    """Standard 4x4 image with two isotopes, all pixels successful."""
    return _make_imaging_results(height=4, width=4, isotope_names=["Ta-181", "W-182"])


@pytest.fixture
def single_isotope_results() -> Imaging2DResults:
    """Standard 4x4 image with a single isotope, all pixels successful."""
    return _make_imaging_results(height=4, width=4, isotope_names=["Ta-181"])


@pytest.fixture
def three_isotope_results() -> Imaging2DResults:
    """Standard 4x4 image with three isotopes, all pixels successful."""
    return _make_imaging_results(height=4, width=4, isotope_names=["Ta-181", "W-182", "W-184"])


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
def five_isotope_results() -> Imaging2DResults:
    """Standard 4x4 image with five isotopes for testing multi-isotope grid layout."""
    return _make_imaging_results(
        height=4,
        width=4,
        isotope_names=["Ta-181", "W-182", "W-184", "Hf-180", "Re-185"],
    )


# ===========================================================================
# TestAbundanceMapVisualizerInit
# ===========================================================================


class TestAbundanceMapVisualizerInit:
    """Tests for AbundanceMapVisualizer.__init__."""

    def test_init_stores_results(self, two_isotope_results: Imaging2DResults) -> None:
        """Constructor should not raise and should store results."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        assert viz is not None

    def test_init_with_single_isotope(self, single_isotope_results: Imaging2DResults) -> None:
        """Constructor should accept results with a single isotope."""
        viz = AbundanceMapVisualizer(single_isotope_results)
        assert viz is not None


# ===========================================================================
# TestPlotSingleIsotope
# ===========================================================================


class TestPlotSingleIsotope:
    """Tests for AbundanceMapVisualizer.plot_single_isotope()."""

    def test_returns_figure_and_axes(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_single_isotope should return a tuple of (Figure, Axes)."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        result = viz.plot_single_isotope("Ta-181")

        assert isinstance(result, tuple)
        assert len(result) == 2
        fig, ax = result
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_creates_figure_with_colorbar(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_single_isotope should create a figure with a colorbar by default."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_single_isotope("Ta-181")

        # A colorbar adds an extra axes to the figure
        # The figure should have more than 1 axes when colorbar is present
        assert len(fig.axes) > 1, "Expected colorbar axes in addition to the main axes"

    def test_without_colorbar(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_single_isotope(show_colorbar=False) should not add a colorbar."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_single_isotope("Ta-181", show_colorbar=False)

        # Without colorbar, figure should have exactly 1 axes
        assert len(fig.axes) == 1, "Expected only one axes when colorbar is disabled"

    def test_with_provided_axes(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_single_isotope should plot onto provided axes."""
        viz = AbundanceMapVisualizer(two_isotope_results)

        external_fig, external_ax = plt.subplots()
        fig, ax = viz.plot_single_isotope("Ta-181", ax=external_ax)

        # The returned axes should be the same as the one we provided
        assert ax is external_ax

    def test_with_custom_cmap(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_single_isotope should accept and use a custom colormap."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        # Should not raise with valid colormap
        fig, ax = viz.plot_single_isotope("Ta-181", cmap="plasma")
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_with_custom_vmin_vmax(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_single_isotope should accept custom vmin and vmax."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_single_isotope("Ta-181", vmin=0.0, vmax=1.0)

        # Verify the image has correct clim
        images = ax.get_images()
        assert len(images) > 0, "Expected at least one image in the axes"
        clim = images[0].get_clim()
        assert clim[0] == pytest.approx(0.0), f"Expected vmin=0.0, got {clim[0]}"
        assert clim[1] == pytest.approx(1.0), f"Expected vmax=1.0, got {clim[1]}"

    def test_with_only_vmin(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_single_isotope should accept only vmin (vmax auto-scaled)."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_single_isotope("Ta-181", vmin=0.0)

        images = ax.get_images()
        assert len(images) > 0
        clim = images[0].get_clim()
        assert clim[0] == pytest.approx(0.0)

    def test_with_only_vmax(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_single_isotope should accept only vmax (vmin auto-scaled)."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_single_isotope("Ta-181", vmax=1.0)

        images = ax.get_images()
        assert len(images) > 0
        clim = images[0].get_clim()
        assert clim[1] == pytest.approx(1.0)

    def test_unknown_isotope_raises_valueerror(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_single_isotope for an unknown isotope should raise ValueError."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        with pytest.raises(ValueError, match="(?i)isotope|not found|unknown"):
            viz.plot_single_isotope("Hf-180")

    def test_with_failures_does_not_raise(self, results_with_failures: Imaging2DResults) -> None:
        """plot_single_isotope should handle NaN values without raising."""
        viz = AbundanceMapVisualizer(results_with_failures)
        fig, ax = viz.plot_single_isotope("Ta-181")
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_axes_has_image(self, two_isotope_results: Imaging2DResults) -> None:
        """The returned axes should contain at least one image."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_single_isotope("Ta-181")
        assert len(ax.get_images()) > 0, "Expected at least one image in the axes"


# ===========================================================================
# TestPlotMultiIsotope
# ===========================================================================


class TestPlotMultiIsotope:
    """Tests for AbundanceMapVisualizer.plot_multi_isotope()."""

    def test_returns_figure_and_axes_array(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_multi_isotope should return a tuple of (Figure, ndarray of Axes)."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        result = viz.plot_multi_isotope()

        assert isinstance(result, tuple)
        assert len(result) == 2
        fig, axes = result
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axes, np.ndarray)

    def test_plots_all_isotopes_by_default(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_multi_isotope() with no args should plot all isotopes."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, axes = viz.plot_multi_isotope()

        # Should have at least 2 subplots (one per isotope)
        # There may be extra empty subplots depending on grid layout
        total_axes = axes.flatten()
        # At minimum, the number of axes with images should match the isotope count
        axes_with_images = [ax for ax in total_axes if len(ax.get_images()) > 0]
        assert len(axes_with_images) >= 2, "Expected at least 2 subplots with images"

    def test_with_subset_of_isotopes(self, three_isotope_results: Imaging2DResults) -> None:
        """plot_multi_isotope(isotopes=[...]) should plot only the specified isotopes."""
        viz = AbundanceMapVisualizer(three_isotope_results)
        fig, axes = viz.plot_multi_isotope(isotopes=["Ta-181", "W-184"])

        total_axes = axes.flatten()
        axes_with_images = [ax for ax in total_axes if len(ax.get_images()) > 0]
        assert len(axes_with_images) >= 2, "Expected at least 2 subplots with images"

    def test_single_isotope_works(self, single_isotope_results: Imaging2DResults) -> None:
        """plot_multi_isotope should work with a single isotope."""
        viz = AbundanceMapVisualizer(single_isotope_results)
        fig, axes = viz.plot_multi_isotope()

        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(axes, np.ndarray)

        total_axes = axes.flatten()
        axes_with_images = [ax for ax in total_axes if len(ax.get_images()) > 0]
        assert len(axes_with_images) >= 1, "Expected at least 1 subplot with an image"

    def test_with_custom_ncols(self, five_isotope_results: Imaging2DResults) -> None:
        """plot_multi_isotope(ncols=2) should create a grid with 2 columns."""
        viz = AbundanceMapVisualizer(five_isotope_results)
        fig, axes = viz.plot_multi_isotope(ncols=2)

        # With 5 isotopes and ncols=2, we need ceil(5/2) = 3 rows
        # axes shape should be (3, 2) or equivalent
        assert axes.size >= 5, "Expected at least 5 axes slots for 5 isotopes"

    def test_with_custom_figsize(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_multi_isotope(figsize=(12, 8)) should create a figure with the specified size."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, axes = viz.plot_multi_isotope(figsize=(12, 8))

        actual_size = fig.get_size_inches()
        np.testing.assert_allclose(actual_size, (12, 8), atol=0.1)

    def test_with_ncols_1(self, three_isotope_results: Imaging2DResults) -> None:
        """plot_multi_isotope(ncols=1) should create a single-column grid."""
        viz = AbundanceMapVisualizer(three_isotope_results)
        fig, axes = viz.plot_multi_isotope(ncols=1)

        # With 3 isotopes and ncols=1, we need 3 rows
        total_axes = axes.flatten()
        axes_with_images = [ax for ax in total_axes if len(ax.get_images()) > 0]
        assert len(axes_with_images) >= 3

    def test_unknown_isotope_in_list_raises(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_multi_isotope with unknown isotope in list should raise ValueError."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        with pytest.raises(ValueError, match="(?i)isotope|not found|unknown"):
            viz.plot_multi_isotope(isotopes=["Ta-181", "Hf-180"])

    def test_with_failures_does_not_raise(self, results_with_failures: Imaging2DResults) -> None:
        """plot_multi_isotope should handle NaN values without raising."""
        viz = AbundanceMapVisualizer(results_with_failures)
        fig, axes = viz.plot_multi_isotope()
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_each_subplot_has_image(self, three_isotope_results: Imaging2DResults) -> None:
        """Each isotope should get its own subplot with an image."""
        viz = AbundanceMapVisualizer(three_isotope_results)
        fig, axes = viz.plot_multi_isotope()

        total_axes = axes.flatten()
        axes_with_images = [ax for ax in total_axes if len(ax.get_images()) > 0]
        assert len(axes_with_images) == 3, "Expected exactly 3 subplots with images for 3 isotopes"


# ===========================================================================
# TestPlotQualityOverlay
# ===========================================================================


class TestPlotQualityOverlay:
    """Tests for AbundanceMapVisualizer.plot_quality_overlay()."""

    def test_returns_figure_and_axes(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_quality_overlay should return a tuple of (Figure, Axes)."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        result = viz.plot_quality_overlay("Ta-181")

        assert isinstance(result, tuple)
        assert len(result) == 2
        fig, ax = result
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(ax, matplotlib.axes.Axes)

    def test_default_quality_metric_chi_squared(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_quality_overlay should use chi_squared by default."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        # Should not raise -- the default metric should be valid
        fig, ax = viz.plot_quality_overlay("Ta-181")
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_with_success_metric(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_quality_overlay with quality_metric='success' should not raise."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_quality_overlay("Ta-181", quality_metric="success")
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_with_custom_alpha(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_quality_overlay with custom alpha should not raise."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_quality_overlay("Ta-181", alpha=0.3)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_has_images(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_quality_overlay should produce axes with at least two images (abundance + overlay)."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_quality_overlay("Ta-181")

        # The overlay plot should have at least 2 images:
        # one for the abundance map and one for the quality overlay
        images = ax.get_images()
        assert len(images) >= 2, f"Expected at least 2 images (base + overlay), got {len(images)}"

    def test_unknown_isotope_raises(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_quality_overlay for an unknown isotope should raise ValueError."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        with pytest.raises(ValueError, match="(?i)isotope|not found|unknown"):
            viz.plot_quality_overlay("Hf-180")

    def test_invalid_quality_metric_raises(self, two_isotope_results: Imaging2DResults) -> None:
        """plot_quality_overlay with invalid quality metric should raise ValueError."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        with pytest.raises(ValueError, match="(?i)metric|unsupported|unknown|invalid"):
            viz.plot_quality_overlay("Ta-181", quality_metric="r_squared")

    def test_with_failures_does_not_raise(self, results_with_failures: Imaging2DResults) -> None:
        """plot_quality_overlay should handle NaN values without raising."""
        viz = AbundanceMapVisualizer(results_with_failures)
        fig, ax = viz.plot_quality_overlay("Ta-181")
        assert isinstance(fig, matplotlib.figure.Figure)


# ===========================================================================
# TestResourceManagement
# ===========================================================================


class TestResourceManagement:
    """Tests to verify that figures can be properly closed and cleaned up."""

    def test_single_isotope_figure_can_be_closed(self, two_isotope_results: Imaging2DResults) -> None:
        """Closing a figure from plot_single_isotope should not raise."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_single_isotope("Ta-181")
        plt.close(fig)
        # If we get here without error, the figure was properly closeable

    def test_multi_isotope_figure_can_be_closed(self, two_isotope_results: Imaging2DResults) -> None:
        """Closing a figure from plot_multi_isotope should not raise."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, axes = viz.plot_multi_isotope()
        plt.close(fig)

    def test_quality_overlay_figure_can_be_closed(self, two_isotope_results: Imaging2DResults) -> None:
        """Closing a figure from plot_quality_overlay should not raise."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_quality_overlay("Ta-181")
        plt.close(fig)

    def test_close_all_figures(self, two_isotope_results: Imaging2DResults) -> None:
        """plt.close('all') should work after creating multiple figures."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        viz.plot_single_isotope("Ta-181")
        viz.plot_single_isotope("W-182")
        viz.plot_multi_isotope()
        viz.plot_quality_overlay("Ta-181")

        # Close all should not raise
        plt.close("all")

    def test_multiple_visualizers_do_not_conflict(self, two_isotope_results: Imaging2DResults) -> None:
        """Two visualizer instances should not interfere with each other."""
        viz1 = AbundanceMapVisualizer(two_isotope_results)
        viz2 = AbundanceMapVisualizer(two_isotope_results)

        fig1, ax1 = viz1.plot_single_isotope("Ta-181")
        fig2, ax2 = viz2.plot_single_isotope("W-182")

        # They should be different figure objects
        assert fig1 is not fig2


class TestUnitsParameter:
    """Tests for the units parameter (fraction, percent, ppm)."""

    def test_single_isotope_ppm_scales_values(self, two_isotope_results: Imaging2DResults) -> None:
        """PPM units should scale abundance values by 1e6."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig_frac, ax_frac = viz.plot_single_isotope("Ta-181", units="fraction")
        fig_ppm, ax_ppm = viz.plot_single_isotope("Ta-181", units="ppm")

        # Get image data from both plots
        data_frac = ax_frac.images[0].get_array()
        data_ppm = ax_ppm.images[0].get_array()

        np.testing.assert_allclose(data_ppm, data_frac * 1e6, rtol=1e-6)
        plt.close(fig_frac)
        plt.close(fig_ppm)

    def test_single_isotope_percent_scales_values(self, two_isotope_results: Imaging2DResults) -> None:
        """Percent units should scale abundance values by 100."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig_frac, ax_frac = viz.plot_single_isotope("Ta-181", units="fraction")
        fig_pct, ax_pct = viz.plot_single_isotope("Ta-181", units="percent")

        data_frac = ax_frac.images[0].get_array()
        data_pct = ax_pct.images[0].get_array()

        np.testing.assert_allclose(data_pct, data_frac * 100, rtol=1e-6)
        plt.close(fig_frac)
        plt.close(fig_pct)

    def test_single_isotope_invalid_units_raises(self, two_isotope_results: Imaging2DResults) -> None:
        """Invalid units should raise ValueError."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        with pytest.raises(ValueError, match="Unknown units"):
            viz.plot_single_isotope("Ta-181", units="invalid")

    def test_multi_isotope_ppm(self, two_isotope_results: Imaging2DResults) -> None:
        """Multi-isotope plot should accept units parameter."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, axes = viz.plot_multi_isotope(units="ppm")
        # Just verify it runs without error and produces a figure
        assert fig is not None
        plt.close(fig)

    def test_quality_overlay_ppm(self, two_isotope_results: Imaging2DResults) -> None:
        """Quality overlay should accept units parameter."""
        viz = AbundanceMapVisualizer(two_isotope_results)
        fig, ax = viz.plot_quality_overlay("Ta-181", units="ppm")
        assert fig is not None
        plt.close(fig)
