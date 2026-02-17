"""Unit tests for TempFileManager and DiskUsageInfo.

These tests are written BEFORE implementation (TDD). They exercise:
  - TempFileManager: temporary file lifecycle for batch SAMMY execution
  - DiskUsageInfo: pydantic model for disk usage reporting
  - Context manager protocol for both job and shared workspaces
  - Disk space monitoring and enforcement
  - Cleanup policies: immediate, batch, manual

Tests use pytest tmp_path fixture for all disk operations to avoid
polluting the real filesystem.
"""

import threading
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

import pytest

from pleiades.imaging.temp_manager import _BYTES_PER_GB, DiskUsageInfo, TempFileManager

# Named tuple matching the return type of shutil.disk_usage
_DiskUsage = namedtuple("usage", ["total", "used", "free"])

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager_immediate(tmp_path):
    """Create a TempFileManager with immediate cleanup policy."""
    return TempFileManager(base_dir=tmp_path / "workspaces", max_disk_usage_gb=50.0, cleanup_policy="immediate")


@pytest.fixture
def manager_batch(tmp_path):
    """Create a TempFileManager with batch cleanup policy."""
    return TempFileManager(base_dir=tmp_path / "workspaces", max_disk_usage_gb=50.0, cleanup_policy="batch")


@pytest.fixture
def manager_manual(tmp_path):
    """Create a TempFileManager with manual cleanup policy."""
    return TempFileManager(base_dir=tmp_path / "workspaces", max_disk_usage_gb=50.0, cleanup_policy="manual")


# ===========================================================================
# TestInit
# ===========================================================================


class TestInit:
    """Tests for TempFileManager initialization and validation."""

    def test_default_base_dir_uses_system_temp(self):
        """When base_dir is None, a directory under the system temp directory is used."""
        manager = TempFileManager(base_dir=None, cleanup_policy="immediate")
        import tempfile

        system_temp = Path(tempfile.gettempdir())
        assert manager.base_dir is not None
        # The base_dir should be under the system temp directory
        assert str(manager.base_dir).startswith(str(system_temp))

    def test_custom_base_dir(self, tmp_path):
        """Custom base_dir is stored correctly."""
        custom_dir = tmp_path / "my_workspace"
        manager = TempFileManager(base_dir=custom_dir, cleanup_policy="immediate")
        assert manager.base_dir == custom_dir

    def test_invalid_cleanup_policy_raises_value_error(self, tmp_path):
        """Invalid cleanup_policy string raises ValueError."""
        with pytest.raises(ValueError, match="cleanup_policy"):
            TempFileManager(base_dir=tmp_path, cleanup_policy="invalid_policy")

    def test_empty_cleanup_policy_raises_value_error(self, tmp_path):
        """Empty cleanup_policy string raises ValueError."""
        with pytest.raises(ValueError, match="cleanup_policy"):
            TempFileManager(base_dir=tmp_path, cleanup_policy="")

    def test_non_positive_max_disk_usage_raises_value_error(self, tmp_path):
        """Negative max_disk_usage_gb raises ValueError."""
        with pytest.raises(ValueError, match="max_disk_usage_gb"):
            TempFileManager(base_dir=tmp_path, max_disk_usage_gb=-1.0, cleanup_policy="immediate")

    def test_zero_max_disk_usage_raises_value_error(self, tmp_path):
        """Zero max_disk_usage_gb raises ValueError."""
        with pytest.raises(ValueError, match="max_disk_usage_gb"):
            TempFileManager(base_dir=tmp_path, max_disk_usage_gb=0.0, cleanup_policy="immediate")

    def test_valid_cleanup_policies_accepted(self, tmp_path):
        """All three valid cleanup policies are accepted without error."""
        for policy in ("immediate", "batch", "manual"):
            manager = TempFileManager(base_dir=tmp_path / policy, cleanup_policy=policy)
            assert manager is not None

    def test_positive_max_disk_usage_accepted(self, tmp_path):
        """Positive max_disk_usage_gb values are accepted."""
        manager = TempFileManager(base_dir=tmp_path, max_disk_usage_gb=0.001, cleanup_policy="immediate")
        assert manager is not None

    def test_default_base_dir_is_unique_per_instance(self):
        """Each manager instance with default base_dir gets a unique directory."""
        m1 = TempFileManager(base_dir=None, cleanup_policy="immediate")
        m2 = TempFileManager(base_dir=None, cleanup_policy="immediate")
        assert m1.base_dir != m2.base_dir
        # Clean up the mkdtemp directories
        import shutil

        shutil.rmtree(m1.base_dir, ignore_errors=True)
        shutil.rmtree(m2.base_dir, ignore_errors=True)

    def test_initial_free_gb_none_before_context(self, tmp_path):
        """initial_free_gb property is None before entering context."""
        manager = TempFileManager(base_dir=tmp_path / "ws", cleanup_policy="immediate")
        assert manager.initial_free_gb is None

    def test_initial_free_gb_set_after_context_entry(self, tmp_path):
        """initial_free_gb property is set to a float after entering context."""
        manager = TempFileManager(base_dir=tmp_path / "ws", cleanup_policy="immediate")
        with manager:
            assert isinstance(manager.initial_free_gb, float)
            assert manager.initial_free_gb > 0


# ===========================================================================
# TestJobWorkspace
# ===========================================================================


