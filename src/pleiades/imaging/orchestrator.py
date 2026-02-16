"""
Batch orchestrator for parallel SAMMY fitting across hyperspectral imaging pixels.

This module provides tools for managing large-scale SAMMY resonance fitting jobs
(262,144+ pixels for 512×512 images) with parallelism, checkpointing, and progress tracking.
"""

import pickle
import signal
import tempfile
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from tqdm import tqdm

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


def _worker_initializer() -> None:
    """Make child processes ignore SIGINT so only the parent process handles it.

    Without this, Ctrl+C sends SIGINT to the entire process group. Each child gets
    KeyboardInterrupt independently, causing BrokenProcessPool and preventing checkpoint saves.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)


class ProgressReporter:
    """Progress bar wrapper for batch pixel fitting using tqdm.

    Provides progress tracking with ETA estimation and success/failure counts.
    Routes output through tqdm.write() to prevent garbled terminal output when
    combined with logging.

    Example:
        >>> with ProgressReporter(total_pixels=1000) as progress:
        ...     for result in results:
        ...         progress.update(1)
        ...         if result.success:
        ...             progress.record_success()
        ...         else:
        ...             progress.record_failure()
    """

    def __init__(self, total_pixels: int):
        self._bar = tqdm(total=total_pixels, desc="Fitting pixels", unit="px", smoothing=0.1)
        self._successes = 0
        self._failures = 0

    def update(self, n: int = 1) -> None:
        """Advance progress bar by n steps."""
        self._bar.update(n)

    def write(self, msg: str) -> None:
        """Output a message through tqdm to prevent garbled output with progress bar."""
        self._bar.write(msg)

    def record_success(self) -> None:
        """Record a successful pixel fit and update the postfix display."""
        self._successes += 1
        self._bar.set_postfix(ok=self._successes, fail=self._failures)

    def record_failure(self) -> None:
        """Record a failed pixel fit and update the postfix display."""
        self._failures += 1
        self._bar.set_postfix(ok=self._successes, fail=self._failures)

    def close(self) -> None:
        """Finalize and close the progress bar."""
        self._bar.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class GracefulShutdownHandler:
    """Two-stage signal handler for graceful shutdown of batch fitting.

    First SIGINT/SIGTERM: Sets shutdown flag, allows in-flight tasks to complete and checkpoint to save.
    Second SIGINT/SIGTERM: Forces immediate exit via SystemExit.

    Example:
        >>> with GracefulShutdownHandler() as handler:
        ...     while not handler.shutdown_requested:
        ...         do_work()
        ...     save_checkpoint()
    """

    def __init__(self):
        self._shutdown_event = threading.Event()
        self._original_handlers: Dict[int, object] = {}

    @property
    def shutdown_requested(self) -> bool:
        """Whether a shutdown signal has been received."""
        return self._shutdown_event.is_set()

    def install(self) -> "GracefulShutdownHandler":
        """Register signal handlers for SIGINT and SIGTERM.

        Signal handlers can only be registered from the main thread. When called from
        a non-main thread (e.g. GUI/service worker threads), signal registration is
        skipped and shutdown_requested will never be set. This avoids a ValueError
        regression for threaded callers of fit_pixels().
        """
        if threading.current_thread() is not threading.main_thread():
            logger.warning("GracefulShutdownHandler: not on main thread, signal handlers not installed")
            return self
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._original_handlers[sig] = signal.signal(sig, self._handler)
        return self

    def uninstall(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()

    def _handler(self, signum, frame):
        """Handle incoming signal with two-stage behavior.

        First signal: sets shutdown flag, allows in-flight tasks to finish and checkpoint to save.
        Second signal: raises SystemExit for immediate termination.

        Note: Raising SystemExit from a signal handler during ProcessPoolExecutor shutdown may leave
        orphaned worker processes. This is a known trade-off -- the second signal is an emergency exit.
        """
        if not self._shutdown_event.is_set():
            self._shutdown_event.set()
            logger.warning(f"Received {signal.Signals(signum).name}. Finishing current tasks, saving checkpoint...")
            logger.warning("Press Ctrl+C again to force exit.")
        else:
            raise SystemExit(1)

    def __enter__(self):
        self.install()
        return self

    def __exit__(self, *args):
        self.uninstall()


def _fit_pixel_worker(
    pixel: PixelSpectrum,
    imaging_config: ImagingConfig,
    sammy_executable: Path,
    resolution_file: Optional[Path] = None,
    shared_json_config: Optional[Path] = None,
    shared_endf_directory: Optional[Path] = None,
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
        shared_json_config: Optional pre-staged JSON config path (shared across workers)
        shared_endf_directory: Optional pre-staged ENDF directory (shared across workers)

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

            # Step 3: Resolve JSON config + ENDF staging
            if shared_json_config is not None or shared_endf_directory is not None:
                if shared_json_config is None or shared_endf_directory is None:
                    raise ValueError("Both shared_json_config and shared_endf_directory must be provided together.")
                if not shared_json_config.exists():
                    raise FileNotFoundError(f"Shared JSON config not found: {shared_json_config}")
                if not shared_endf_directory.exists():
                    raise FileNotFoundError(f"Shared ENDF directory not found: {shared_endf_directory}")
                json_path = shared_json_config
                endf_directory = shared_endf_directory
            else:
                # Fallback mode for direct worker usage (tests/debug) without orchestrator pre-staging.
                json_manager = JsonManager()
                abundances = imaging_config.get_abundances()
                json_path = json_manager.create_json_config(
                    isotopes=imaging_config.isotopes, abundances=abundances, working_dir=temp_path
                )
                endf_directory = temp_path

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
                input_file=inp_file,
                json_config_file=json_path,
                data_file=twenty_file,
                endf_directory=endf_directory,
            )

            config = LocalSammyConfig(
                sammy_executable=sammy_executable,
                working_dir=temp_path / "sammy_working",
                output_dir=temp_path / "sammy_output",
            )

            runner = LocalSammyRunner(config)
            runner.validate_config()
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

        # Ensure coordinates are unique to avoid result overwrite/corruption in keyed storage.
        seen_coords = set()
        for pixel in pixels:
            coord = (pixel.row, pixel.col)
            if coord in seen_coords:
                raise ValueError(
                    f"Duplicate pixel coordinates detected: {coord}. "
                    "Each pixel in a batch must have a unique (row, col) coordinate."
                )
            seen_coords.add(coord)

        # Load checkpoint if resuming
        completed: Dict[Tuple[int, int], PixelFitResult] = {}
        if resume and checkpoint_file:
            if not checkpoint_file.exists():
                raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_file}")
            checkpoint = self._load_checkpoint(checkpoint_file)

            # Checkpoint must be from the same batch shape to avoid mixing stale results.
            if checkpoint.total_pixels != len(pixels):
                raise ValueError(
                    f"Checkpoint total_pixels={checkpoint.total_pixels} does not match current batch "
                    f"size={len(pixels)}. Use a checkpoint created for this exact pixel batch."
                )

            current_coords = {(p.row, p.col) for p in pixels}
            checkpoint_coords = set(checkpoint.completed_pixels.keys())
            invalid_coords = checkpoint_coords - current_coords
            if invalid_coords:
                invalid_coord = sorted(invalid_coords)[0]
                raise ValueError(
                    f"Checkpoint contains pixel {invalid_coord} not present in current batch. "
                    "Use a checkpoint created for this exact pixel batch."
                )

            completed = checkpoint.completed_pixels
            logger.info(f"Resuming from checkpoint: {len(completed)}/{checkpoint.total_pixels} pixels completed")

        # Filter out already completed pixels
        remaining_pixels = [p for p in pixels if (p.row, p.col) not in completed]
        total_pixels = len(pixels)
        logger.info(f"Fitting {len(remaining_pixels)} pixels ({len(completed)} already completed)")

        # Execute remaining pixels in parallel
        if remaining_pixels:
            with tempfile.TemporaryDirectory(prefix="batch_shared_") as shared_workspace_dir:
                shared_json_path, shared_endf_dir = self._prepare_shared_sammy_inputs(Path(shared_workspace_dir))

                with GracefulShutdownHandler() as shutdown_handler:
                    with ProcessPoolExecutor(max_workers=self.n_workers, initializer=_worker_initializer) as executor:
                        # Submit all jobs
                        future_to_pixel = {
                            executor.submit(
                                _fit_pixel_worker,
                                pixel,
                                self.imaging_config,
                                self.sammy_executable,
                                self.resolution_file,
                                shared_json_path,
                                shared_endf_dir,
                            ): pixel
                            for pixel in remaining_pixels
                        }

                        # Collect results with progress tracking
                        iterations_since_checkpoint = 0
                        completed_futures: set = set()
                        with ProgressReporter(total_pixels=len(remaining_pixels)) as progress:
                            for future in as_completed(future_to_pixel):
                                pixel = future_to_pixel[future]
                                try:
                                    result = future.result()
                                    completed[(pixel.row, pixel.col)] = result
                                    iterations_since_checkpoint += 1
                                    progress.update(1)

                                    if result.success:
                                        progress.record_success()
                                        chi_sq_str = (
                                            f"{result.chi_squared:.4f}" if result.chi_squared is not None else "N/A"
                                        )
                                        logger.info(f"Pixel ({pixel.row}, {pixel.col}) SUCCESS: χ² = {chi_sq_str}")
                                    else:
                                        progress.record_failure()
                                        logger.warning(
                                            f"Pixel ({pixel.row}, {pixel.col}) FAILED: {result.error_message}"
                                        )

                                    # Checkpoint at intervals
                                    if checkpoint_file and iterations_since_checkpoint >= checkpoint_interval:
                                        self._save_checkpoint(checkpoint_file, completed, total_pixels)
                                        logger.info(
                                            f"Checkpoint saved: {len(completed)}/{total_pixels} pixels completed"
                                        )
                                        iterations_since_checkpoint = 0

                                except Exception as e:
                                    logger.exception(
                                        f"Exception collecting result for pixel ({pixel.row}, {pixel.col})"
                                    )
                                    completed[(pixel.row, pixel.col)] = PixelFitResult(
                                        row=pixel.row,
                                        col=pixel.col,
                                        fit_results=None,
                                        success=False,
                                        error_message=f"Executor exception: {str(e)}",
                                        chi_squared=None,
                                    )
                                    iterations_since_checkpoint += 1
                                    progress.update(1)
                                    progress.record_failure()

                                    # Checkpoint at intervals (even for exceptions)
                                    if checkpoint_file and iterations_since_checkpoint >= checkpoint_interval:
                                        self._save_checkpoint(checkpoint_file, completed, total_pixels)
                                        logger.info(
                                            f"Checkpoint saved: {len(completed)}/{total_pixels} pixels completed"
                                        )
                                        iterations_since_checkpoint = 0

                                completed_futures.add(future)

                                # Check shutdown AFTER processing the current future to avoid
                                # dropping already-completed results (P1-03 review fix)
                                if shutdown_handler.shutdown_requested:
                                    logger.warning("Shutdown requested, collecting remaining results...")
                                    # Cancel futures that haven't started yet. Running futures
                                    # cannot be cancelled and will complete during executor shutdown.
                                    for f in future_to_pixel:
                                        if not f.done():
                                            f.cancel()
                                    # Collect results from ALL non-cancelled futures we haven't
                                    # processed yet. This includes both already-done futures and
                                    # still-running futures (which we wait for). Without this,
                                    # valid completed fits are lost and replaced with "interrupted"
                                    # placeholders, producing incomplete checkpoints.
                                    for f in future_to_pixel:
                                        if f not in completed_futures and not f.cancelled():
                                            drain_pixel = future_to_pixel[f]
                                            try:
                                                drain_result = f.result()
                                                completed[(drain_pixel.row, drain_pixel.col)] = drain_result
                                                progress.update(1)
                                                if drain_result.success:
                                                    progress.record_success()
                                                else:
                                                    progress.record_failure()
                                            except Exception as e:
                                                completed[(drain_pixel.row, drain_pixel.col)] = PixelFitResult(
                                                    row=drain_pixel.row,
                                                    col=drain_pixel.col,
                                                    fit_results=None,
                                                    success=False,
                                                    error_message=f"Executor exception: {str(e)}",
                                                    chi_squared=None,
                                                )
                                                progress.update(1)
                                                progress.record_failure()
                                    break

        # Final checkpoint
        if checkpoint_file:
            self._save_checkpoint(checkpoint_file, completed, total_pixels)
            logger.info(f"Final checkpoint saved: {len(completed)}/{total_pixels} pixels completed")

        # Convert to ordered list matching input order
        # For shutdown scenarios, fill missing pixels with failure placeholders
        results = []
        for p in pixels:
            coord = (p.row, p.col)
            if coord in completed:
                results.append(completed[coord])
            else:
                results.append(
                    PixelFitResult(
                        row=p.row,
                        col=p.col,
                        fit_results=None,
                        success=False,
                        error_message="Batch fitting interrupted by shutdown signal",
                        chi_squared=None,
                    )
                )

        # Summary statistics
        n_success = sum(1 for r in results if r.success)
        n_failed = total_pixels - n_success
        logger.info(f"Batch fitting complete: {n_success} success, {n_failed} failed")

        return results

    def _prepare_shared_sammy_inputs(self, workspace_dir: Path) -> Tuple[Path, Path]:
        """Stage JSON + ENDF inputs once per batch for worker reuse."""
        shared_inputs_dir = workspace_dir / "shared_sammy_inputs"
        json_manager = JsonManager()
        abundances = self.imaging_config.get_abundances()
        shared_json_path = json_manager.create_json_config(
            isotopes=self.imaging_config.isotopes,
            abundances=abundances,
            working_dir=shared_inputs_dir,
        )
        return shared_json_path, shared_inputs_dir

    def _save_checkpoint(
        self, checkpoint_file: Path, completed: Dict[Tuple[int, int], PixelFitResult], total_pixels: int
    ) -> None:
        """Save checkpoint data to file atomically.

        Writes to a temporary .tmp file first, then atomically replaces the target file.
        This prevents corrupted checkpoints if the process is interrupted mid-write.

        Args:
            checkpoint_file: Path to checkpoint file
            completed: Dictionary of completed PixelFitResults
            total_pixels: Total number of pixels in batch
        """
        checkpoint = CheckpointData(completed_pixels=completed, total_pixels=total_pixels, config=self.imaging_config)
        tmp_file = checkpoint_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "wb") as f:
                pickle.dump(checkpoint, f)
            tmp_file.replace(checkpoint_file)
        except Exception:
            if tmp_file.exists():
                tmp_file.unlink()
            raise

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

        if not isinstance(checkpoint, CheckpointData):
            raise ValueError(f"Invalid checkpoint file: expected CheckpointData, got {type(checkpoint).__name__}")

        # Validate config consistency - all physics parameters must match to ensure
        # scientifically valid results when resuming. Uses Pydantic model equality so
        # new fields added to ImagingConfig are automatically caught.
        if checkpoint.config != self.imaging_config:
            checkpoint_dict = checkpoint.config.model_dump()
            current_dict = self.imaging_config.model_dump()
            mismatched = {
                k: {"checkpoint": checkpoint_dict[k], "current": current_dict[k]}
                for k in checkpoint_dict
                if checkpoint_dict.get(k) != current_dict.get(k)
            }
            raise ValueError(f"Checkpoint config does not match current config. Mismatched fields: {mismatched}")

        return checkpoint
