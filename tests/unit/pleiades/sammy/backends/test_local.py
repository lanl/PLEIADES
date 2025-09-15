#!/usr/bin/env python
"""Unit tests for local SAMMY backend."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pleiades.sammy.backends.local import LocalSammyRunner
from pleiades.sammy.config import LocalSammyConfig
from pleiades.sammy.interface import EnvironmentPreparationError, SammyExecutionError, SammyFiles, SammyFilesMultiMode


@pytest.fixture
def mock_sammy_executable(monkeypatch):
    """Mock shutil.which to simulate SAMMY being available."""

    def mock_which(cmd):
        if cmd == "sammy":
            return "sammy"
        return None

    monkeypatch.setattr("shutil.which", mock_which)
    return mock_which


@pytest.fixture
def local_config(temp_working_dir, mock_sammy_executable):
    """Create local SAMMY configuration."""
    _ = mock_sammy_executable  # make pre-commit happy
    local_sammy_config = LocalSammyConfig(
        working_dir=temp_working_dir,
        output_dir=temp_working_dir / "output",
        sammy_executable=Path("sammy"),
        shell_path=Path("/bin/bash"),
    )
    # call validate to ensure directories are created
    local_sammy_config.validate()
    return local_sammy_config


@pytest.fixture
def mock_subprocess_run(monkeypatch, mock_sammy_output):
    """Mock subprocess.run to avoid actual SAMMY execution."""

    def mock_run(*args, **kwargs):
        _ = kwargs
        result = subprocess.CompletedProcess(args=args, returncode=0, stdout=mock_sammy_output, stderr="")
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    return mock_run


@pytest.fixture
def mock_subprocess_fail(monkeypatch, mock_sammy_error_output):
    """Mock subprocess.run to simulate SAMMY failure."""

    def mock_run(*args, **kwargs):
        _ = kwargs
        result = subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr=mock_sammy_error_output,
        )
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)
    return mock_run


class TestLocalSammyRunner:
    """Tests for LocalSammyRunner."""

    def test_initialization(self, local_config):
        """Should initialize with valid config."""
        runner = LocalSammyRunner(local_config)
        assert runner.config == local_config
        assert runner.validate_config()

    def test_prepare_environment(self, local_config, mock_sammy_files):
        """Should prepare environment successfully."""
        runner = LocalSammyRunner(local_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        assert local_config.output_dir.exists()

    def test_prepare_environment_invalid_files(self, local_config, tmp_path):
        """Should raise error with invalid files."""
        runner = LocalSammyRunner(local_config)
        files = SammyFiles(
            input_file=tmp_path / "nonexistent.inp",
            parameter_file=tmp_path / "nonexistent.par",
            data_file=tmp_path / "nonexistent.dat",
        )

        with pytest.raises(EnvironmentPreparationError):
            runner.prepare_environment(files)

    def test_execute_sammy_success(self, local_config, mock_sammy_files, mock_subprocess_run):
        """Should execute SAMMY successfully."""
        _ = mock_subprocess_run  # make pre-commit happy
        runner = LocalSammyRunner(local_config)
        files = SammyFiles(**mock_sammy_files)

        # mock_subprocess_run is used implicitly via the fixture's monkeypatch
        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        assert result.success
        assert "Normal finish to SAMMY" in result.console_output
        assert result.error_message is None

    def test_execute_sammy_failure(self, local_config, mock_sammy_files, mock_subprocess_fail):
        """Should handle SAMMY execution failure."""
        _ = mock_subprocess_fail  # make pre-commit happy
        runner = LocalSammyRunner(local_config)
        files = SammyFiles(**mock_sammy_files)

        # mock_subprocess_fail is used implicitly via the fixture's monkeypatch
        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        assert not result.success
        assert "SAMMY execution failed" in result.error_message

    def test_execute_sammy_crash(self, local_config, mock_sammy_files, monkeypatch):
        """Should handle subprocess crash."""

        def mock_run(*args, **kwargs):
            _ = args
            _ = kwargs
            raise subprocess.SubprocessError("Mock crash")

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = LocalSammyRunner(local_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        with pytest.raises(SammyExecutionError) as exc:
            runner.execute_sammy(files)
        assert "Mock crash" in str(exc.value)

    def test_collect_outputs(self, local_config, mock_sammy_files, mock_subprocess_run, mock_sammy_results):
        """Should collect output files."""
        _ = mock_subprocess_run  # make pre-commit happy
        _ = mock_sammy_results  # make pre-commit happy
        runner = LocalSammyRunner(local_config)
        files = SammyFiles(**mock_sammy_files)

        # Execute SAMMY to create outputs
        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        # Collect outputs
        runner.collect_outputs(result)

        # Check output files were moved
        assert (local_config.output_dir / "SAMMY.LPT").exists()
        assert (local_config.output_dir / "SAMMY.PAR").exists()

    def test_cleanup(self, local_config, mock_sammy_files, mock_subprocess_run, mock_sammy_results):
        """Should perform cleanup successfully."""
        _ = mock_subprocess_run  # make pre-commit happy
        _ = mock_sammy_results  # make pre-commit happy
        runner = LocalSammyRunner(local_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)
        runner.collect_outputs(result)
        runner.cleanup()


class TestLocalSammyRunnerJsonMode:
    """Tests for LocalSammyRunner JSON mode functionality."""

    @pytest.fixture
    def mock_multimode_files(self, tmp_path):
        """Create mock files for JSON mode testing."""
        # Create mock files
        inp_file = tmp_path / "test.inp"
        json_file = tmp_path / "test.json"
        dat_file = tmp_path / "test.dat"
        endf_dir = tmp_path / "endf"

        inp_file.write_text("INPUT IS ENDF/B FILE\nchi squared is wanted")
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

    def test_json_mode_validation_success(self, local_config, mock_multimode_files):
        """Should validate JSON mode files successfully."""
        runner = LocalSammyRunner(local_config)
        files = SammyFilesMultiMode(**mock_multimode_files)

        # Should not raise any exceptions
        runner._validate_json_endf_mapping(files)

    def test_json_mode_validation_missing_endf(self, local_config, mock_multimode_files):
        """Should detect missing ENDF files referenced in JSON."""
        runner = LocalSammyRunner(local_config)

        # Create JSON that references missing ENDF file
        import json

        json_data = {"forceRMoore": "yes", "missing-endf-file.par": [{"mat": "1234", "abundance": "0.5"}]}
        with open(mock_multimode_files["json_config_file"], "w") as f:
            json.dump(json_data, f)

        files = SammyFilesMultiMode(**mock_multimode_files)

        with pytest.raises(ValueError, match="missing ENDF files"):
            runner._validate_json_endf_mapping(files)

    def test_json_mode_command_generation(self, local_config, mock_multimode_files, monkeypatch):
        """Should generate correct SAMMY command for JSON mode."""
        # Mock subprocess to capture command
        executed_commands = []

        def mock_run(command, **kwargs):
            executed_commands.append(command)
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = " Normal finish to SAMMY"
            return mock_result

        monkeypatch.setattr(subprocess, "run", mock_run)

        runner = LocalSammyRunner(local_config)
        files = SammyFilesMultiMode(**mock_multimode_files)

        # Execute (will be mocked)
        runner.execute_sammy(files)

        # Verify command format
        assert len(executed_commands) == 1
        command = executed_commands[0]

        # Should contain #file for JSON mode
        assert "#file" in command
        assert "test.json" in command
        assert "test.inp" in command
        assert "test.dat" in command

    def test_prepare_environment_json_mode(self, local_config, mock_multimode_files):
        """Should prepare environment for JSON mode successfully."""
        runner = LocalSammyRunner(local_config)
        files = SammyFilesMultiMode(**mock_multimode_files)

        # Should not raise any exceptions
        runner.prepare_environment(files)

        # Verify files were moved to working directory
        assert files.input_file.parent == local_config.working_dir
        assert files.json_config_file.parent == local_config.working_dir
        assert files.data_file.parent == local_config.working_dir


if __name__ == "__main__":
    pytest.main(["-v", __file__])
