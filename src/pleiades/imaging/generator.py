"""Abundance map generation from 2D imaging results.

This module provides the AbundanceMapGenerator class which extracts individual
isotope abundance maps and quality maps from an Imaging2DResults object.
"""

from __future__ import annotations

import numpy as np

from pleiades.imaging.models import Imaging2DResults

_VALID_QUALITY_METRICS = ("chi_squared", "success")


class AbundanceMapGenerator:
    """Extract isotope abundance and quality maps from imaging results.

    Provides methods to retrieve individual isotope abundance maps, all maps
    at once, and quality metric maps (chi-squared, success rate) from a
    completed batch imaging run.

    All returned arrays are copies to prevent accidental mutation of internal
    data.

    Args:
        results: Completed 2D imaging results containing abundance maps,
            isotope names, chi-squared map, and success mask.

    Example:
        >>> gen = AbundanceMapGenerator(imaging_results)
        >>> ta_map = gen.generate_map("Ta-181")
        >>> all_maps = gen.generate_all_maps()
        >>> chi2 = gen.generate_quality_map("chi_squared")
    """

    def __init__(self, results: Imaging2DResults) -> None:
        self._results = results
        self._isotope_index = {name: i for i, name in enumerate(results.isotope_names)}

    def generate_map(self, isotope: str, fill_value: float = np.nan) -> np.ndarray:
        """Extract the 2D abundance map for a single isotope.

        Args:
            isotope: Isotope name (e.g. ``"Ta-181"``). Must be present in
                the results.
            fill_value: Value to substitute for NaN entries (failed pixels).
                Defaults to ``np.nan`` (no replacement).

        Returns:
            2D array of shape ``(height, width)`` with abundance values.

        Raises:
            ValueError: If isotope is not found in the results.
        """
        if isotope not in self._isotope_index:
            available = ", ".join(self._results.isotope_names) or "(none)"
            raise ValueError(f"Unknown isotope {isotope!r}. Available: {available}")

        idx = self._isotope_index[isotope]
        result = self._results.abundance_maps[idx].copy()

        if not np.isnan(fill_value):
            nan_mask = np.isnan(result)
            result[nan_mask] = fill_value

        return result

    def generate_all_maps(self) -> dict[str, np.ndarray]:
        """Extract abundance maps for all isotopes.

        Returns:
            Dictionary mapping isotope name to 2D abundance array.
            Each array is a copy of the internal data.
        """
        return {name: self.generate_map(name) for name in self._results.isotope_names}

    def generate_quality_map(self, metric: str = "chi_squared") -> np.ndarray:
        """Extract a 2D quality metric map.

        Args:
            metric: Quality metric to extract. Supported values:
                - ``"chi_squared"``: Per-pixel chi-squared from fitting.
                - ``"success"``: Success mask as float (1.0 = success, 0.0 = failure).

        Returns:
            2D array of shape ``(height, width)`` with quality values.

        Raises:
            ValueError: If metric is not one of the supported values.
        """
        if metric not in _VALID_QUALITY_METRICS:
            raise ValueError(f"Unsupported metric {metric!r}. Valid metrics: {_VALID_QUALITY_METRICS}")

        if metric == "chi_squared":
            return self._results.chi_squared_map.copy()

        # metric == "success"
        return self._results.success_mask.astype(float, copy=True)