class TestJobWorkspace:
    """Tests for job_workspace context manager."""

    def test_creates_directory_and_yields_path(self, manager_immediate):
        """job_workspace creates a directory and yields a valid Path."""
        with manager_immediate:
            with manager_immediate.job_workspace("job_001") as ws:
                assert isinstance(ws, Path)
                assert ws.exists()
                assert ws.is_dir()

    def test_directory_name_matches_job_id(self, manager_immediate):
        """Created directory name should incorporate the job_id."""
        with manager_immediate:
            with manager_immediate.job_workspace("job_001") as ws:
                assert "job_001" in ws.name

    def test_immediate_cleanup_removes_directory(self, manager_immediate):
        """With immediate policy, directory is removed after context exit."""
        with manager_immediate:
            with manager_immediate.job_workspace("job_001") as ws:
                workspace_path = ws
                assert ws.exists()
            # After context exit, directory should be gone
            assert not workspace_path.exists()

    def test_batch_cleanup_preserves_directory(self, manager_batch):
        """With batch policy, directory persists after context exit."""
        with manager_batch:
            with manager_batch.job_workspace("job_001") as ws:
                workspace_path = ws
                assert ws.exists()
            # After context exit, directory should still exist
            assert workspace_path.exists()

    def test_manual_cleanup_preserves_directory(self, manager_manual):
        """With manual policy, directory persists after context exit."""
        with manager_manual:
            with manager_manual.job_workspace("job_001") as ws:
                workspace_path = ws
                assert ws.exists()
            # After context exit, directory should still exist
            assert workspace_path.exists()

    def test_empty_job_id_raises_value_error(self, manager_immediate):
        """Empty job_id raises ValueError."""
        with manager_immediate:
            with pytest.raises(ValueError, match="job_id"):
                with manager_immediate.job_workspace(""):
                    pass  # pragma: no cover

    def test_files_created_inside_workspace_persist_during_context(self, manager_immediate):
        """Files written inside workspace are accessible during the context."""
        with manager_immediate:
            with manager_immediate.job_workspace("job_file_test") as ws:
                # Write a file
                test_file = ws / "test_output.dat"
                test_file.write_text("SAMMY output data\n", encoding="utf-8")

                # Read it back
                assert test_file.exists()
                content = test_file.read_text(encoding="utf-8")
                assert content == "SAMMY output data\n"

    def test_multiple_concurrent_workspaces_do_not_interfere(self, manager_batch):
        """Multiple workspaces created simultaneously have independent directories."""
        with manager_batch:
            with manager_batch.job_workspace("job_A") as ws_a:
                with manager_batch.job_workspace("job_B") as ws_b:
                    assert ws_a != ws_b
                    assert ws_a.exists()
                    assert ws_b.exists()

                    # Write files in each
                    (ws_a / "data_a.txt").write_text("A", encoding="utf-8")
                    (ws_b / "data_b.txt").write_text("B", encoding="utf-8")

                    # Files are isolated
                    assert (ws_a / "data_a.txt").exists()
                    assert not (ws_a / "data_b.txt").exists()
                    assert (ws_b / "data_b.txt").exists()
                    assert not (ws_b / "data_a.txt").exists()

    def test_tracks_workspace_in_active_workspaces(self, manager_immediate):
        """Workspace is tracked in active_workspaces during context."""
        with manager_immediate:
            assert len(manager_immediate.active_workspaces) == 0

            with manager_immediate.job_workspace("job_tracked") as ws:
                assert ws in manager_immediate.active_workspaces

    def test_removes_workspace_from_active_after_immediate_cleanup(self, manager_immediate):
        """With immediate policy, workspace is removed from active_workspaces after exit."""
        with manager_immediate:
            with manager_immediate.job_workspace("job_tracked") as ws:
                assert ws in manager_immediate.active_workspaces

            # After exit, should no longer be tracked
            assert ws not in manager_immediate.active_workspaces
            assert len(manager_immediate.active_workspaces) == 0

    def test_workspace_remains_in_active_after_batch_exit(self, manager_batch):
        """With batch policy, workspace stays in active_workspaces after exit."""
        with manager_batch:
            with manager_batch.job_workspace("job_batch") as ws:
                pass

            # After exit with batch policy, workspace should still be tracked
            assert ws in manager_batch.active_workspaces

    def test_disk_space_check_failure_raises_os_error(self, tmp_path):
        """job_workspace raises OSError when disk space check fails."""
        manager = TempFileManager(base_dir=tmp_path / "ws", max_disk_usage_gb=50.0, cleanup_policy="immediate")

        # Mock shutil.disk_usage to report very low free space
        mock_usage = _DiskUsage(total=100 * 1024**3, used=99 * 1024**3, free=0)
        with manager:
            with patch("shutil.disk_usage", return_value=mock_usage):
                with pytest.raises(OSError, match="[Dd]isk|[Ss]pace"):
                    with manager.job_workspace("job_no_space"):
                        pass  # pragma: no cover

    def test_exception_inside_context_still_triggers_cleanup(self, manager_immediate):
        """Exception inside job_workspace still triggers directory cleanup (immediate)."""
        with manager_immediate:
            workspace_path = None
            with pytest.raises(RuntimeError, match="deliberate error"):
                with manager_immediate.job_workspace("job_error") as ws:
                    workspace_path = ws
                    raise RuntimeError("deliberate error")

            # Directory should still be cleaned up
            assert workspace_path is not None
            assert not workspace_path.exists()

    def test_exception_inside_batch_context_preserves_directory(self, manager_batch):
        """Exception inside job_workspace with batch policy preserves directory."""
        with manager_batch:
            workspace_path = None
            with pytest.raises(RuntimeError, match="deliberate error"):
                with manager_batch.job_workspace("job_batch_error") as ws:
                    workspace_path = ws
                    raise RuntimeError("deliberate error")

            # Directory should still exist with batch policy
            assert workspace_path is not None
            assert workspace_path.exists()


# ===========================================================================
# TestSharedWorkspace
# ===========================================================================


class TestSharedWorkspace:
    """Tests for shared_workspace context manager."""

    def test_creates_directory_and_yields_path(self, manager_immediate):
        """shared_workspace creates a directory and yields a valid Path."""
        with manager_immediate:
            with manager_immediate.shared_workspace("shared") as ws:
                assert isinstance(ws, Path)
                assert ws.exists()
                assert ws.is_dir()

    def test_always_cleaned_up_immediate_policy(self, manager_immediate):
        """shared_workspace directory is cleaned up after exit (immediate policy)."""
        with manager_immediate:
            with manager_immediate.shared_workspace("shared") as ws:
                workspace_path = ws
                assert ws.exists()
            assert not workspace_path.exists()

    def test_always_cleaned_up_batch_policy(self, manager_batch):
        """shared_workspace directory is cleaned up after exit (batch policy)."""
        with manager_batch:
            with manager_batch.shared_workspace("shared") as ws:
                workspace_path = ws
                assert ws.exists()
            assert not workspace_path.exists()

    def test_always_cleaned_up_manual_policy(self, manager_manual):
        """shared_workspace directory is cleaned up after exit (manual policy)."""
        with manager_manual:
            with manager_manual.shared_workspace("shared") as ws:
                workspace_path = ws
                assert ws.exists()
            assert not workspace_path.exists()

    def test_empty_name_raises_value_error(self, manager_immediate):
        """Empty name raises ValueError."""
        with manager_immediate:
            with pytest.raises(ValueError, match="name"):
                with manager_immediate.shared_workspace(""):
                    pass  # pragma: no cover

    def test_custom_name(self, manager_immediate):
        """shared_workspace uses the provided name."""
        with manager_immediate:
            with manager_immediate.shared_workspace("my_shared_resources") as ws:
                assert "my_shared_resources" in ws.name


