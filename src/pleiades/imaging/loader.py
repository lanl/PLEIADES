"""
Hyperspectral data loader for 2D resonance imaging.

This module provides tools for loading and managing hyperspectral neutron
imaging data from multiple sources: TIFF files, directories, and NeXus/HDF5.
"""

from pathlib import Path
from typing import Iterator, Optional, Tuple, Union

import h5py
import numpy as np
import tifffile

from pleiades.imaging.models import HyperspectralData, PixelSpectrum
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class HyperspectralLoader:
    """Load and manage hyperspectral neutron imaging data from multiple sources.

    Supports three data loading modes:
    1. Single multi-page TIFF file
    2. Multiple TIFF files from directory (sorted)
    3. NeXus/HDF5 histogram data

    Attributes:
        source: Path to data source (file or directory)
        energy: Optional 1D energy array in eV
        _data: Loaded 3D numpy array (n_energy, height, width)
        _hyperspectral: Cached HyperspectralData object

    Example:
        Single multi-page TIFF:
        >>> loader = HyperspectralLoader("data.tif", energy=energy_array)
        >>> hyperspectral = loader.load()

        Multiple TIFFs from directory:
        >>> loader = HyperspectralLoader.from_directory("run_8022/", pattern="*.tif")
        >>> hyperspectral = loader.load()

        NeXus/HDF5 histogram:
        >>> loader = HyperspectralLoader.from_nexus("data.nxs.h5", dataset_path="/entry/data/histogram")
        >>> hyperspectral = loader.load()
    """

    def __init__(self, source: Union[Path, str], energy: Optional[np.ndarray] = None):
        """Initialize loader for single multi-page TIFF file.

        Args:
            source: Path to multi-page TIFF file
            energy: Optional 1D energy array in eV. If None, placeholder generated.

        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        self.source = Path(source)
        self.energy = energy
        self._data: Optional[np.ndarray] = None
        self._hyperspectral: Optional[HyperspectralData] = None
        self._load_mode = "single_tiff"

        if not self.source.exists():
            raise FileNotFoundError(f"Source not found: {self.source}")

    @classmethod
    def from_directory(
        cls, directory: Union[Path, str], pattern: str = "*.tif", energy: Optional[np.ndarray] = None
    ) -> "HyperspectralLoader":
        """Create loader from multiple TIFF files in directory (sorted).

        Loads and stacks sorted TIFF files from a directory, following the same
        pattern as pleiades.utils.load.load_tiff().

        Args:
            directory: Path to directory containing TIFF files
            pattern: Glob pattern for file matching (default: "*.tif")
            energy: Optional 1D energy array in eV

        Returns:
            HyperspectralLoader instance configured for directory loading

        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If no files match pattern

        Example:
            >>> loader = HyperspectralLoader.from_directory("run_8022/", pattern="*.tif")
            >>> hyperspectral = loader.load()
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")

        # Find matching files (sorted for deterministic order)
        files = sorted(directory.glob(pattern))
        if not files:
            raise ValueError(f"No files matching pattern '{pattern}' in {directory}")

        logger.info(f"Found {len(files)} files matching '{pattern}' in {directory}")

        # Create instance
        instance = cls.__new__(cls)
        instance.source = directory
        instance.energy = energy
        instance._data = None
        instance._hyperspectral = None
        instance._load_mode = "directory"
        instance._file_list = files
        instance._pattern = pattern

        return instance

    @classmethod
    def from_nexus(
        cls,
        nexus_file: Union[Path, str],
        dataset_path: str = "/entry/data/histogram",
        energy_path: Optional[str] = "/entry/data/energy",
    ) -> "HyperspectralLoader":
        """Create loader from NeXus/HDF5 histogram data.

        Loads hyperspectral data from NeXus/HDF5 files, commonly produced by
        scitiff or scipp for neutron imaging experiments.

        Args:
            nexus_file: Path to NeXus/HDF5 file
            dataset_path: HDF5 path to histogram dataset (default: "/entry/data/histogram")
            energy_path: Optional HDF5 path to energy axis. If None, placeholder generated.

        Returns:
            HyperspectralLoader instance configured for NeXus loading

        Raises:
            FileNotFoundError: If NeXus file doesn't exist

        Example:
            >>> loader = HyperspectralLoader.from_nexus("data.nxs.h5")
            >>> hyperspectral = loader.load()
        """
        nexus_file = Path(nexus_file)
        if not nexus_file.exists():
            raise FileNotFoundError(f"NeXus file not found: {nexus_file}")

        # Create instance
        instance = cls.__new__(cls)
        instance.source = nexus_file
        instance.energy = None
        instance._data = None
        instance._hyperspectral = None
        instance._load_mode = "nexus"
        instance._dataset_path = dataset_path
        instance._energy_path = energy_path

        return instance

    def load(self) -> HyperspectralData:
        """Load hyperspectral data based on configured mode.

        Returns:
            HyperspectralData object with data, energy, and metadata

        Raises:
            FileNotFoundError: If source doesn't exist
            ValueError: If data structure is invalid
        """
        if self._load_mode == "single_tiff":
            self._data = self._load_single_tiff()
        elif self._load_mode == "directory":
            self._data = self._load_from_directory()
        elif self._load_mode == "nexus":
            self._data = self._load_from_nexus()
        else:
            raise ValueError(f"Unknown load mode: {self._load_mode}")

        # Validate shape
        if self._data.ndim != 3:
            raise ValueError(f"Expected 3D data (n_energy, height, width), got {self._data.ndim}D")

        n_energy, height, width = self._data.shape
        logger.debug(f"Loaded data: {n_energy} frames × {height}×{width} pixels, dtype={self._data.dtype}")

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
            source_file=self.source,
            metadata={
                "n_energy": n_energy,
                "height": height,
                "width": width,
                "dtype": str(self._data.dtype),
                "load_mode": self._load_mode,
            },
        )

        logger.info(f"Loaded hyperspectral data: {self._hyperspectral.shape}")
        return self._hyperspectral

    def _load_single_tiff(self) -> np.ndarray:
        """Load single multi-page TIFF file.

        Returns:
            3D numpy array (n_energy, height, width)
        """
        logger.info(f"Loading multi-page TIFF: {self.source}")
        data = tifffile.imread(str(self.source))
        return data.astype(np.float32)

    def _load_from_directory(self) -> np.ndarray:
        """Load and stack sorted TIFF files from directory.

        Follows the pattern from pleiades.utils.load.load_tiff().

        Returns:
            3D numpy array (n_files, height, width)
        """
        logger.info(f"Loading {len(self._file_list)} TIFF files from {self.source}")

        # Load first image to get dimensions
        first_image = tifffile.imread(str(self._file_list[0]))
        n_files = len(self._file_list)
        height, width = first_image.shape

        # Allocate 3D array
        data = np.empty((n_files, height, width), dtype=np.float32)
        data[0] = first_image

        # Load remaining files
        for i, file_path in enumerate(self._file_list[1:], start=1):
            image = tifffile.imread(str(file_path))
            if image.shape != (height, width):
                raise ValueError(f"Shape mismatch in {file_path.name}: {image.shape} vs ({height}, {width})")
            data[i] = image

        logger.info(f"Stacked {n_files} images into shape {data.shape}")
        return data

    def _load_from_nexus(self) -> np.ndarray:
        """Load histogram from NeXus/HDF5 file.

        Returns:
            3D numpy array (n_energy, height, width)
        """
        logger.info(f"Loading NeXus histogram from {self.source}")

        with h5py.File(self.source, "r") as f:
            # Load histogram dataset
            if self._dataset_path not in f:
                raise ValueError(f"Dataset path '{self._dataset_path}' not found in {self.source}")

            data = f[self._dataset_path][:]

            # Load energy axis if available
            if self._energy_path and self._energy_path in f:
                self.energy = f[self._energy_path][:]
                logger.debug(f"Loaded energy axis from {self._energy_path}")
            else:
                logger.warning(f"Energy path '{self._energy_path}' not found, will use placeholder")

        logger.info(f"Loaded NeXus data: shape={data.shape}, dtype={data.dtype}")
        return data.astype(np.float32)

    def _infer_energy_axis(self, n_energy: int) -> np.ndarray:
        """Infer energy axis from metadata or create placeholder.

        For data without energy metadata, creates placeholder linear spacing.
        Future enhancement: analyze resonance patterns to match known isotopes
        and infer energy scale.

        Args:
            n_energy: Number of energy bins

        Returns:
            1D energy array in eV
        """
        source_name = self.source.name if hasattr(self.source, "name") else str(self.source)
        logger.warning(
            f"Energy axis not provided for {source_name}. "
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
                    metadata={"source": str(self.source), "load_mode": self._load_mode},
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
            metadata={"source": str(self.source), "load_mode": self._load_mode},
        )
