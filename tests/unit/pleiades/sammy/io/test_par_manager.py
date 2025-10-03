import tempfile
from pathlib import Path

import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.par_manager import Cards, ParManager


@pytest.fixture
def par_file_block1():
    return [
        "PARTICLE PAIR DEFINITIONS",
        "Name=Inc Chan     Particle a=neutron       Particle b=Other",
        "     Za= 0        Zb= 0         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   0.0     Ma=   1.008664915780000     Mb=  57.935000000000",
        "Name=Inc Ch#1     Particle a=neutron       Particle b=Other",
        "     Za= 0        Zb= 0         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   0.0     Ma=   1.008664915780000     Mb=  18.000000000000",
        "",
        "SPIN GROUPS",
        "  1      1    0  0.5 1.0000000",
        "    1  Inc Chan    0  0.5",
        "  2      1    0 -0.5 1.0000000",
        "    1  Inc Chan    1  0.5",
        "  3      1    0 -1.5 1.0000000",
        "    1  Inc Chan    1  0.5",
        "  4      1    0  1.5 1.0000000",
        "    1  Inc Chan    2  0.5",
        "  5      1    0  2.5 1.0000000",
        "    1  Inc Chan    2  0.5",
        "  6      1    0  0.5 0.0001000",
        "    1  Inc Ch#1    0  0.5",
        "",
        "RESONANCES are listed next",
        "-3661600.00 158770.000 3698500.+3  0.0000               0 0 1 0   1",
        "-873730.000 1025.30000 101.510000  0.0000               0 0 1 0   1",
        "-365290.000 1000.00000 30.4060000  0.0000               0 0 0 0   1",
        "-63159.0000 1000.00000 46.8940000  0.0000               0 0 0 0   1",
        "-48801.0000 1000.00000 9.24960000  0.0000               0 0 0 0   1",
        "31739.99805 1000.00000 15.6670000  0.0000     0.0000    0 0 0 0 0 5",
        "55676.96094 1580.30000 653310.000  0.0000               0 0 0 0   1",
        "67732.84375 2500.00000 2658.90000  0.0000               0 0 0 0   3",
        "70800.00781 1000.00000 29.6170000  0.0000     0.0000    0 0 0 0 0 5",
        "86797.35938 2500.00000 726.180000  0.0000               0 0 0 0   3",
        "181617.5000 5600.00000 34894000.0  0.0000               0 0 0 0   1",
        "298700.0000 1000.00000 9886.00000  0.0000     0.0000    0 0 0 0 0 5",
        "301310.8125 3600.00000 2354.80000  0.0000               0 0 0 0   1",
        "354588.6875 1000.00000 14460.0000  0.0000     0.0000    0 0 0 0 0 5",
        "399675.9375 660.000000 813.610000  0.0000               0 0 0 0   3",
        "532659.8750 2500.00000 532810.000  0.0000               0 0 0 0   3",
        "565576.8750 2900.00000 10953000.0  0.0000               0 0 0 0   3",
        "587165.7500 8800.00000 199160.000  0.0000               0 0 0 0   2",
        "590290.1250 3600.00000 523660.000  0.0000               0 0 0 0   1",
        "602467.3125 3400.00000 50491.0000  0.0000     0.0000    0 0 0 0 0 4",
        "714043.4375 2500.00000 1216.50000  0.0000               0 0 0 0   3",
        "771711.9375 1000.00000 53139.0000  0.0000     0.0000    0 0 0 0 0 5",
        "812491.6250 9700.00000 30100000.0  0.0000               0 0 0 0   3",
        "845233.8750 2000.00000 397910.000  0.0000     0.0000    0 0 0 0 0 4",
        "872305.8125 1300.00000 32140.0000  0.0000     0.0000    0 0 0 0 0 5",
        "",
        "Channel radii in key-word format",
        "Radii=  6.303510,  6.303510    Flags=0, 0",
        "   Group=  1   Chan=  1,",
        "   Group=  4   Chan=  1,",
        "   Group=  5   Chan=  1,",
        "Radii=  4.233810,  4.233810    Flags=0, 0",
        "   Group=  2   Chan=  1,",
        "   Group=  3   Chan=  1,",
        "Radii=  3.570000,  3.570000    Flags=0, 0",
        "   Group=  6   Chan=  1,",
        "",
        "NUCLIDE MASSES AND ABUNDANCES FOLLOW",
        "57.9350000 1.0000000 5.00000-5 0 1 2 3 4 5",
        "18.0000000 .00010306 5.00000-5 1 6",
        "",
        "NORMAlization and constant background follow",
        ".958021531 .00718871 0.        0.        0.        0.        1 1 0 0 0 0",
        ".100000002 .00071887 0.        0.        0.        0.",
        "",
    ]


@pytest.fixture
def blank_block():
    return []


@pytest.fixture
def fit_config():
    return FitConfig()


