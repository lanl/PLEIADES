#!/usr/bin/env python
"""Unit tests for SAMMY configuration classes."""

from pathlib import Path

import pytest

from pleiades.sammy.config.sammy_options import ConfigurationError, DockerSammyConfig, LocalSammyConfig, NovaSammyConfig


class TestLocalSammyConfig:
    """Tests for LocalSammyConfig."""

    def test_create_with_valid_paths(self, temp_working_dir):
        """Should create config with valid paths."""
        config = LocalSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            sammy_executable=Path("/usr/local/bin/sammy"),
            shell_path=Path("/bin/bash"),
        )
        assert config.working_dir == temp_working_dir
        assert config.shell_path == Path("/bin/bash")

    def test_create_with_defaults(self, temp_working_dir):
        """Should create config with default values."""
        config = LocalSammyConfig(
            working_dir=temp_working_dir, output_dir=temp_working_dir / "output", sammy_executable=Path("sammy")
        )
        assert config.shell_path == Path("/bin/bash")

    def test_validate_sammy_in_path(self, temp_working_dir, monkeypatch):
        """Should validate SAMMY executable in PATH."""

        def mock_which(path):
            return "/usr/local/bin/sammy" if path == "sammy" else None

        monkeypatch.setattr("shutil.which", mock_which)

        config = LocalSammyConfig(
            working_dir=temp_working_dir, output_dir=temp_working_dir / "output", sammy_executable=Path("sammy")
        )
        assert config.validate()

    def test_validate_sammy_not_in_path(self, temp_working_dir, monkeypatch):
        """Should raise error if SAMMY not in PATH."""
        monkeypatch.setattr("shutil.which", lambda _: None)

        config = LocalSammyConfig(
            working_dir=temp_working_dir, output_dir=temp_working_dir / "output", sammy_executable=Path("sammy")
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "not found" in str(exc.value)

    def test_invalid_shell_path(self, temp_working_dir):
        """Should raise error for invalid shell path."""
        config = LocalSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            sammy_executable=Path("ls"),  # use a unix command as sammy executable
            shell_path=Path("/bin/invalid_shell"),
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "Shell not found" in str(exc.value)


class TestDockerSammyConfig:
    """Tests for DockerSammyConfig."""

    def test_create_with_valid_config(self, temp_working_dir):
        """Should create config with valid values."""
        config = DockerSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            image_name="kedokudo/sammy-docker",
            container_working_dir=Path("/sammy/work"),
            container_data_dir=Path("/sammy/data"),
        )
        assert config.image_name == "kedokudo/sammy-docker"
        assert config.container_working_dir == Path("/sammy/work")
        assert config.container_data_dir == Path("/sammy/data")
        # call validate
        assert config.validate()

    def test_validate_empty_image_name(self, temp_working_dir):
        """Should raise error for empty image name."""
        config = DockerSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            image_name="",
            container_working_dir=Path("/sammy/work"),
            container_data_dir=Path("/sammy/data"),
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "image name cannot be empty" in str(exc.value)

    def test_validate_relative_container_paths(self, temp_working_dir):
        """Should raise error for relative container paths."""
        config = DockerSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            image_name="kedokudo/sammy-docker",
            container_working_dir=Path("relative/path"),
            container_data_dir=Path("/sammy/data"),
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "must be absolute" in str(exc.value)

    def test_validate_relative_data_dir(self, temp_working_dir):
        """Should raise error for relative data dir."""
        config = DockerSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            image_name="kedokudo/sammy-docker",
            container_working_dir=Path("/sammy/work"),
            container_data_dir=Path("relative/path"),
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "must be absolute" in str(exc.value)

    def test_validate_same_container_dirs(self, temp_working_dir):
        """Should raise error if working and data dirs are same."""
        same_path = Path("/sammy/work")
        config = DockerSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            image_name="kedokudo/sammy-docker",
            container_working_dir=same_path,
            container_data_dir=same_path,
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "must be different" in str(exc.value)


class TestNovaSammyConfig:
    """Tests for NovaSammyConfig."""

    def test_create_with_valid_config(self, temp_working_dir):
        """Should create config with valid values."""
        config = NovaSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            url="https://nova.ornl.gov",
            api_key="valid_api_key",
            tool_id="neutrons_imaging_sammy",
        )
        assert config.url == "https://nova.ornl.gov"
        assert config.api_key == "valid_api_key"
        assert config.tool_id == "neutrons_imaging_sammy"
        assert config.timeout == 3600  # default value
        # call validate
        assert config.validate()

    def test_validate_invalid_url(self, temp_working_dir):
        """Should raise error for invalid URL format."""
        config = NovaSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            url="not_a_url",
            api_key="valid_api_key",
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "Invalid URL format" in str(exc.value)

    def test_empty_url(self, temp_working_dir):
        """Should raise error for empty URL."""
        config = NovaSammyConfig(
            working_dir=temp_working_dir, output_dir=temp_working_dir / "output", url="", api_key="valid_api_key"
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "NOVA service URL cannot be empty" in str(exc.value)

    def test_validate_missing_api_key(self, temp_working_dir):
        """Should raise error for empty API key."""
        config = NovaSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            url="https://nova.ornl.gov",
            api_key="",
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "API key cannot be empty" in str(exc.value)

    def test_validate_invalid_timeout(self, temp_working_dir):
        """Should raise error for invalid timeout value."""
        config = NovaSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            url="https://nova.ornl.gov",
            api_key="valid_api_key",
            timeout=-1,
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "Invalid timeout value" in str(exc.value)

    def test_create_with_custom_timeout(self, temp_working_dir):
        """Should accept custom timeout value."""
        config = NovaSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            url="https://nova.ornl.gov",
            api_key="valid_api_key",
            timeout=7200,
        )
        assert config.timeout == 7200

    def test_empty_tool_id(self, temp_working_dir):
        """Should raise error for empty tool ID."""
        config = NovaSammyConfig(
            working_dir=temp_working_dir,
            output_dir=temp_working_dir / "output",
            url="https://nova.ornl.gov",
            api_key="valid_api_key",
            tool_id="",
        )
        with pytest.raises(ConfigurationError) as exc:
            config.validate()
        assert "Tool ID cannot be empty" in str(exc.value)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
