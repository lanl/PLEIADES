"""
Batch orchestrator for parallel SAMMY fitting across hyperspectral imaging pixels.

This module provides tools for managing large-scale SAMMY resonance fitting jobs
(262,144+ pixels for 512×512 images) with parallelism, checkpointing, and progress tracking.
"""

import contextlib
import pickle
import signal
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

from tqdm import tqdm

from pleiades.imaging.config import ImagingConfig
from pleiades.imaging.models import PixelFitResult, PixelSpectrum
from pleiades.imaging.temp_manager import _BYTES_PER_GB, TempFileManager
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
    Also exposes a write() helper that routes messages through tqdm.write() to
    prevent garbled terminal output when combined with logging.

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


def _check_worker_disk_space(
    base_dir: Path,
    max_disk_usage_gb: Optional[float],
    initial_free_gb: Optional[float],
    required_gb: float = 0.1,
) -> Optional[str]:
    """Check disk space in a worker subprocess, replicating TempFileManager logic.

    Uses ``_BYTES_PER_GB`` from ``temp_manager`` to stay consistent with the
    parent-process disk checks.

    Returns None if space is sufficient, or an error message string if not.
    """
    import shutil

    try:
        usage = shutil.disk_usage(base_dir)
        free_gb = usage.free / _BYTES_PER_GB
        if free_gb < required_gb:
            return f"{free_gb:.2f} GB free, need at least {required_gb} GB"
        if initial_free_gb is not None and max_disk_usage_gb is not None:
            consumed_gb = initial_free_gb - free_gb
            if consumed_gb > max_disk_usage_gb:
                return f"{consumed_gb:.2f} GB consumed, limit is {max_disk_usage_gb} GB"
    except Exception as e:
        return f"disk check failed: {e}"
    return None


def _fit_pixel_worker(
    pixel: PixelSpectrum,
    imaging_config: ImagingConfig,
    sammy_executable: Path,
    resolution_file: Optional[Path] = None,
    shared_json_config: Optional[Path] = None,
    shared_endf_directory: Optional[Path] = None,
    temp_base_dir: Optional[Path] = None,
    cleanup_policy: str = "immediate",
    attempt_id: int = 0,
    max_disk_usage_gb: Optional[float] = None,
    initial_free_gb: Optional[float] = None,
) -> PixelFitResult:
    """Worker function to fit a single pixel using SAMMY.

    This function runs in a subprocess and performs the complete SAMMY workflow:
    1. Export pixel spectrum to CSV
    2. Convert CSV to SAMMY .twenty format
    3. Create JSON config (auto-downloads ENDF files)
    4. Create .inp file
    5. Execute SAMMY via LocalSammyRunner
    6. Parse results

    Args:
        pixel: PixelSpectrum to fit
        imaging_config: Configuration with isotopes and material properties
        sammy_executable: Path to SAMMY binary
        resolution_file: Optional path to resolution function file
        shared_json_config: Optional pre-staged JSON config path (shared across workers)
        shared_endf_directory: Optional pre-staged ENDF directory (shared across workers)
        temp_base_dir: Optional base directory for managed temp files. When provided,
            creates per-pixel workspaces under this directory instead of the system temp.
        cleanup_policy: Cleanup policy when using temp_base_dir ("immediate", "batch", "manual").
        attempt_id: Attempt number for this pixel (0 = first attempt, 1+ = retries).
            Used to create unique workspace directories so that timed-out zombie workers
            from a previous attempt do not collide with retries.
        max_disk_usage_gb: Maximum disk usage limit from TempFileManager. When set,
            the worker checks disk space before creating the workspace.
        initial_free_gb: Free space recorded at batch start, used with max_disk_usage_gb
            to enforce the consumed-space limit.

    Returns:
        PixelFitResult with fitted abundances and chi-squared, or failure info
    """
    if temp_base_dir is not None:
        # Ensure base dir exists so shutil.disk_usage doesn't fail with FileNotFoundError
        temp_base_dir.mkdir(parents=True, exist_ok=True)
        # Check disk space before creating workspace (replicates TempFileManager.check_disk_space)
        disk_err = _check_worker_disk_space(temp_base_dir, max_disk_usage_gb, initial_free_gb)
        if disk_err is not None:
            return PixelFitResult(
                row=pixel.row,
                col=pixel.col,
                fit_results=None,
                success=False,
                error_message=f"Disk space check failed: {disk_err}",
                chi_squared=None,
            )
        # Include attempt_id in dir name so retries don't collide with timed-out zombie workers
        dir_name = f"pixel_{pixel.row}_{pixel.col}_a{attempt_id}"
        temp_path = temp_base_dir / dir_name
        # Remove any stale workspace from a previous crashed run to avoid contamination
        if temp_path.exists():
            import shutil

            shutil.rmtree(temp_path, ignore_errors=True)
        temp_path.mkdir(parents=True, exist_ok=True)
    else:
        temp_path = None  # Sentinel; set below in context manager

    return _fit_pixel_worker_impl(
        pixel,
        imaging_config,
        sammy_executable,
        resolution_file,
        shared_json_config,
        shared_endf_directory,
        temp_path,
        cleanup_policy,
    )


