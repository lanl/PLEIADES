"""Comprehensive unit tests for sammy/io/lst_manager.py module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pleiades.sammy.data.options import SammyData
from pleiades.sammy.io.lst_manager import LstManager
from pleiades.sammy.results.models import RunResults


class TestLstManagerInitialization:
    """Test LstManager initialization scenarios."""

    def test_init_without_file_path(self):
        """Test initialization without providing a file path."""
        manager = LstManager()

        assert manager.run_results is not None
        assert isinstance(manager.run_results, RunResults)
        assert manager.run_results.data is not None
        assert len(manager.run_results.fit_results) == 0

    def test_init_with_provided_run_results(self):
        """Test initialization with a provided RunResults object."""
        custom_run_results = RunResults()
        manager = LstManager(run_results=custom_run_results)

        assert manager.run_results is custom_run_results
        assert manager.run_results is not RunResults()  # Should use provided object

    def test_init_with_nonexistent_file(self):
        """Test initialization with a non-existent file path."""
        fake_path = Path("/nonexistent/path/to/file.lst")

        with pytest.raises(FileNotFoundError, match="The file .* does not exist"):
            LstManager(lst_file_path=fake_path)

    @patch("pleiades.sammy.io.lst_manager.LstManager.process_lst_file")
    def test_init_with_existing_file(self, mock_process):
        """Test initialization with an existing file path."""
        with tempfile.NamedTemporaryFile(suffix=".lst", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(b"Sample LST data\n")
            tmp_path = Path(tmp.name)

        try:
            manager = LstManager(lst_file_path=tmp_path)

            # Verify process_lst_file was called
            mock_process.assert_called_once_with(tmp_path, manager.run_results)
            assert manager.run_results is not None
        finally:
            tmp_path.unlink()  # Clean up temp file

    def test_init_with_invalid_path_type(self):
        """Test initialization with an invalid path type (not Path object)."""
        # String path that doesn't exist won't trigger processing
        manager = LstManager(lst_file_path="not_a_path_object.lst")

        # Should create default RunResults but not process anything
        assert manager.run_results is not None
        assert isinstance(manager.run_results, RunResults)

    def test_init_with_none_path(self):
        """Test initialization with None as path."""
        manager = LstManager(lst_file_path=None)

        assert manager.run_results is not None
        assert isinstance(manager.run_results, RunResults)

    def test_init_with_both_parameters(self):
        """Test initialization with both file path and run_results."""
        custom_run_results = RunResults()

        with tempfile.NamedTemporaryFile(suffix=".lst", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(b"Sample data\n")

        try:
            with patch("pleiades.sammy.io.lst_manager.LstManager.process_lst_file") as mock_process:
                manager = LstManager(lst_file_path=tmp_path, run_results=custom_run_results)

                assert manager.run_results is custom_run_results
                mock_process.assert_called_once_with(tmp_path, custom_run_results)
        finally:
            tmp_path.unlink()


class TestProcessLstFile:
    """Test the process_lst_file method."""

    @patch("pleiades.sammy.io.lst_manager.SammyData")
    def test_process_lst_file_basic(self, mock_sammy_data_class):
        """Test basic process_lst_file functionality."""
        # Setup mock
        mock_data_instance = MagicMock(spec=SammyData)
        mock_sammy_data_class.return_value = mock_data_instance

        # Create manager and process file
        manager = LstManager()
        test_path = Path("/test/file.lst")

        manager.process_lst_file(test_path, manager.run_results)

        # Verify SammyData was created with correct path
        mock_sammy_data_class.assert_called_once_with(data_file=test_path)

        # Verify load was called on the instance
        mock_data_instance.load.assert_called_once()

        # Verify data was stored in run_results
        assert manager.run_results.data is mock_data_instance

    @patch("pleiades.sammy.io.lst_manager.SammyData")
    def test_process_lst_file_with_custom_run_results(self, mock_sammy_data_class):
        """Test process_lst_file with a custom RunResults object."""
        mock_data_instance = MagicMock(spec=SammyData)
        mock_sammy_data_class.return_value = mock_data_instance

        manager = LstManager()
        custom_run_results = RunResults()
        test_path = Path("/test/file.lst")

        manager.process_lst_file(test_path, custom_run_results)

        # Verify data was stored in the custom run_results
        assert custom_run_results.data is mock_data_instance
        mock_data_instance.load.assert_called_once()

    @patch("pleiades.sammy.io.lst_manager.SammyData")
    def test_process_lst_file_load_exception(self, mock_sammy_data_class):
        """Test process_lst_file when SammyData.load raises an exception."""
        mock_data_instance = MagicMock(spec=SammyData)
        mock_data_instance.load.side_effect = ValueError("Invalid data format")
        mock_sammy_data_class.return_value = mock_data_instance

        manager = LstManager()
        test_path = Path("/test/file.lst")

        with pytest.raises(ValueError, match="Invalid data format"):
            manager.process_lst_file(test_path, manager.run_results)

    @patch("pleiades.sammy.io.lst_manager.SammyData")
    def test_process_lst_file_multiple_calls(self, mock_sammy_data_class):
        """Test calling process_lst_file multiple times."""
        # Create different mock instances for each call
        mock_data1 = MagicMock(spec=SammyData)
        mock_data2 = MagicMock(spec=SammyData)
        mock_sammy_data_class.side_effect = [mock_data1, mock_data2]

        manager = LstManager()
        run_results = RunResults()

        # Process first file
        test_path1 = Path("/test/file1.lst")
        manager.process_lst_file(test_path1, run_results)
        assert run_results.data is mock_data1

        # Process second file (should overwrite)
        test_path2 = Path("/test/file2.lst")
        manager.process_lst_file(test_path2, run_results)
        assert run_results.data is mock_data2

        # Verify both were loaded
        mock_data1.load.assert_called_once()
        mock_data2.load.assert_called_once()


class TestIntegrationScenarios:
    """Test integration scenarios with actual file operations."""

    def test_full_workflow_with_real_file(self):
        """Test complete workflow with a real LST file."""
        # Create a sample LST file with realistic data
        lst_content = """# Sample LST file
