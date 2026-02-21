"""High-level API for 2D resonance imaging analysis.

Provides the ``analyze_imaging()`` function that wires together all imaging
pipeline components (loader, orchestrator, aggregator) into a single call.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pleiades.imaging.aggregator import ResultsAggregator
from pleiades.imaging.binner import SpatialBinner
from pleiades.imaging.config import ImagingConfig
from pleiades.imaging.loader import HyperspectralLoader
from pleiades.imaging.models import HyperspectralData, Imaging2DResults, PixelSpectrum
from pleiades.imaging.orchestrator import BatchFittingOrchestrator
from pleiades.imaging.temp_manager import TempFileManager
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


def _iter_hyperspectral_pixels(
    hyperspectral: HyperspectralData,
    roi: tuple[int, int, int, int] | None = None,
    stride: int = 1,
):
    """Yield PixelSpectrum objects directly from a HyperspectralData cube.

    Used when the loader's ``iter_pixels`` would read from the wrong
    (unbinned) cube — e.g. after spatial binning.
    """
    n_energy, height, width = hyperspectral.shape

    if roi is None:
        x1, y1, x2, y2 = 0, 0, width, height
    else:
        x1, y1, x2, y2 = roi

    for row in range(y1, y2, stride):
        for col in range(x1, x2, stride):
            transmission = hyperspectral.data[:, row, col]
            if hyperspectral.uncertainty is not None:
                uncertainty = hyperspectral.uncertainty[:, row, col]
            else:
                uncertainty = 0.01 * np.abs(transmission)

            yield PixelSpectrum(
                row=row,
                col=col,
                energy=hyperspectral.energy,
                transmission=transmission,
                uncertainty=uncertainty,
            )


def analyze_imaging(
    source: Path | str,
    imaging_config: ImagingConfig,
    sammy_executable: Path,
    energy: np.ndarray | None = None,
    directory_pattern: str = "*.tif",
    n_workers: int = 4,
    roi: tuple[int, int, int, int] | None = None,
    stride: int = 1,
    bin_size: int = 1,
    resolution_file: Path | None = None,
    checkpoint_file: Path | None = None,
    checkpoint_interval: int = 10,
    resume: bool = False,
    timeout_per_job: float | None = None,
    max_retries: int = 0,
    temp_manager: TempFileManager | None = None,
    save_path: Path | None = None,
) -> Imaging2DResults:
    """Perform 2D resonance imaging analysis.

    Loads hyperspectral data, fits each pixel spectrum using SAMMY, and
    aggregates the results into 2D abundance maps.

    Args:
        source: Path to hyperspectral TIFF file or directory of TIFF files.
            When a directory is given, all files matching ``directory_pattern``
            are sorted and stacked into a single hyperspectral cube.
        imaging_config: Configuration with isotopes and material properties.
        sammy_executable: Path to the SAMMY binary.
        energy: Energy axis in eV. If None, inferred from data.
        directory_pattern: Glob pattern used to find TIFF files when ``source``
            is a directory (e.g. ``"*.tif"`` or ``"frame_*.tiff"``).
            Ignored when ``source`` is a file.
        n_workers: Number of parallel SAMMY workers. Must be >= 1.
        roi: Region of interest as ``(x1, y1, x2, y2)``. If None, all pixels.
        stride: Spatial stride for pixel iteration. ``stride=4`` fits every
            4th pixel in both directions (about 16x fewer evaluated pixels),
            but the returned abundance maps always have the full input
            ``(height, width)`` shape. Pixels that are not evaluated are left
            as NaN in the output maps. For an input of shape ``(H, W)``, only
            roughly ``ceil(H / stride) * ceil(W / stride)`` locations contain
            fitted values, so for large strides most entries may be NaN; when
            visualizing or computing statistics, use NaN-aware methods or
            masking as appropriate.
        bin_size: Spatial binning factor applied before fitting. ``bin_size=2``
            averages 2×2 blocks of pixels before fitting and upscales results
            back to the original resolution afterwards. Must be >= 1. Default
            is 1 (no binning, fully backward-compatible).
        resolution_file: Optional path to instrument resolution function file.
            Forwarded to the SAMMY backend for broadening calculations.
        checkpoint_file: Path to save/load checkpoint data.
        checkpoint_interval: Save checkpoint every N completed pixels. Must be >= 1.
        resume: If True, resume from an existing checkpoint file.
        timeout_per_job: Maximum seconds per pixel fit. None for no timeout.
        max_retries: Number of retry attempts for failed pixels. Must be >= 0.
        temp_manager: TempFileManager for workspace control. If None, a default
            is created.
        save_path: If provided, save results to this HDF5 path.

    Returns:
        Imaging2DResults with abundance maps and fit quality metrics.

    Raises:
        ValueError: If parameters are invalid.
    """
    # --- Input validation ---
    if n_workers < 1:
        raise ValueError(f"n_workers must be >= 1, got {n_workers}")
    if stride < 1:
        raise ValueError(f"stride must be >= 1, got {stride}")
    if bin_size < 1:
        raise ValueError(f"bin_size must be >= 1, got {bin_size}")
    if checkpoint_interval < 1:
        raise ValueError(f"checkpoint_interval must be >= 1, got {checkpoint_interval}")
    if max_retries < 0:
        raise ValueError(f"max_retries must be >= 0, got {max_retries}")
    if roi is not None and len(roi) != 4:
        raise ValueError(f"roi must have exactly 4 elements (x1, y1, x2, y2), got {len(roi)}")
    if resume and checkpoint_file is None:
        raise ValueError("resume=True requires checkpoint_file to be set")

    source = Path(source)

    # --- 1. Load hyperspectral data ---
    logger.info(f"Loading hyperspectral data from {source}")
    if source.is_dir():
        loader = HyperspectralLoader.from_directory(source, pattern=directory_pattern, energy=energy)
    else:
        loader = HyperspectralLoader(source, energy=energy)
    hyperspectral = loader.load()
    original_hyperspectral = hyperspectral

    _, height, width = hyperspectral.shape
    logger.info(f"Loaded image: {height}x{width} pixels, {hyperspectral.shape[0]} energy bins")

    # --- 1b. Optional spatial binning ---
    binner: SpatialBinner | None = None
    if bin_size > 1:
        binner = SpatialBinner(bin_size=bin_size)
        hyperspectral = binner.bin_hyperspectral(hyperspectral)
        _, height, width = hyperspectral.shape
        logger.info(f"Binned image (bin_size={bin_size}): {height}x{width} pixels")

    # --- Create default TempFileManager if none provided ---
    # Deferred until after loading succeeds so that early failures (missing
    # TIFF, bad config, etc.) don't leave an orphaned temp directory on disk.
    # Wrapped in try/finally so the temp directory is removed if any
    # subsequent step (orchestrator init, fit_pixels, etc.) raises before the
    # manager's __exit__ gets a chance to run.
    owns_temp_manager = temp_manager is None
    if owns_temp_manager:
        temp_manager = TempFileManager()

    try:
        # --- 2. Fit pixels (streamed from loader to orchestrator) ---
        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config,
            sammy_executable=sammy_executable,
            n_workers=n_workers,
            resolution_file=resolution_file,
            temp_manager=temp_manager,
        )
        # When binning is active, iterate over the binned hyperspectral
        # instead of the loader's original unbinned cube, so that pixel
        # coordinates match the binned (height, width) expected by the
        # aggregator.
        if binner is not None:

            def pixel_factory():
                return _iter_hyperspectral_pixels(hyperspectral, roi=roi, stride=stride)
        else:

            def pixel_factory():
                return loader.iter_pixels(roi=roi, stride=stride)

        pixel_results = orchestrator.fit_pixels(
            pixel_factory,
            checkpoint_file=checkpoint_file,
            checkpoint_interval=checkpoint_interval,
            resume=resume,
            timeout_per_job=timeout_per_job,
            max_retries=max_retries,
        )

        # --- 4. Aggregate results ---
        aggregator = ResultsAggregator(
            isotope_names=imaging_config.isotopes,
            height=height,
            width=width,
        )
        results = aggregator.aggregate(pixel_results, hyperspectral)

        # --- 4b. Unbin results to original resolution ---
        if binner is not None:
            results = binner.unbin_results(results, original_hyperspectral)

        # --- 5. Optionally save ---
        if save_path is not None:
            logger.info(f"Saving results to {save_path}")
            results.save_hdf5(save_path)

        return results
    except BaseException:
        if owns_temp_manager:
            import shutil

            shutil.rmtree(temp_manager.base_dir, ignore_errors=True)
        raise
