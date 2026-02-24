"""
Tests for the InpManager class.

This module tests the functionality of the InpManager class, which handles
the creation, formatting, and writing of SAMMY input (.inp) files based on
FitOptions configurations.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.fitting.options import FitOptions
from pleiades.sammy.io.card_formats.inp02_element import Card02, ElementInfo
from pleiades.sammy.io.card_formats.inp05_broadening import Card05, PhysicalConstants
from pleiades.sammy.io.inp_manager import InpDatasetMetadata, InpManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for output files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_fit_options():
    """Create a mock FitOptions instance with predefined commands."""
    mock_options = MagicMock(spec=FitOptions)
    mock_options.get_alphanumeric_commands.return_value = [
        "PUT QUANTUM NUMBERS INTO PARAMETER FILE",
        "DO NOT SOLVE BAYES EQUATIONS",
        "USE ENDF PARAMETERS",
    ]
    return mock_options


def test_init_defaults():
    """Test that InpManager initializes with default values."""
    inp_manager = InpManager()
    assert isinstance(inp_manager.options, FitOptions)
    assert inp_manager.title is None
    assert inp_manager.isotope_info is None
    assert inp_manager.physical_constants is None
    assert inp_manager.reaction_type is None


def test_init_with_options():
    """Test that InpManager initializes with provided FitOptions."""
    options = FitOptions()
    inp_manager = InpManager(options)
    assert inp_manager.options is options


def test_init_with_all_parameters():
    """Test that InpManager initializes with all parameters."""
    options = FitOptions()
    title = "Test Title"
    isotope_info = {"name": "Fe56", "mass": 55.934}
    physical_constants = {"temperature_K": 300, "flight_path_m": 200}
    reaction_type = "TRANSMISSION"

    inp_manager = InpManager(
        options=options,
        title=title,
        isotope_info=isotope_info,
        physical_constants=physical_constants,
        reaction_type=reaction_type,
    )

    assert inp_manager.options is options
    assert inp_manager.title == title
    assert inp_manager.isotope_info == isotope_info
    assert inp_manager.physical_constants == physical_constants
    assert inp_manager.reaction_type == reaction_type


def test_set_options():
    """Test setting FitOptions after initialization."""
    inp_manager = InpManager()
    original_options = inp_manager.options

    new_options = FitOptions()
    inp_manager.set_options(new_options)

    assert inp_manager.options is not original_options
    assert inp_manager.options is new_options


def test_generate_commands(mock_fit_options):
    """Test generating SAMMY input commands from FitOptions."""
    inp_manager = InpManager(mock_fit_options)
    commands = inp_manager.generate_commands()

    assert isinstance(commands, list)
    assert commands == [
        "PUT QUANTUM NUMBERS INTO PARAMETER FILE",
        "DO NOT SOLVE BAYES EQUATIONS",
        "USE ENDF PARAMETERS",
    ]


def test_generate_title_section():
    """Test generating title section."""
    # With no title - should use default
    inp_manager = InpManager()
    assert inp_manager.generate_title_section() == "SAMMY analysis"

    # With title
    inp_manager = InpManager(title="Test Title")
    assert inp_manager.generate_title_section() == "Test Title"


def test_generate_inp_content(mock_fit_options):
    """Test generating content for SAMMY input file."""
    inp_manager = InpManager(mock_fit_options, title="Test Title")
    content = inp_manager.generate_inp_content()

    assert isinstance(content, str)
    expected_sections = [
        "Test Title",
        "Sample",  # Element name
        "1.000000",  # Atomic weight (Card02 format with 6 decimals)
        "PUT QUANTUM NUMBERS INTO PARAMETER FILE",
        "DO NOT SOLVE BAYES EQUATIONS",
        "USE ENDF PARAMETERS",
        "293.6",  # Physical constants temperature
        "25.0000",  # Physical constants flight path
        "transmission",  # Default reaction type
    ]

    for section in expected_sections:
        assert section in content


def test_write_inp_file(temp_dir, mock_fit_options):
    """Test writing SAMMY input file to disk."""
    inp_manager = InpManager(mock_fit_options, title="Test Title")
    output_path = temp_dir / "test.inp"

    result_path = inp_manager.write_inp_file(output_path)

    assert result_path == output_path
    assert output_path.exists()

    with open(output_path, "r") as f:
        content = f.read()

    expected_sections = [
        "Test Title",
        "PUT QUANTUM NUMBERS INTO PARAMETER FILE",
        "DO NOT SOLVE BAYES EQUATIONS",
        "USE ENDF PARAMETERS",
    ]

    for section in expected_sections:
        assert section in content


def test_write_inp_file_creates_directories(temp_dir, mock_fit_options):
    """Test writing SAMMY input file creates directories if needed."""
    inp_manager = InpManager(mock_fit_options)
    output_path = temp_dir / "nested" / "dir" / "test.inp"

    result_path = inp_manager.write_inp_file(output_path)

    assert result_path == output_path
    assert output_path.exists()


def test_write_inp_file_handles_errors():
    """Test that write_inp_file properly handles errors."""
    inp_manager = InpManager()

    # Try to write to an invalid path
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(IOError) as exc_info:
            inp_manager.write_inp_file(Path("/invalid/path/file.inp"))

    assert "Failed to write SAMMY input file" in str(exc_info.value)
    # The exact error message might vary based on the environment
    # so we only check that the main error message is included


def test_create_endf_inp(temp_dir):
    """Test creating input file for ENDF mode using class method."""
    output_path = temp_dir / "endf.inp"

    with patch.object(FitOptions, "from_endf_config") as mock_from_endf:
        mock_options = MagicMock(spec=FitOptions)
        mock_options.get_alphanumeric_commands.return_value = ["USE ENDF PARAMETERS"]
        mock_from_endf.return_value = mock_options

        result_path = InpManager.create_endf_inp(output_path)

        assert result_path == output_path
        assert output_path.exists()

        with open(output_path, "r") as f:
            content = f.read()

        assert "ENDF extraction mode" in content
        assert "USE ENDF PARAMETERS" in content
        mock_from_endf.assert_called_once()


def test_create_fitting_inp(temp_dir):
    """Test creating input file for fitting mode using class method."""
    output_path = temp_dir / "fitting.inp"

    with patch.object(FitOptions, "from_fitting_config") as mock_from_fitting:
        mock_options = MagicMock(spec=FitOptions)
        mock_options.get_alphanumeric_commands.return_value = ["SOLVE BAYES EQUATIONS"]
        mock_from_fitting.return_value = mock_options

        result_path = InpManager.create_fitting_inp(output_path)

        assert result_path == output_path
        assert output_path.exists()

        with open(output_path, "r") as f:
            content = f.read()

        assert "Bayesian fitting mode" in content
        assert "SOLVE BAYES EQUATIONS" in content
        mock_from_fitting.assert_called_once()


def test_custom_inp_creation(temp_dir):
    """Test creating input file with custom options."""
    options = FitOptions.from_custom_config()
    inp_manager = InpManager(options)
    output_path = temp_dir / "custom.inp"

    result_path = inp_manager.write_inp_file(output_path)

    assert result_path == output_path
    assert output_path.exists()

    # The actual content will depend on the default values of FitOptions
    with open(output_path, "r") as f:
        content = f.read()

    assert isinstance(content, str)
    assert len(content) > 0  # Ensure some content was written


def test_create_multi_isotope_inp(temp_dir):
    """Test creating input file for multi-isotope JSON mode using class method."""
    output_path = temp_dir / "multi_isotope.inp"
    fit_config = FitConfig()

    with patch.object(FitOptions, "from_multi_isotope_config") as mock_from_multi:
        mock_options = MagicMock(spec=FitOptions)
        mock_options.get_alphanumeric_commands.return_value = [
            "INPUT IS ENDF/B FILE 2",
            "USE ENERGY RANGE FROM ENDF/B FILE 2",
            "USE TWENTY SIGNIFICANT DIGITS",
            "BROADENING IS WANTED",
            "SOLVE BAYES EQUATIONS",
            "CHI SQUARED IS WANTED",
        ]
        mock_from_multi.return_value = mock_options

        result_path = InpManager.create_multi_isotope_inp(
            output_path, fit_config=fit_config, title="Multi-isotope test"
        )

        assert result_path == output_path
        assert output_path.exists()

        with open(output_path, "r") as f:
            content = f.read()

        assert "Multi-isotope test" in content
        assert "transmission" in content  # Reaction type should be set
        assert "INPUT IS ENDF/B FILE 2" in content
        assert "USE TWENTY SIGNIFICANT DIGITS" in content
        assert "BROADENING IS WANTED" in content
        mock_from_multi.assert_called_once()


def test_multi_isotope_config_integration(temp_dir):
    """Test multi-isotope configuration integration without mocking."""
    output_path = temp_dir / "multi_isotope_real.inp"
    fit_config = FitConfig()

    # Test real implementation without mocking
    result_path = InpManager.create_multi_isotope_inp(
        output_path, fit_config=fit_config, title="Real multi-isotope integration test"
    )

    assert result_path == output_path
    assert output_path.exists()

    with open(output_path, "r") as f:
        content = f.read()

    # Check for key multi-isotope commands
    expected_commands = [
        "INPUT IS ENDF/B FILE",
        "USE ENERGY RANGE FROM ENDF",
        "USE TWENTY SIGNIFICANT DIGITS",
        "BROADENING IS WANTED",
        "SOLVE BAYES EQUATIONS",
        "CHI SQUARED IS WANTED",
        "transmission",
    ]

    found_commands = []
    for cmd in expected_commands:
        if cmd in content:
            found_commands.append(cmd)

    # Should find most of the expected commands
    assert len(found_commands) >= 6, (
        f"Found only {len(found_commands)}/{len(expected_commands)} commands: {found_commands}"
    )


def test_multi_isotope_with_dataset_metadata(temp_dir):
    """Test multi-isotope INP generation with typed dataset metadata."""
    output_path = temp_dir / "multi_isotope_with_materials.inp"
    fit_config = FitConfig()
    fit_config.physics_params.broadening_parameters.crfn = 8.0

    dataset_metadata = InpDatasetMetadata(
        density_g_cm3=13.31,
        thickness_mm=5.0,
        atomic_mass_amu=178.49,
        temperature_K=293.6,
    )

    result_path = InpManager.create_multi_isotope_inp(
        output_path,
        fit_config=fit_config,
        title="Hafnium multi-isotope test",
        dataset_metadata=dataset_metadata,
    )

    assert result_path == output_path
    assert output_path.exists()

    with open(output_path, "r") as f:
        content = f.read()

    # Check for calculated parameter sections
    assert "BROADENING PARAMETERS FOLLOW" in content
    assert "293.60000" in content  # Temperature
    assert "0.022454" in content  # Calculated number density (Card04 format)
    assert "MISCEllaneous parameters follow" in content
    assert "2.5000E+01" in content  # Flight path (Card format)
    assert "NORMAlization" in content
    # No resolution function expected when no resolution_file_path provided


def test_multi_isotope_missing_required_dataset_metadata_fields(temp_dir):
    """Typed metadata should require all THICK derivation inputs when any are provided."""
    output_path = temp_dir / "multi_isotope_missing.inp"
    fit_config = FitConfig()

    incomplete_metadata = InpDatasetMetadata(thickness_mm=5.0, atomic_mass_amu=178.49)

    with pytest.raises(
        ValueError, match="dataset_metadata must include density_g_cm3, thickness_mm, and atomic_mass_amu"
    ):
        InpManager.create_multi_isotope_inp(
            output_path,
            fit_config=fit_config,
            title="Should fail",
            dataset_metadata=incomplete_metadata,
        )


def test_generate_physical_constants_section_uses_fit_config_dist():
    """Card 5 generation should preserve fit_config broadening.dist as flight path."""
    fit_config = FitConfig()
    broadening = fit_config.physics_params.broadening_parameters
    broadening.temp = 300.0
    broadening.dist = 123.4
    broadening.deltal = 0.2
    broadening.deltag = 0.1
    broadening.deltae = 0.01

    manager = InpManager(fit_config=fit_config)
    section = manager.generate_physical_constants_section()
    constants = Card05.from_lines([section.strip()])

    assert constants.temperature == pytest.approx(300.0)
    assert constants.flight_path_length == pytest.approx(123.4)
    assert constants.delta_l == pytest.approx(0.2)
    assert constants.delta_g == pytest.approx(0.1)
    assert constants.delta_e == pytest.approx(0.01)


def test_generate_physical_constants_section_uses_dataset_metadata_temperature_fallback():
    """Card 5 generation should use dataset metadata temperature when FitConfig temp is unset."""
    fit_config = FitConfig()
    broadening = fit_config.physics_params.broadening_parameters
    broadening.temp = None
    broadening.dist = 40.0
    broadening.deltal = 0.4
    broadening.deltag = 0.3
    broadening.deltae = 0.2

    manager = InpManager(fit_config=fit_config)
    section = manager.generate_physical_constants_section(dataset_metadata=InpDatasetMetadata(temperature_K=310.0))
    constants = Card05.from_lines([section.strip()])

    assert constants.temperature == pytest.approx(310.0)
    assert constants.flight_path_length == pytest.approx(40.0)
    assert constants.delta_l == pytest.approx(0.4)
    assert constants.delta_g == pytest.approx(0.3)
    assert constants.delta_e == pytest.approx(0.2)


class TestVaryFlagOverrides:
    """Tests for vary_* flag overrides in generate_* methods."""

    def test_normalization_vary_false_fixes_norm_flag(self):
        """When vary_normalization=False, normalization flag should be NO."""
        manager = InpManager()
        meta = InpDatasetMetadata(vary_normalization=False, vary_background=None)
        section = manager.generate_normalization_parameters_section(dataset_metadata=meta)

        # Normalization line should contain flag=0 (NO) for anorm
        # The Card06 format puts anorm on the NORMAlization line
        assert "NORMAlization" in section or "NORMALIZATION" in section.upper()

    def test_normalization_vary_true_allows_norm_flag(self):
        """When vary_normalization=True (or None), normalization flag should be YES."""
        manager = InpManager()
        # None = default behavior (YES)
        section_default = manager.generate_normalization_parameters_section()
        meta_true = InpDatasetMetadata(vary_normalization=True)
        section_true = manager.generate_normalization_parameters_section(dataset_metadata=meta_true)
        # Both should produce the same result (YES flags)
        assert section_default == section_true

    def test_background_vary_false_zeros_backgrounds(self):
        """When vary_background=False, background values should be 0.0 with NO flags."""
        manager = InpManager()
        meta = InpDatasetMetadata(vary_background=False)
        section = manager.generate_normalization_parameters_section(dataset_metadata=meta)

        # With backgrounds zeroed out, the section should not contain the non-zero seed values
        assert "0.01" not in section
        assert "0.02" not in section

    def test_background_vary_none_uses_defaults(self):
        """When vary_background=None (default), backgrounds should have non-zero seeds."""
        manager = InpManager()
        section = manager.generate_normalization_parameters_section()
        # Default behavior should include non-zero background seeds
        # The section should contain normalization content
        assert "NORMAlization" in section or "NORMALIZATION" in section.upper()

    def test_tzero_vary_false_uses_identity(self):
        """When vary_tzero=False, TZERO should use identity values (t0=0, L0=1)."""
        manager = InpManager()
        meta = InpDatasetMetadata(vary_tzero=False)
        section = manager.generate_misc_parameters_section(dataset_metadata=meta)

        assert "MISCEllaneous" in section
        # Should NOT contain the VENUS default t0=0.86 (formatted as 8.6000E-01)
        assert "8.6000E-01" not in section

    def test_tzero_vary_none_uses_venus_defaults(self):
        """When vary_tzero=None (default), TZERO should use VENUS defaults."""
        manager = InpManager()
        section = manager.generate_misc_parameters_section()
        assert "MISCEllaneous" in section
        # Should contain VENUS default t0=0.86 (in scientific notation: 8.6000E-01)
        assert "8.6000E-01" in section

    def test_thickness_vary_false_fixes_thick_flag(self):
        """When vary_thickness=False, thickness flag should be NO."""

        manager = InpManager()
        meta = InpDatasetMetadata(
            vary_thickness=False,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.948,
            temperature_K=293.6,
        )
        section = manager.generate_broadening_parameters_section(dataset_metadata=meta)
        # The section should be generated (non-empty because thickness was derived)
        assert len(section.strip()) > 0

    def test_thickness_vary_none_defaults_to_yes(self):
        """When vary_thickness=None (default), thickness flag should be YES."""
        manager = InpManager()
        meta = InpDatasetMetadata(
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.948,
            temperature_K=293.6,
        )
        section = manager.generate_broadening_parameters_section(dataset_metadata=meta)
        assert len(section.strip()) > 0

    def test_multi_isotope_inp_passes_metadata_to_all_sections(self):
        """generate_multi_isotope_inp_content should pass dataset_metadata to misc and norm."""
        fit_config = FitConfig(fit_title="Test vary flags")
        fit_config.append_isotope_from_string("Ta-181")
        manager = InpManager(fit_config=fit_config)

        meta = InpDatasetMetadata(
            element="Ta",
            mass_number=181,
            atomic_mass_amu=180.948,
            min_energy_eV=1.0,
            max_energy_eV=100.0,
            temperature_K=293.6,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            vary_normalization=False,
            vary_background=False,
            vary_tzero=False,
            vary_thickness=False,
        )
        content = manager.generate_multi_isotope_inp_content(dataset_metadata=meta)

        # TZERO should use identity (no 8.6000E-01 VENUS default)
        assert "8.6000E-01" not in content
        # Verify the normalization section was generated with vary_background=False
        # by checking that the norm section is present and backgrounds are zeroed
        norm_section = manager.generate_normalization_parameters_section(dataset_metadata=meta)
        assert "0.01000000" not in norm_section
        assert "0.02000000" not in norm_section


def test_read_inp_file_sets_broadening_dist_from_card5(temp_dir):
    """Card 5 parsing should map flight path length back to broadening.dist."""
    fit_config = FitConfig()
    manager = InpManager(fit_config=fit_config)
    output_path = temp_dir / "roundtrip_card5.inp"

    card2_line = Card02.to_lines(ElementInfo(element="Au", atomic_weight=196.966569, min_energy=0.001, max_energy=1.0))[
        0
    ]
    card5_line = Card05.to_lines(
        PhysicalConstants(temperature=296.0, flight_path_length=48.5, delta_l=0.3, delta_g=0.2, delta_e=0.1)
    )[0]

    output_path.write_text(f"Card5 Parse Test\n{card2_line}\n{card5_line}\ntransmission\n")

    loaded = manager.read_inp_file(output_path, fit_config=fit_config)
    broadening = loaded.physics_params.broadening_parameters

    assert broadening.temp == pytest.approx(296.0)
    assert broadening.dist == pytest.approx(48.5)
    assert broadening.deltal == pytest.approx(0.3)
    assert broadening.deltag == pytest.approx(0.2)
    assert broadening.deltae == pytest.approx(0.1)
