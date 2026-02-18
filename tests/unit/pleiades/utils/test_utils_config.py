#!/usr/bin/env python
"""Unit tests for global configuration management."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
from pleiades.nuclear.models import DataRetrievalMethod, EndfLibrary, IsotopeParameters
from pleiades.utils.config import (
    FitRoutineConfig,
    IsotopeConfig,
    PleiadesConfig,
    get_config,
    reset_config,
    set_config,
)
from pleiades.utils.helper import VaryFlag


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
        assert config.nuclear is not None
        assert config.nuclear.data_cache_dir == expected_path
        assert config.nuclear.sources == config.nuclear_data_sources

    def test_custom_initialization(self):
        """Test custom initialization of PleiadesConfig."""
        custom_path = Path("/custom/path")
        custom_sources = {"TEST": "https://test.com"}

        config = PleiadesConfig(nuclear_data_cache_dir=custom_path, nuclear_data_sources=custom_sources)

        assert config.nuclear_data_cache_dir == custom_path
        assert config.nuclear_data_sources == custom_sources
        assert config.nuclear is not None
        assert config.nuclear.data_cache_dir == custom_path
        assert config.nuclear.sources == custom_sources

    def test_post_init_conversion(self):
        """Test conversion of string paths to Path objects."""
        config = PleiadesConfig(nuclear_data_cache_dir="/test/string/path")

        assert isinstance(config.nuclear_data_cache_dir, Path)
        assert config.nuclear_data_cache_dir == Path("/test/string/path")
        assert config.nuclear is not None
        assert config.nuclear.data_cache_dir == Path("/test/string/path")

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

            config = PleiadesConfig(
                nuclear_data_cache_dir=temp_path,
                nuclear_data_sources=custom_sources,
                fit_routines={"example_fit": {"dataset_id": "example_dataset"}},
            )

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
        assert loaded_config.nuclear is not None
        assert loaded_config.nuclear.data_cache_dir == temp_path
        assert loaded_config.nuclear.sources == custom_sources
        assert "example_fit" in loaded_config.fit_routines
        assert loaded_config.fit_routines["example_fit"].dataset_id == "example_dataset"

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

    def test_workspace_path_expansion_from_workspace_tokens(self, tmp_path):
        """Workspace fields should expand ${workspace.*} tokens consistently."""
        config = PleiadesConfig(
            workspace={
                "root": tmp_path,
                "endf_dir": "${workspace.root}/endf_dir",
                "fitting_dir": "${workspace.root}/fitting_dir",
                "results_dir": "${workspace.root}/results_dir",
                "data_dir": "${workspace.root}/data_dir",
                "image_dir": "${workspace.root}/image_dir",
            },
            fit_routines={"fit_1": {"dataset_id": "dataset_1"}},
        )

        assert config.workspace is not None
        assert config.workspace.root == tmp_path
        assert config.workspace.endf_dir == tmp_path / "endf_dir"
        assert config.workspace.fitting_dir == tmp_path / "fitting_dir"
        assert config.workspace.results_dir == tmp_path / "results_dir"
        assert config.workspace.data_dir == tmp_path / "data_dir"
        assert config.workspace.image_dir == tmp_path / "image_dir"

    def test_workspace_unresolved_token_results_in_none(self, tmp_path):
        """Unresolved workspace tokens should produce None after expansion."""
        config = PleiadesConfig(
            workspace={
                "root": tmp_path,
                "fitting_dir": "${workspace.missing_dir}/fits",
            },
            fit_routines={"fit_1": {"dataset_id": "dataset_1"}},
        )

        assert config.workspace is not None
        assert config.workspace.fitting_dir is None

    def test_fit_routines_are_normalized_to_typed_models(self):
        """fit_routines entries provided as dicts should be normalized to FitRoutineConfig."""
        pre_typed = FitRoutineConfig(dataset_id="dataset_2")
        config = PleiadesConfig(
            fit_routines={
                "fit_1": {"dataset_id": "dataset_1", "mode": "sammy"},
                "fit_2": pre_typed,
            }
        )

        assert isinstance(config.fit_routines["fit_1"], FitRoutineConfig)
        assert isinstance(config.fit_routines["fit_2"], FitRoutineConfig)
        assert config.fit_routines["fit_1"].dataset_id == "dataset_1"
        assert config.fit_routines["fit_2"].dataset_id == "dataset_2"

    def test_from_dict_requires_fit_routines(self):
        """Loading from user config should fail when fit_routines are missing."""
        with pytest.raises(ValidationError, match="fit_routines must be defined"):
            PleiadesConfig.from_dict({"workspace": {"root": "/tmp/pleiades"}})

    def test_isotope_config_normalization_and_defaults(self):
        """Isotope dicts should normalize to IsotopeConfig with default library applied."""
        config = PleiadesConfig(
            nuclear={
                "default_library": EndfLibrary.JEFF_3_3,
                "isotopes": [
                    {
                        "isotope": "Ta-181",
                        "abundance": 0.6,
                        "uncertainty": 0.01,
                        "vary_abundance": VaryFlag.YES,
                    }
                ],
            },
            fit_routines={"fit_1": {"dataset_id": "dataset_1"}},
        )

        assert len(config.nuclear.isotopes) == 1
        isotope = config.nuclear.isotopes[0]
        assert isinstance(isotope, IsotopeConfig)
        assert isotope.endf_library == EndfLibrary.JEFF_3_3
        assert isotope.vary_abundance == VaryFlag.YES

    def test_isotope_config_validation_rejects_invalid_library(self):
        """Invalid enum values in isotope config should raise validation errors."""
        with pytest.raises(ValidationError):
            PleiadesConfig(
                nuclear={"isotopes": [{"isotope": "Ta-181", "endf_library": "NOT_A_LIBRARY"}]},
                fit_routines={"fit_1": {"dataset_id": "dataset_1"}},
            )

    def test_build_nuclear_params_uses_configured_isotopes(self, monkeypatch):
        """build_nuclear_params should map config isotopes into nuclearParameters."""

        class FakeIsotopeManager:
            def get_isotope_parameters_from_isotope_string(self, isotope: str):
                if isotope != "Ta-181":
                    return None
                return IsotopeParameters(
                    isotope_information=IsotopeInfo(
                        name="Ta-181",
                        element="Ta",
                        mass_number=181,
                        atomic_number=73,
                        mass_data=IsotopeMassData(atomic_mass=180.9479958),
                        spin=3.5,
                    )
                )

        monkeypatch.setattr("pleiades.nuclear.isotopes.manager.IsotopeManager", FakeIsotopeManager)

        config = PleiadesConfig(
            nuclear={
                "default_library": EndfLibrary.JEFF_3_3,
                "isotopes": [
                    {
                        "isotope": "Ta-181",
                        "abundance": 0.8,
                        "uncertainty": 0.05,
                        "vary_abundance": VaryFlag.NO,
                    }
                ],
            },
            fit_routines={"fit_1": {"dataset_id": "dataset_1"}},
        )

        nuclear_params = config.build_nuclear_params()
        assert len(nuclear_params.isotopes) == 1
        isotope = nuclear_params.isotopes[0]
        assert isotope.isotope_information.name == "Ta-181"
        assert isotope.abundance == pytest.approx(0.8)
        assert isotope.uncertainty == pytest.approx(0.05)
        assert isotope.vary_abundance == VaryFlag.NO
        assert isotope.endf_library == EndfLibrary.JEFF_3_3

    def test_build_nuclear_params_raises_when_isotope_not_found(self, monkeypatch):
        """Unknown isotopes should raise a clear error."""

        class FakeIsotopeManager:
            def get_isotope_parameters_from_isotope_string(self, isotope: str):
                return None

        monkeypatch.setattr("pleiades.nuclear.isotopes.manager.IsotopeManager", FakeIsotopeManager)

        config = PleiadesConfig(
            nuclear={"isotopes": [{"isotope": "Unknown-999"}]},
            fit_routines={"fit_1": {"dataset_id": "dataset_1"}},
        )

        with pytest.raises(ValueError, match="Isotope not found"):
            config.build_nuclear_params()

    def test_ensure_endf_cache_downloads_to_workspace_endf_dir(self, monkeypatch, tmp_path):
        """ensure_endf_cache should call downloader for each isotope and return output paths."""
        calls = []

        class FakeIsotopeManager:
            def get_isotope_info(self, isotope: str):
                return IsotopeInfo(name=isotope, element="Ta", mass_number=181, atomic_number=73)

        class FakeNuclearDataManager:
            def __init__(self):
                self.isotope_manager = FakeIsotopeManager()

            def download_endf_resonance_file(self, isotope, library, output_dir, method, use_cache):
                calls.append(
                    {
                        "isotope": isotope.name,
                        "library": library,
                        "output_dir": output_dir,
                        "method": method,
                        "use_cache": use_cache,
                    }
                )
                return Path(output_dir) / f"{isotope.name}.endf"

        monkeypatch.setattr("pleiades.utils.config.set_config", lambda cfg: None)
        monkeypatch.setattr("pleiades.nuclear.manager.NuclearDataManager", FakeNuclearDataManager)

        config = PleiadesConfig(
            workspace={"root": tmp_path, "endf_dir": "${workspace.root}/endf_dir"},
            nuclear={"isotopes": [{"isotope": "Ta-181"}]},
            fit_routines={"fit_1": {"dataset_id": "dataset_1"}},
        )

        outputs = config.ensure_endf_cache(method=DataRetrievalMethod.API, use_cache=False)

        expected_dir = tmp_path / "endf_dir"
        assert expected_dir.exists()
        assert outputs == [expected_dir / "Ta-181.endf"]
        assert calls == [
            {
                "isotope": "Ta-181",
                "library": EndfLibrary.ENDF_B_VIII_0,
                "output_dir": str(expected_dir),
                "method": DataRetrievalMethod.API,
                "use_cache": False,
            }
        ]

    def test_create_routine_dirs_creates_fit_and_fit_results_dirs(self, tmp_path):
        """create_routine_dirs should create timestamped routine dirs and fit_results_dir."""
        config = PleiadesConfig(
            workspace={
                "root": tmp_path,
                "fitting_dir": "${workspace.root}/fitting_dir",
                "results_dir": "${workspace.root}/results_dir",
            },
            fit_routines={
                "fit_1": {"dataset_id": "dataset_1"},
                "fit_2": {"dataset_id": "dataset_2"},
            },
        )

        timestamp = "20260101T000000Z"
        created = config.create_routine_dirs(timestamp=timestamp)

        assert len(created) == 2
        routine_ids = {entry["routine_id"] for entry in created}
        assert routine_ids == {f"fit_1_{timestamp}", f"fit_2_{timestamp}"}
        for entry in created:
            assert entry["fit_dir"].exists()
            assert entry["fit_dir"].is_dir()
            assert entry["fit_results_dir"].exists()
            assert entry["fit_results_dir"].is_dir()

        assert config.workspace is not None
        assert config.workspace.results_dir is not None
        assert config.workspace.results_dir.exists()

    def test_create_routine_dirs_requires_fitting_dir(self, tmp_path):
        """create_routine_dirs should fail when workspace.fitting_dir is not configured."""
        config = PleiadesConfig(
            workspace={"root": tmp_path},
            fit_routines={"fit_1": {"dataset_id": "dataset_1"}},
        )

        with pytest.raises(ValueError, match="workspace.fitting_dir is required"):
            config.create_routine_dirs()

    def test_create_routine_dirs_requires_fit_routines(self, tmp_path):
        """create_routine_dirs should fail when no fit routines are available."""
        config = PleiadesConfig(
            workspace={"root": tmp_path, "fitting_dir": "${workspace.root}/fitting_dir"},
        )

        with pytest.raises(ValueError, match="No fit_routines defined"):
            config.create_routine_dirs()


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
