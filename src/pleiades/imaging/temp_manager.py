"""Temporary file management for batch SAMMY execution.

This module provides centralized control over the temporary files generated
during large-scale 2D imaging fitting (262K+ pixel jobs). It handles
workspace isolation, disk space monitoring, and configurable cleanup policies.
"""

import shutil
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional

from pydantic import BaseModel

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

_VALID_CLEANUP_POLICIES = ("immediate", "batch", "manual")
_BYTES_PER_GB = 1024**3


class DiskUsageInfo(BaseModel):
    """Disk usage information for monitoring batch job storage.

    Attributes:
        total_gb: Total disk capacity in GB.
        used_gb: Currently used disk space in GB.
        free_gb: Currently free disk space in GB.
        limit_gb: Configured maximum disk usage limit in GB.
        base_dir: Base directory being monitored.
    """

    total_gb: float
    used_gb: float
    free_gb: float
    limit_gb: float
    base_dir: Path


class TempFileManager:
    """Manage temporary files for batch SAMMY execution.

    Provides workspace isolation, disk monitoring, and cleanup policies
    for large-scale pixel fitting jobs. Each SAMMY run creates ~7 files in
    an isolated working directory; with 262K pixels this means managing
    millions of temporary files.

    Cleanup policies:
        - ``"immediate"``: Worker cleans up directory after each job completes.
        - ``"batch"``: Directories persist until ``cleanup_all()`` is called.
        - ``"manual"``: No automatic cleanup; user is responsible.

    Disk usage enforcement:
        ``max_disk_usage_gb`` caps how much disk the batch is allowed to consume.
        The manager records the free space when entering the context manager and
        refuses new workspaces once the consumed amount (``initial_free - current_free``)
        exceeds the limit. This is an approximation: other processes consuming disk
        make the estimate more conservative (safe), while other processes freeing
        disk make it less conservative.

    Note on thread/process safety:
        ``active_workspaces`` tracking uses a ``threading.Lock`` and is only valid
        within the parent process. Subprocess workers (via ``ProcessPoolExecutor``)
        create directories independently under ``base_dir``; the lock does not
        protect cross-process access. The orchestrator passes ``base_dir`` and
        ``cleanup_policy`` as serializable values, not the manager object itself.

    Example:
        >>> with TempFileManager(base_dir=Path("/fast_ssd/tmp"), cleanup_policy="immediate") as mgr:
        ...     with mgr.job_workspace("pixel_10_20") as ws:
        ...         run_sammy_in(ws)
        ...     # workspace cleaned up here (immediate policy)
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        max_disk_usage_gb: float = 50.0,
        cleanup_policy: str = "immediate",
    ):
        """Initialize the temporary file manager.

        Args:
            base_dir: Root directory for all workspaces. If None, creates a
                subdirectory under the system temp directory.
            max_disk_usage_gb: Maximum disk space (in GB) the batch may consume.
                Enforced by comparing free space at context entry vs. current free
                space. ``job_workspace()`` raises ``OSError`` when the consumed
                amount exceeds this limit or when free space is critically low.
            cleanup_policy: One of ``"immediate"``, ``"batch"``, ``"manual"``.

        Raises:
            ValueError: If cleanup_policy is not one of the valid options, or
                max_disk_usage_gb is not positive.
        """
        if cleanup_policy not in _VALID_CLEANUP_POLICIES:
            raise ValueError(f"cleanup_policy must be one of {_VALID_CLEANUP_POLICIES}, got {cleanup_policy!r}")
        if max_disk_usage_gb <= 0:
            raise ValueError(f"max_disk_usage_gb must be positive, got {max_disk_usage_gb}")

        if base_dir is None:
            # Use a unique directory per manager instance to avoid cross-run
            # collisions and stale directory reuse after crashes.
            self.base_dir = Path(tempfile.mkdtemp(prefix="pleiades_imaging_"))
        else:
            # When a caller-provided base_dir is given, create a dedicated
            # subdirectory inside it so that cleanup only removes the manager-owned
            # directory, not the caller's directory itself.
            Path(base_dir).mkdir(parents=True, exist_ok=True)
            self.base_dir = Path(tempfile.mkdtemp(prefix="pleiades_imaging_", dir=str(base_dir)))
        self.max_disk_usage_gb = max_disk_usage_gb
        self.cleanup_policy = cleanup_policy

        self._active_workspaces: List[Path] = []
        self._lock = threading.Lock()
        self._initial_free_gb: Optional[float] = None

    @contextmanager
    def job_workspace(self, job_id: str) -> Iterator[Path]:
        """Create an isolated workspace directory for a single SAMMY job.

        The directory is created under ``base_dir`` using the ``job_id`` as the
        directory name. Cleanup behavior depends on the configured policy.

        Note: The disk space check and directory creation are not atomic (TOCTOU).
        In high-concurrency scenarios, disk may fill between the check and mkdir.
        This is inherent to the two-step pattern and considered acceptable.

        Args:
            job_id: Unique identifier for this job (used as directory name).
                Must not be empty or contain path separators.

        Yields:
            Path to the created workspace directory.

        Raises:
            ValueError: If job_id is empty or contains path separators.
            OSError: If disk space is insufficient or usage limit exceeded.
        """
        if not job_id:
            raise ValueError("job_id must not be empty")
        if "/" in job_id or "\\" in job_id:
            raise ValueError(f"job_id must not contain path separators, got {job_id!r}")
        if job_id in (".", "..") or Path(job_id).parts != (job_id,):
            raise ValueError(f"job_id must be a single safe path component, got {job_id!r}")

        # Ensure base_dir exists before checking disk space
        self.base_dir.mkdir(parents=True, exist_ok=True)

        if not self.check_disk_space():
            info = self._safe_disk_info_message()
            raise OSError(f"Insufficient disk space or usage limit exceeded: {info}")

        workspace = self.base_dir / job_id
        workspace.mkdir(parents=True, exist_ok=True)

        with self._lock:
            self._active_workspaces.append(workspace)

        try:
            yield workspace
        finally:
            if self.cleanup_policy == "immediate":
                try:
                    shutil.rmtree(workspace)
                except Exception:
                    logger.warning(f"Immediate cleanup failed for workspace: {workspace}")
                with self._lock:
                    if workspace in self._active_workspaces:
                        self._active_workspaces.remove(workspace)

    @contextmanager
    def shared_workspace(self, name: str = "shared") -> Iterator[Path]:
        """Create a shared workspace for batch-wide resources.

        Shared workspaces hold resources used across all workers (e.g., JSON
        config, ENDF files). They are **always** cleaned up on context exit
        regardless of cleanup policy, since shared resources are only needed
        while the batch run is active.

        Args:
            name: Name for the shared workspace directory.

        Yields:
            Path to the created shared workspace directory.

        Raises:
            ValueError: If name is empty.
        """
        if not name:
            raise ValueError("name must not be empty")
        if name in (".", "..") or Path(name).parts != (name,):
            raise ValueError(f"name must be a single safe path component, got {name!r}")

        workspace = self.base_dir / name
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            yield workspace
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def check_disk_space(self, required_gb: float = 0.1) -> bool:
        """Check whether sufficient disk space is available.

        Checks two conditions:
        1. Free space on the filesystem >= ``required_gb``.
        2. If usage tracking is active (context manager entered), the consumed
           disk space (``initial_free - current_free``) does not exceed
           ``max_disk_usage_gb``.

        Args:
            required_gb: Minimum free space required in GB (default: 0.1 GB).

        Returns:
            True if both conditions are met, False otherwise.
            Never raises exceptions — returns False on any error.
        """
        try:
            usage = shutil.disk_usage(self.base_dir)
            free_gb = usage.free / _BYTES_PER_GB

            if free_gb < required_gb:
                return False

            # Enforce max_disk_usage_gb when usage tracking is active
            if self._initial_free_gb is not None:
                consumed_gb = self._initial_free_gb - free_gb
                if consumed_gb > self.max_disk_usage_gb:
                    return False

            return True
        except Exception:
            return False

    def get_disk_usage_info(self) -> DiskUsageInfo:
        """Get current disk usage information.

        Returns:
            DiskUsageInfo with current disk statistics and configured limits.
        """
        usage = shutil.disk_usage(self.base_dir)
        return DiskUsageInfo(
            total_gb=usage.total / _BYTES_PER_GB,
            used_gb=usage.used / _BYTES_PER_GB,
            free_gb=usage.free / _BYTES_PER_GB,
            limit_gb=self.max_disk_usage_gb,
            base_dir=self.base_dir,
        )

    def cleanup_all(self) -> int:
        """Remove all directories under base_dir.

        Returns:
            Number of directories successfully removed.
        """
        count = 0
        if not self.base_dir.exists():
            return count

        for child in list(self.base_dir.iterdir()):
            if child.is_dir():
                try:
                    shutil.rmtree(child)
                    count += 1
                except Exception:
                    logger.warning(f"Failed to remove workspace: {child}")

        with self._lock:
            self._active_workspaces.clear()

        return count

    @property
    def initial_free_gb(self) -> Optional[float]:
        """Free disk space (GB) recorded when the context manager was entered.

        Returns None if the context manager has not been entered yet.
        """
        return self._initial_free_gb

    @property
    def active_workspaces(self) -> List[Path]:
        """List of currently active (not yet cleaned up) workspace directories.

        Returns a copy so callers cannot modify internal state.
        """
        with self._lock:
            return list(self._active_workspaces)

    def _safe_disk_info_message(self) -> str:
        """Build a safe disk info string for error messages, handling failures."""
        try:
            usage = shutil.disk_usage(self.base_dir)
            free_gb = usage.free / _BYTES_PER_GB
            msg = f"{free_gb:.2f} GB free"
            if self._initial_free_gb is not None:
                consumed = self._initial_free_gb - free_gb
                msg += f", {consumed:.2f} GB consumed (limit: {self.max_disk_usage_gb} GB)"
            return msg
        except Exception:
            return f"unable to read disk usage for {self.base_dir}"

    def __enter__(self) -> "TempFileManager":
        """Create base_dir and record initial free space for usage tracking."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._initial_free_gb = shutil.disk_usage(self.base_dir).free / _BYTES_PER_GB
        except Exception:
            self._initial_free_gb = None
        return self

    def __exit__(self, *args) -> None:
        """Clean up on exit. For non-manual policies, remove the manager-owned base_dir."""
        if self.cleanup_policy != "manual":
            # base_dir is always a manager-owned mkdtemp directory (even when the caller
            # supplied a parent path), so it is safe to remove it unconditionally.
            if self.base_dir.exists():
                shutil.rmtree(self.base_dir, ignore_errors=True)
