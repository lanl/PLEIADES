"""Unit tests for Issue #177: Per-job timeout and retry logic.

These tests validate the following BatchFittingOrchestrator features:
1. Per-job timeout (timeout_per_job parameter)
2. Retry logic (max_retries parameter)
"""

import pickle
from concurrent.futures import Future
from typing import Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pleiades.imaging.config import ImagingConfig
from pleiades.imaging.models import PixelFitResult, PixelSpectrum
from pleiades.imaging.orchestrator import (
    BatchFittingOrchestrator,
    CheckpointData,
)
from pleiades.sammy.results.models import FitResults

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def imaging_config():
    """Create test imaging configuration."""
    return ImagingConfig(
        isotopes=["Ta-181"],
        element="Ta",
        mass_number=181,
        density_g_cm3=16.6,
        thickness_mm=0.025,
        atomic_mass_amu=180.9479958,
        natural_abundances=True,
        min_energy_eV=1.0,
        max_energy_eV=100.0,
    )


@pytest.fixture
def mock_sammy_executable(tmp_path):
    """Create mock SAMMY executable file on disk."""
    sammy_exe = tmp_path / "sammy"
    sammy_exe.touch()
    sammy_exe.chmod(0o755)
    return sammy_exe


def _make_pixel(row: int, col: int) -> PixelSpectrum:
    """Helper to create a PixelSpectrum with deterministic data."""
    energy = np.linspace(1, 100, 50)
    transmission = np.full(50, 0.75)
    uncertainty = np.full(50, 0.01)
    return PixelSpectrum(row=row, col=col, energy=energy, transmission=transmission, uncertainty=uncertainty)


def _make_success_result(row: int, col: int, chi_squared: float = 1.0) -> PixelFitResult:
    """Helper to create a successful PixelFitResult with mocked FitResults."""
    mock_fit = MagicMock(spec=FitResults)
    return PixelFitResult(
        row=row,
        col=col,
        fit_results=mock_fit,
        success=True,
        error_message=None,
        chi_squared=chi_squared,
    )


def _make_failure_result(row: int, col: int, error_message: str = "SAMMY failed") -> PixelFitResult:
    """Helper to create a failed PixelFitResult."""
    return PixelFitResult(
        row=row,
        col=col,
        fit_results=None,
        success=False,
        error_message=error_message,
        chi_squared=None,
    )


def _mock_json_manager_side_effect(isotopes, abundances, working_dir):
    """Side effect for JsonManager.create_json_config that creates real files."""
    working_dir.mkdir(parents=True, exist_ok=True)
    shared_json = working_dir / "config.json"
    shared_json.write_text("{}", encoding="utf-8")
    return shared_json


# ===========================================================================
# TestPerJobTimeout: tests for timeout_per_job parameter on fit_pixels()
# ===========================================================================