def test_readin_par_file(fit_config, par_file_block1):
    """Test reading a complete parameter file with multiple card types."""
    # Create a temporary file with the test data
    with tempfile.NamedTemporaryFile(mode="w", suffix=".par", delete=False) as tmp_file:
        tmp_file.write("\n".join(par_file_block1))
        tmp_file_path = Path(tmp_file.name)

    try:
        # Test reading the parameter file
        par_manager = ParManager(fit_config=fit_config, par_file=tmp_file_path)

        # Verify that data was loaded correctly
        assert len(par_manager.fit_config.nuclear_params.isotopes) > 0
        # Check particle pairs are stored in isotopes
        first_isotope = par_manager.fit_config.nuclear_params.isotopes[0]
        assert hasattr(first_isotope, "particle_pairs")
        assert len(first_isotope.particle_pairs) > 0

        # Check that radius parameters were loaded
        first_isotope = par_manager.fit_config.nuclear_params.isotopes[0]
        assert hasattr(first_isotope, "radius_parameters")
        assert len(first_isotope.radius_parameters) > 0

    finally:
        # Clean up temporary file
        tmp_file_path.unlink()


def test_parmanager_initialization():
    """Test ParManager initialization with and without FitConfig."""
    # Test initialization without FitConfig
    par_manager1 = ParManager()
    assert isinstance(par_manager1.fit_config, FitConfig)
    assert par_manager1.par_file is None

    # Test initialization with FitConfig
    fit_config = FitConfig()
    par_manager2 = ParManager(fit_config=fit_config)
    assert par_manager2.fit_config is fit_config
    assert par_manager2.par_file is None


def test_detect_par_cards(fit_config, par_file_block1):
    """Test detection of parameter cards in file content."""
    par_manager = ParManager(fit_config=fit_config)
    detected_cards = par_manager.detect_par_cards(par_file_block1)

    # Should detect multiple card types
    assert len(detected_cards) > 0
    assert Cards.PAR_CARD_1 in detected_cards  # Always included by default
    assert Cards.PAR_CARD_7A in detected_cards  # Channel radii
    assert Cards.PAR_CARD_10 in detected_cards  # Isotopes
    assert Cards.PAR_CARD_6 in detected_cards  # Normalization
    assert Cards.INP_CARD_4 in detected_cards  # Particle pairs
    assert Cards.INP_CARD_10_2 in detected_cards  # Spin groups


def test_extract_particle_pairs(fit_config, par_file_block1):
    """Test extraction of particle pair definitions."""
    par_manager = ParManager(fit_config=fit_config)
    result = par_manager.extract_particle_pairs(par_file_block1)

    assert result is True
    # Particle pairs should be stored in isotopes, check if we have isotopes with particle pairs
    assert len(par_manager.fit_config.nuclear_params.isotopes) > 0
    first_isotope = par_manager.fit_config.nuclear_params.isotopes[0]
    assert hasattr(first_isotope, "particle_pairs")
    assert len(first_isotope.particle_pairs) > 0

    # Check first particle pair
    first_pair = first_isotope.particle_pairs[0]
    assert first_pair.name == "Inc Chan"


def test_extract_radii_parameters(fit_config, par_file_block1):
    """Test extraction of radius parameters."""
    par_manager = ParManager(fit_config=fit_config)
    result = par_manager.extract_radii_parameters(par_file_block1)

    assert result is True
    # Should create default isotope if none exist
    assert len(par_manager.fit_config.nuclear_params.isotopes) > 0

    first_isotope = par_manager.fit_config.nuclear_params.isotopes[0]
    assert hasattr(first_isotope, "radius_parameters")
    assert len(first_isotope.radius_parameters) > 0


def test_extract_isotopes_and_abundances(fit_config, par_file_block1):
    """Test extraction of isotope information."""
    par_manager = ParManager(fit_config=fit_config)
    result = par_manager.extract_isotopes_and_abundances(par_file_block1)

    assert result is True
    assert len(par_manager.fit_config.nuclear_params.isotopes) > 0


def test_extract_normalization_parameters(fit_config, par_file_block1):
    """Test extraction of normalization parameters."""
    par_manager = ParManager(fit_config=fit_config)
    result = par_manager.extract_normalization_parameters(par_file_block1)

    assert result is True


def test_extract_spin_groups(fit_config, par_file_block1):
    """Test extraction of spin group definitions."""
    par_manager = ParManager(fit_config=fit_config)
    result = par_manager.extract_spin_groups(par_file_block1)

    assert result is True


def test_extract_resonance_entries(fit_config, par_file_block1):
    """Test extraction of resonance entries."""
    par_manager = ParManager(fit_config=fit_config)
    result = par_manager.extract_resonance_entries(par_file_block1)

    assert result is True


def test_file_not_found():
    """Test handling of non-existent parameter file."""
    non_existent_path = Path("/non/existent/file.par")

    with pytest.raises(FileNotFoundError):
        ParManager(par_file=non_existent_path)


