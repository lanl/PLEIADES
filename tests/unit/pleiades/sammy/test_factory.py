import shutil
import subprocess
import sys
from unittest import mock

import pytest

from pleiades.sammy.backends.docker import DockerSammyRunner
from pleiades.sammy.backends.local import LocalSammyRunner
from pleiades.sammy.backends.nova_ornl import NovaSammyRunner
from pleiades.sammy.factory import (
    BackendNotAvailableError,
    BackendType,
    ConfigurationError,
    SammyFactory,
)
from pleiades.sammy.interface import SammyRunner
from pleiades.utils.logger import loguru_logger


# Create a fixture to capture loguru logs for test assertions
@pytest.fixture
def loguru_caplog():
    """Capture loguru logs for testing."""

    # Prepare a place to store logs
    class LogCapture:
        def __init__(self):
            self.logs = []
            self.min_level = "INFO"

        @property
        def text(self):
            return "\n".join(self.logs)

        def set_level(self, level):
            self.min_level = level

    log_capture = LogCapture()

    # Remove default handlers
    loguru_logger.remove()

    # Add a specialized handler to capture logs
    def sink(message):
        log_capture.logs.append(message)

    # Add handler with captured sink
    handler_id = loguru_logger.add(sink, level=log_capture.min_level, format="{message}")

    # Also add stderr handler for visibility
    stderr_id = loguru_logger.add(sys.stderr, level="DEBUG")

    yield log_capture

    # Clean up after the test
    loguru_logger.remove(handler_id)
    loguru_logger.remove(stderr_id)
    loguru_logger.add(sys.stderr)


# Mock environment variables for NOVA backend checks
@pytest.fixture
def mock_nova_env_vars(monkeypatch):
    """Mock shutil.which to simulate docker being available."""
    monkeypatch.setenv("NOVA_URL", "https://mock_nova_url")
    monkeypatch.setenv("NOVA_API_KEY", "mock_api_key")


# Mock shutil.which for backend availability checks
@pytest.fixture
def mock_which(monkeypatch):
    """Mock shutil.which to simulate command availability."""

    def _mock_which(cmd):
        if cmd == "sammy":
            return "/usr/bin/sammy"
        if cmd == "docker":
            return "/usr/bin/docker"
        return None

    monkeypatch.setattr(shutil, "which", _mock_which)


@pytest.fixture
def mock_which_unavailable(monkeypatch):
    """
    Mock shutil.which to simulate no commands being available
    except for docker.
    """

    def _mock_which(cmd):
        if cmd == "docker":
            return "/usr/bin/docker"  # Return a valid path for docker
        return None

    monkeypatch.setattr(shutil, "which", _mock_which)


