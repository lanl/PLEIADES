#!/usr/bin/env python
"""Unit tests for Docker SAMMY backend."""

import subprocess
from pathlib import Path

import pytest

from pleiades.sammy.backends.docker import DockerSammyRunner
from pleiades.sammy.config.config_errors import EnvironmentPreparationError
from pleiades.sammy.config.sammy_options import DockerConfig
from pleiades.sammy.interface import SammyFiles


@pytest.fixture
def mock_docker_command(monkeypatch):
    """Mock shutil.which to simulate docker being available."""

    def mock_which(cmd):
        if cmd == "docker":
            return "/usr/bin/docker"
        return None

    monkeypatch.setattr("shutil.which", mock_which)
    return mock_which


@pytest.fixture
def mock_subprocess_docker(monkeypatch, mock_sammy_output):
    """Mock subprocess.run for docker commands."""

    def mock_run(*args, **kwargs):
        _ = kwargs  # Unused
        cmd_str = " ".join(str(x) for x in args[0])  # Convert command array to string
        if "docker image inspect" in cmd_str:  # Image check
            return subprocess.CompletedProcess(args=args, returncode=0, stdout='[{"Id": "mock_image_id"}]', stderr="")
        if "docker run" in cmd_str:  # Docker run
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=mock_sammy_output, stderr="")
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="Command not found")

    monkeypatch.setattr(subprocess, "run", mock_run)
    return mock_run


@pytest.fixture
def mock_subprocess_docker_fail(monkeypatch, mock_sammy_error_output):
    """Mock subprocess.run for docker failure."""

    def mock_run(*args, **kwargs):
        _ = kwargs  # Unused
        cmd_str = " ".join(str(x) for x in args[0])  # Convert command array to string
        if "docker image inspect" in cmd_str:  # Image check should succeed
            return subprocess.CompletedProcess(args=args, returncode=0, stdout='[{"Id": "mock_image_id"}]', stderr="")
        if "docker run" in cmd_str:  # Docker run should fail
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr=mock_sammy_error_output)
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="Command not found")

    monkeypatch.setattr(subprocess, "run", mock_run)
    return mock_run


@pytest.fixture
def docker_config(temp_working_dir):
    """Create Docker SAMMY configuration."""
    config = DockerConfig(
        working_dir=temp_working_dir,
        output_dir=temp_working_dir / "output",
        image_name="kedokudo/sammy-docker",
        container_working_dir=Path("/sammy/work"),
        container_data_dir=Path("/sammy/data"),
    )
    config.validate()
    return config


class TestDockerSammyRunner:
    """Tests for DockerSammyRunner."""

    def test_initialization(self, docker_config, mock_docker_command):
        """Should initialize with valid config."""
        _ = mock_docker_command  # implicitly used via fixture
        runner = DockerSammyRunner(docker_config)
        assert runner.config == docker_config

    def test_prepare_environment(self, docker_config, mock_sammy_files, mock_subprocess_docker, mock_docker_command):
        """Should prepare environment successfully."""
        _ = mock_docker_command  # implicitly used via fixture
        _ = mock_subprocess_docker  # implicitly used via fixture
        runner = DockerSammyRunner(docker_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        assert docker_config.output_dir.exists()

    def test_prepare_environment_missing_docker(self, docker_config, mock_sammy_files, monkeypatch):
        """Should raise error when docker is not available."""

        def mock_which(cmd):
            _ = cmd  # Unused
            return None

        monkeypatch.setattr("shutil.which", mock_which)

        runner = DockerSammyRunner(docker_config)
        files = SammyFiles(**mock_sammy_files)

        with pytest.raises(EnvironmentPreparationError) as exc:
            runner.prepare_environment(files)
        assert "Docker not found" in str(exc.value)

    def test_execute_sammy_success(self, docker_config, mock_sammy_files, mock_subprocess_docker, mock_docker_command):
        """Should execute SAMMY successfully in container."""
        _ = mock_docker_command  # implicitly used via fixture
        _ = mock_subprocess_docker  # implicitly used via fixture
        runner = DockerSammyRunner(docker_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        assert result.success
        assert "Normal finish to SAMMY" in result.console_output
        assert result.error_message is None

    def test_execute_sammy_failure(
        self, docker_config, mock_sammy_files, mock_subprocess_docker_fail, mock_docker_command
    ):
        """Should handle SAMMY execution failure in container."""
        _ = mock_docker_command  # implicitly used via fixture
        _ = mock_subprocess_docker_fail  # implicitly used via fixture
        runner = DockerSammyRunner(docker_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        assert not result.success
        assert "Docker execution failed" in result.error_message

    def test_collect_outputs(
        self, docker_config, mock_sammy_files, mock_subprocess_docker, mock_docker_command, mock_sammy_results
    ):
        """Should collect output files from container."""
        _ = mock_docker_command  # implicitly used via fixture
        _ = mock_subprocess_docker  # implicitly used via fixture
        _ = mock_sammy_results  # implicitly used via fixture
        runner = DockerSammyRunner(docker_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)
        runner.collect_outputs(result)

        assert (docker_config.output_dir / "SAMMY.LPT").exists()
        assert (docker_config.output_dir / "SAMMY.PAR").exists()

    def test_cleanup(self, docker_config, mock_sammy_files, mock_subprocess_docker, mock_docker_command):
        """Should perform cleanup successfully."""
        _ = mock_docker_command  # implicitly used via fixture
        _ = mock_subprocess_docker  # implicitly used via fixture
        runner = DockerSammyRunner(docker_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)
        runner.collect_outputs(result)
        runner.cleanup()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