def test_generate_sections(fit_config, par_file_block1):
    """Test generation of parameter file sections."""
    # First load some data
    with tempfile.NamedTemporaryFile(mode="w", suffix=".par", delete=False) as tmp_file:
        tmp_file.write("\n".join(par_file_block1))
        tmp_file_path = Path(tmp_file.name)

    try:
        par_manager = ParManager(fit_config=fit_config, par_file=tmp_file_path)

        # Test section generation
        card1_section = par_manager.generate_par_card1_section()
        assert isinstance(card1_section, str)
        assert len(card1_section) > 0

        card7a_section = par_manager.generate_par_card7a_section()
        assert isinstance(card7a_section, str)
        assert len(card7a_section) > 0

        card10_section = par_manager.generate_par_card10_section()
        assert isinstance(card10_section, str)
        assert len(card10_section) > 0

        inp_card4_section = par_manager.generate_inp_card4_section()
        assert isinstance(inp_card4_section, str)
        assert len(inp_card4_section) > 0

    finally:
        tmp_file_path.unlink()


def test_write_par_file(fit_config, par_file_block1):
    """Test writing parameter file to disk."""
    # First load some data
    with tempfile.NamedTemporaryFile(mode="w", suffix=".par", delete=False) as tmp_file:
        tmp_file.write("\n".join(par_file_block1))
        tmp_file_path = Path(tmp_file.name)

    try:
        par_manager = ParManager(fit_config=fit_config, par_file=tmp_file_path)

        # Test writing to a new file
        with tempfile.NamedTemporaryFile(suffix=".par", delete=False) as output_file:
            output_path = Path(output_file.name)

        try:
            result_path = par_manager.write_par_file(output_path)
            assert result_path == output_path
            assert output_path.exists()
            assert output_path.stat().st_size > 0

            # Verify content was written
            with open(output_path, "r") as f:
                content = f.read()
                assert len(content) > 0

        finally:
            if output_path.exists():
                output_path.unlink()

    finally:
        tmp_file_path.unlink()


def test_generate_par_content(fit_config, par_file_block1):
    """Test generation of complete parameter file content."""
    # First load some data
    with tempfile.NamedTemporaryFile(mode="w", suffix=".par", delete=False) as tmp_file:
        tmp_file.write("\n".join(par_file_block1))
        tmp_file_path = Path(tmp_file.name)

    try:
        par_manager = ParManager(fit_config=fit_config, par_file=tmp_file_path)
        content = par_manager.generate_par_content()

        assert isinstance(content, str)
        assert len(content) > 0

        # Should contain various sections
        assert "PARTICLE PAIR" in content
        assert "SPIN GROUPS" in content
        assert "RESONANCES" in content or "resonances" in content.lower()

    finally:
        tmp_file_path.unlink()


def test_extraction_methods_with_empty_data(fit_config, blank_block):
    """Test extraction methods with empty or invalid data."""
    par_manager = ParManager(fit_config=fit_config)

    # All extraction methods should return False for empty data
    assert par_manager.extract_particle_pairs(blank_block) is False
    assert par_manager.extract_radii_parameters(blank_block) is False
    assert par_manager.extract_isotopes_and_abundances(blank_block) is False
    assert par_manager.extract_normalization_parameters(blank_block) is False
    assert par_manager.extract_spin_groups(blank_block) is False
    assert par_manager.extract_resonance_entries(blank_block) is False


def test_round_trip_consistency(fit_config, par_file_block1):
    """Test that reading and writing maintains data consistency."""
    # First load data from the test fixture
    with tempfile.NamedTemporaryFile(mode="w", suffix=".par", delete=False) as tmp_file:
        tmp_file.write("\n".join(par_file_block1))
        tmp_file_path = Path(tmp_file.name)

    try:
        # Read the original file
        par_manager1 = ParManager(fit_config=FitConfig(), par_file=tmp_file_path)

        # Write to a new file
        with tempfile.NamedTemporaryFile(suffix=".par", delete=False) as output_file:
            output_path = Path(output_file.name)

        try:
            par_manager1.write_par_file(output_path)

            # Read the written file
            par_manager2 = ParManager(fit_config=FitConfig(), par_file=output_path)

            # Compare key data
            assert len(par_manager1.fit_config.nuclear_params.isotopes) == len(
                par_manager2.fit_config.nuclear_params.isotopes
            )
            # Compare particle pairs in the first isotope if available
            if par_manager1.fit_config.nuclear_params.isotopes and par_manager2.fit_config.nuclear_params.isotopes:
                iso1 = par_manager1.fit_config.nuclear_params.isotopes[0]
                iso2 = par_manager2.fit_config.nuclear_params.isotopes[0]
                if hasattr(iso1, "particle_pairs") and hasattr(iso2, "particle_pairs"):
                    assert len(iso1.particle_pairs) == len(iso2.particle_pairs)

        finally:
            if output_path.exists():
                output_path.unlink()

    finally:
        tmp_file_path.unlink()
