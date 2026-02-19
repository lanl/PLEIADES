"""High-level API for 2D resonance imaging analysis.

Provides the ``analyze_imaging()`` function that wires together all imaging
pipeline components (loader, orchestrator, aggregator) into a single call.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pleiades.imaging.aggregator import ResultsAggregator
from pleiades.imaging.config import ImagingConfig
from pleiades.imaging.loader import HyperspectralLoader
from pleiades.imaging.models import Imaging2DResults
from pleiades.imaging.orchestrator import BatchFittingOrchestrator
from pleiades.imaging.temp_manager import TempFileManager
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


def analyze_imaging(
    source: Path | str,
    imaging_config: ImagingConfig,
    sammy_executable: Path,
    energy: np.ndarray | None = None,
    n_workers: int = 4,
    roi: tuple[int, int, int, int] | None = None,
    stride: int = 1,
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
        source: Path to hyperspectral TIFF file or directory.
        imaging_config: Configuration with isotopes and material properties.
        sammy_executable: Path to the SAMMY binary.
        energy: Energy axis in eV. If None, inferred from data.
        n_workers: Number of parallel SAMMY workers. Must be >= 1.
        roi: Region of interest as ``(x1, y1, x2, y2)``. If None, all pixels.
        stride: Spatial stride for pixel iteration.  ``stride=4`` fits every
            4th pixel in both directions (16x fewer pixels).  Unfitted pixels
            appear as NaN in the output maps.
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
    loader = HyperspectralLoader(source, energy=energy)
    hyperspectral = loader.load()

    _, height, width = hyperspectral.shape
    logger.info(f"Loaded image: {height}x{width} pixels, {hyperspectral.shape[0]} energy bins")

    # --- Create default TempFileManager if none provided ---
    # Deferred until after loading succeeds so that early failures (missing
    # TIFF, bad config, etc.) don't leave an orphaned temp directory on disk.
    if temp_manager is None:
        temp_manager = TempFileManager()

    # --- 2. Fit pixels (streamed from loader to orchestrator) ---
    orchestrator = BatchFittingOrchestrator(
        imaging_config=imaging_config,
        sammy_executable=sammy_executable,
        n_workers=n_workers,
        resolution_file=resolution_file,
        temp_manager=temp_manager,
    )
    pixel_results = orchestrator.fit_pixels(
        lambda: loader.iter_pixels(roi=roi, stride=stride),
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

    # --- 5. Optionally save ---
    if save_path is not None:
        logger.info(f"Saving results to {save_path}")
        results.save_hdf5(save_path)

    return results
