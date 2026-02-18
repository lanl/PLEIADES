#!/usr/bin/env python
"""Unit tests for local SAMMY backend."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pleiades.sammy.backends.local import (
    LocalSammyRunner,
    _enable_abundance_fitting_in_par,
    _move_broadening_inp_to_par,
)
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
        # Mock subprocess to capture command and input
        executed_commands = []
        captured_inputs = []

        def mock_run(command, **kwargs):
            executed_commands.append(command)
            if "input" in kwargs:
                captured_inputs.append(kwargs["input"])
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

        # Verify command format - now using list format without shell
        assert len(executed_commands) == 1
        command = executed_commands[0]
        assert isinstance(command, list)
        assert str(local_config.sammy_executable) in command[0]

        # Verify input contains the JSON mode format
        assert len(captured_inputs) == 1
        input_text = captured_inputs[0]
        assert "#file" in input_text
        assert "test.json" in input_text
        assert "test.inp" in input_text
        assert "test.dat" in input_text

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


class TestEnableAbundanceFittingInPar:
    """Tests for the _enable_abundance_fitting_in_par helper function."""

    def test_modifies_ifliso_flags(self, tmp_path):
        """Should change IFLISO from 0 to 1 for all isotopes in Card 10."""
        par_content = (
            "ISOTOpic abundances and masses\n"
            "180.94788   0.50000   0.02000 0 1 2 3 4 5\n"
            "235.04393   0.50000   0.02000 0 6 7 8 9\n"
            "\n"
        )
        par_file = tmp_path / "test.par"
        par_file.write_text(par_content)

        _enable_abundance_fitting_in_par(par_file)

        result = par_file.read_text()
        lines = result.splitlines()
        # Header unchanged
        assert lines[0] == "ISOTOpic abundances and masses"
        # IFLISO changed from 0 to 1 (columns 31-32)
        assert lines[1][30:32] == " 1"
        assert lines[2][30:32] == " 1"

    def test_preserves_other_content(self, tmp_path):
        """Should not modify content outside Card 10."""
        par_content = (
            "KEY-WORD PARTICLE-PAIR definitions are given\n"
            "some particle pair data\n"
            "\n"
            "ISOTOpic abundances and masses\n"
            "180.94788   0.50000   0.02000 0 1 2 3\n"
            "\n"
            "NORMAlization and background are next\n"
            " 1.000000  0.000000  0.000000\n"
        )
        par_file = tmp_path / "test.par"
        par_file.write_text(par_content)

        _enable_abundance_fitting_in_par(par_file)

        result = par_file.read_text()
        lines = result.splitlines()
        # Non-Card-10 lines unchanged
        assert lines[0] == "KEY-WORD PARTICLE-PAIR definitions are given"
        assert lines[1] == "some particle pair data"
        assert lines[6] == "NORMAlization and background are next"
        assert lines[7] == " 1.000000  0.000000  0.000000"
        # Card 10 isotope line modified
        assert lines[4][30:32] == " 1"

    def test_handles_nuclide_header(self, tmp_path):
        """Should also recognize NUCLIde header variant."""
        par_content = "NUCLIde abundances and masses\n180.94788   0.50000   0.02000 0 1 2 3\n\n"
        par_file = tmp_path / "test.par"
        par_file.write_text(par_content)

        _enable_abundance_fitting_in_par(par_file)

        result = par_file.read_text()
        lines = result.splitlines()
        assert lines[1][30:32] == " 1"

    def test_skips_continuation_markers(self, tmp_path):
        """Should not modify -1 continuation lines."""
        par_content = (
            "ISOTOpic abundances and masses\n"
            "180.94788   0.50000   0.02000 0 1 2 3 4 5 6 7 8 9101112131415161718192021222324\n"
            "-1\n"
            "   25   26   27\n"
            "\n"
        )
        par_file = tmp_path / "test.par"
        par_file.write_text(par_content)

        _enable_abundance_fitting_in_par(par_file)

        result = par_file.read_text()
        lines = result.splitlines()
        assert lines[1][30:32] == " 1"
        assert lines[2].strip() == "-1"

    def test_no_card10_is_noop(self, tmp_path):
        """Should not crash when par file has no Card 10."""
        par_content = "NORMAlization and background are next\n 1.000000  0.000000  0.000000\n"
        par_file = tmp_path / "test.par"
        par_file.write_text(par_content)

        _enable_abundance_fitting_in_par(par_file)

        result = par_file.read_text()
        assert result == par_content


class TestMoveBroadeningInpToPar:
    """Tests for the _move_broadening_inp_to_par helper function."""

    def test_moves_fitted_broadening_to_par(self, tmp_path):
        """Should extract last broadening section from INP and append to PAR."""
        inp_content = (
            "Title line\n"
            "BROADENING IS WANTED\n"
            "SOLVE BAYES EQUATIONS\n"
            "\n"
            "    293.6     25.0000\n"
            "transmission\n"
            "BROADENING PARAMETERS FOLLOW\n"
            "  8.000000293.600000  0.000139 0 0 1 0 0\n"
            "\n"
            "BROADENING PARAMETERS FOLLOW\n"
            "7.86000000 293.60000 2.80939-5 0 0 1 0 0 0\n"
            " 0.        0.        1.41723-5\n"
            " \n"
            "MISCEllaneous parameters follow\n"
        )
        par_content = (
            "ISOTOPIC ABUNDANCES\n   180.948       0.5         1 0 1 2\n   235.044       0.5         1 0 3 4\n"
        )
        inp_file = tmp_path / "SAMNDF.INP"
        par_file = tmp_path / "SAMNDF.PAR"
        inp_file.write_text(inp_content)
        par_file.write_text(par_content)

        _move_broadening_inp_to_par(inp_file, par_file)

        # INP: broadening command and data removed
        inp_result = inp_file.read_text()
        assert "BROADENING" not in inp_result.upper()
        assert "SOLVE BAYES EQUATIONS" in inp_result
        assert "MISCEllaneous" in inp_result

        # PAR: fitted broadening appended (last section)
        par_result = par_file.read_text()
        assert "BROADENING PARAMETERS FOLLOW" in par_result
        assert "2.80939-5" in par_result  # fitted thickness, not original
        assert "ISOTOPIC ABUNDANCES" in par_result  # original content preserved

    def test_single_broadening_section(self, tmp_path):
        """Should handle INP with only one broadening section."""
        inp_content = (
            "Title\n"
            "BROADENING IS WANTED\n"
            "\n"
            "BROADENING PARAMETERS FOLLOW\n"
            "  8.000000293.600000  0.000139 0 0 1 0 0\n"
            "\n"
            "NORMAlization\n"
        )
        par_content = "ISOTOPIC ABUNDANCES\n"
        inp_file = tmp_path / "test.inp"
        par_file = tmp_path / "test.par"
        inp_file.write_text(inp_content)
        par_file.write_text(par_content)

        _move_broadening_inp_to_par(inp_file, par_file)

        inp_result = inp_file.read_text()
        assert "BROADENING" not in inp_result.upper()

        par_result = par_file.read_text()
        assert "BROADENING PARAMETERS FOLLOW" in par_result

    def test_no_broadening_is_noop(self, tmp_path):
        """Should not crash when no broadening in INP."""
        inp_content = "Title\nSOLVE BAYES\n\ntransmission\n"
        par_content = "ISOTOPIC ABUNDANCES\n"
        inp_file = tmp_path / "test.inp"
        par_file = tmp_path / "test.par"
        inp_file.write_text(inp_content)
        par_file.write_text(par_content)

        _move_broadening_inp_to_par(inp_file, par_file)

        assert inp_file.read_text() == inp_content
        # PAR unchanged (no broadening to move)
        assert par_file.read_text() == par_content


if __name__ == "__main__":
    pytest.main(["-v", __file__])