# ===========================================================================
# TestDiskMonitoring
# ===========================================================================


class TestDiskMonitoring:
    """Tests for disk space checking methods."""

    def test_check_disk_space_returns_bool(self, manager_immediate):
        """check_disk_space returns a boolean value."""
        with manager_immediate:
            result = manager_immediate.check_disk_space()
            assert isinstance(result, bool)

    def test_check_disk_space_with_small_requirement_returns_true(self, manager_immediate):
        """check_disk_space with a tiny required_gb should return True on any system."""
        with manager_immediate:
            assert manager_immediate.check_disk_space(required_gb=0.0001) is True

    def test_check_disk_space_with_very_large_required_gb_returns_false(self, manager_immediate):
        """check_disk_space with impossibly large required_gb should return False."""
        with manager_immediate:
            # 1 exabyte should exceed any real disk
            assert manager_immediate.check_disk_space(required_gb=1_000_000_000.0) is False

    def test_get_disk_usage_info_returns_model(self, manager_immediate):
        """get_disk_usage_info returns a DiskUsageInfo instance."""
        with manager_immediate:
            info = manager_immediate.get_disk_usage_info()
            assert isinstance(info, DiskUsageInfo)

    def test_get_disk_usage_info_has_correct_fields(self, manager_immediate):
        """DiskUsageInfo has all required fields with correct types."""
        with manager_immediate:
            info = manager_immediate.get_disk_usage_info()
            assert isinstance(info.total_gb, float)
            assert isinstance(info.used_gb, float)
            assert isinstance(info.free_gb, float)
            assert isinstance(info.limit_gb, float)
            assert isinstance(info.base_dir, Path)

    def test_get_disk_usage_info_reports_configured_limit(self, tmp_path):
        """DiskUsageInfo.limit_gb should reflect the configured max_disk_usage_gb."""
        manager = TempFileManager(base_dir=tmp_path / "ws", max_disk_usage_gb=42.0, cleanup_policy="immediate")
        with manager:
            info = manager.get_disk_usage_info()
            assert info.limit_gb == 42.0

    def test_get_disk_usage_info_reports_base_dir(self, tmp_path):
        """DiskUsageInfo.base_dir should reflect the manager's base_dir."""
        base = tmp_path / "ws"
        manager = TempFileManager(base_dir=base, max_disk_usage_gb=50.0, cleanup_policy="immediate")
        with manager:
            info = manager.get_disk_usage_info()
            assert info.base_dir == base

    def test_check_disk_space_does_not_raise(self, manager_immediate):
        """check_disk_space should never raise exceptions, only return bool."""
        with manager_immediate:
            # Even with mocked failure, it should return False, not raise
            mock_usage = _DiskUsage(total=100 * 1024**3, used=99 * 1024**3, free=0)
            with patch("shutil.disk_usage", return_value=mock_usage):
                result = manager_immediate.check_disk_space(required_gb=1.0)
                assert result is False

    def test_job_workspace_raises_oserror_when_disk_full(self, tmp_path):
        """job_workspace raises OSError when disk space is insufficient (mocked)."""
        manager = TempFileManager(base_dir=tmp_path / "ws", max_disk_usage_gb=50.0, cleanup_policy="immediate")

        # Mock to simulate disk full
        mock_usage = _DiskUsage(total=100 * 1024**3, used=99 * 1024**3, free=0)
        with manager:
            with patch("shutil.disk_usage", return_value=mock_usage):
                with pytest.raises(OSError):
                    with manager.job_workspace("job_full"):
                        pass  # pragma: no cover

    def test_check_disk_space_enforces_max_disk_usage_limit(self, tmp_path):
        """check_disk_space returns False when consumed space exceeds max_disk_usage_gb."""
        manager = TempFileManager(base_dir=tmp_path / "ws", max_disk_usage_gb=1.0, cleanup_policy="immediate")

        with manager:
            # At entry, initial_free_gb was recorded from the real filesystem.
            # Now mock disk_usage to simulate that 2 GB has been consumed since entry.
            initial_free = manager.initial_free_gb
            assert initial_free is not None

            # Simulate: 2 GB consumed (more than the 1 GB limit)
            mock_free = (initial_free - 2.0) * _BYTES_PER_GB
            mock_usage = _DiskUsage(total=100 * _BYTES_PER_GB, used=50 * _BYTES_PER_GB, free=int(mock_free))
            with patch("shutil.disk_usage", return_value=mock_usage):
                result = manager.check_disk_space(required_gb=0.0001)
                assert result is False


# ===========================================================================
# TestCleanup
# ===========================================================================


class TestCleanup:
    """Tests for cleanup_all method."""

    def test_removes_all_directories(self, manager_batch):
        """cleanup_all removes all directories under base_dir."""
        with manager_batch:
            # Create several job workspaces (batch = persist after exit)
            paths = []
            for i in range(5):
                with manager_batch.job_workspace(f"job_{i}") as ws:
                    (ws / "output.dat").write_text(f"data_{i}", encoding="utf-8")
                    paths.append(ws)

            # All should exist
            assert all(p.exists() for p in paths)

            count = manager_batch.cleanup_all()
            assert count == 5

            # All should be gone
            assert all(not p.exists() for p in paths)

    def test_returns_correct_count(self, manager_batch):
        """cleanup_all returns the number of directories removed."""
        with manager_batch:
            for i in range(3):
                with manager_batch.job_workspace(f"job_{i}") as ws:
                    pass

            count = manager_batch.cleanup_all()
            assert count == 3

    def test_safe_when_no_directories_exist(self, manager_immediate):
        """cleanup_all returns 0 when no directories exist."""
        with manager_immediate:
            count = manager_immediate.cleanup_all()
            assert count == 0

    def test_safe_to_call_multiple_times(self, manager_batch):
        """cleanup_all can be called multiple times without error."""
        with manager_batch:
            with manager_batch.job_workspace("job_once") as ws:
                pass

            first_count = manager_batch.cleanup_all()
            assert first_count == 1

            second_count = manager_batch.cleanup_all()
            assert second_count == 0

            third_count = manager_batch.cleanup_all()
            assert third_count == 0

    def test_handles_permission_errors_gracefully(self, manager_batch):
        """cleanup_all handles permission errors without raising."""
        with manager_batch:
            with manager_batch.job_workspace("job_perm") as ws:
                (ws / "locked.dat").write_text("locked", encoding="utf-8")

            # Mock shutil.rmtree to raise PermissionError
            with patch("shutil.rmtree", side_effect=PermissionError("no permission")):
                # Should NOT raise -- errors are logged but swallowed
                count = manager_batch.cleanup_all()
                # Count may be 0 since removal failed, but no exception
                assert isinstance(count, int)

    def test_cleanup_removes_nested_directories(self, manager_batch):
        """cleanup_all removes workspaces containing nested subdirectories."""
        with manager_batch:
            with manager_batch.job_workspace("job_nested") as ws:
                nested = ws / "subdir1" / "subdir2"
                nested.mkdir(parents=True)
                (nested / "deep_file.dat").write_text("deep", encoding="utf-8")
                workspace_path = ws

            assert workspace_path.exists()
            count = manager_batch.cleanup_all()
            assert count >= 1
            assert not workspace_path.exists()


