"""
Hyperspectral data loader for 2D resonance imaging.

This module provides tools for loading and managing hyperspectral neutron
imaging data from TIFF files.
"""

from pathlib import Path
from typing import Iterator, Optional, Tuple

import numpy as np
import tifffile

from pleiades.imaging.models import HyperspectralData, PixelSpectrum
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class HyperspectralLoader:
    """Load and manage hyperspectral neutron imaging data from TIFF files.

    Uses tifffile library for robust multi-page TIFF loading. Supports optional
    energy axis specification or automatic placeholder generation.

    Attributes:
        filepath: Path to multi-page TIFF file
        energy: Optional 1D energy array in eV
        _data: Loaded 3D numpy array (n_energy, height, width)
        _hyperspectral: Cached HyperspectralData object

    Example:
        >>> loader = HyperspectralLoader("data.tif", energy=energy_array)
        >>> hyperspectral = loader.load()
        >>> print(hyperspectral.shape)
        (500, 256, 256)
        >>> for pixel in loader.iter_pixels():
        ...     print(f"Pixel ({pixel.row}, {pixel.col}): {pixel.transmission.mean():.4f}")
    """

    def __init__(self, filepath: Path, energy: Optional[np.ndarray] = None):
        """Initialize loader.

        Args:
            filepath: Path to multi-page TIFF file
            energy: Optional 1D energy array in eV. If None, placeholder generated.
        """
        self.filepath = Path(filepath)
        self.energy = energy
        self._data: Optional[np.ndarray] = None
        self._hyperspectral: Optional[HyperspectralData] = None

        if not self.filepath.exists():
            raise FileNotFoundError(f"TIFF file not found: {self.filepath}")

    def load(self) -> HyperspectralData:
        """Load hyperspectral data from TIFF file.

        Returns:
            HyperspectralData object with data, energy, and metadata

        Raises:
            FileNotFoundError: If TIFF file doesn't exist
            ValueError: If TIFF structure is invalid
        """
        logger.info(f"Loading hyperspectral data from {self.filepath}")

        # Load multi-page TIFF using tifffile
        self._data = tifffile.imread(str(self.filepath))

        # Validate shape
        if self._data.ndim != 3:
            raise ValueError(f"Expected 3D TIFF (n_energy, height, width), got {self._data.ndim}D")

        n_energy, height, width = self._data.shape
        logger.debug(f"Loaded TIFF: {n_energy} frames × {height}×{width} pixels, dtype={self._data.dtype}")

        # Handle energy axis
        if self.energy is None:
            self.energy = self._infer_energy_axis(n_energy)
        elif len(self.energy) != n_energy:
            raise ValueError(f"Energy length {len(self.energy)} != n_frames {n_energy}")

        # Estimate uncertainties (simple Poisson approximation for now)
        uncertainty = self._estimate_uncertainty(self._data)

        # Create HyperspectralData object
        self._hyperspectral = HyperspectralData(
            data=self._data,
            energy=self.energy,
            uncertainty=uncertainty,
            source_file=self.filepath,
            metadata={"n_energy": n_energy, "height": height, "width": width, "dtype": str(self._data.dtype)},
        )

        logger.info(f"Loaded hyperspectral data: {self._hyperspectral.shape}")
        return self._hyperspectral

    def _infer_energy_axis(self, n_energy: int) -> np.ndarray:
        """Infer energy axis from TIFF metadata or create placeholder.

        For LANL-ORNL_example.tif, no energy metadata is available. This method
        creates a placeholder linear spacing. Future enhancement: analyze resonance
        patterns to match known isotopes and infer energy scale.

        Args:
            n_energy: Number of energy bins

        Returns:
            1D energy array in eV
        """
        logger.warning(
            f"Energy axis not provided for {self.filepath.name}. "
            "Using placeholder linear spacing (1-100 eV). "
            "For accurate results, provide energy array explicitly."
        )
        return np.linspace(1.0, 100.0, n_energy)

    def _estimate_uncertainty(self, data: np.ndarray) -> np.ndarray:
        """Estimate uncertainties for transmission data.

        Uses simple Poisson approximation: σ_T = sqrt(T * (1-T) / N)
        where T is transmission and N is effective counts (~1000 as estimate).

        For real data from normalization process, uncertainties should come
        from the transmission calculation that propagates open beam and sample
        uncertainties properly.

        Args:
            data: 3D transmission data

        Returns:
            3D uncertainty array (same shape as data)
        """
        # Placeholder: assume ~1000 effective counts per bin
        # Real implementation should use proper uncertainty propagation
        effective_counts = 1000.0
        uncertainty = np.sqrt(np.abs(data * (1 - data)) / effective_counts)

        # Clip to reasonable range (min 0.1% relative uncertainty)
        min_uncertainty = 0.001 * np.abs(data)
        uncertainty = np.maximum(uncertainty, min_uncertainty)

        return uncertainty.astype(np.float32)

    def iter_pixels(self, roi: Optional[Tuple[int, int, int, int]] = None) -> Iterator[PixelSpectrum]:
        """Iterate over pixel spectra.

        Args:
            roi: Optional ROI as (x1, y1, x2, y2). If None, iterate all pixels.

        Yields:
            PixelSpectrum objects for each spatial pixel

        Raises:
            ValueError: If load() not called first
        """
        if self._hyperspectral is None:
            raise ValueError("Must call load() before iter_pixels()")

        n_energy, height, width = self._hyperspectral.shape

        # Determine iteration bounds
        if roi is None:
            x1, y1, x2, y2 = 0, 0, width, height
        else:
            x1, y1, x2, y2 = roi
            # Validate ROI bounds
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError(f"Invalid ROI {roi} for image shape (height={height}, width={width})")

        logger.info(f"Iterating pixels in ROI: x=[{x1},{x2}), y=[{y1},{y2})")

        for row in range(y1, y2):
            for col in range(x1, x2):
                # Extract pixel spectrum
                transmission = self._hyperspectral.data[:, row, col]

                # Extract uncertainty if available
                if self._hyperspectral.uncertainty is not None:
                    uncertainty = self._hyperspectral.uncertainty[:, row, col]
                else:
                    # Fallback: 1% relative uncertainty
                    uncertainty = 0.01 * np.abs(transmission)

                yield PixelSpectrum(
                    row=row,
                    col=col,
                    energy=self._hyperspectral.energy.copy(),
                    transmission=transmission.copy(),
                    uncertainty=uncertainty.copy(),
                    metadata={"source_file": str(self.filepath)},
                )

    def get_pixel(self, row: int, col: int) -> PixelSpectrum:
        """Get spectrum for a specific pixel.

        Args:
            row: Pixel row (0-indexed)
            col: Pixel column (0-indexed)

        Returns:
            PixelSpectrum for specified pixel

        Raises:
            ValueError: If load() not called first or coordinates out of bounds
        """
        if self._hyperspectral is None:
            raise ValueError("Must call load() before get_pixel()")

        n_energy, height, width = self._hyperspectral.shape
        if not (0 <= row < height and 0 <= col < width):
            raise ValueError(f"Pixel ({row}, {col}) out of bounds (height={height}, width={width})")

        transmission = self._hyperspectral.data[:, row, col]
        uncertainty = (
            self._hyperspectral.uncertainty[:, row, col]
            if self._hyperspectral.uncertainty is not None
            else 0.01 * np.abs(transmission)
        )

        return PixelSpectrum(
            row=row,
            col=col,
            energy=self._hyperspectral.energy.copy(),
            transmission=transmission.copy(),
            uncertainty=uncertainty.copy(),
            metadata={"source_file": str(self.filepath)},
        )
