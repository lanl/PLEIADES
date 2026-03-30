"""Results aggregation for 2D resonance imaging.

This module provides the ResultsAggregator class that builds spatially-resolved
isotope abundance maps from per-pixel SAMMY fit results.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from pleiades.imaging.models import HyperspectralData, Imaging2DResults, PixelFitResult
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class ResultsAggregator:
    """Aggregates per-pixel SAMMY fit results into 2D abundance maps.

    Takes a list of PixelFitResult objects (one per fitted pixel) and assembles
    them into 2D numpy arrays for abundance maps, chi-squared maps, and
    success masks.

    Args:
        isotope_names: List of isotope names (e.g., ["Ta-181", "W-182"]).
            Abundances are mapped by name, so the order in each pixel's fit
            results does not need to match this order.
        height: Image height in pixels.
        width: Image width in pixels.

    Example:
        >>> aggregator = ResultsAggregator(isotope_names=["Ta-181"], height=256, width=256)
        >>> result = aggregator.aggregate(pixel_results, source_hyperspectral)
        >>> result.save_hdf5("output.h5")
    """

    def __init__(self, isotope_names: List[str], height: int, width: int) -> None:
        if not isotope_names:
            raise ValueError("isotope_names must not be empty")
        if height <= 0:
            raise ValueError(f"height must be positive, got {height}")
        if width <= 0:
            raise ValueError(f"width must be positive, got {width}")

        self._isotope_names = list(isotope_names)
        self._height = height
        self._width = width
        self._n_isotopes = len(isotope_names)

    def aggregate(
        self,
        pixel_results: List[PixelFitResult],
        source_hyperspectral: HyperspectralData,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Imaging2DResults:
        """Build 2D imaging results from a list of pixel fit results.

        For each pixel result:
          - If success=True, abundance values are placed in the corresponding
            (row, col) position of the abundance maps and chi-squared map.
          - If success=False or the pixel is absent, np.nan is used.

        Args:
            pixel_results: List of PixelFitResult objects from batch fitting.
            source_hyperspectral: Original hyperspectral data (stored as reference).
            metadata: Optional dict of processing metadata.

        Returns:
            Imaging2DResults with populated maps.

        Raises:
            ValueError: If pixel coordinates are out of bounds, duplicated,
                isotope names don't match, or isotope count is inconsistent.
        """
        abundance_maps = np.full((self._n_isotopes, self._height, self._width), np.nan, dtype=np.float64)
        chi_squared_map = np.full((self._height, self._width), np.nan, dtype=np.float64)
        success_mask = np.zeros((self._height, self._width), dtype=bool)
        seen_coords: set = set()

        # Pre-build name→index mapping for O(1) lookup
        name_to_index = {name: i for i, name in enumerate(self._isotope_names)}

        for pixel in pixel_results:
            row, col = pixel.row, pixel.col

            if row < 0 or row >= self._height or col < 0 or col >= self._width:
                raise ValueError(
                    f"Pixel coordinate ({row}, {col}) out of bounds for image of size ({self._height}, {self._width})"
                )

            coord = (row, col)
            if coord in seen_coords:
                raise ValueError(f"Duplicate pixel result at coordinate ({row}, {col})")
            seen_coords.add(coord)

            if pixel.success:
                isotopes = pixel.fit_results.nuclear_data.isotopes

                if len(isotopes) != self._n_isotopes:
                    raise ValueError(
                        f"Isotope count mismatch at pixel ({row}, {col}): "
                        f"expected {self._n_isotopes}, got {len(isotopes)}"
                    )

                for isotope_param in isotopes:
                    iso_name = isotope_param.isotope_information.name
                    if iso_name not in name_to_index:
                        pixel_names = [ip.isotope_information.name for ip in isotopes]
                        raise ValueError(
                            f"Isotope name mismatch at pixel ({row}, {col}): "
                            f"pixel has {pixel_names}, expected {self._isotope_names}"
                        )
                    idx = name_to_index[iso_name]
                    abundance_maps[idx, row, col] = isotope_param.abundance

                if pixel.chi_squared is not None:
                    chi_squared_map[row, col] = pixel.chi_squared

                success_mask[row, col] = True
            # Failed pixels: NaN abundance/chi-squared and False success_mask
            # are already the initialized defaults; no action needed.

        # --- Normalize multi-isotope abundances per pixel ---
        #
        # SAMMY's two-pass strategy (IFLISO=1) fits per-isotope abundance as
        # an unconstrained free parameter.  The SAMMY input file (Card Set 2)
        # describes the sample with a single element's atomic mass, density,
        # and thickness.  When the sample is actually a multi-element alloy,
        # SAMMY compensates for the mass/density mismatch by pushing
        # individual abundances above 1.0.  For example, a Ta-181 + U-235
        # sample modelled with Ta properties will yield f_U > 1.0 because
        # U-235's atomic mass (235 amu) is 30% higher than Ta's (181 amu).
        #
        # The *ratio* between fitted abundances is still physically
        # meaningful, so we rescale each pixel's abundances to sum to 1.0.
        # This makes the values interpretable as isotopic fractions.
        #
        # Single-isotope fits are left untouched because the abundance
        # carries absolute information (e.g. natural vs enriched) and there
        # is nothing to normalise against.
        if self._n_isotopes > 1:
            abundance_sum = np.nansum(abundance_maps, axis=0)  # (height, width)
            # Avoid division by zero for pixels where all abundances are NaN or 0
            nonzero = abundance_sum > 0
            for i in range(self._n_isotopes):
                abundance_maps[i, nonzero] /= abundance_sum[nonzero]

        logger.info(
            f"Aggregated {len(pixel_results)} pixel results: "
            f"{np.sum(success_mask)} succeeded, {np.sum(~success_mask)} failed/missing"
        )

        return Imaging2DResults(
            abundance_maps=abundance_maps,
            isotope_names=self._isotope_names,
            chi_squared_map=chi_squared_map,
            success_mask=success_mask,
            source_hyperspectral=source_hyperspectral,
            pixel_results=list(pixel_results),
            metadata=metadata or {},
        )
