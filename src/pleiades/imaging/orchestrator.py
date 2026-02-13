"""
Batch orchestrator for parallel SAMMY fitting across hyperspectral imaging pixels.

This module provides tools for managing large-scale SAMMY resonance fitting jobs
(262,144+ pixels for 512×512 images) with parallelism, checkpointing, and progress tracking.
"""

import pickle
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pleiades.imaging.config import ImagingConfig
from pleiades.imaging.models import PixelFitResult, PixelSpectrum
from pleiades.sammy.backends.local import LocalSammyRunner
from pleiades.sammy.config import LocalSammyConfig
from pleiades.sammy.interface import SammyFilesMultiMode
from pleiades.sammy.io.data_manager import convert_csv_to_sammy_twenty
from pleiades.sammy.io.inp_manager import InpManager
from pleiades.sammy.io.json_manager import JsonManager
from pleiades.sammy.results.manager import ResultsManager
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


@dataclass
class CheckpointData:
    """Container for checkpoint state.

    Attributes:
        completed_pixels: Mapping from (row, col) to PixelFitResult for finished pixels
        total_pixels: Total number of pixels in the original batch (not just completed)
        config: ImagingConfig used for the batch (must match on resume)
    """

    completed_pixels: Dict[Tuple[int, int], PixelFitResult]
    total_pixels: int
    config: ImagingConfig


def _fit_pixel_worker(
    pixel: PixelSpectrum,
    imaging_config: ImagingConfig,
    sammy_executable: Path,
    resolution_file: Optional[Path] = None,
) -> PixelFitResult:
    """Worker function to fit a single pixel using SAMMY.

    This function runs in a subprocess and performs the complete SAMMY workflow:
    1. Export pixel spectrum to CSV
    2. Convert CSV to SAMMY .twenty format
    3. Create JSON config (auto-downloads ENDF files)
    4. Create .inp file
    5. Execute SAMMY
    6. Parse results

    Args:
        pixel: PixelSpectrum to fit
        imaging_config: Configuration with isotopes and material properties
        sammy_executable: Path to SAMMY binary
        resolution_file: Optional path to resolution function file

    Returns:
        PixelFitResult with fitted abundances and chi-squared, or failure info
    """
    with tempfile.TemporaryDirectory(prefix=f"pixel_{pixel.row}_{pixel.col}_") as temp_dir:
        temp_path = Path(temp_dir)

        try:
            # Step 1: Export pixel to CSV
            csv_file = temp_path / "pixel.txt"
            pixel.to_csv(csv_file)

            # Step 2: Convert to .twenty format
            twenty_file = temp_path / "pixel.twenty"
            convert_csv_to_sammy_twenty(csv_file, twenty_file)

            # Step 3: Create JSON config (auto-retrieves ENDF)
            json_manager = JsonManager()
            abundances = imaging_config.get_abundances()
            json_path = json_manager.create_json_config(
                isotopes=imaging_config.isotopes, abundances=abundances, working_dir=temp_path
            )

            # Step 4: Create .inp file
            inp_file = temp_path / "sammy.inp"
            material_props = imaging_config.get_material_properties()
            InpManager.create_multi_isotope_inp(
                inp_file,
                title=f"Pixel ({pixel.row}, {pixel.col}) resonance fitting",
                material_properties=material_props,
                resolution_file_path=resolution_file,
            )

            # Step 5: Execute SAMMY
            files = SammyFilesMultiMode(
                input_file=inp_file, json_config_file=json_path, data_file=twenty_file, endf_directory=temp_path
            )

            config = LocalSammyConfig(
                sammy_executable=sammy_executable,
                working_dir=temp_path / "sammy_working",
                output_dir=temp_path / "sammy_output",
            )

            runner = LocalSammyRunner(config)
            runner.prepare_environment(files)
            result = runner.execute_sammy(files)

            if not result.success:
                return PixelFitResult(
                    row=pixel.row,
                    col=pixel.col,
                    fit_results=None,
                    success=False,
                    error_message=f"SAMMY execution failed: {result.error_message}",
                    chi_squared=None,
                )

            runner.collect_outputs(result)
            # Note: Abstract interface expects cleanup(files), but all concrete implementations
            # (LocalSammyRunner, DockerSammyRunner) use cleanup() without parameters.
            # This is existing technical debt in PLEIADES backends.
            runner.cleanup()

            # Step 6: Parse results
            lpt_file = temp_path / "sammy_output" / "SAMMY.LPT"
            lst_file = temp_path / "sammy_output" / "SAMMY.LST"

            results_manager = ResultsManager(lpt_file_path=lpt_file, lst_file_path=lst_file)

            if not results_manager.run_results.fit_results:
                return PixelFitResult(
                    row=pixel.row,
                    col=pixel.col,
                    fit_results=None,
                    success=False,
                    error_message="No fit results found in SAMMY.LPT",
                    chi_squared=None,
                )

            # Extract final fit results
            final_fit = results_manager.run_results.fit_results[-1]
            chi_sq = final_fit.get_chi_squared_results()

            # Extract chi-squared value (can be None if fit failed to converge)
            chi_squared_value = chi_sq.chi_squared if chi_sq is not None else None

            return PixelFitResult(
                row=pixel.row,
                col=pixel.col,
                fit_results=final_fit,
                success=True,
                error_message=None,
                chi_squared=chi_squared_value,
            )

        except Exception as e:
            logger.exception(f"Exception during pixel fitting at ({pixel.row}, {pixel.col})")
            return PixelFitResult(
                row=pixel.row,
                col=pixel.col,
                fit_results=None,
                success=False,
                error_message=f"Exception: {str(e)}",
                chi_squared=None,
            )


