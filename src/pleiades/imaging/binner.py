"""Spatial binning for hyperspectral imaging data.

Provides ``SpatialBinner`` to reduce spatial resolution by averaging N×N blocks
of pixels, improving SNR for sparse / noisy datasets. Includes unbinning helpers
to restore results to the original spatial shape.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from skimage.measure import block_reduce

from pleiades.imaging.models import HyperspectralData, Imaging2DResults


class SpatialBinner:
    """Bin and unbin hyperspectral imaging data spatially.

    Averaging an N×N block of pixels improves SNR by a factor of N (noise
    is reduced to 1/N of that of a single pixel).  The binned data
    can be processed by the normal fitting pipeline and then unbinned back
    to the original resolution.

    Args:
        bin_size: Spatial binning factor.  ``bin_size=2`` averages 2×2 blocks
            (4 pixels → 1), ``bin_size=4`` averages 4×4 blocks.  Must be >= 1.
            ``bin_size=1`` is a no-op identity.
        method: Aggregation method for each block.  ``"mean"`` (default) or
            ``"median"``.

    Raises:
        ValueError: If ``bin_size < 1`` or ``method`` is not recognised.
    """

    def __init__(self, bin_size: int, method: str = "mean") -> None:
        if bin_size < 1:
            raise ValueError(f"bin_size must be >= 1, got {bin_size}")
        if method not in ("mean", "median"):
            raise ValueError(f"method must be 'mean' or 'median', got {method!r}")
        self.bin_size = bin_size
        self.method = method

    def bin_hyperspectral(self, hyperspectral: HyperspectralData) -> HyperspectralData:
        """Bin the spatial dimensions of a hyperspectral dataset.

        The energy axis is left unchanged.  Spatial dimensions are reduced by
        ``bin_size`` via block averaging.  Rows/columns that do not fill a
        complete block are discarded (floor division).

        Uncertainty propagation:
            ``σ_bin = sqrt(Σ σ_i²) / N`` where N = bin_size² — correct for
            independent pixels with heterogeneous uncertainties.

        Args:
            hyperspectral: Dataset of shape ``(n_energy, H, W)``.

        Returns:
            New ``HyperspectralData`` of shape
            ``(n_energy, H // bin_size, W // bin_size)`` with the same energy
            axis and updated uncertainty (if present).
        """
        if self.bin_size == 1:
            return hyperspectral

        data = hyperspectral.data  # (n_e, H, W)
        n_e, h_orig, w_orig = data.shape
        bs = self.bin_size

        # Crop to exact multiples of bin_size so no zero-padding occurs
        h_crop = (h_orig // bs) * bs
        w_crop = (w_orig // bs) * bs
        if h_crop == 0 or w_crop == 0:
            raise ValueError(
                f"bin_size={bs} produces a zero-sized binned image for input shape "
                f"({h_orig}, {w_orig}); bin_size must be <= min(height, width)"
            )
        data = data[:, :h_crop, :w_crop]

        func = np.mean if self.method == "mean" else np.median
        # block_reduce over spatial axes (1, 2); axis 0 (energy) block = 1
        block_shape = (1, bs, bs)
        binned_data = block_reduce(data, block_size=block_shape, func=func)

        # Uncertainty propagation: σ_bin = sqrt(Σ σ_i²) / N for N = bs²
        binned_uncertainty = None
        if hyperspectral.uncertainty is not None:
            unc_cropped = hyperspectral.uncertainty[:, :h_crop, :w_crop]
            variance_sum = block_reduce(unc_cropped**2, block_size=block_shape, func=np.sum)
            n_pixels = bs * bs
            binned_uncertainty = np.sqrt(variance_sum) / n_pixels

        return HyperspectralData(
            data=binned_data,
            energy=hyperspectral.energy.copy(),
            uncertainty=binned_uncertainty,
            source_file=hyperspectral.source_file,
            metadata={**hyperspectral.metadata, "bin_size": bs},
        )

    def unbin_map(self, binned_map: np.ndarray, original_shape: Tuple[int, int]) -> np.ndarray:
        """Upscale a 2-D binned map to the original spatial resolution.

        Uses nearest-neighbour repeat: each binned value is copied into a
        ``bin_size × bin_size`` tile.  NaN values are preserved.

        Args:
            binned_map: 2-D array of shape ``(H_bin, W_bin)``.
            original_shape: Target ``(H, W)`` shape to upscale to.

        Returns:
            2-D array of shape ``original_shape``.  The output is cropped or
            padded (with NaN) to match ``original_shape`` exactly.

        Raises:
            ValueError: If ``binned_map`` is not 2-D.
        """
        if binned_map.ndim != 2:
            raise ValueError(f"binned_map must be 2-D, got {binned_map.ndim}D")

        if self.bin_size == 1:
            upscaled = binned_map
        else:
            # Nearest-neighbour upscale via np.repeat
            upscaled = np.repeat(np.repeat(binned_map, self.bin_size, axis=0), self.bin_size, axis=1)

        # Crop/pad to original_shape
        h, w = original_shape
        uh, uw = upscaled.shape
        if uh >= h and uw >= w:
            return upscaled[:h, :w]

        # Pad with NaN if the upscaled result is smaller than original.
        # Promote to float if needed so NaN is representable.
        pad_dtype = upscaled.dtype if np.issubdtype(upscaled.dtype, np.floating) else np.float64
        result = np.full((h, w), np.nan, dtype=pad_dtype)
        result[: min(uh, h), : min(uw, w)] = upscaled[: min(uh, h), : min(uw, w)]
        return result

    def unbin_results(self, results: Imaging2DResults, original_hyperspectral: HyperspectralData) -> Imaging2DResults:
        """Upscale all spatial maps in ``results`` to the original image resolution.

        Upscales:
        - ``abundance_maps`` (3-D: each isotope map individually)
        - ``chi_squared_map`` (2-D)
        - ``success_mask`` (2-D boolean)
        - ``fitted_energy_maps`` (3-D, if present)

        Restores ``source_hyperspectral`` to ``original_hyperspectral`` and
        records ``bin_size`` in ``results.metadata``.

        Args:
            results: ``Imaging2DResults`` from the binned pipeline run.
            original_hyperspectral: The pre-binning ``HyperspectralData``.

        Returns:
            New ``Imaging2DResults`` with all spatial maps at original resolution.
        """
        _, orig_h, orig_w = original_hyperspectral.shape
        original_shape = (orig_h, orig_w)

        # Abundance maps: (n_isotopes, H_bin, W_bin) → (n_isotopes, H, W)
        n_isotopes = results.abundance_maps.shape[0]
        unbinned_abundance = np.stack(
            [self.unbin_map(results.abundance_maps[i], original_shape) for i in range(n_isotopes)],
            axis=0,
        )

        # Chi-squared map
        unbinned_chi2 = self.unbin_map(results.chi_squared_map, original_shape)

        # Success mask (boolean) — NaN-padded edges must become False, not
        # True (bool(np.nan) is truthy), so replace NaN with 0 before casting.
        unbinned_success_float = self.unbin_map(results.success_mask.astype(np.float64), original_shape)
        unbinned_success = np.nan_to_num(unbinned_success_float, nan=0.0).astype(bool)

        # Fitted energy maps (optional)
        unbinned_energy_maps = None
        if results.fitted_energy_maps is not None:
            n_res = results.fitted_energy_maps.shape[0]
            unbinned_energy_maps = np.stack(
                [self.unbin_map(results.fitted_energy_maps[r], original_shape) for r in range(n_res)],
                axis=0,
            )

        updated_metadata = {**results.metadata, "bin_size": self.bin_size}

        return Imaging2DResults(
            abundance_maps=unbinned_abundance,
            isotope_names=results.isotope_names,
            fitted_energy_maps=unbinned_energy_maps,
            chi_squared_map=unbinned_chi2,
            success_mask=unbinned_success,
            source_hyperspectral=original_hyperspectral,
            pixel_results=results.pixel_results,
            metadata=updated_metadata,
        )