class TestPerJobTimeout:
    """Tests for per-job timeout in fit_pixels().

    When timeout_per_job is set, pixel jobs exceeding that duration are
    marked as failed with an error message containing 'timed out'.
    """

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_timeout_none_means_no_timeout(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable
    ):
        """timeout_per_job=None (default) means no timeout is applied."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        def submit_side_effect(fn, *args, **kwargs):
            pixel = args[0]
            future = Future()
            future.set_result(_make_success_result(pixel.row, pixel.col))
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        # Default call - no timeout_per_job argument
        results = orchestrator.fit_pixels(pixels)

        assert len(results) == 1
        assert results[0].success is True

    @patch("pleiades.imaging.orchestrator.wait")
    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_timeout_marks_slow_pixel_as_failed(
        self, mock_executor_cls, mock_json_mgr, mock_wait, imaging_config, mock_sammy_executable
    ):
        """A pixel job exceeding timeout_per_job is marked success=False."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        # Create a mock future that simulates a running, timed-out job
        mock_future = MagicMock()
        mock_future.done.return_value = False
        mock_future.cancelled.return_value = False
        mock_future.running.return_value = True

        mock_executor.submit.return_value = mock_future

        # Simulate wait() returning no completed futures (timeout expired),
        # then the running future gets marked as timed out by _collect_results_with_timeout
        mock_wait.return_value = (set(), {mock_future})

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels, timeout_per_job=0.001)

        assert len(results) == 1
        assert results[0].success is False

    @patch("pleiades.imaging.orchestrator.time")
    @patch("pleiades.imaging.orchestrator.wait")
    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_timeout_error_message_contains_timed_out(
        self, mock_executor_cls, mock_json_mgr, mock_wait, mock_time, imaging_config, mock_sammy_executable
    ):
        """Error message for timed-out pixels must contain 'timed out'."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        mock_future = MagicMock()
        mock_future.done.return_value = False
        mock_future.cancelled.return_value = False
        mock_future.running.return_value = True

        mock_executor.submit.return_value = mock_future

        # wait() returns no completions → running future stays pending
        mock_wait.return_value = (set(), {mock_future})

        # Simulate time passing so the per-job timeout path fires:
        # Call 1 (before loop): 0.0
        # Call 2 (after 1st wait): 1.0 → records start time = 1.0, elapsed = 0
        # Call 3 (after 2nd wait): 3.0 → elapsed = 3.0 - 1.0 = 2.0 >= 0.5 → timeout!
        mock_time.monotonic.side_effect = [0.0, 1.0, 3.0]

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels, timeout_per_job=0.5)

        assert len(results) == 1
        assert results[0].success is False
        assert "timed out" in results[0].error_message.lower(), (
            f"Error message must contain 'timed out', got: '{results[0].error_message}'"
        )

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_timeout_does_not_affect_fast_pixels(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable
    ):
        """Pixels that complete within timeout are not affected."""
        pixels = [_make_pixel(0, 0), _make_pixel(1, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        def submit_side_effect(fn, *args, **kwargs):
            pixel = args[0]
            future = Future()
            future.set_result(_make_success_result(pixel.row, pixel.col, chi_squared=2.0))
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=2
        )

        # Large timeout - pixels should complete normally
        results = orchestrator.fit_pixels(pixels, timeout_per_job=3600.0)

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.chi_squared == 2.0 for r in results)

    def test_timeout_negative_raises(self, imaging_config, mock_sammy_executable):
        """Negative timeout_per_job raises ValueError."""
        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        pixels = [_make_pixel(0, 0)]

        with pytest.raises(ValueError, match="timeout"):
            orchestrator.fit_pixels(pixels, timeout_per_job=-1.0)

    def test_timeout_zero_raises(self, imaging_config, mock_sammy_executable):
        """Zero timeout_per_job raises ValueError (must be strictly positive)."""
        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        pixels = [_make_pixel(0, 0)]

        with pytest.raises(ValueError, match="timeout"):
            orchestrator.fit_pixels(pixels, timeout_per_job=0.0)

    @patch("pleiades.imaging.orchestrator.wait")
    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_timeout_with_checkpoint(
        self, mock_executor_cls, mock_json_mgr, mock_wait, imaging_config, mock_sammy_executable, tmp_path
    ):
        """Timed-out results are saved in checkpoint files."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        mock_future = MagicMock()
        mock_future.done.return_value = False
        mock_future.cancelled.return_value = False
        mock_future.running.return_value = True

        mock_executor.submit.return_value = mock_future

        # wait() returns no completions → running future gets timed out
        mock_wait.return_value = (set(), {mock_future})

        checkpoint_file = tmp_path / "timeout_checkpoint.pkl"

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(
            pixels,
            checkpoint_file=checkpoint_file,
            checkpoint_interval=1,
            timeout_per_job=0.001,
        )

        assert checkpoint_file.exists(), "Checkpoint must be saved even for timed-out pixels"
        with open(checkpoint_file, "rb") as f:
            loaded = pickle.load(f)
        assert isinstance(loaded, CheckpointData)
        assert (0, 0) in loaded.completed_pixels
        assert loaded.completed_pixels[(0, 0)].success is False