class BatchFittingOrchestrator:
    """Orchestrate parallel SAMMY fitting across hyperspectral imaging pixels.

    Manages execution of thousands of SAMMY fitting jobs with:
    - Parallel execution via ProcessPoolExecutor
    - Checkpointing for resume capability
    - Progress tracking
    - Failure handling and logging

    Example:
        >>> config = ImagingConfig(
        ...     isotopes=["Ta-181"],
        ...     element="Ta",
        ...     mass_number=181,
        ...     density_g_cm3=16.6,
        ...     thickness_mm=0.025,
        ...     atomic_mass_amu=180.9479958
        ... )
        >>> orchestrator = BatchFittingOrchestrator(
        ...     imaging_config=config,
        ...     sammy_executable=Path("/path/to/sammy"),
        ...     n_workers=4
        ... )
        >>> results = orchestrator.fit_pixels(pixel_list, checkpoint_file=Path("checkpoint.pkl"))
    """

    def __init__(
        self,
        imaging_config: ImagingConfig,
        sammy_executable: Path,
        n_workers: int = 4,
        resolution_file: Optional[Path] = None,
    ):
        """Initialize batch fitting orchestrator.

        Args:
            imaging_config: Configuration with isotopes and material properties
            sammy_executable: Path to SAMMY binary
            n_workers: Number of parallel workers (default: 4)
            resolution_file: Optional path to resolution function file

        Raises:
            FileNotFoundError: If SAMMY executable or resolution file doesn't exist
        """
        if not sammy_executable.exists():
            raise FileNotFoundError(f"SAMMY executable not found: {sammy_executable}")

        if resolution_file is not None and not resolution_file.exists():
            raise FileNotFoundError(f"Resolution file not found: {resolution_file}")

        self.imaging_config = imaging_config
        self.sammy_executable = sammy_executable
        self.n_workers = n_workers
        self.resolution_file = resolution_file

    def fit_pixels(
        self,
        pixels: List[PixelSpectrum],
        checkpoint_file: Optional[Path] = None,
        checkpoint_interval: int = 10,
        resume: bool = False,
    ) -> List[PixelFitResult]:
        """Fit all pixels using parallel SAMMY execution.

        Args:
            pixels: List of PixelSpectrum to fit
            checkpoint_file: Optional path to save/load checkpoint
            checkpoint_interval: Save checkpoint every N completed pixels (default: 10)
            resume: If True, resume from existing checkpoint file

        Returns:
            List of PixelFitResult for all pixels

        Raises:
            FileNotFoundError: If resume=True but checkpoint file doesn't exist
            ValueError: If resume=True but checkpoint_file is None
        """
        # Handle empty pixel list
        if not pixels:
            logger.warning("fit_pixels called with empty pixel list")
            return []

        # Validate resume request
        if resume and checkpoint_file is None:
            raise ValueError("Cannot resume without checkpoint_file. Specify checkpoint_file or set resume=False.")

        # Load checkpoint if resuming
        completed: Dict[Tuple[int, int], PixelFitResult] = {}
        if resume and checkpoint_file:
            if not checkpoint_file.exists():
                raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_file}")
            checkpoint = self._load_checkpoint(checkpoint_file)
            completed = checkpoint.completed_pixels
            logger.info(f"Resuming from checkpoint: {len(completed)}/{checkpoint.total_pixels} pixels completed")

        # Filter out already completed pixels
        remaining_pixels = [p for p in pixels if (p.row, p.col) not in completed]
        total_pixels = len(pixels)
        logger.info(f"Fitting {len(remaining_pixels)} pixels ({len(completed)} already completed)")

        # Execute remaining pixels in parallel
        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            # Submit all jobs
            future_to_pixel = {
                executor.submit(
                    _fit_pixel_worker, pixel, self.imaging_config, self.sammy_executable, self.resolution_file
                ): pixel
                for pixel in remaining_pixels
            }

            # Collect results with progress tracking
            iterations_since_checkpoint = 0
            for future in as_completed(future_to_pixel):
                pixel = future_to_pixel[future]
                try:
                    result = future.result()
                    completed[(pixel.row, pixel.col)] = result
                    iterations_since_checkpoint += 1

                    if result.success:
                        chi_sq_str = f"{result.chi_squared:.4f}" if result.chi_squared is not None else "N/A"
                        logger.info(f"Pixel ({pixel.row}, {pixel.col}) SUCCESS: χ² = {chi_sq_str}")
                    else:
                        logger.warning(f"Pixel ({pixel.row}, {pixel.col}) FAILED: {result.error_message}")

                    # Checkpoint at intervals (based on iterations, not total count, to maintain consistency)
                    if checkpoint_file and iterations_since_checkpoint >= checkpoint_interval:
                        self._save_checkpoint(checkpoint_file, completed, total_pixels)
                        logger.info(f"Checkpoint saved: {len(completed)}/{total_pixels} pixels completed")
                        iterations_since_checkpoint = 0

                except Exception as e:
                    logger.exception(f"Exception collecting result for pixel ({pixel.row}, {pixel.col})")
                    completed[(pixel.row, pixel.col)] = PixelFitResult(
                        row=pixel.row,
                        col=pixel.col,
                        fit_results=None,
                        success=False,
                        error_message=f"Executor exception: {str(e)}",
                        chi_squared=None,
                    )

        # Final checkpoint
        if checkpoint_file:
            self._save_checkpoint(checkpoint_file, completed, total_pixels)
            logger.info(f"Final checkpoint saved: {total_pixels}/{total_pixels} pixels completed")

        # Convert to ordered list matching input order
        results = [completed[(p.row, p.col)] for p in pixels]

        # Summary statistics
        n_success = sum(1 for r in results if r.success)
        n_failed = total_pixels - n_success
        logger.info(f"Batch fitting complete: {n_success} success, {n_failed} failed")

        return results

    def _save_checkpoint(
        self, checkpoint_file: Path, completed: Dict[Tuple[int, int], PixelFitResult], total_pixels: int
    ) -> None:
        """Save checkpoint data to file.

        Args:
            checkpoint_file: Path to checkpoint file
            completed: Dictionary of completed PixelFitResults
            total_pixels: Total number of pixels in batch
        """
        checkpoint = CheckpointData(completed_pixels=completed, total_pixels=total_pixels, config=self.imaging_config)
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

    def _load_checkpoint(self, checkpoint_file: Path) -> CheckpointData:
        """Load checkpoint data from file.

        Args:
            checkpoint_file: Path to checkpoint file

        Returns:
            CheckpointData with completed results

        Raises:
            ValueError: If checkpoint config doesn't match current config
        """
        with open(checkpoint_file, "rb") as f:
            checkpoint = pickle.load(f)

        # Validate config consistency - all physics parameters must match
        # to ensure scientifically valid results when resuming
        if checkpoint.config.isotopes != self.imaging_config.isotopes:
            raise ValueError(
                f"Checkpoint isotopes {checkpoint.config.isotopes} != current {self.imaging_config.isotopes}"
            )

        if checkpoint.config.density_g_cm3 != self.imaging_config.density_g_cm3:
            raise ValueError(
                f"Checkpoint density {checkpoint.config.density_g_cm3} g/cm³ != current {self.imaging_config.density_g_cm3} g/cm³"
            )

        if checkpoint.config.thickness_mm != self.imaging_config.thickness_mm:
            raise ValueError(
                f"Checkpoint thickness {checkpoint.config.thickness_mm} mm != current {self.imaging_config.thickness_mm} mm"
            )

        if checkpoint.config.atomic_mass_amu != self.imaging_config.atomic_mass_amu:
            raise ValueError(
                f"Checkpoint atomic mass {checkpoint.config.atomic_mass_amu} amu != current {self.imaging_config.atomic_mass_amu} amu"
            )

        if checkpoint.config.temperature_K != self.imaging_config.temperature_K:
            raise ValueError(
                f"Checkpoint temperature {checkpoint.config.temperature_K} K != current {self.imaging_config.temperature_K} K"
            )

        # Validate energy bounds (directly affect SAMMY fit inputs)
        if checkpoint.config.min_energy_eV != self.imaging_config.min_energy_eV:
            raise ValueError(
                f"Checkpoint min_energy {checkpoint.config.min_energy_eV} eV != current {self.imaging_config.min_energy_eV} eV"
            )

        if checkpoint.config.max_energy_eV != self.imaging_config.max_energy_eV:
            raise ValueError(
                f"Checkpoint max_energy {checkpoint.config.max_energy_eV} eV != current {self.imaging_config.max_energy_eV} eV"
            )

        # Validate abundance settings (directly affect SAMMY fit inputs)
        if checkpoint.config.natural_abundances != self.imaging_config.natural_abundances:
            raise ValueError(
                f"Checkpoint natural_abundances {checkpoint.config.natural_abundances} != current {self.imaging_config.natural_abundances}"
            )

        if checkpoint.config.custom_abundances != self.imaging_config.custom_abundances:
            raise ValueError(
                f"Checkpoint custom_abundances {checkpoint.config.custom_abundances} != current {self.imaging_config.custom_abundances}"
            )

        return checkpoint
