#!/usr/bin/env python
"""Unit tests for SAMMY interface module."""

from datetime import datetime

import pytest

from pleiades.sammy.interface import (
    BaseSammyConfig,
    EnvironmentPreparationError,
    SammyExecutionResult,
    SammyFiles,
    SammyFilesMultiMode,
    SammyRunner,
)


class TestSammyFiles:
    """Tests for SammyFiles data structure."""

    def test_create_valid(self, mock_sammy_files):
        """Should create with valid paths."""
        files = SammyFiles(**mock_sammy_files)
        assert files.input_file == mock_sammy_files["input_file"]
        assert files.parameter_file == mock_sammy_files["parameter_file"]
        assert files.data_file == mock_sammy_files["data_file"]

    def test_validate_missing_file(self, mock_sammy_files, tmp_path):
        """Should raise FileNotFoundError for missing files."""
        # Create with non-existent file
        files = SammyFiles(
            input_file=tmp_path / "nonexistent.inp",
            parameter_file=mock_sammy_files["parameter_file"],
            data_file=mock_sammy_files["data_file"],
        )

        with pytest.raises(FileNotFoundError) as exc:
            files.validate()
        assert "not found" in str(exc.value)

    def test_validate_directory(self, mock_sammy_files):
        """Should validate input files are actual files not directories."""
        # Create a directory with same name as input file
        dir_path = mock_sammy_files["input_file"].parent / "test.inp"
        dir_path.mkdir(exist_ok=True)

        files = SammyFiles(
            input_file=dir_path,
            parameter_file=mock_sammy_files["parameter_file"],
            data_file=mock_sammy_files["data_file"],
        )

        with pytest.raises(FileNotFoundError) as exc:
            files.validate()
        assert "is not a file" in str(exc.value)

    def test_move_to_working_dir(self, mock_sammy_files, tmp_path):
        """Test file copying and symlinking to working directory."""
        # Create a new working directory
        working_dir = tmp_path / "working_dir"
        working_dir.mkdir()

        # Create the files container with valid files
        files = SammyFiles(**mock_sammy_files)

        # Save original paths
        original_input = files.input_file
        original_parameter = files.parameter_file
        original_data = files.data_file

        # Move files to working directory
        files.move_to_working_dir(working_dir)

        # Check paths have been updated
        assert files.input_file.parent == working_dir
        assert files.parameter_file.parent == working_dir
        assert files.data_file.parent == working_dir

        # Check filenames remain the same
        assert files.input_file.name == original_input.name
        assert files.parameter_file.name == original_parameter.name
        assert files.data_file.name == original_data.name

        # Verify input and parameter files were copied
        assert files.input_file.exists()
        assert files.parameter_file.exists()
        assert not files.input_file.is_symlink()
        assert not files.parameter_file.is_symlink()

        # Verify data file was symlinked
        assert files.data_file.exists()
        assert files.data_file.is_symlink()

        # Verify original paths were stored
        assert files._original_input_file == original_input
        assert files._original_parameter_file == original_parameter
        assert files._original_data_file == original_data


class TestSammyExecutionResult:
    """Tests for SammyExecutionResult data structure."""

    def test_create_success(self):
        """Should create successful result."""
        start_time = datetime.now()
        result = SammyExecutionResult(
            success=True,
            execution_id="test_123",
            start_time=start_time,
            end_time=start_time,
            console_output="Normal finish to SAMMY",
        )
        assert result.success
        assert result.error_message is None

    def test_create_failure(self):
        """Should create failure result."""
        start_time = datetime.now()
        result = SammyExecutionResult(
            success=False,
            execution_id="test_456",
            start_time=start_time,
            end_time=start_time,
            console_output="Error occurred",
            error_message="Test error",
        )
        assert not result.success
        assert result.error_message == "Test error"

    def test_runtime_calculation(self):
        """Should calculate runtime correctly."""
        from datetime import timedelta

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=10)
        result = SammyExecutionResult(
            success=True,
            execution_id="test_789",
            start_time=start_time,
            end_time=end_time,
            console_output="Test output",
        )
        assert result.runtime_seconds == pytest.approx(10.0)


class MockSammyConfig(BaseSammyConfig):
    """Mock configuration for testing."""

    def validate(self) -> bool:
        return super().validate()


class TestBaseSammyConfig:
    """Tests for BaseSammyConfig."""

    def test_validate_working_dir(self, temp_working_dir):
        """Should validate working directory exists."""
        config = MockSammyConfig(working_dir=temp_working_dir, output_dir=temp_working_dir / "output")
        assert config.validate()

    def test_creates_output_dir(self, temp_working_dir):
        """Should create output directory if it doesn't exist."""
        output_dir = temp_working_dir / "new_output"
        assert not output_dir.exists()

        config = MockSammyConfig(working_dir=temp_working_dir, output_dir=output_dir)
        config.validate()

        assert output_dir.exists()

    def test_shared_working_output_dir(self, temp_working_dir):
        """Should allow working_dir and output_dir to be the same."""
        config = MockSammyConfig(working_dir=temp_working_dir, output_dir=temp_working_dir)
        assert config.validate()

    def test_nested_output_dir(self, temp_working_dir):
        """Should handle nested output directory."""
        nested_output = temp_working_dir / "level1" / "level2" / "output"
        config = MockSammyConfig(working_dir=temp_working_dir, output_dir=nested_output)
        config.validate()
        assert nested_output.exists()