def _fit_pixel_worker_impl(
    pixel: PixelSpectrum,
    imaging_config: ImagingConfig,
    sammy_executable: Path,
    resolution_file: Optional[Path],
    shared_json_config: Optional[Path],
    shared_endf_directory: Optional[Path],
    temp_path: Optional[Path],
    cleanup_policy: str,
) -> PixelFitResult:
    """Inner implementation for _fit_pixel_worker.

    Separated so that the managed-dir path and the tempfile.TemporaryDirectory fallback
    share the same SAMMY workflow code without duplicating the try/except block.
    """
    import shutil

    # If no managed temp_path was provided, fall back to a system temp directory
    ctx = None
    if temp_path is None:
        ctx = tempfile.TemporaryDirectory(prefix=f"pixel_{pixel.row}_{pixel.col}_")
        temp_path = Path(ctx.__enter__())

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

            # Copy shared files into the worker's local temp directory so that
            # timed-out workers remain self-contained after the shared workspace
            # is torn down by the main process (SammyFilesMultiMode.move_to_working_dir
            # would otherwise create symlinks back into the shared directory,
            # breaking with ENOENT when that directory is deleted).
            local_json_path = temp_path / shared_json_config.name
            shutil.copy2(shared_json_config, local_json_path)
            json_path = local_json_path

            local_endf_dir = temp_path / "endf_local"
            local_endf_dir.mkdir(exist_ok=True)
            for endf_file in shared_endf_directory.iterdir():
                if endf_file.is_file():
                    shutil.copy2(endf_file, local_endf_dir / endf_file.name)
            endf_directory = local_endf_dir
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
        fit_config = imaging_config.to_fit_config()
        dataset_metadata = imaging_config.to_dataset_metadata()
        InpManager.create_multi_isotope_inp(
            inp_file,
            fit_config=fit_config,
            title=f"Pixel ({pixel.row}, {pixel.col}) resonance fitting",
            dataset_metadata=dataset_metadata,
            resolution_file_path=resolution_file,
        )

        # Step 5: Execute SAMMY
        files = SammyFilesMultiMode(
            input_file=inp_file,
            json_config_file=json_path,
            data_file=twenty_file,
            endf_directory=endf_directory,
            fit_abundances=imaging_config.fit_abundances,
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

        # Ensure nuclear_data.isotopes is populated.
        #
        # For single-isotope fits, SAMMY does not output the "Isotopic
        # abundance and mass for each nuclide" section in the LPT, so the
        # parser legitimately returns an empty isotopes list.  In that case
        # we populate from config with abundance=1.0.
        #
        # For multi-isotope fits, an empty parse result means the LPT
        # format changed or parsing failed — that must be surfaced as a
        # failure, not papered over with config defaults.
        nuclear = getattr(final_fit, "nuclear_data", None)
        if nuclear is not None:
            parsed_isotopes = getattr(nuclear, "isotopes", None) or []
            n_config_isotopes = len(imaging_config.isotopes)

            if len(parsed_isotopes) == n_config_isotopes:
                # LPT parsed the expected number of isotopes — just inject names
                for iso_param, iso_name in zip(parsed_isotopes, imaging_config.isotopes):
                    if iso_param.isotope_information is not None:
                        iso_param.isotope_information.name = iso_name
            elif len(parsed_isotopes) == 0 and n_config_isotopes == 1:
                # Single-isotope: SAMMY omits isotope section, populate from config
                from pleiades.nuclear.isotopes.models import IsotopeInfo
                from pleiades.nuclear.models import IsotopeParameters

                iso_name = imaging_config.isotopes[0]
                iso_info = IsotopeInfo.from_string(iso_name)
                iso_param = IsotopeParameters(
                    isotope_information=iso_info,
                    abundance=1.0,
                )
                nuclear.isotopes.append(iso_param)
            elif len(parsed_isotopes) == 0 and n_config_isotopes > 1:
                # Multi-isotope but parser found nothing — this is a real failure
                return PixelFitResult(
                    row=pixel.row,
                    col=pixel.col,
                    fit_results=None,
                    success=False,
                    error_message=(
                        f"LPT parser returned 0 isotopes but {n_config_isotopes} "
                        f"were expected; isotope abundance data missing from SAMMY output"
                    ),
                    chi_squared=None,
                )

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
    finally:
        # Clean up temp directory
        if ctx is not None:
            ctx.__exit__(None, None, None)
        elif cleanup_policy == "immediate":
            shutil.rmtree(temp_path, ignore_errors=True)


class BatchFittingOrchestrator:
    """Orchestrate parallel SAMMY fitting across hyperspectral imaging pixels.

    Manages execution of thousands of SAMMY fitting jobs with:
    - Parallel execution via ProcessPoolExecutor
    - Checkpointing for resume capability
    - Progress tracking
    - Failure handling and logging

    Example:
        >>> config = ImagingConfig(
        ...     isotopes=["Ta-181"], element="Ta", mass_number=181,
        ...     density_g_cm3=16.6, thickness_mm=0.025, atomic_mass_amu=180.9479958
        ... )
        >>> orchestrator = BatchFittingOrchestrator(
        ...     imaging_config=config, sammy_executable=Path("/path/to/sammy"), n_workers=4
        ... )
        >>> results = orchestrator.fit_pixels(pixel_list, checkpoint_file=Path("checkpoint.pkl"))
    """

    def __init__(
        self,
        imaging_config: ImagingConfig,
        sammy_executable: Path,
        n_workers: int = 4,
        resolution_file: Optional[Path] = None,
        temp_manager: Optional[TempFileManager] = None,
    ):
        """Initialize batch fitting orchestrator.

        Args:
            imaging_config: Configuration with isotopes and material properties
            sammy_executable: Path to SAMMY binary
            n_workers: Number of parallel workers (default: 4)
            resolution_file: Optional path to resolution function file
            temp_manager: Optional TempFileManager for controlling workspace
                locations and cleanup policy. If None, uses system temp directory
                with immediate cleanup (original behavior).

        Raises:
            FileNotFoundError: If SAMMY executable or resolution file doesn't exist
        """
        sammy_executable = Path(sammy_executable)
        if not sammy_executable.exists():
            raise FileNotFoundError(f"SAMMY executable not found: {sammy_executable}")

        if resolution_file is not None and not resolution_file.exists():
            raise FileNotFoundError(f"Resolution file not found: {resolution_file}")

        self.imaging_config = imaging_config
        self.sammy_executable = sammy_executable
        self.n_workers = n_workers
        self.resolution_file = resolution_file
        self.temp_manager = temp_manager

    def fit_pixels(
        self,
        pixels: "Union[Callable[[], Iterable[PixelSpectrum]], Iterable[PixelSpectrum]]",
        checkpoint_file: Optional[Path] = None,
        checkpoint_interval: int = 10,
        resume: bool = False,
        timeout_per_job: Optional[float] = None,
        max_retries: int = 0,
    ) -> List[PixelFitResult]:
        """Fit all pixels using parallel SAMMY execution.

        Args:
            pixels: Pixel source — either a callable (factory) that returns a
                fresh ``Iterable[PixelSpectrum]`` each time it is called, or a
                plain ``Iterable[PixelSpectrum]``.  When a factory is provided,
                pixel data is **never** fully materialised in memory: a
                lightweight first pass collects only ``(row, col)`` coordinates
                for validation, and a second pass streams pixels directly to
                the executor.
            checkpoint_file: Optional path to save/load checkpoint
            checkpoint_interval: Save checkpoint every N completed pixels (default: 10)
            resume: If True, resume from existing checkpoint file
            timeout_per_job: Maximum seconds per pixel job. None means no timeout.
                When set, uses ``concurrent.futures.wait(FIRST_COMPLETED)`` to
                process futures in completion order while enforcing a per-job
                deadline. Only futures that are actively ``running()`` past the
                deadline are marked as timed out -- queued futures that have not
                started yet are left alone until a worker becomes available.
                Already-running tasks cannot be killed by ``Future.cancel()``;
                timed-out workers continue consuming resources until they finish.
                When combined with ``max_retries``, each retry round uses a
                fresh ``ProcessPoolExecutor`` so that timed-out zombie workers
                do not starve retry submissions.
            max_retries: Number of retry attempts for failed pixels (default: 0).
                A value of 2 means each pixel can be attempted up to 3 times total.

        Returns:
            List of PixelFitResult for all pixels

        Raises:
            FileNotFoundError: If resume=True but checkpoint file doesn't exist
            ValueError: If resume=True but checkpoint_file is None, or invalid parameters
        """
        # --- Normalise pixel source into a re-iterable factory ---
        if callable(pixels):
            pixel_factory = pixels
        elif isinstance(pixels, list):
            pixel_factory = lambda: iter(pixels)  # noqa: E731
        else:
            # One-shot iterable (generator, etc.) — must materialise once
            _cached = list(pixels)
            pixel_factory = lambda: iter(_cached)  # noqa: E731

        # --- Lightweight first pass: collect (row, col) for validation ---
        all_coords: List[Tuple[int, int]] = []
        seen_coords: Set[Tuple[int, int]] = set()
        for p in pixel_factory():
            coord = (p.row, p.col)
            if coord in seen_coords:
                raise ValueError(
                    f"Duplicate pixel coordinates detected: {coord}. "
                    "Each pixel in a batch must have a unique (row, col) coordinate."
                )
            seen_coords.add(coord)
            all_coords.append(coord)

        total_pixels = len(all_coords)

        if total_pixels == 0:
            logger.warning("fit_pixels called with empty pixel source")
            return []

        # Validate parameters
        if timeout_per_job is not None and timeout_per_job <= 0:
            raise ValueError(f"timeout_per_job must be positive, got {timeout_per_job}")
        if max_retries < 0:
            raise ValueError(f"max_retries must be non-negative, got {max_retries}")
        if checkpoint_interval <= 0:
            raise ValueError(f"checkpoint_interval must be positive, got {checkpoint_interval}")

        # Validate resume request
        if resume and checkpoint_file is None:
            raise ValueError("Cannot resume without checkpoint_file. Specify checkpoint_file or set resume=False.")

        # Load checkpoint if resuming
        completed: Dict[Tuple[int, int], PixelFitResult] = {}
        if resume and checkpoint_file:
            if not checkpoint_file.exists():
                raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_file}")
            checkpoint = self._load_checkpoint(checkpoint_file)

            # Checkpoint must be from the same batch shape to avoid mixing stale results.
            if checkpoint.total_pixels != total_pixels:
                raise ValueError(
                    f"Checkpoint total_pixels={checkpoint.total_pixels} does not match current batch "
                    f"size={total_pixels}. Use a checkpoint created for this exact pixel batch."
                )

            checkpoint_coords = set(checkpoint.completed_pixels.keys())
            invalid_coords = checkpoint_coords - seen_coords
            if invalid_coords:
                invalid_coord = sorted(invalid_coords)[0]
                raise ValueError(
                    f"Checkpoint contains pixel {invalid_coord} not present in current batch. "
                    "Use a checkpoint created for this exact pixel batch."
                )

            completed = checkpoint.completed_pixels
            logger.info(f"Resuming from checkpoint: {len(completed)}/{checkpoint.total_pixels} pixels completed")

        remaining_coords = seen_coords - set(completed.keys())
        logger.info(f"Fitting {len(remaining_coords)} pixels ({len(completed)} already completed)")

        # Execute remaining pixels in parallel
        if remaining_coords:
            with contextlib.ExitStack() as exit_stack:
                # Enter TempFileManager context first so _initial_free_gb is recorded
                # (enables disk-cap enforcement in workers) and __exit__ runs cleanup
                # for non-manual policies when the batch completes.
                if self.temp_manager is not None:
                    exit_stack.enter_context(self.temp_manager)
                    shared_workspace_dir = exit_stack.enter_context(self.temp_manager.shared_workspace("batch_shared"))
                else:
                    shared_workspace_dir = exit_stack.enter_context(tempfile.TemporaryDirectory(prefix="batch_shared_"))

                shared_json_path, shared_endf_dir = self._prepare_shared_sammy_inputs(Path(shared_workspace_dir))

                with GracefulShutdownHandler() as shutdown_handler:
                    # Accumulate all future-to-coord maps for post-executor drain
                    all_future_maps: List[Dict] = []
                    # Track actual attempts per pixel for accurate retry annotation
                    attempt_counts: Dict[Tuple[int, int], int] = {}

                    # --- Second pass: stream pixels to executor (no list) ---
                    remaining_iter = (p for p in pixel_factory() if (p.row, p.col) in remaining_coords)

                    executor = ProcessPoolExecutor(max_workers=self.n_workers, initializer=_worker_initializer)
                    try:
                        future_to_coord, submit_fn = self._submit_pixels_bounded(
                            executor,
                            remaining_iter,
                            shared_json_path,
                            shared_endf_dir,
                            max_in_flight=self.n_workers * 4,
                        )
                        all_future_maps.append(future_to_coord)
                        for coord in future_to_coord.values():
                            attempt_counts[coord] = 1

                        self._collect_results(
                            future_to_coord,
                            completed,
                            total_pixels,
                            checkpoint_file,
                            checkpoint_interval,
                            shutdown_handler,
                            timeout_per_job,
                            submit_fn=submit_fn,
                            batch_size=len(remaining_coords),
                        )
                    finally:
                        # When timeout is enabled, use non-blocking shutdown to avoid
                        # waiting for timed-out zombie workers. Without timeout, wait
                        # normally for clean process cleanup.
                        if timeout_per_job is not None:
                            executor.shutdown(wait=False, cancel_futures=True)
                        else:
                            executor.shutdown(wait=True)

                    # Retry failed pixels.
                    # Each retry round uses a FRESH executor so that timed-out workers
                    # from the previous round (which cannot be killed) do not occupy
                    # worker slots and starve retry submissions.
                    if max_retries > 0:
                        for retry_round in range(max_retries):
                            if shutdown_handler.shutdown_requested:
                                break
                            failed_coords = {c for c, r in completed.items() if not r.success and c in remaining_coords}
                            if not failed_coords:
                                break
                            logger.info(
                                f"Retry round {retry_round + 1}/{max_retries}: {len(failed_coords)} pixels to retry"
                            )
                            # Re-iterate factory to get pixel data for failed coords only
                            retry_iter = (p for p in pixel_factory() if (p.row, p.col) in failed_coords)
                            retry_executor = ProcessPoolExecutor(
                                max_workers=self.n_workers, initializer=_worker_initializer
                            )
                            try:
                                retry_futures, retry_submit_fn = self._submit_pixels_bounded(
                                    retry_executor,
                                    retry_iter,
                                    shared_json_path,
                                    shared_endf_dir,
                                    attempt_round=retry_round + 1,
                                )
                                all_future_maps.append(retry_futures)
                                # Count all failed coords (not just the initial in-flight window).
                                for coord in failed_coords:
                                    attempt_counts[coord] = attempt_counts.get(coord, 0) + 1
                                self._collect_results(
                                    retry_futures,
                                    completed,
                                    total_pixels,
                                    checkpoint_file,
                                    checkpoint_interval,
                                    shutdown_handler,
                                    timeout_per_job,
                                    submit_fn=retry_submit_fn,
                                    batch_size=len(failed_coords),
                                )
                            finally:
                                if timeout_per_job is not None:
                                    retry_executor.shutdown(wait=False, cancel_futures=True)
                                else:
                                    retry_executor.shutdown(wait=True)

                        # Annotate exhausted retries with actual attempt count
                        for coord, result in completed.items():
                            if not result.success and coord in remaining_coords:
                                actual_attempts = attempt_counts.get(coord, 1)
                                completed[coord] = PixelFitResult(
                                    row=result.row,
                                    col=result.col,
                                    fit_results=None,
                                    success=False,
                                    error_message=(
                                        f"Failed after {actual_attempts} attempts (last error: {result.error_message})"
                                    ),
                                    chi_squared=None,
                                )

                    # Post-executor drain: collect any results not yet in `completed`
                    # (futures that completed after shutdown but before drain).
                    # Drain ALL future maps (initial + retry rounds).
                    for ftmap in all_future_maps:
                        for f, coord in ftmap.items():
                            if coord not in completed and f.done() and not f.cancelled():
                                try:
                                    result = f.result()
                                    completed[coord] = result
                                except Exception as e:
                                    row, col = coord
                                    completed[coord] = PixelFitResult(
                                        row=row,
                                        col=col,
                                        fit_results=None,
                                        success=False,
                                        error_message=f"Executor exception: {str(e)}",
                                        chi_squared=None,
                                    )

        # Final checkpoint
        if checkpoint_file:
            self._save_checkpoint(checkpoint_file, completed, total_pixels)
            logger.info(f"Final checkpoint saved: {len(completed)}/{total_pixels} pixels completed")

        # Convert to ordered list matching input coord order
        # For shutdown scenarios, fill missing pixels with failure placeholders
        results = []
        for coord in all_coords:
            if coord in completed:
                results.append(completed[coord])
            else:
                row, col = coord
                results.append(
                    PixelFitResult(
                        row=row,
                        col=col,
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

    def _submit_pixels(
        self,
        executor: ProcessPoolExecutor,
        pixels: Iterable[PixelSpectrum],
        shared_json_path: Path,
        shared_endf_dir: Path,
        attempt_round: int = 0,
    ) -> Dict[Future, Tuple[int, int]]:
        """Submit pixel fitting jobs to the executor.

        Each pixel is pickled and sent to a worker on submission; the returned
        dict maps futures to lightweight ``(row, col)`` coordinate tuples so
        that the caller never needs to keep the heavy ``PixelSpectrum`` objects
        in memory.

        Args:
            executor: ProcessPoolExecutor to submit jobs to.
            pixels: Iterable of PixelSpectrum to fit (consumed once).
            shared_json_path: Path to pre-staged JSON config.
            shared_endf_dir: Path to pre-staged ENDF directory.
            attempt_round: Attempt number (0 = first, 1+ = retries). Included in
                workspace directory names to prevent collisions with timed-out workers.
        """
        temp_base_dir = self.temp_manager.base_dir if self.temp_manager is not None else None
        cleanup_policy = self.temp_manager.cleanup_policy if self.temp_manager is not None else "immediate"
        max_disk_usage_gb = self.temp_manager.max_disk_usage_gb if self.temp_manager is not None else None
        initial_free_gb = self.temp_manager.initial_free_gb if self.temp_manager is not None else None

        return {
            executor.submit(
                _fit_pixel_worker,
                pixel,
                self.imaging_config,
                self.sammy_executable,
                self.resolution_file,
                shared_json_path,
                shared_endf_dir,
                temp_base_dir,
                cleanup_policy,
                attempt_round,
                max_disk_usage_gb,
                initial_free_gb,
            ): (pixel.row, pixel.col)
            for pixel in pixels
        }

    def _submit_pixels_bounded(
        self,
        executor: ProcessPoolExecutor,
        pixels: Iterable[PixelSpectrum],
        shared_json_path: Path,
        shared_endf_dir: Path,
        attempt_round: int = 0,
        max_in_flight: Optional[int] = None,
    ) -> Tuple[Dict[Future, Tuple[int, int]], Optional[Callable[[], Optional[Future]]]]:
        """Submit an initial bounded window of pixels and return a submit_fn for the rest.

        Unlike ``_submit_pixels`` (which eagerly queues every pixel), this method
        submits at most ``max_in_flight`` futures upfront. The caller passes the
        returned ``submit_fn`` to ``_collect_results`` so that one new future is
        submitted for each future that completes, keeping in-flight memory bounded.

        Args:
            executor: ProcessPoolExecutor to submit jobs to.
            pixels: Iterable of PixelSpectrum (consumed incrementally by submit_fn).
            shared_json_path: Path to the pre-staged JSON config.
            shared_endf_dir: Path to the pre-staged ENDF directory.
            attempt_round: Attempt number (0 = first pass, 1+ = retries).
            max_in_flight: Maximum futures to keep queued at once.
                Defaults to ``n_workers * 4``.

        Returns:
            Tuple of (initial future_to_coord dict, submit_fn).
            submit_fn returns the new Future on each call or None when exhausted.
            future_to_coord is updated in-place by submit_fn as new pixels are submitted.
        """
        if max_in_flight is None:
            max_in_flight = self.n_workers * 4

        temp_base_dir = self.temp_manager.base_dir if self.temp_manager is not None else None
        cleanup_policy = self.temp_manager.cleanup_policy if self.temp_manager is not None else "immediate"
        max_disk_usage_gb = self.temp_manager.max_disk_usage_gb if self.temp_manager is not None else None
        initial_free_gb = self.temp_manager.initial_free_gb if self.temp_manager is not None else None

        future_to_coord: Dict[Future, Tuple[int, int]] = {}
        pixels_iter = iter(pixels)
        exhausted = False

        def _do_submit(pixel: PixelSpectrum) -> Future:
            future = executor.submit(
                _fit_pixel_worker,
                pixel,
                self.imaging_config,
                self.sammy_executable,
                self.resolution_file,
                shared_json_path,
                shared_endf_dir,
                temp_base_dir,
                cleanup_policy,
                attempt_round,
                max_disk_usage_gb,
                initial_free_gb,
            )
            future_to_coord[future] = (pixel.row, pixel.col)
            return future

        def submit_fn() -> Optional[Future]:
            nonlocal exhausted
            if exhausted:
                return None
            try:
                return _do_submit(next(pixels_iter))
            except StopIteration:
                exhausted = True
                return None

        # Fill the initial window
        while len(future_to_coord) < max_in_flight:
            if submit_fn() is None:
                break

        return future_to_coord, (None if exhausted else submit_fn)

    def _maybe_checkpoint(
        self,
        checkpoint_file: Optional[Path],
        iterations_since_checkpoint: int,
        checkpoint_interval: int,
        completed: Dict[Tuple[int, int], PixelFitResult],
        total_pixels: int,
    ) -> int:
        """Save checkpoint if enough iterations have passed since the last one.

        Returns:
            Updated iterations_since_checkpoint (reset to 0 if checkpoint saved).
        """
        if checkpoint_file and iterations_since_checkpoint >= checkpoint_interval:
            self._save_checkpoint(checkpoint_file, completed, total_pixels)
            logger.info(f"Checkpoint saved: {len(completed)}/{total_pixels} pixels completed")
            return 0
        return iterations_since_checkpoint

    def _collect_results(
        self,
        future_to_coord: Dict[Future, Tuple[int, int]],
        completed: Dict[Tuple[int, int], PixelFitResult],
        total_pixels: int,
        checkpoint_file: Optional[Path],
        checkpoint_interval: int,
        shutdown_handler: GracefulShutdownHandler,
        timeout_per_job: Optional[float],
        submit_fn: Optional[Callable[[], Optional[Future]]] = None,
        batch_size: Optional[int] = None,
    ) -> None:
        """Collect results from submitted futures with progress tracking.

        When timeout_per_job is set, uses ``concurrent.futures.wait()`` with
        ``FIRST_COMPLETED`` to process futures in completion order while
        enforcing a per-job deadline. Only futures that are actively
        ``running()`` past the deadline are marked as timed out -- queued
        futures that have not started yet are **not** falsely timed out.

        When no timeout, uses ``wait(FIRST_COMPLETED)`` with a mutable pending
        set so that ``submit_fn`` can inject new futures as slots open up
        (bounded in-flight submission).

        Args:
            submit_fn: Optional callable that submits the next pixel and
                returns its Future, or None when the pixel stream is exhausted.
                When provided, one new future is submitted for each completed
                future, keeping the in-flight count bounded.
            batch_size: Total pixels expected in this collection round, used
                for the progress bar. Defaults to ``len(future_to_coord)``
                (i.e. eager-submit compat).

        Timed-out futures have ``cancel()`` called as a best-effort cleanup.
        Note: ``ProcessPoolExecutor`` only cancels tasks that haven't started;
        already-running tasks continue until they finish.
        """
        iterations_since_checkpoint = 0

        if timeout_per_job is not None:
            self._collect_results_with_timeout(
                future_to_coord,
                completed,
                total_pixels,
                checkpoint_file,
                checkpoint_interval,
                shutdown_handler,
                timeout_per_job,
                submit_fn=submit_fn,
                batch_size=batch_size,
            )
            return

        progress_total = batch_size if batch_size is not None else len(future_to_coord)
        pending: Set[Future] = set(future_to_coord.keys())
        with ProgressReporter(total_pixels=progress_total) as progress:
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                shutdown_triggered = False
                for future in done:
                    coord = future_to_coord[future]
                    row, col = coord
                    try:
                        result = future.result()
                        completed[coord] = result
                        progress.update(1)

                        if result.success:
                            progress.record_success()
                            chi_sq_str = f"{result.chi_squared:.4f}" if result.chi_squared is not None else "N/A"
                            logger.info(f"Pixel ({row}, {col}) SUCCESS: χ² = {chi_sq_str}")
                        else:
                            progress.record_failure()
                            logger.warning(f"Pixel ({row}, {col}) FAILED: {result.error_message}")

                    except Exception as e:
                        logger.exception(f"Exception collecting result for pixel ({row}, {col})")
                        completed[coord] = PixelFitResult(
                            row=row,
                            col=col,
                            fit_results=None,
                            success=False,
                            error_message=f"Executor exception: {str(e)}",
                            chi_squared=None,
                        )
                        progress.update(1)
                        progress.record_failure()

                    # Bounded submission: refill one slot for each completed future.
                    if submit_fn is not None:
                        new_future = submit_fn()
                        if new_future is not None:
                            pending.add(new_future)

                    iterations_since_checkpoint += 1
                    iterations_since_checkpoint = self._maybe_checkpoint(
                        checkpoint_file, iterations_since_checkpoint, checkpoint_interval, completed, total_pixels
                    )

                    # On shutdown: cancel remaining pending futures and stop immediately.
                    # Check inside the per-future loop so we react as soon as possible
                    # rather than after draining the entire batch of completed futures.
                    if shutdown_handler.shutdown_requested:
                        logger.warning("Shutdown requested, cancelling pending futures...")
                        for f in pending:
                            if not f.done():
                                f.cancel()
                        shutdown_triggered = True
                        break

                if shutdown_triggered:
                    break

    def _collect_results_with_timeout(
        self,
        future_to_coord: Dict[Future, Tuple[int, int]],
        completed: Dict[Tuple[int, int], PixelFitResult],
        total_pixels: int,
        checkpoint_file: Optional[Path],
        checkpoint_interval: int,
        shutdown_handler: GracefulShutdownHandler,
        timeout_per_job: float,
        submit_fn: Optional[Callable[[], Optional[Future]]] = None,
        batch_size: Optional[int] = None,
    ) -> None:
        """Collect results using ``wait()`` with per-job timeout enforcement.

        Uses ``concurrent.futures.wait(FIRST_COMPLETED)`` in a loop to process
        futures in completion order while enforcing a per-job deadline. Each
        future's running start time is tracked: when a future is first observed
        as ``running()``, its start time is recorded. A future is only marked as
        timed out if it has been ``running()`` for longer than ``timeout_per_job``
        seconds, regardless of whether other futures are completing concurrently.

        Queued futures that have not started yet are left alone -- they will run
        once a worker becomes available. If no progress is made (no futures
        complete and no running futures remain to time out) for two consecutive
        timeout windows, all remaining pending futures are cancelled as a safety
        net to prevent infinite loops.
        """
        pending: Set[Future] = set(future_to_coord.keys())
        running_start_times: Dict[Future, float] = {}
        iterations_since_checkpoint = 0
        stall_rounds = 0
        now = time.monotonic()

        # Record start times for futures that are already running before
        # the first wait() call, so their timeout clock starts immediately
        # rather than being deferred by one timeout window.
        for f in pending:
            if f.running():
                running_start_times[f] = now

        progress_total = batch_size if batch_size is not None else len(future_to_coord)
        with ProgressReporter(total_pixels=progress_total) as progress:
            while pending and not shutdown_handler.shutdown_requested:
                # Wait for at least one future to complete, up to timeout_per_job
                done, pending = wait(pending, timeout=timeout_per_job, return_when=FIRST_COMPLETED)
                now = time.monotonic()

                # Process completed futures
                for future in done:
                    running_start_times.pop(future, None)
                    coord = future_to_coord[future]
                    row, col = coord
                    try:
                        result = future.result()
                        completed[coord] = result
                        progress.update(1)
                        if result.success:
                            progress.record_success()
                            chi_sq_str = f"{result.chi_squared:.4f}" if result.chi_squared is not None else "N/A"
                            logger.info(f"Pixel ({row}, {col}) SUCCESS: χ² = {chi_sq_str}")
                        else:
                            progress.record_failure()
                            logger.warning(f"Pixel ({row}, {col}) FAILED: {result.error_message}")
                    except Exception as e:
                        logger.exception(f"Exception collecting result for pixel ({row}, {col})")
                        completed[coord] = PixelFitResult(
                            row=row,
                            col=col,
                            fit_results=None,
                            success=False,
                            error_message=f"Executor exception: {str(e)}",
                            chi_squared=None,
                        )
                        progress.update(1)
                        progress.record_failure()

                    # Bounded submission: refill one slot for each completed future.
                    if submit_fn is not None:
                        new_future = submit_fn()
                        if new_future is not None:
                            pending.add(new_future)

                    iterations_since_checkpoint += 1
                    iterations_since_checkpoint = self._maybe_checkpoint(
                        checkpoint_file, iterations_since_checkpoint, checkpoint_interval, completed, total_pixels
                    )

                # Record start times for newly-running futures
                for f in pending:
                    if f not in running_start_times and f.running():
                        running_start_times[f] = now

                # Check for per-job timeout: any running future that has exceeded the deadline
                timed_out_futures = [
                    f for f in pending if f in running_start_times and (now - running_start_times[f]) >= timeout_per_job
                ]
                for future in timed_out_futures:
                    coord = future_to_coord[future]
                    row, col = coord
                    elapsed = now - running_start_times[future]
                    logger.warning(f"Pixel ({row}, {col}) timed out after {elapsed:.1f}s")
                    future.cancel()  # Best-effort; won't stop already-running process
                    completed[coord] = PixelFitResult(
                        row=row,
                        col=col,
                        fit_results=None,
                        success=False,
                        error_message=f"Pixel ({row}, {col}) timed out after {timeout_per_job}s",
                        chi_squared=None,
                    )
                    pending.discard(future)
                    running_start_times.pop(future, None)
                    progress.update(1)
                    progress.record_failure()
                    iterations_since_checkpoint += 1
                    iterations_since_checkpoint = self._maybe_checkpoint(
                        checkpoint_file, iterations_since_checkpoint, checkpoint_interval, completed, total_pixels
                    )

                if done or timed_out_futures:
                    stall_rounds = 0
                    continue

                # No completions and no timeouts. Remaining futures are either queued
                # (not started) or running but not yet past their deadline.
                # Allow a grace period before bailing out.
                stall_rounds += 1
                if stall_rounds >= 2:
                    logger.warning(
                        f"No progress for {stall_rounds} timeout windows. "
                        f"Cancelling {len(pending)} queued futures (workers occupied by timed-out tasks)."
                    )
                    for future in list(pending):
                        coord = future_to_coord[future]
                        row, col = coord
                        future.cancel()
                        completed[coord] = PixelFitResult(
                            row=row,
                            col=col,
                            fit_results=None,
                            success=False,
                            error_message=(
                                f"Pixel ({row}, {col}) cancelled: "
                                f"workers occupied by timed-out tasks after {timeout_per_job}s"
                            ),
                            chi_squared=None,
                        )
                        progress.update(1)
                        progress.record_failure()
                    pending.clear()

            # On shutdown: cancel remaining pending futures
            if shutdown_handler.shutdown_requested and pending:
                logger.warning("Shutdown requested, cancelling pending futures...")
                for f in pending:
                    f.cancel()

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