# ===========================================================================
# TestRetryLogic: tests for max_retries parameter on fit_pixels()
# ===========================================================================


class TestRetryLogic:
    """Tests for retry logic in fit_pixels().

    When max_retries > 0, failed pixel jobs are re-submitted up to max_retries
    additional times. Successful pixels are never retried.
    """

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_no_retry_by_default(self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable):
        """max_retries=0 (default) means failed pixels are NOT retried."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        submit_count = 0

        def submit_side_effect(fn, *args, **kwargs):
            nonlocal submit_count
            submit_count += 1
            pixel = args[0]
            future = Future()
            future.set_result(_make_failure_result(pixel.row, pixel.col, "SAMMY crashed"))
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels)

        assert len(results) == 1
        assert results[0].success is False
        # With max_retries=0, the pixel should only be submitted once
        assert submit_count == 1, f"Expected 1 submit (no retries), got {submit_count}"

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_retry_succeeds_on_second_attempt(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable
    ):
        """Pixel fails first attempt, succeeds on retry."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        attempt_count = 0

        def submit_side_effect(fn, *args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            pixel = args[0]
            future = Future()
            if attempt_count == 1:
                # First attempt fails
                future.set_result(_make_failure_result(pixel.row, pixel.col, "Transient error"))
            else:
                # Second attempt succeeds
                future.set_result(_make_success_result(pixel.row, pixel.col, chi_squared=1.5))
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels, max_retries=1)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].chi_squared == 1.5
        assert attempt_count == 2, f"Expected 2 attempts (1 initial + 1 retry), got {attempt_count}"

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_retry_exhausts_all_attempts(self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable):
        """When all retries fail, the last failure result is used."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        attempt_count = 0

        def submit_side_effect(fn, *args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            pixel = args[0]
            future = Future()
            future.set_result(_make_failure_result(pixel.row, pixel.col, f"Failure attempt {attempt_count}"))
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels, max_retries=2)

        assert len(results) == 1
        assert results[0].success is False
        # Should have attempted 3 times total (1 initial + 2 retries)
        assert attempt_count == 3, f"Expected 3 total attempts (1 + 2 retries), got {attempt_count}"

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_retry_count_in_error_message(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable
    ):
        """Error message for exhausted retries mentions the retry count."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        def submit_side_effect(fn, *args, **kwargs):
            pixel = args[0]
            future = Future()
            future.set_result(_make_failure_result(pixel.row, pixel.col, "SAMMY diverged"))
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels, max_retries=2)

        assert len(results) == 1
        assert results[0].success is False
        error_msg = results[0].error_message.lower()
        # Error message should mention retry count - check for common patterns
        assert "retr" in error_msg or "attempt" in error_msg, (
            f"Error message should mention retries or attempts, got: '{results[0].error_message}'"
        )

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_retry_only_failed_pixels(self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable):
        """Successful pixels are NOT retried even when max_retries > 0."""
        pixels = [_make_pixel(0, 0), _make_pixel(1, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        submit_count = 0

        def submit_side_effect(fn, *args, **kwargs):
            nonlocal submit_count
            submit_count += 1
            pixel = args[0]
            future = Future()
            # Pixel (0,0) always succeeds, pixel (1,0) always fails
            if pixel.row == 0:
                future.set_result(_make_success_result(pixel.row, pixel.col))
            else:
                future.set_result(_make_failure_result(pixel.row, pixel.col, "always fails"))
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels, max_retries=2)

        assert len(results) == 2
        # Pixel (0,0) succeeds on first try
        result_00 = next(r for r in results if r.row == 0 and r.col == 0)
        assert result_00.success is True
        # Pixel (1,0) fails all 3 attempts
        result_10 = next(r for r in results if r.row == 1 and r.col == 0)
        assert result_10.success is False

        # Total submits: pixel(0,0) once + pixel(1,0) three times = 5
        # (2 initial + 1 retry for pixel(1,0) + 1 retry for pixel(1,0) again)
        # That is: 2 initial submits + 2 retries for pixel(1,0) = 4 total, not 5
        # Actually: initial batch = 2 submits. Then pixel(1,0) retried twice = 2 more.
        # Total = 4 submits.
        assert submit_count == 4, (
            f"Expected 4 total submits (2 initial + 2 retries for failed pixel), got {submit_count}"
        )

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_retry_with_max_retries_2(self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable):
        """max_retries=2 allows up to 3 total attempts per pixel."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        attempt_count = 0

        def submit_side_effect(fn, *args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            pixel = args[0]
            future = Future()
            if attempt_count <= 2:
                # First two attempts fail
                future.set_result(_make_failure_result(pixel.row, pixel.col, f"Fail #{attempt_count}"))
            else:
                # Third attempt succeeds
                future.set_result(_make_success_result(pixel.row, pixel.col, chi_squared=3.0))
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels, max_retries=2)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].chi_squared == 3.0
        assert attempt_count == 3, f"Expected 3 attempts (1 + 2 retries), got {attempt_count}"

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_retry_preserves_result_order(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable
    ):
        """Results are returned in the same order as input pixels regardless of retries."""
        pixels = [_make_pixel(0, 0), _make_pixel(1, 0), _make_pixel(2, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        # Track per-pixel attempt counts
        pixel_attempts: Dict[int, int] = {}

        def submit_side_effect(fn, *args, **kwargs):
            pixel = args[0]
            pixel_attempts[pixel.row] = pixel_attempts.get(pixel.row, 0) + 1
            future = Future()

            if pixel.row == 1 and pixel_attempts[pixel.row] == 1:
                # Pixel (1,0) fails on first attempt only
                future.set_result(_make_failure_result(pixel.row, pixel.col, "transient"))
            else:
                # All others succeed (including pixel (1,0) retry)
                future.set_result(_make_success_result(pixel.row, pixel.col, chi_squared=float(pixel.row)))
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels, max_retries=1)

        assert len(results) == 3
        # Results must be in the SAME order as input pixels
        assert results[0].row == 0
        assert results[1].row == 1
        assert results[2].row == 2
        # All should ultimately succeed
        assert all(r.success for r in results)

    @patch("pleiades.imaging.orchestrator.wait")
    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_retry_with_timeout_interaction(
        self, mock_executor_cls, mock_json_mgr, mock_wait, imaging_config, mock_sammy_executable
    ):
        """Pixel that times out on first attempt can succeed on retry (fresh executor)."""
        pixels = [_make_pixel(0, 0)]

        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.side_effect = _mock_json_manager_side_effect
        mock_json_mgr.return_value = mock_json_instance

        # Each ProcessPoolExecutor() call returns a fresh mock executor
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        attempt_count = 0

        def submit_side_effect(fn, *args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                # First attempt: return a "running" mock that will be timed out
                mock_future = MagicMock()
                mock_future.done.return_value = False
                mock_future.cancelled.return_value = False
                mock_future.running.return_value = True
                return mock_future
            else:
                # Retry: return a real completed future
                pixel = args[0]
                future = Future()
                future.set_result(_make_success_result(pixel.row, pixel.col, chi_squared=2.0))
                return future

        mock_executor.submit.side_effect = submit_side_effect

        call_count = 0

        def mock_wait_side_effect(fs, timeout=None, return_when=None):
            nonlocal call_count
            call_count += 1
            fs_set = set(fs) if not isinstance(fs, set) else fs
            if call_count == 1:
                # First call (initial batch): no completions → triggers timeout
                return (set(), fs_set)
            else:
                # Second call (retry batch): all done
                return (fs_set, set())

        mock_wait.side_effect = mock_wait_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels(pixels, timeout_per_job=5.0, max_retries=1)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].chi_squared == 2.0
        assert attempt_count == 2

    def test_retry_negative_raises(self, imaging_config, mock_sammy_executable):
        """Negative max_retries raises ValueError."""
        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        pixels = [_make_pixel(0, 0)]

        with pytest.raises(ValueError, match="retr"):
            orchestrator.fit_pixels(pixels, max_retries=-1)
