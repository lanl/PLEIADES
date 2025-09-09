"""
Tests for the JsonManager class.

This module tests the functionality of the JsonManager class, which handles
the creation, parsing, and validation of SAMMY JSON configuration files used
in multi-isotope fitting workflows. It also tests the Pydantic models for
JSON structure validation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from pleiades.nuclear.manager import NuclearDataManager
from pleiades.sammy.io.json_manager import IsotopeEntry, JsonManager, SammyJsonConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for output files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_json_data():
    """Create sample JSON data matching SAMMY JSON format."""
    return {
        "forceRMoore": "yes",
        "purgeSpinGroups": "yes",
        "fudge": "0.7",
        "hf174_test": [{"mat": "7225", "abundance": "0.0016", "adjust": "false", "uncertainty": "0.02"}],
        "hf176_test": [{"mat": "7231", "abundance": "0.0526", "adjust": "false", "uncertainty": "0.02"}],
    }


@pytest.fixture
def mock_nuclear_manager():
    """Create a mock NuclearDataManager instance."""
    mock_manager = MagicMock(spec=NuclearDataManager)
    return mock_manager


class TestIsotopeEntry:
    """Test the IsotopeEntry Pydantic model."""

    def test_valid_isotope_entry(self):
        """Test creating a valid IsotopeEntry."""
        entry = IsotopeEntry(mat="7225", abundance="0.0016", adjust="false", uncertainty="0.02")

        assert entry.mat == "7225"
        assert entry.abundance == "0.0016"
        assert entry.adjust == "false"
        assert entry.uncertainty == "0.02"

    def test_isotope_entry_defaults(self):
        """Test IsotopeEntry with default values."""
        entry = IsotopeEntry(mat="7225", abundance="0.0016")

        assert entry.mat == "7225"
        assert entry.abundance == "0.0016"
        assert entry.adjust == "false"  # default
        assert entry.uncertainty == "0.02"  # default

    def test_invalid_mat_number(self):
        """Test validation of invalid MAT number."""
        with pytest.raises(ValidationError, match="MAT number must be a valid integer string"):
            IsotopeEntry(mat="invalid", abundance="0.5")

    def test_invalid_abundance_format(self):
        """Test validation of invalid abundance format."""
        with pytest.raises(ValidationError, match="Abundance must be a valid float string"):
            IsotopeEntry(mat="7225", abundance="invalid")

    def test_abundance_out_of_range(self):
        """Test validation of abundance out of range."""
        with pytest.raises(ValidationError, match="Abundance must be between 0.0 and 1.0"):
            IsotopeEntry(mat="7225", abundance="1.5")

    def test_model_dump(self):
        """Test serialization of IsotopeEntry."""
        entry = IsotopeEntry(mat="7225", abundance="0.0016")
        data = entry.model_dump()

        expected = {"mat": "7225", "abundance": "0.0016", "adjust": "false", "uncertainty": "0.02"}
        assert data == expected


class TestSammyJsonConfig:
    """Test the SammyJsonConfig Pydantic model."""

    def test_default_config(self):
        """Test creating SammyJsonConfig with defaults."""
        config = SammyJsonConfig()

        assert config.forceRMoore == "yes"
        assert config.purgeSpinGroups == "yes"
        assert config.fudge == "0.7"

    def test_custom_global_settings(self):
        """Test creating SammyJsonConfig with custom global settings."""
        config = SammyJsonConfig(forceRMoore="no", purgeSpinGroups="no", fudge="0.8")

        assert config.forceRMoore == "no"
        assert config.purgeSpinGroups == "no"
        assert config.fudge == "0.8"

    def test_add_isotope_entry(self):
        """Test adding isotope entry to configuration."""
        config = SammyJsonConfig()
        entry = IsotopeEntry(mat="7225", abundance="0.0016")

        config.add_isotope_entry("hf174_test", entry)

        entries = config.get_isotope_entries()
        assert "hf174_test" in entries
        assert len(entries["hf174_test"]) == 1
        assert entries["hf174_test"][0].mat == "7225"

    def test_get_isotope_entries_empty(self):
        """Test getting isotope entries from empty configuration."""
        config = SammyJsonConfig()
        entries = config.get_isotope_entries()

        assert entries == {}

    def test_get_isotope_entries_multiple(self):
        """Test getting multiple isotope entries."""
        config = SammyJsonConfig()

        entry1 = IsotopeEntry(mat="7225", abundance="0.0016")
        entry2 = IsotopeEntry(mat="7231", abundance="0.0526")

        config.add_isotope_entry("hf174_test", entry1)
        config.add_isotope_entry("hf176_test", entry2)

        entries = config.get_isotope_entries()
        assert len(entries) == 2
        assert "hf174_test" in entries
        assert "hf176_test" in entries

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = SammyJsonConfig(fudge="0.8")
        entry = IsotopeEntry(mat="7225", abundance="0.0016")
        config.add_isotope_entry("hf174_test", entry)

        result = config.to_dict()

        expected = {
            "forceRMoore": "yes",
            "purgeSpinGroups": "yes",
            "fudge": "0.8",
            "hf174_test": [{"mat": "7225", "abundance": "0.0016", "adjust": "false", "uncertainty": "0.02"}],
        }
        assert result == expected


class TestJsonManager:
    """Test the JsonManager class."""

    def test_init_default(self):
        """Test JsonManager initialization with default nuclear manager."""
        with patch("pleiades.sammy.io.json_manager.NuclearDataManager") as mock_nuclear_class:
            mock_manager = MagicMock()
            mock_nuclear_class.return_value = mock_manager

            json_manager = JsonManager()

            mock_nuclear_class.assert_called_once()
            assert json_manager.nuclear_manager == mock_manager

    def test_init_with_nuclear_manager(self, mock_nuclear_manager):
        """Test JsonManager initialization with provided nuclear manager."""
        json_manager = JsonManager(nuclear_manager=mock_nuclear_manager)

        assert json_manager.nuclear_manager == mock_nuclear_manager

    def test_create_json_config_single_isotope(self, mock_nuclear_manager, temp_dir):
        """Test creating JSON config for single isotope with new API."""
        json_manager = JsonManager(nuclear_manager=mock_nuclear_manager)

        # Mock isotope manager and isotope info
        mock_isotope_manager = MagicMock()
        mock_isotope_info = MagicMock()
        mock_isotope_info.material_number = 7225

        mock_nuclear_manager.isotope_manager = mock_isotope_manager
        mock_isotope_manager.get_isotope_info.return_value = mock_isotope_info

        # Mock ENDF file download - need to create actual file for new API
        expected_endf_path = temp_dir / "072-Hf-174.B-VIII.0.par"
        expected_endf_path.write_text("mock endf content")
        mock_nuclear_manager.download_endf_resonance_file.return_value = str(expected_endf_path)

        # Test new API: working_dir instead of output_path
        result_path = json_manager.create_json_config(isotopes=["Hf-174"], abundances=[0.0016], working_dir=temp_dir)

        # Verify JSON file was created with default name
        expected_json_path = temp_dir / "config.json"
        assert result_path.exists()
        assert result_path == expected_json_path

        # Verify ENDF file exists in same directory
        assert expected_endf_path.exists()

        # Verify JSON content uses actual ENDF filename as key
        with open(result_path, "r") as f:
            json_data = json.load(f)

        # Check structure
        assert "forceRMoore" in json_data
        assert "072-Hf-174.B-VIII.0.par" in json_data  # Actual ENDF filename as key
        assert isinstance(json_data["072-Hf-174.B-VIII.0.par"], list)
        assert len(json_data["072-Hf-174.B-VIII.0.par"]) == 1

        # Check isotope entry
        entry = json_data["072-Hf-174.B-VIII.0.par"][0]
        assert entry["mat"] == "7225"
        assert entry["abundance"] == "0.0016"
        assert entry["adjust"] == "false"
        assert entry["uncertainty"] == "0.02"

    def test_create_json_config_validation_errors(self, mock_nuclear_manager, temp_dir):
        """Test validation errors in create_json_config with new API."""
        json_manager = JsonManager(nuclear_manager=mock_nuclear_manager)

        # Test mismatched lengths
        with pytest.raises(ValueError, match="must have same length"):
            json_manager.create_json_config(isotopes=["Hf-174", "Hf-176"], abundances=[0.5], working_dir=temp_dir)

        # Test empty lists
        with pytest.raises(ValueError, match="At least one isotope must be provided"):
            json_manager.create_json_config(isotopes=[], abundances=[], working_dir=temp_dir)

    def test_stage_endf_files_success(self, mock_nuclear_manager, temp_dir):
        """Test successful ENDF file staging."""
        json_manager = JsonManager(nuclear_manager=mock_nuclear_manager)

        # Mock isotope manager and isotope info
        mock_isotope_manager = MagicMock()
        mock_isotope_info = MagicMock()
        mock_isotope_info.material_number = 7225

        mock_nuclear_manager.isotope_manager = mock_isotope_manager
        mock_isotope_manager.get_isotope_info.return_value = mock_isotope_info

        # Mock ENDF file download
        test_endf_path = temp_dir / "072-Hf-174.B-VIII.0.par"
        test_endf_path.write_text("mock endf content")
        mock_nuclear_manager.download_endf_resonance_file.return_value = str(test_endf_path)

        # Test staging
        staged_files = json_manager.stage_endf_files(isotopes=["Hf-174"], working_dir=temp_dir)

        # Verify results
        assert "Hf-174" in staged_files
        assert staged_files["Hf-174"] == test_endf_path
        assert test_endf_path.exists()

        # Verify nuclear manager was called correctly
        mock_isotope_manager.get_isotope_info.assert_called_once_with("Hf-174")
        mock_nuclear_manager.download_endf_resonance_file.assert_called_once()

    def test_parse_json_config_file_not_found(self, mock_nuclear_manager):
        """Test parsing non-existent JSON file."""
        json_manager = JsonManager(nuclear_manager=mock_nuclear_manager)

        with pytest.raises(FileNotFoundError, match="JSON file not found"):
            json_manager.parse_json_config("nonexistent.json")

    def test_parse_json_config_invalid_json(self, mock_nuclear_manager, temp_dir):
        """Test parsing invalid JSON file."""
        json_manager = JsonManager(nuclear_manager=mock_nuclear_manager)

        # Create invalid JSON file
        invalid_json_path = temp_dir / "invalid.json"
        with open(invalid_json_path, "w") as f:
            f.write("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            json_manager.parse_json_config(invalid_json_path)

    def test_parse_json_config_valid(self, mock_nuclear_manager, temp_dir, sample_json_data):
        """Test parsing valid JSON file."""
        json_manager = JsonManager(nuclear_manager=mock_nuclear_manager)

        # Create valid JSON file
        json_path = temp_dir / "valid.json"
        with open(json_path, "w") as f:
            json.dump(sample_json_data, f)

        config = json_manager.parse_json_config(json_path)

        # Verify global settings
        assert config.forceRMoore == "yes"
        assert config.purgeSpinGroups == "yes"
        assert config.fudge == "0.7"

        # Verify isotope entries
        entries = config.get_isotope_entries()
        assert len(entries) == 2
        assert "hf174_test" in entries
        assert "hf176_test" in entries

        # Verify isotope entry content
        hf174_entry = entries["hf174_test"][0]
        assert hf174_entry.mat == "7225"
        assert hf174_entry.abundance == "0.0016"

    def test_parse_json_config_custom_globals(self, mock_nuclear_manager, temp_dir):
        """Test parsing JSON with custom global settings."""
        json_manager = JsonManager(nuclear_manager=mock_nuclear_manager)

        custom_json_data = {"forceRMoore": "no", "purgeSpinGroups": "no", "fudge": "0.8"}

        json_path = temp_dir / "custom.json"
        with open(json_path, "w") as f:
            json.dump(custom_json_data, f)

        config = json_manager.parse_json_config(json_path)

        assert config.forceRMoore == "no"
        assert config.purgeSpinGroups == "no"
        assert config.fudge == "0.8"

    def test_parse_json_config_roundtrip(self, mock_nuclear_manager, temp_dir, sample_json_data):
        """Test round-trip parsing and serialization."""
        json_manager = JsonManager(nuclear_manager=mock_nuclear_manager)

        # Write original JSON
        json_path = temp_dir / "roundtrip.json"
        with open(json_path, "w") as f:
            json.dump(sample_json_data, f)

        # Parse and re-serialize
        config = json_manager.parse_json_config(json_path)
        result_dict = config.to_dict()

        # Should match original data
        assert result_dict == sample_json_data


class TestJsonManagerIntegration:
    """Integration tests for JsonManager with real components."""

    @pytest.mark.integration
    def test_parse_real_sammy_json_example(self):
        """Test parsing the actual SAMMY JSON example file."""
        # This test requires the real sammy_json_example file
        reference_path = Path("/SNS/users/8cz/tmp/sammy_json_example/endfAdd_new_1.js")

        if not reference_path.exists():
            pytest.skip("SAMMY JSON example file not available")

        json_manager = JsonManager()

        try:
            config = json_manager.parse_json_config(reference_path)

            # Verify it parsed successfully
            assert config.forceRMoore == "yes"
            assert config.fudge == "0.7"

            # Should have hafnium isotope entries
            entries = config.get_isotope_entries()
            assert len(entries) > 0

            # Check for expected isotope names
            isotope_names = list(entries.keys())
            assert any("hf" in name.lower() for name in isotope_names)

        except Exception as e:
            pytest.fail(f"Failed to parse real SAMMY JSON example: {e}")