# ===========================================================================
# TestContextManager
# ===========================================================================


class TestContextManager:
    """Tests for __enter__ / __exit__ protocol."""

    def test_creates_base_dir_on_enter(self, tmp_path):
        """__enter__ creates base_dir if it doesn't exist."""
        base = tmp_path / "new_workspace_dir"
        assert not base.exists()

        manager = TempFileManager(base_dir=base, cleanup_policy="immediate")
        with manager:
            assert base.exists()

    def test_cleans_up_on_exit_immediate(self, tmp_path):
        """__exit__ cleans up for immediate policy."""
        base = tmp_path / "ws_immediate"
        manager = TempFileManager(base_dir=base, cleanup_policy="immediate")

        with manager:
            with manager.job_workspace("job_1") as ws:
                (ws / "file.dat").write_text("data", encoding="utf-8")
            # immediate cleanup already removed workspace
            # but base_dir should be cleaned up on __exit__

        # After __exit__, base_dir itself should be removed
        assert not base.exists()

    def test_cleans_up_on_exit_batch(self, tmp_path):
        """__exit__ cleans up for batch policy."""
        base = tmp_path / "ws_batch"
        manager = TempFileManager(base_dir=base, cleanup_policy="batch")

        with manager:
            with manager.job_workspace("job_1") as ws:
                workspace_path = ws
            # batch policy -- workspace persists during context
            assert workspace_path.exists()

        # After __exit__, everything should be cleaned up
        assert not base.exists()

    def test_no_cleanup_on_exit_manual(self, tmp_path):
        """__exit__ does NOT clean up for manual policy."""
        base = tmp_path / "ws_manual"
        manager = TempFileManager(base_dir=base, cleanup_policy="manual")

        with manager:
            with manager.job_workspace("job_1") as ws:
                (ws / "file.dat").write_text("data", encoding="utf-8")
                workspace_path = ws

        # After __exit__ with manual policy, base_dir should still exist
        assert base.exists()
        assert workspace_path.exists()

    def test_base_dir_removed_on_exit_non_manual(self, tmp_path):
        """base_dir itself is removed on __exit__ for non-manual policies."""
        for policy in ("immediate", "batch"):
            base = tmp_path / f"ws_{policy}_remove"
            manager = TempFileManager(base_dir=base, cleanup_policy=policy)
            with manager:
                assert base.exists()
            assert not base.exists(), f"base_dir should be removed on __exit__ for {policy} policy"

    def test_enter_returns_self(self, tmp_path):
        """__enter__ returns the manager instance itself."""
        manager = TempFileManager(base_dir=tmp_path / "ws", cleanup_policy="immediate")
        with manager as m:
            assert m is manager


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_job_id_with_spaces(self, manager_immediate):
        """job_id containing spaces should either work or raise ValueError."""
        with manager_immediate:
            try:
                with manager_immediate.job_workspace("job with spaces") as ws:
                    # If it works, the workspace should exist
                    assert ws.exists()
            except ValueError:
                # Raising ValueError for invalid job_id is also acceptable
                pass

    def test_job_id_with_slashes_rejected(self, manager_immediate):
        """job_id containing path separators is rejected with ValueError."""
        with manager_immediate:
            with pytest.raises(ValueError, match="path separators"):
                with manager_immediate.job_workspace("job/sub/path"):
                    pass  # pragma: no cover

    def test_job_id_dot_dot_rejected(self, manager_immediate):
        """job_id '..' is rejected to prevent directory traversal."""
        with manager_immediate:
            with pytest.raises(ValueError, match="single safe path component"):
                with manager_immediate.job_workspace(".."):
                    pass  # pragma: no cover

    def test_job_id_single_dot_rejected(self, manager_immediate):
        """job_id '.' is rejected to prevent directory traversal."""
        with manager_immediate:
            with pytest.raises(ValueError, match="single safe path component"):
                with manager_immediate.job_workspace("."):
                    pass  # pragma: no cover

    def test_shared_workspace_dot_dot_rejected(self, manager_immediate):
        """shared_workspace name '..' is rejected to prevent directory traversal."""
        with manager_immediate:
            with pytest.raises(ValueError, match="single safe path component"):
                with manager_immediate.shared_workspace(".."):
                    pass  # pragma: no cover

    def test_shared_workspace_single_dot_rejected(self, manager_immediate):
        """shared_workspace name '.' is rejected to prevent directory traversal."""
        with manager_immediate:
            with pytest.raises(ValueError, match="single safe path component"):
                with manager_immediate.shared_workspace("."):
                    pass  # pragma: no cover

    def test_very_long_job_id(self, manager_immediate):
        """Very long job_id should be handled (either works or raises)."""
        long_id = "x" * 500
        with manager_immediate:
            try:
                with manager_immediate.job_workspace(long_id) as ws:
                    assert ws.exists()
            except (ValueError, OSError):
                # Raising for too-long IDs is acceptable
                pass

    def test_thread_safe_active_workspaces(self, tmp_path):
        """active_workspaces tracking is thread-safe with concurrent access."""
        manager = TempFileManager(base_dir=tmp_path / "ws", max_disk_usage_gb=50.0, cleanup_policy="batch")
        errors = []

        def worker(job_id):
            try:
                with manager.job_workspace(job_id) as ws:
                    # Verify workspace is in active list
                    assert ws in manager.active_workspaces
            except Exception as e:
                errors.append(e)

        with manager:
            threads = [threading.Thread(target=worker, args=(f"thread_job_{i}",)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert len(errors) == 0, f"Thread-safety errors: {errors}"

    def test_base_dir_that_does_not_exist_created_on_enter(self, tmp_path):
        """base_dir that doesn't exist is created when entering context."""
        deep_path = tmp_path / "a" / "b" / "c" / "workspaces"
        assert not deep_path.exists()

        manager = TempFileManager(base_dir=deep_path, cleanup_policy="immediate")
        with manager:
            assert deep_path.exists()

    def test_cleanup_workspace_with_nested_directories(self, manager_immediate):
        """Cleanup handles workspaces with deeply nested subdirectories."""
        with manager_immediate:
            with manager_immediate.job_workspace("nested_job") as ws:
                deep = ws / "a" / "b" / "c"
                deep.mkdir(parents=True)
                (deep / "result.dat").write_text("data", encoding="utf-8")
                workspace_path = ws

            # With immediate policy, nested directory should be fully cleaned
            assert not workspace_path.exists()

    def test_exception_inside_job_workspace_still_triggers_immediate_cleanup(self, manager_immediate):
        """Exception propagation doesn't skip cleanup in immediate mode."""
        with manager_immediate:
            workspace_path = None
            try:
                with manager_immediate.job_workspace("error_job") as ws:
                    workspace_path = ws
                    (ws / "partial.dat").write_text("partial", encoding="utf-8")
                    raise ValueError("processing failed")
            except ValueError:
                pass

            assert workspace_path is not None
            assert not workspace_path.exists()
            assert workspace_path not in manager_immediate.active_workspaces

    def test_multiple_files_in_workspace(self, manager_immediate):
        """Workspace handles multiple files (simulating SAMMY's ~7 files per job)."""
        with manager_immediate:
            with manager_immediate.job_workspace("sammy_job") as ws:
                # Simulate typical SAMMY job files
                file_names = [
                    "config.json",
                    "input.dat",
                    "output.dat",
                    "par_file.par",
                    "endf.dat",
                    "results.lst",
                    "chi_squared.txt",
                ]
                for name in file_names:
                    (ws / name).write_text(f"content of {name}", encoding="utf-8")

                # All files should exist
                assert len(list(ws.iterdir())) == 7
                workspace_path = ws

            # After exit, everything should be cleaned up
            assert not workspace_path.exists()


# ===========================================================================
# TestDiskUsageInfo
# ===========================================================================


class TestDiskUsageInfo:
    """Tests for DiskUsageInfo pydantic model."""

    def test_validates_fields_are_present(self):
        """DiskUsageInfo requires all fields to be present."""
        info = DiskUsageInfo(
            total_gb=100.0,
            used_gb=50.0,
            free_gb=50.0,
            limit_gb=80.0,
            base_dir=Path("/tmp/test"),
        )
        assert info.total_gb == 100.0
        assert info.used_gb == 50.0
        assert info.free_gb == 50.0
        assert info.limit_gb == 80.0
        assert info.base_dir == Path("/tmp/test")

    def test_float_fields_are_float(self):
        """total_gb, used_gb, free_gb, limit_gb are all float."""
        info = DiskUsageInfo(
            total_gb=100.0,
            used_gb=50.0,
            free_gb=50.0,
            limit_gb=80.0,
            base_dir=Path("/tmp"),
        )
        assert isinstance(info.total_gb, float)
        assert isinstance(info.used_gb, float)
        assert isinstance(info.free_gb, float)
        assert isinstance(info.limit_gb, float)

    def test_base_dir_is_path(self):
        """base_dir field is a Path instance."""
        info = DiskUsageInfo(
            total_gb=1.0,
            used_gb=0.5,
            free_gb=0.5,
            limit_gb=1.0,
            base_dir=Path("/tmp/workspace"),
        )
        assert isinstance(info.base_dir, Path)

    def test_accepts_integer_coercion(self):
        """Integer values should be coerced to float for numeric fields."""
        info = DiskUsageInfo(
            total_gb=100,
            used_gb=50,
            free_gb=50,
            limit_gb=80,
            base_dir=Path("/tmp"),
        )
        assert isinstance(info.total_gb, float)
        assert info.total_gb == 100.0

    def test_accepts_string_path(self):
        """String path should be coerced to Path."""
        info = DiskUsageInfo(
            total_gb=1.0,
            used_gb=0.5,
            free_gb=0.5,
            limit_gb=1.0,
            base_dir="/tmp/test",
        )
        assert isinstance(info.base_dir, Path)
        assert info.base_dir == Path("/tmp/test")


# ===========================================================================
# TestActiveWorkspaces
# ===========================================================================


class TestActiveWorkspaces:
    """Tests for active_workspaces property."""

    def test_initially_empty(self, manager_immediate):
        """active_workspaces is empty before any workspace is created."""
        with manager_immediate:
            assert manager_immediate.active_workspaces == []

    def test_returns_list(self, manager_immediate):
        """active_workspaces returns a list."""
        with manager_immediate:
            assert isinstance(manager_immediate.active_workspaces, list)

    def test_multiple_active_workspaces_tracked(self, manager_batch):
        """Multiple active workspaces are all tracked simultaneously."""
        with manager_batch:
            workspaces = []
            for i in range(3):
                ctx = manager_batch.job_workspace(f"multi_{i}")
                ws = ctx.__enter__()
                workspaces.append((ctx, ws))

            assert len(manager_batch.active_workspaces) == 3
            for _, ws in workspaces:
                assert ws in manager_batch.active_workspaces

            # Clean up contexts
            for ctx, _ in workspaces:
                ctx.__exit__(None, None, None)

    def test_returns_copy_not_internal_reference(self, manager_batch):
        """active_workspaces should return a copy, not a direct reference to internal state."""
        with manager_batch:
            with manager_batch.job_workspace("ref_test") as ws:
                active = manager_batch.active_workspaces
                # Modifying the returned list should not affect internal state
                active.clear()
                assert ws in manager_batch.active_workspaces


# ===========================================================================
# TestOrchestratorIntegration
# ===========================================================================


class TestOrchestratorIntegration:
    """Tests for BatchFittingOrchestrator + TempFileManager integration."""

    def test_orchestrator_accepts_temp_manager(self, tmp_path):
        """BatchFittingOrchestrator.__init__ accepts a temp_manager parameter."""
        from pleiades.imaging.orchestrator import BatchFittingOrchestrator

        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        mgr = TempFileManager(base_dir=tmp_path / "ws", cleanup_policy="batch")
        config = _make_imaging_config()

        orch = BatchFittingOrchestrator(imaging_config=config, sammy_executable=sammy_exe, temp_manager=mgr)
        assert orch.temp_manager is mgr

    def test_orchestrator_without_temp_manager_defaults_to_none(self, tmp_path):
        """BatchFittingOrchestrator works without temp_manager (backward compat)."""
        from pleiades.imaging.orchestrator import BatchFittingOrchestrator

        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        config = _make_imaging_config()
        orch = BatchFittingOrchestrator(imaging_config=config, sammy_executable=sammy_exe)
        assert orch.temp_manager is None

    def test_submit_pixels_extracts_base_dir_and_policy(self, tmp_path):
        """_submit_pixels passes temp_base_dir and cleanup_policy from temp_manager."""
        from concurrent.futures import ProcessPoolExecutor
        from unittest.mock import MagicMock

        from pleiades.imaging.orchestrator import BatchFittingOrchestrator

        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        mgr = TempFileManager(base_dir=tmp_path / "ws", cleanup_policy="batch")
        config = _make_imaging_config()

        orch = BatchFittingOrchestrator(imaging_config=config, sammy_executable=sammy_exe, temp_manager=mgr)

        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_future = MagicMock()
        mock_executor.submit.return_value = mock_future

        pixel = _make_pixel(0, 0)
        orch._submit_pixels(mock_executor, [pixel], Path("/json"), Path("/endf"))

        # Verify submit was called with temp_base_dir and cleanup_policy
        call_args = mock_executor.submit.call_args
        assert call_args is not None
        # positional args: (worker_fn, pixel, config, exe, resolution, json, endf, base_dir, policy)
        args = call_args[0]
        assert args[7] == tmp_path / "ws"  # temp_base_dir
        assert args[8] == "batch"  # cleanup_policy

    def test_submit_pixels_without_temp_manager_passes_none(self, tmp_path):
        """Without temp_manager, _submit_pixels passes None for temp_base_dir."""
        from concurrent.futures import ProcessPoolExecutor
        from unittest.mock import MagicMock

        from pleiades.imaging.orchestrator import BatchFittingOrchestrator

        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        config = _make_imaging_config()
        orch = BatchFittingOrchestrator(imaging_config=config, sammy_executable=sammy_exe)

        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_future = MagicMock()
        mock_executor.submit.return_value = mock_future

        pixel = _make_pixel(0, 0)
        orch._submit_pixels(mock_executor, [pixel], Path("/json"), Path("/endf"))

        call_args = mock_executor.submit.call_args
        args = call_args[0]
        assert args[7] is None  # temp_base_dir
        assert args[8] == "immediate"  # cleanup_policy

    def test_worker_creates_workspace_under_temp_base_dir(self, tmp_path):
        """_fit_pixel_worker creates workspace under temp_base_dir when provided."""
        from unittest.mock import MagicMock, patch

        from pleiades.imaging.orchestrator import _fit_pixel_worker

        pixel = _make_pixel(3, 7)
        config = _make_imaging_config()
        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()
        base_dir = tmp_path / "managed_ws"
        base_dir.mkdir()

        # Mock the worker implementation to avoid SAMMY execution
        mock_result = MagicMock()
        mock_result.row = 3
        mock_result.col = 7
        mock_result.success = False
        mock_result.error_message = "mock"

        with patch("pleiades.imaging.orchestrator._fit_pixel_worker_impl") as mock_impl:
            mock_impl.return_value = mock_result
            _fit_pixel_worker(pixel, config, sammy_exe, temp_base_dir=base_dir, cleanup_policy="batch")

            # Verify impl was called with a path under base_dir
            call_args = mock_impl.call_args[0]
            temp_path_arg = call_args[6]  # temp_path positional arg
            assert temp_path_arg is not None
            assert str(temp_path_arg).startswith(str(base_dir))
            assert "pixel_3_7" in str(temp_path_arg)

    def test_worker_falls_back_to_tempdir_without_temp_base_dir(self, tmp_path):
        """_fit_pixel_worker uses tempfile.TemporaryDirectory when temp_base_dir is None."""
        from unittest.mock import MagicMock, patch

        from pleiades.imaging.orchestrator import _fit_pixel_worker

        pixel = _make_pixel(1, 2)
        config = _make_imaging_config()
        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        mock_result = MagicMock()
        mock_result.row = 1
        mock_result.col = 2
        mock_result.success = False
        mock_result.error_message = "mock"

        with patch("pleiades.imaging.orchestrator._fit_pixel_worker_impl") as mock_impl:
            mock_impl.return_value = mock_result
            _fit_pixel_worker(pixel, config, sammy_exe)  # No temp_base_dir

            # Verify impl was called with temp_path=None (will use TemporaryDirectory)
            call_args = mock_impl.call_args[0]
            temp_path_arg = call_args[6]
            assert temp_path_arg is None

    def test_worker_attempt_id_in_workspace_name(self, tmp_path):
        """attempt_id is included in workspace directory name to prevent retry collisions (P1)."""
        from unittest.mock import MagicMock, patch

        from pleiades.imaging.orchestrator import _fit_pixel_worker

        pixel = _make_pixel(5, 9)
        config = _make_imaging_config()
        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()
        base_dir = tmp_path / "managed_ws"
        base_dir.mkdir()

        mock_result = MagicMock()
        mock_result.row = 5
        mock_result.col = 9
        mock_result.success = False
        mock_result.error_message = "mock"

        with patch("pleiades.imaging.orchestrator._fit_pixel_worker_impl") as mock_impl:
            mock_impl.return_value = mock_result
            _fit_pixel_worker(pixel, config, sammy_exe, temp_base_dir=base_dir, cleanup_policy="batch", attempt_id=2)

            call_args = mock_impl.call_args[0]
            temp_path_arg = call_args[6]
            assert temp_path_arg is not None
            assert temp_path_arg.name == "pixel_5_9_a2"

    def test_worker_different_attempts_get_different_dirs(self, tmp_path):
        """Different attempt_id values produce different workspace directories (P1)."""
        from unittest.mock import MagicMock, patch

        from pleiades.imaging.orchestrator import _fit_pixel_worker

        pixel = _make_pixel(1, 1)
        config = _make_imaging_config()
        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()
        base_dir = tmp_path / "managed_ws"
        base_dir.mkdir()

        mock_result = MagicMock()
        mock_result.row = 1
        mock_result.col = 1
        mock_result.success = False
        mock_result.error_message = "mock"

        paths = []
        for attempt in range(3):
            with patch("pleiades.imaging.orchestrator._fit_pixel_worker_impl") as mock_impl:
                mock_impl.return_value = mock_result
                _fit_pixel_worker(
                    pixel, config, sammy_exe, temp_base_dir=base_dir, cleanup_policy="batch", attempt_id=attempt
                )
                paths.append(mock_impl.call_args[0][6])

        # All three paths should be unique
        assert len(set(str(p) for p in paths)) == 3
        assert paths[0].name == "pixel_1_1_a0"
        assert paths[1].name == "pixel_1_1_a1"
        assert paths[2].name == "pixel_1_1_a2"

    def test_worker_cleans_stale_workspace_before_reuse(self, tmp_path):
        """Worker removes pre-existing stale workspace before creating a new one (C8)."""
        from unittest.mock import MagicMock, patch

        from pleiades.imaging.orchestrator import _fit_pixel_worker

        pixel = _make_pixel(2, 4)
        config = _make_imaging_config()
        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()
        base_dir = tmp_path / "managed_ws"
        base_dir.mkdir()

        # Pre-create a stale workspace with leftover data
        stale_dir = base_dir / "pixel_2_4_a0"
        stale_dir.mkdir()
        stale_file = stale_dir / "old_output.dat"
        stale_file.write_text("stale data from crashed run", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.row = 2
        mock_result.col = 4
        mock_result.success = False
        mock_result.error_message = "mock"

        with patch("pleiades.imaging.orchestrator._fit_pixel_worker_impl") as mock_impl:
            mock_impl.return_value = mock_result
            _fit_pixel_worker(pixel, config, sammy_exe, temp_base_dir=base_dir, cleanup_policy="batch", attempt_id=0)

            # The workspace should exist but the stale file should be gone
            call_args = mock_impl.call_args[0]
            temp_path_arg = call_args[6]
            assert temp_path_arg.exists()
            assert not (temp_path_arg / "old_output.dat").exists()

    def test_submit_pixels_passes_attempt_round_and_disk_params(self, tmp_path):
        """_submit_pixels passes attempt_round, max_disk_usage_gb, initial_free_gb (P1+P2)."""
        from concurrent.futures import ProcessPoolExecutor
        from unittest.mock import MagicMock

        from pleiades.imaging.orchestrator import BatchFittingOrchestrator

        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        mgr = TempFileManager(base_dir=tmp_path / "ws", max_disk_usage_gb=25.0, cleanup_policy="batch")
        config = _make_imaging_config()

        orch = BatchFittingOrchestrator(imaging_config=config, sammy_executable=sammy_exe, temp_manager=mgr)

        # Simulate entering the context manager to set _initial_free_gb
        with mgr:
            mock_executor = MagicMock(spec=ProcessPoolExecutor)
            mock_future = MagicMock()
            mock_executor.submit.return_value = mock_future

            pixel = _make_pixel(0, 0)
            orch._submit_pixels(mock_executor, [pixel], Path("/json"), Path("/endf"), attempt_round=3)

            call_args = mock_executor.submit.call_args
            args = call_args[0]
            # args: (fn, pixel, config, exe, resolution, json, endf, base_dir, policy,
            #        attempt_round, max_disk_usage_gb, initial_free_gb)
            assert args[9] == 3  # attempt_round
            assert args[10] == 25.0  # max_disk_usage_gb
            assert isinstance(args[11], float)  # initial_free_gb (recorded from real disk)

    def test_submit_pixels_without_temp_manager_passes_none_for_disk_params(self, tmp_path):
        """Without temp_manager, disk params are None (P2)."""
        from concurrent.futures import ProcessPoolExecutor
        from unittest.mock import MagicMock

        from pleiades.imaging.orchestrator import BatchFittingOrchestrator

        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        config = _make_imaging_config()
        orch = BatchFittingOrchestrator(imaging_config=config, sammy_executable=sammy_exe)

        mock_executor = MagicMock(spec=ProcessPoolExecutor)
        mock_future = MagicMock()
        mock_executor.submit.return_value = mock_future

        pixel = _make_pixel(0, 0)
        orch._submit_pixels(mock_executor, [pixel], Path("/json"), Path("/endf"))

        call_args = mock_executor.submit.call_args
        args = call_args[0]
        assert args[9] == 0  # attempt_round defaults to 0
        assert args[10] is None  # max_disk_usage_gb
        assert args[11] is None  # initial_free_gb

    def test_fit_pixels_enters_temp_manager_context(self, tmp_path):
        """fit_pixels enters TempFileManager context so _initial_free_gb is set for disk cap."""
        from concurrent.futures import Future
        from unittest.mock import MagicMock, patch

        from pleiades.imaging.models import PixelFitResult
        from pleiades.imaging.orchestrator import BatchFittingOrchestrator

        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        mgr = TempFileManager(base_dir=tmp_path / "ws", max_disk_usage_gb=25.0, cleanup_policy="batch")
        config = _make_imaging_config()
        orch = BatchFittingOrchestrator(imaging_config=config, sammy_executable=sammy_exe, temp_manager=mgr)

        # Before fit_pixels, initial_free_gb should be None
        assert mgr.initial_free_gb is None

        pixel = _make_pixel(0, 0)

        # Use real Future objects so as_completed works
        def submit_side_effect(fn, px, *args, **kwargs):
            future = Future()
            future.set_result(
                PixelFitResult(row=px.row, col=px.col, fit_results=None, success=False, error_message="mock")
            )
            return future

        mock_json_instance = MagicMock()

        def create_json_side_effect(isotopes, abundances, working_dir):
            working_dir.mkdir(parents=True, exist_ok=True)
            shared_json = working_dir / "config.json"
            shared_json.write_text("{}", encoding="utf-8")
            return shared_json

        mock_json_instance.create_json_config.side_effect = create_json_side_effect

        with patch("pleiades.imaging.orchestrator.JsonManager") as mock_json_cls:
            mock_json_cls.return_value = mock_json_instance
            with patch("pleiades.imaging.orchestrator.ProcessPoolExecutor") as mock_pool_cls:
                mock_executor = MagicMock()
                mock_pool_cls.return_value = mock_executor
                mock_executor.submit.side_effect = submit_side_effect
                orch.fit_pixels([pixel])

        # After fit_pixels, initial_free_gb should have been set by __enter__
        # Note: __exit__ already ran, but initial_free_gb persists on the object
        assert mgr.initial_free_gb is not None

    def test_fit_pixels_cleans_up_batch_workspaces(self, tmp_path):
        """fit_pixels cleans up batch workspaces on exit for non-manual policies."""
        from concurrent.futures import Future
        from unittest.mock import MagicMock, patch

        from pleiades.imaging.models import PixelFitResult
        from pleiades.imaging.orchestrator import BatchFittingOrchestrator

        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()

        base_dir = tmp_path / "ws"
        mgr = TempFileManager(base_dir=base_dir, max_disk_usage_gb=25.0, cleanup_policy="batch")
        config = _make_imaging_config()
        orch = BatchFittingOrchestrator(imaging_config=config, sammy_executable=sammy_exe, temp_manager=mgr)

        pixel = _make_pixel(0, 0)

        def submit_side_effect(fn, px, *args, **kwargs):
            future = Future()
            future.set_result(
                PixelFitResult(row=px.row, col=px.col, fit_results=None, success=False, error_message="mock")
            )
            return future

        mock_json_instance = MagicMock()

        def create_json_side_effect(isotopes, abundances, working_dir):
            working_dir.mkdir(parents=True, exist_ok=True)
            shared_json = working_dir / "config.json"
            shared_json.write_text("{}", encoding="utf-8")
            return shared_json

        mock_json_instance.create_json_config.side_effect = create_json_side_effect

        with patch("pleiades.imaging.orchestrator.JsonManager") as mock_json_cls:
            mock_json_cls.return_value = mock_json_instance
            with patch("pleiades.imaging.orchestrator.ProcessPoolExecutor") as mock_pool_cls:
                mock_executor = MagicMock()
                mock_pool_cls.return_value = mock_executor
                mock_executor.submit.side_effect = submit_side_effect
                orch.fit_pixels([pixel])

        # After fit_pixels, base_dir should be cleaned up for batch policy
        # (TempFileManager.__exit__ removes base_dir for non-manual policies)
        assert not base_dir.exists()


# ===========================================================================
# TestCheckWorkerDiskSpace
# ===========================================================================


class TestCheckWorkerDiskSpace:
    """Tests for _check_worker_disk_space function (P2: worker-side disk enforcement)."""

    def test_returns_none_when_space_sufficient(self, tmp_path):
        """Returns None (no error) when disk has enough space."""
        from pleiades.imaging.orchestrator import _check_worker_disk_space

        result = _check_worker_disk_space(tmp_path, max_disk_usage_gb=50.0, initial_free_gb=100.0)
        assert result is None

    def test_returns_error_when_free_space_too_low(self, tmp_path):
        """Returns error message when free space is below required_gb."""
        from pleiades.imaging.orchestrator import _check_worker_disk_space

        mock_usage = _DiskUsage(total=100 * _BYTES_PER_GB, used=99 * _BYTES_PER_GB, free=0)
        with patch("shutil.disk_usage", return_value=mock_usage):
            result = _check_worker_disk_space(tmp_path, max_disk_usage_gb=50.0, initial_free_gb=100.0)
            assert result is not None
            assert "free" in result

    def test_returns_error_when_consumed_exceeds_limit(self, tmp_path):
        """Returns error when consumed space exceeds max_disk_usage_gb."""
        from pleiades.imaging.orchestrator import _check_worker_disk_space

        # Simulate: initial_free was 100 GB, now 90 GB free → consumed 10 GB, limit 5 GB
        mock_usage = _DiskUsage(total=200 * _BYTES_PER_GB, used=110 * _BYTES_PER_GB, free=90 * _BYTES_PER_GB)
        with patch("shutil.disk_usage", return_value=mock_usage):
            result = _check_worker_disk_space(tmp_path, max_disk_usage_gb=5.0, initial_free_gb=100.0, required_gb=0.1)
            assert result is not None
            assert "consumed" in result
            assert "limit" in result

    def test_returns_none_when_consumed_within_limit(self, tmp_path):
        """Returns None when consumed space is within the limit."""
        from pleiades.imaging.orchestrator import _check_worker_disk_space

        # Simulate: initial_free was 100 GB, now 97 GB free → consumed 3 GB, limit 5 GB
        mock_usage = _DiskUsage(total=200 * _BYTES_PER_GB, used=103 * _BYTES_PER_GB, free=97 * _BYTES_PER_GB)
        with patch("shutil.disk_usage", return_value=mock_usage):
            result = _check_worker_disk_space(tmp_path, max_disk_usage_gb=5.0, initial_free_gb=100.0, required_gb=0.1)
            assert result is None

    def test_skips_consumed_check_when_params_none(self, tmp_path):
        """When max_disk_usage_gb or initial_free_gb is None, skips consumed-space check."""
        from pleiades.imaging.orchestrator import _check_worker_disk_space

        # With None params, only the free-space check runs
        result = _check_worker_disk_space(tmp_path, max_disk_usage_gb=None, initial_free_gb=None)
        assert result is None

    def test_returns_error_on_disk_usage_exception(self):
        """Returns error message when shutil.disk_usage raises an exception."""
        from pleiades.imaging.orchestrator import _check_worker_disk_space

        with patch("shutil.disk_usage", side_effect=OSError("disk gone")):
            result = _check_worker_disk_space(Path("/nonexistent"), max_disk_usage_gb=50.0, initial_free_gb=100.0)
            assert result is not None
            assert "disk check failed" in result

    def test_worker_returns_failure_on_disk_space_check(self, tmp_path):
        """_fit_pixel_worker returns PixelFitResult(success=False) when disk check fails (P2)."""
        from pleiades.imaging.orchestrator import _fit_pixel_worker

        pixel = _make_pixel(2, 3)
        config = _make_imaging_config()
        sammy_exe = tmp_path / "sammy"
        sammy_exe.touch()
        base_dir = tmp_path / "managed_ws"
        base_dir.mkdir()

        # Simulate disk full
        mock_usage = _DiskUsage(total=100 * _BYTES_PER_GB, used=99 * _BYTES_PER_GB, free=0)
        with patch("shutil.disk_usage", return_value=mock_usage):
            result = _fit_pixel_worker(
                pixel,
                config,
                sammy_exe,
                temp_base_dir=base_dir,
                cleanup_policy="batch",
                max_disk_usage_gb=50.0,
                initial_free_gb=100.0,
            )
            assert result.success is False
            assert "Disk space check failed" in result.error_message


# ---------------------------------------------------------------------------
# Helpers for integration tests
# ---------------------------------------------------------------------------


def _make_imaging_config():
    """Create a minimal ImagingConfig for testing."""
    from pleiades.imaging.config import ImagingConfig

    return ImagingConfig(
        isotopes=["Ta-181"],
        element="Ta",
        mass_number=181,
        density_g_cm3=16.6,
        thickness_mm=0.025,
        atomic_mass_amu=180.948,
    )


def _make_pixel(row: int, col: int):
    """Create a minimal PixelSpectrum for testing."""
    import numpy as np

    from pleiades.imaging.models import PixelSpectrum

    energy = np.linspace(1.0, 100.0, 10)
    return PixelSpectrum(
        row=row,
        col=col,
        energy=energy,
        transmission=np.full(10, 0.9),
        uncertainty=np.full(10, 0.01),
    )