# Mock subprocess.run for Docker backend checks
@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run to simulate successful docker info."""

    def _mock_run(*args, **kwargs):
        _ = kwargs  # Unused
        # Check if the command is docker info
        if args[0] == ["docker", "info"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=b"Mock docker info")
        return subprocess.CompletedProcess(args=args, returncode=1)

    monkeypatch.setattr(subprocess, "run", _mock_run)


@pytest.fixture
def mock_subprocess_run_docker_fail(monkeypatch):
    """Mock subprocess.run to simulate docker info failure."""
    monkeypatch.setattr(
        subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args=args, returncode=1, **kwargs)
    )


# Mock SammyRunner creation for runner tests
@pytest.fixture
def mock_sammy_runner(monkeypatch):
    """Mock SammyRunner to track instantiation."""
    mock_runner_class = mock.MagicMock(spec=SammyRunner)
    monkeypatch.setattr("pleiades.sammy.factory.SammyRunner", mock_runner_class)
    return mock_runner_class


class TestSammyFactory:
    """Tests for SammyFactory."""

    def test_list_available_backends_all_available(self, mock_which, mock_subprocess_run, mock_nova_env_vars):
        """All backends should be available."""
        _ = mock_which, mock_subprocess_run, mock_nova_env_vars  # implicitly used by the fixture
        available = SammyFactory.list_available_backends()
        assert available == {
            BackendType.LOCAL: True,
            BackendType.DOCKER: True,
            BackendType.NOVA: True,
        }

    def test_list_available_backends_none_available(
        self, monkeypatch, mock_which_unavailable, mock_subprocess_run_docker_fail
    ):
        """No backends should be available."""
        _ = mock_which_unavailable, mock_subprocess_run_docker_fail  # implicitly used by the fixture
        # remove NOVA env vars to simulate unavailability
        monkeypatch.delenv("NOVA_URL", raising=False)
        monkeypatch.delenv("NOVA_API", raising=False)
        # check availability
        available = SammyFactory.list_available_backends()
        assert available == {
            BackendType.LOCAL: False,
            BackendType.DOCKER: False,
            BackendType.NOVA: False,
        }

    def test_create_runner_local(self, mock_sammy_runner, tmp_path, mock_which):
        """Should create LocalSammyRunner."""
        _ = mock_sammy_runner, mock_which  # implicitly used by the fixture
        runner = SammyFactory.create_runner("local", tmp_path)
        assert isinstance(runner, LocalSammyRunner)  # Check if it's the mocked runner

    @pytest.mark.skip(reason="This test will be fixed later")
    def test_create_runner_docker(self, mock_sammy_runner, tmp_path):
        """Should create DockerSammyRunner."""
        _ = mock_sammy_runner  # implicitly used by the fixture
        runner = SammyFactory.create_runner("docker", tmp_path)
        assert isinstance(runner, DockerSammyRunner)

    def test_create_runner_nova(self, mock_sammy_runner, tmp_path):
        """Should create NovaSammyRunner."""
        _ = mock_sammy_runner  # implicitly used by the fixture
        runner = SammyFactory.create_runner("nova", tmp_path)
        assert isinstance(runner, NovaSammyRunner)

    def test_create_runner_invalid_backend(self, tmp_path):
        """Should raise error for invalid backend."""
        with pytest.raises(ConfigurationError) as exc:
            SammyFactory.create_runner("invalid", tmp_path)
        assert "Invalid backend type" in str(exc.value)

    def test_create_runner_local_unavailable(self, mock_which_unavailable, tmp_path):
        """Should raise error for unavailable local backend."""
        _ = mock_which_unavailable  # implicitly used by the fixture
        with pytest.raises(BackendNotAvailableError) as exc:
            SammyFactory.create_runner("local", tmp_path)
        assert "Backend local is not available" in str(exc.value)

    def test_create_runner_docker_unavailable(self, mock_which_unavailable, mock_subprocess_run_docker_fail, tmp_path):
        """Should raise error for unavailable docker backend."""
        _ = mock_which_unavailable, mock_subprocess_run_docker_fail  # implicitly used by the fixture
        with pytest.raises(BackendNotAvailableError) as exc:
            SammyFactory.create_runner("docker", tmp_path)
        assert "Backend docker is not available" in str(exc.value)

    def test_from_config_valid(self, tmp_path, mock_sammy_runner, mock_which):
        """Should create runner from valid config file."""
        _ = mock_sammy_runner, mock_which  # implicitly used by the fixture
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            f"""
            backend: local
            working_dir: {tmp_path}
            """
        )
        runner = SammyFactory.from_config(config_file)
        assert isinstance(runner, LocalSammyRunner)

    def test_from_config_invalid_yaml(self, tmp_path):
        """Should raise error for invalid YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml:")
        with pytest.raises(ConfigurationError) as exc:
            SammyFactory.from_config(config_file)
        assert "Invalid YAML format" in str(exc.value)

    def test_from_config_missing_fields(self, tmp_path):
        """Should raise error for missing fields."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("backend: local")
        with pytest.raises(ConfigurationError) as exc:
            SammyFactory.from_config(config_file)
        assert "Missing required fields" in str(exc.value)

    def test_from_config_env_vars(self, tmp_path, mock_sammy_runner, monkeypatch, mock_which):
        """Should expand environment variables."""
        _ = mock_sammy_runner, mock_which  # implicitly used by the fixture
        monkeypatch.setenv("MY_VAR", f"{tmp_path}")
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
            backend: local
            working_dir: ${MY_VAR}
            """
        )
        runner = SammyFactory.from_config(config_file)
        assert isinstance(runner, LocalSammyRunner)

    def test_from_config_missing_env_var(self, tmp_path):
        """Should raise error for missing environment variable."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
            backend: local
            working_dir: ${MISSING_VAR}
            """
        )
        with pytest.raises(ConfigurationError) as exc:
            SammyFactory.from_config(config_file)
        assert "Environment variable not found" in str(exc.value)

    def test_auto_select_local(self, mock_which, mock_subprocess_run, mock_sammy_runner, tmp_path, loguru_caplog):
        """Should auto-select local backend."""
        _ = mock_which, mock_subprocess_run, mock_sammy_runner  # implicitly used by the fixture
        loguru_caplog.set_level("INFO")
        runner = SammyFactory.auto_select(tmp_path)
        assert isinstance(runner, LocalSammyRunner)
        assert "Attempting to use local backend" in loguru_caplog.text

    def test_auto_select_docker(
        self, monkeypatch, mock_which_unavailable, mock_subprocess_run, mock_sammy_runner, tmp_path, loguru_caplog
    ):
        """Should auto-select docker backend if local unavailable."""
        _ = mock_which_unavailable, mock_subprocess_run, mock_sammy_runner  # implicitly used by the fixture
        # remove NOVA env vars to simulate unavailability
        monkeypatch.delenv("NOVA_URL", raising=False)
        monkeypatch.delenv("NOVA_API", raising=False)
        # check availability
        loguru_caplog.set_level("INFO")
        runner = SammyFactory.auto_select(tmp_path)
        assert isinstance(runner, DockerSammyRunner)
        assert "Attempting to use docker backend" in loguru_caplog.text

    def test_auto_select_preferred(self, mock_which, mock_subprocess_run, mock_sammy_runner, tmp_path, loguru_caplog):
        """Should respect preferred backend."""
        _ = mock_which, mock_subprocess_run, mock_sammy_runner  # implicitly used by the fixture
        loguru_caplog.set_level("INFO")
        runner = SammyFactory.auto_select(tmp_path, preferred_backend="docker")
        assert isinstance(runner, DockerSammyRunner)
        assert "Using preferred backend: docker" in loguru_caplog.text

    def test_auto_select_none_available(
        self, monkeypatch, mock_which_unavailable, mock_subprocess_run_docker_fail, tmp_path, loguru_caplog
    ):
        """Should raise error if no backends available."""
        _ = mock_which_unavailable, mock_subprocess_run_docker_fail  # implicitly used by the fixture
        # remove NOVA env vars to simulate unavailability
        monkeypatch.delenv("NOVA_URL", raising=False)
        monkeypatch.delenv("NOVA_API", raising=False)
        # check availability
        loguru_caplog.set_level("INFO")
        with pytest.raises(BackendNotAvailableError) as exc:
            SammyFactory.auto_select(tmp_path)
        assert "No suitable backend available." in str(exc.value)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
