"""Visualization of isotope abundance maps from 2D imaging results.

This module provides the AbundanceMapVisualizer class which produces
matplotlib plots of isotope abundance maps, multi-isotope grids, and
quality overlay visualizations.
"""

from __future__ import annotations

import math
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from pleiades.imaging.generator import AbundanceMapGenerator
from pleiades.imaging.models import Imaging2DResults

#: Supported abundance display units.
AbundanceUnits = Literal["fraction", "percent", "ppm"]

#: Scale factors and colorbar labels for each unit.
_UNIT_CONFIG: dict[str, tuple[float, str]] = {
    "fraction": (1.0, "Abundance (fraction)"),
    "percent": (100.0, "Abundance (%)"),
    "ppm": (1e6, "Abundance (ppm)"),
}


class AbundanceMapVisualizer:
    """Visualize isotope abundance maps using matplotlib.

    Creates publication-quality plots of individual isotope maps, multi-isotope
    comparison grids, and quality metric overlays.

    Callers are responsible for closing returned figures (``plt.close(fig)``)
    to avoid memory leaks in batch processing loops.

    Args:
        results: Completed 2D imaging results.

    Example:
        >>> viz = AbundanceMapVisualizer(imaging_results)
        >>> fig, ax = viz.plot_single_isotope("Ta-181")
        >>> fig, axes = viz.plot_multi_isotope()
        >>> fig, ax = viz.plot_quality_overlay("Ta-181")
    """

    def __init__(self, results: Imaging2DResults) -> None:
        self._results = results
        self._generator = AbundanceMapGenerator(results)

    def plot_single_isotope(
        self,
        isotope: str,
        ax: Axes | None = None,
        cmap: str = "viridis",
        vmin: float | None = None,
        vmax: float | None = None,
        show_colorbar: bool = True,
        units: AbundanceUnits = "fraction",
    ) -> tuple[Figure, Axes]:
        """Plot the abundance map for a single isotope.

        Args:
            isotope: Isotope name (e.g. ``"Ta-181"``).
            ax: Matplotlib axes to plot on. If None, creates a new figure.
                Note: when providing an axes from a complex layout,
                ``fig.colorbar()`` may resize the axes.
            cmap: Colormap name.
            vmin: Minimum value for color scale. Auto-scaled if None.
            vmax: Maximum value for color scale. Auto-scaled if None.
            show_colorbar: Whether to add a colorbar.
            units: Display units for the abundance values.
                ``"fraction"`` (default, 0-1), ``"percent"`` (0-100),
                or ``"ppm"`` (0-1e6).

        Returns:
            Tuple of (Figure, Axes).

        Raises:
            ValueError: If isotope is not found in the results or units is invalid.
        """
        scale, label = _UNIT_CONFIG.get(units, (None, None))
        if scale is None:
            raise ValueError(f"Unknown units {units!r}. Choose from: {list(_UNIT_CONFIG)}")

        abundance_map = self._generator.generate_map(isotope) * scale

        if ax is None:
            fig, ax = plt.subplots()
        else:
            fig = ax.figure

        im = ax.imshow(abundance_map, cmap=cmap, vmin=vmin, vmax=vmax, origin="upper")
        ax.set_title(isotope)

        if show_colorbar:
            fig.colorbar(im, ax=ax, label=label)

        return fig, ax

    def plot_multi_isotope(
        self,
        isotopes: list[str] | None = None,
        ncols: int = 3,
        figsize: tuple[float, float] | None = None,
        units: AbundanceUnits = "fraction",
    ) -> tuple[Figure, np.ndarray]:
        """Plot abundance maps for multiple isotopes in a grid.

        Args:
            isotopes: List of isotope names to plot. If None, plots all.
            ncols: Number of columns in the grid. Must be >= 1.
            figsize: Figure size as (width, height). Auto-calculated if None.
            units: Display units for the abundance values.
                ``"fraction"`` (default, 0-1), ``"percent"`` (0-100),
                or ``"ppm"`` (0-1e6).

        Returns:
            Tuple of (Figure, ndarray of Axes).

        Raises:
            ValueError: If any isotope in the list is not found, or if
                isotopes list is empty, or if ncols < 1, or if units is invalid.
        """
        scale, label = _UNIT_CONFIG.get(units, (None, None))
        if scale is None:
            raise ValueError(f"Unknown units {units!r}. Choose from: {list(_UNIT_CONFIG)}")

        if ncols < 1:
            raise ValueError(f"ncols must be >= 1, got {ncols}")

        if isotopes is None:
            isotopes = list(self._results.isotope_names)

        if not isotopes:
            raise ValueError("isotopes list must not be empty")

        # Validate all isotopes exist before creating figures
        for iso in isotopes:
            if iso not in self._results.isotope_names:
                available = ", ".join(self._results.isotope_names)
                raise ValueError(f"Unknown isotope {iso!r}. Available: {available}")

        n = len(isotopes)
        nrows = max(1, math.ceil(n / ncols))

        if figsize is None:
            figsize = (4 * ncols, 4 * nrows)

        fig, axes = plt.subplots(nrows, ncols, figsize=figsize, squeeze=False)

        for i, iso in enumerate(isotopes):
            row, col = divmod(i, ncols)
            abundance_map = self._generator.generate_map(iso) * scale
            im = axes[row, col].imshow(abundance_map, cmap="viridis", origin="upper")
            axes[row, col].set_title(iso)
            fig.colorbar(im, ax=axes[row, col], label=label, shrink=0.8)

        # Hide unused axes
        for i in range(n, nrows * ncols):
            row, col = divmod(i, ncols)
            axes[row, col].set_visible(False)

        fig.tight_layout()
        return fig, axes

    def plot_quality_overlay(
        self,
        isotope: str,
        quality_metric: str = "chi_squared",
        alpha: float = 0.5,
        units: AbundanceUnits = "fraction",
    ) -> tuple[Figure, Axes]:
        """Plot an abundance map with a quality metric overlay.

        Renders the abundance map as the base layer and overlays a
        semi-transparent quality metric map on top.

        Args:
            isotope: Isotope name for the base abundance map.
            quality_metric: Quality metric for the overlay (``"chi_squared"``
                or ``"success"``).
            alpha: Transparency of the overlay (0 = transparent, 1 = opaque).
                Must be in [0, 1].
            units: Display units for the abundance base layer.
                ``"fraction"`` (default, 0-1), ``"percent"`` (0-100),
                or ``"ppm"`` (0-1e6).

        Returns:
            Tuple of (Figure, Axes).

        Raises:
            ValueError: If isotope or quality_metric is invalid, if
                alpha is outside [0, 1], or if units is invalid.
        """
        scale, _ = _UNIT_CONFIG.get(units, (None, None))
        if scale is None:
            raise ValueError(f"Unknown units {units!r}. Choose from: {list(_UNIT_CONFIG)}")

        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"alpha must be in [0, 1], got {alpha}")

        abundance_map = self._generator.generate_map(isotope) * scale
        quality_map = self._generator.generate_quality_map(metric=quality_metric)

        fig, ax = plt.subplots()

        ax.imshow(abundance_map, cmap="viridis", origin="upper")
        im_overlay = ax.imshow(quality_map, cmap="hot", alpha=alpha, origin="upper")
        ax.set_title(f"{isotope} + {quality_metric}")

        fig.colorbar(im_overlay, ax=ax, label=quality_metric)

        return fig, ax