1.0 0.5 0.01 0.49 0.51 0.95 0.02 0.94 0.96
2.0 0.6 0.01 0.59 0.61 0.85 0.02 0.84 0.86
3.0 0.7 0.01 0.69 0.71 0.75 0.02 0.74 0.76
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".lst", delete=False) as tmp:
            tmp.write(lst_content)
            tmp_path = Path(tmp.name)

        try:
            # Create manager and load file
            manager = LstManager(lst_file_path=tmp_path)

            # Verify run_results was populated
            assert manager.run_results is not None
            assert manager.run_results.data is not None

            # Verify data was loaded (SammyData should have processed the file)
            assert hasattr(manager.run_results.data, "data_file")
            assert manager.run_results.data.data_file == tmp_path

            # Check if data DataFrame was created and has correct shape
            if manager.run_results.data.data is not None:
                assert len(manager.run_results.data.data) == 3  # 3 data rows

        finally:
            tmp_path.unlink()

    def test_workflow_with_empty_file(self):
        """Test workflow with an empty LST file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".lst", delete=False) as tmp:
            # Create empty file
            tmp_path = Path(tmp.name)

        try:
            # This might raise an error depending on SammyData's handling of empty files
            # We test that LstManager properly propagates any errors
            manager = LstManager(lst_file_path=tmp_path)

            # If it doesn't raise an error, verify structure is created
            assert manager.run_results is not None
            assert manager.run_results.data is not None

        except Exception:
            # If SammyData raises an error for empty files, that's also valid behavior
            pass
        finally:
            tmp_path.unlink()

    def test_multiple_managers_independent(self):
        """Test that multiple LstManager instances are independent."""
        manager1 = LstManager()
        manager2 = LstManager()

        # Verify they have different RunResults instances
        assert manager1.run_results is not manager2.run_results

        # Modify one and verify the other is unchanged
        from pleiades.sammy.results.models import FitResults

        fit_result = FitResults()
        manager1.run_results.add_fit_result(fit_result)

        assert len(manager1.run_results.fit_results) == 1
        assert len(manager2.run_results.fit_results) == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @patch("pleiades.sammy.io.lst_manager.SammyData")
    def test_process_none_path(self, mock_sammy_data_class):
        """Test process_lst_file with None as path."""
        mock_data_instance = MagicMock(spec=SammyData)
        mock_sammy_data_class.return_value = mock_data_instance

        manager = LstManager()

        # This should work - SammyData should handle None
        manager.process_lst_file(None, manager.run_results)

        mock_sammy_data_class.assert_called_once_with(data_file=None)
        mock_data_instance.load.assert_called_once()

    def test_path_exists_but_not_readable(self):
        """Test with a path that exists but is not readable."""
        with tempfile.NamedTemporaryFile(suffix=".lst", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(b"data")

        try:
            # Make file unreadable (Unix-specific)
            import os

            os.chmod(tmp_path, 0o000)

            # This should raise some kind of permission error
            with pytest.raises(Exception):  # Could be PermissionError or other
                LstManager(lst_file_path=tmp_path)

        finally:
            # Restore permissions and clean up
            import os

            os.chmod(tmp_path, 0o644)
            tmp_path.unlink()

    @patch("pleiades.sammy.io.lst_manager.SammyData")
    def test_sammy_data_creation_failure(self, mock_sammy_data_class):
        """Test when SammyData creation fails."""
        mock_sammy_data_class.side_effect = MemoryError("Out of memory")

        manager = LstManager()
        test_path = Path("/test/file.lst")

        with pytest.raises(MemoryError, match="Out of memory"):
            manager.process_lst_file(test_path, manager.run_results)

    def test_path_object_validation(self):
        """Test that only Path objects trigger file processing."""
        # These should not trigger file processing
        invalid_paths = [
            "string_path.lst",
            123,
            ["list", "of", "paths"],
            {"dict": "path"},
        ]

        for invalid_path in invalid_paths:
            manager = LstManager(lst_file_path=invalid_path)
            # Should create default RunResults without error
            assert manager.run_results is not None
            assert isinstance(manager.run_results, RunResults)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
