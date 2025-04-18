#!/usr/bin/env python
"""Unit tests for global configuration management."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from pleiades.utils.config import PleiadesConfig, get_config, reset_config, set_config


class TestPleiadesConfig:
    """Test suite for PleiadesConfig class."""

    def test_default_initialization(self):
        """Test default initialization of PleiadesConfig."""
        config = PleiadesConfig()

        # Check default nuclear data cache dir
        expected_path = Path(os.path.expanduser("~/.pleiades/nuclear_data"))
        assert config.nuclear_data_cache_dir == expected_path

        # Check default nuclear data sources
        assert "DIRECT" in config.nuclear_data_sources
        assert "API" in config.nuclear_data_sources
        assert config.nuclear_data_sources["DIRECT"] == "https://www-nds.iaea.org/public/download-endf"
        assert config.nuclear_data_sources["API"] == "https://www-nds.iaea.org/exfor/servlet"

    def test_custom_initialization(self):
        """Test custom initialization of PleiadesConfig."""
        custom_path = Path("/custom/path")
        custom_sources = {"TEST": "https://test.com"}

        config = PleiadesConfig(nuclear_data_cache_dir=custom_path, nuclear_data_sources=custom_sources)

        assert config.nuclear_data_cache_dir == custom_path
        assert config.nuclear_data_sources == custom_sources

    def test_post_init_conversion(self):
        """Test __post_init__ conversion of string paths to Path objects."""
        config = PleiadesConfig(nuclear_data_cache_dir="/test/string/path")

        assert isinstance(config.nuclear_data_cache_dir, Path)
        assert config.nuclear_data_cache_dir == Path("/test/string/path")

    def test_ensure_directories(self, monkeypatch):
        """Test directory creation functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "nuclear_data"

            # Create config with temp path
            config = PleiadesConfig(nuclear_data_cache_dir=temp_path)

            # Verify directory doesn't exist yet
            assert not temp_path.exists()

            # Create directories
            config.ensure_directories()

            # Verify directory was created
            assert temp_path.exists()
            assert temp_path.is_dir()

    def test_to_dict(self):
        """Test conversion of config to dictionary."""
        custom_path = Path("/custom/path")
        custom_sources = {"TEST": "https://test.com"}

        config = PleiadesConfig(nuclear_data_cache_dir=custom_path, nuclear_data_sources=custom_sources)

        config_dict = config.to_dict()

        # Path should be converted to string
        assert config_dict["nuclear_data_cache_dir"] == str(custom_path)
        assert config_dict["nuclear_data_sources"] == custom_sources

    def test_save_and_load(self):
        """Test saving and loading config to/from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a config with custom values
            temp_path = Path(tmpdir) / "nuclear_data"
            custom_sources = {"TEST": "https://test.com"}

            config = PleiadesConfig(nuclear_data_cache_dir=temp_path, nuclear_data_sources=custom_sources)

            # Save to temp file
            save_path = Path(tmpdir) / "config.yaml"
            actual_save_path = config.save(save_path)

            # Verify save path
            assert actual_save_path == save_path
            assert save_path.exists()

            # Verify file content
            with open(save_path, "r") as f:
                saved_data = yaml.safe_load(f)
                assert saved_data["nuclear_data_cache_dir"] == str(temp_path)
                assert saved_data["nuclear_data_sources"] == custom_sources

            # Load config from saved file
            loaded_config = PleiadesConfig.load(save_path)

            # Verify loaded config matches original
            assert loaded_config.nuclear_data_cache_dir == temp_path
            assert loaded_config.nuclear_data_sources == custom_sources

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file returns default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent_path = Path(tmpdir) / "nonexistent.yaml"

            # Load should return default config
            config = PleiadesConfig.load(nonexistent_path)

            # Verify default values
            expected_path = Path(os.path.expanduser("~/.pleiades/nuclear_data"))
            assert config.nuclear_data_cache_dir == expected_path
            assert "DIRECT" in config.nuclear_data_sources
            assert "API" in config.nuclear_data_sources

    def test_load_empty_file(self):
        """Test loading from empty file returns default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_path = Path(tmpdir) / "empty.yaml"

            # Create empty file
            with open(empty_path, "w") as f:
                f.write("")

            # Load should return default config
            config = PleiadesConfig.load(empty_path)

            # Verify default values
            expected_path = Path(os.path.expanduser("~/.pleiades/nuclear_data"))
            assert config.nuclear_data_cache_dir == expected_path
            assert "DIRECT" in config.nuclear_data_sources
            assert "API" in config.nuclear_data_sources


class TestGlobalConfigFunctions:
    """Test suite for global configuration functions."""

    def test_get_config(self, monkeypatch):
        """Test get_config returns a valid config and initializes directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock home directory to use our temp dir
            monkeypatch.setattr(os.path, "expanduser", lambda path: path.replace("~", tmpdir))

            # Reset global state
            monkeypatch.setattr("pleiades.utils.config._config", None)

            # Get config
            config = get_config()

            # Verify it's a PleiadesConfig instance
            assert isinstance(config, PleiadesConfig)

            # Verify directories were created
            expected_path = Path(tmpdir) / ".pleiades" / "nuclear_data"
            assert expected_path.exists()
            assert expected_path.is_dir()

    def test_set_config(self, monkeypatch):
        """Test set_config updates the global config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a custom config with path in the temporary directory
            custom_path = Path(tmpdir) / "custom/path"
            custom_config = PleiadesConfig(nuclear_data_cache_dir=custom_path)

            monkeypatch.setattr("pleiades.utils.config._config", None)

            # Set custom config
            set_config(custom_config)

            # Get config and verify it matches our custom config
            config = get_config()
            assert config is custom_config
            assert config.nuclear_data_cache_dir == custom_path

            # Verify directory was created
            assert custom_path.exists()
            assert custom_path.is_dir()

    def test_reset_config(self, monkeypatch):
        """Test reset_config resets to default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock home directory to use our temp dir for the default path
            monkeypatch.setattr(os.path, "expanduser", lambda path: path.replace("~", tmpdir))

            # Create a custom config with a different path
            custom_path = Path(tmpdir) / "custom/path"
            custom_config = PleiadesConfig(nuclear_data_cache_dir=custom_path)

            monkeypatch.setattr("pleiades.utils.config._config", custom_config)

            # Reset config
            reset_config()

            # Get config and verify it's a default config
            config = get_config()
            assert config is not custom_config
            expected_path = Path(tmpdir) / ".pleiades" / "nuclear_data"
            assert config.nuclear_data_cache_dir == expected_path
            assert expected_path.exists()
            assert expected_path.is_dir()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