class MockSammyRunner(SammyRunner):
    """Mock runner for testing abstract base class."""

    def prepare_environment(self, files: SammyFiles) -> None:
        self.prepared = True
        _ = files  # deal with unused variable warning

    def execute_sammy(self, files: SammyFiles) -> SammyExecutionResult:
        _ = files  # deal with unused variable warning
        if not hasattr(self, "prepared"):
            raise EnvironmentPreparationError("Environment not prepared")
        return SammyExecutionResult(
            success=True,
            execution_id="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            console_output="Test output",
        )

    def cleanup(self) -> None:
        self.cleaned = True

    def validate_config(self) -> bool:
        return self.config.validate()


class TestSammyRunner:
    """Tests for SammyRunner abstract base class."""

    def test_execution_flow(self, mock_sammy_files, temp_working_dir):
        """Should follow correct execution flow."""
        config = MockSammyConfig(working_dir=temp_working_dir, output_dir=temp_working_dir / "output")
        runner = MockSammyRunner(config)
        files = SammyFiles(**mock_sammy_files)

        # Test preparation
        runner.prepare_environment(files)
        assert runner.prepared

        # Test execution
        result = runner.execute_sammy(files)
        assert result.success
        assert isinstance(result, SammyExecutionResult)

        # Test cleanup
        runner.cleanup()
        assert runner.cleaned

    def test_execution_without_preparation(self, mock_sammy_files, temp_working_dir):
        """Should raise error if executing without preparation."""
        config = MockSammyConfig(working_dir=temp_working_dir, output_dir=temp_working_dir / "output")
        runner = MockSammyRunner(config)
        files = SammyFiles(**mock_sammy_files)

        with pytest.raises(EnvironmentPreparationError):
            runner.execute_sammy(files)

    def test_validate_config(self, temp_working_dir):
        """Should validate configuration."""
        config = MockSammyConfig(working_dir=temp_working_dir, output_dir=temp_working_dir / "output")
        runner = MockSammyRunner(config)
        assert runner.validate_config()


class TestSammyFilesMultiMode:
    """Tests for SammyFilesMultiMode data structure."""

    @pytest.fixture
    def mock_multimode_files(self, tmp_path):
        """Create mock files for SammyFilesMultiMode testing."""
        # Create mock files
        inp_file = tmp_path / "test.inp"
        json_file = tmp_path / "test.json"
        dat_file = tmp_path / "test.dat"
        endf_dir = tmp_path / "endf"

        inp_file.write_text("mock inp content")
        dat_file.write_text("mock dat content")
        endf_dir.mkdir()

        # Create valid JSON with ENDF reference
        import json

        json_data = {"forceRMoore": "yes", "079-Au-197.B-VIII.0.par": [{"mat": "7925", "abundance": "1.0"}]}
        with open(json_file, "w") as f:
            json.dump(json_data, f)

        # Create referenced ENDF file
        endf_file = endf_dir / "079-Au-197.B-VIII.0.par"
        endf_file.write_text("mock endf content")

        return {
            "input_file": inp_file,
            "json_config_file": json_file,
            "data_file": dat_file,
            "endf_directory": endf_dir,
        }

    def test_create_valid(self, mock_multimode_files):
        """Should create with valid paths."""
        files = SammyFilesMultiMode(**mock_multimode_files)
        assert files.input_file == mock_multimode_files["input_file"]
        assert files.json_config_file == mock_multimode_files["json_config_file"]
        assert files.data_file == mock_multimode_files["data_file"]
        assert files.endf_directory == mock_multimode_files["endf_directory"]

    def test_validate_success(self, mock_multimode_files):
        """Should validate successfully with all required files."""
        files = SammyFilesMultiMode(**mock_multimode_files)
        # Should not raise any exceptions
        files.validate()

    def test_validate_missing_file(self, mock_multimode_files):
        """Should raise FileNotFoundError for missing files."""
        # Test missing input file
        mock_multimode_files["input_file"] = mock_multimode_files["input_file"].parent / "nonexistent.inp"
        files = SammyFilesMultiMode(**mock_multimode_files)

        with pytest.raises(FileNotFoundError, match="Input File not found"):
            files.validate()

    def test_validate_missing_endf_directory(self, mock_multimode_files):
        """Should raise FileNotFoundError for missing ENDF directory."""
        mock_multimode_files["endf_directory"] = mock_multimode_files["endf_directory"].parent / "nonexistent"
        files = SammyFilesMultiMode(**mock_multimode_files)

        with pytest.raises(FileNotFoundError, match="ENDF directory not found"):
            files.validate()

    def test_move_to_working_dir(self, mock_multimode_files, tmp_path):
        """Should move files to working directory correctly."""
        files = SammyFilesMultiMode(**mock_multimode_files)
        working_dir = tmp_path / "working"
        working_dir.mkdir()

        # Move files
        files.move_to_working_dir(working_dir)

        # Verify files were moved/symlinked
        assert (working_dir / "test.inp").exists()
        assert (working_dir / "test.json").exists()
        assert (working_dir / "test.dat").exists()
        assert (working_dir / "079-Au-197.B-VIII.0.par").exists()

        # Verify symlinks
        assert (working_dir / "test.dat").is_symlink()
        assert (working_dir / "079-Au-197.B-VIII.0.par").is_symlink()

    def test_cleanup_working_files(self, mock_multimode_files, tmp_path):
        """Should cleanup working files correctly."""
        files = SammyFilesMultiMode(**mock_multimode_files)
        working_dir = tmp_path / "working"
        working_dir.mkdir()

        # Move files first
        original_input = files.input_file
        files.move_to_working_dir(working_dir)

        # Cleanup
        files.cleanup_working_files()

        # Verify original paths restored
        assert files.input_file == original_input
        assert files._original_input_file is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
