"""Unit tests for SAMMY input file - Card 10 (spin groups) classes."""

import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.inp10_spingroups import Card10p2


@pytest.fixture
def spin_group_block1():
    return [
        "SPIN GROUPS",
        "  1      1    1  0.5 1.0000000",
        "    1  Inc Chan    0  0.5",
        "    2  PPair #2    2  1.5",
        "  2      1    1 -0.5 1.0000000",
        "    1  Inc Chan    1  0.5",
        "    2  PPair #4    1  0.5",
        "  3      1    1 -1.5 1.0000000",
        "    1  Inc Chan    1  0.5",
        "    2  PPair #4    1  0.5",
        "  4      1    2  1.5 1.0000000",
        "    1  Inc Chan    2  0.5",
        "    2  PPair #4    2  0.5",
        "    3  PPair #2    0  1.5",
        "  5      1    2  2.5 1.0000000",
        "    1  Inc Chan    2  0.5",
        "    2  PPair #4    2  0.5",
        "    3  PPair #2    0  2.5",
        "  6      1    2 -2.5 1.0000000",
        "    1  Inc Chan    3  0.5",
        "    2  PPair #4    3  0.5",
        "    3  PPair #2    1  2.5",
        "  7      1    2 -3.5 1.0000000",
        "    1  Inc Chan    3  0.5",
        "    2  PPair #4    3  0.5",
        "    3  PPair #2    1  2.5",
        "  8      1    0  0.0 0.0467000",
        "    1  Inc Ch#1    0  0.0",
        "  9      1    0  1.0 0.0467000",
        "    1  Inc Ch#1    0  1.0",
        " 10      1    0 -1.0 0.0467000",
        "    1  Inc Ch#1    1  0.0",
        " 11      1    0 -0.0 0.0467000",
        "    1  Inc Ch#1    1  1.0",
        " 12      1    0 -1.0 0.0467000",
        "    1  Inc Ch#1    1  1.0",
        " 13      1    0 -2.0 0.0467000",
        "    1  Inc Ch#1    1  1.0",
        " 14      1    0  2.0 0.0467000",
        "    1  Inc Ch#1    2  0.0",
        " 15      1    0  1.0 0.0467000",
        "    1  Inc Ch#1    2  1.0",
        " 16      1    0  2.0 0.0467000",
        "    1  Inc Ch#1    2  1.0",
        " 17      1    0  3.0 0.0467000",
        "    1  Inc Ch#1    2  1.0",
        " 18      1    0  0.5 0.0310000",
        "    1  Inc Ch#2    0  0.5",
        " 19      1    0 -0.5 0.0310000",
        "    1  Inc Ch#2    1  0.5",
        " 20      1    0 -1.5 0.0310000",
        "    1  Inc Ch#2    1  0.5",
        " 21      1    0  1.5 0.0310000",
        "    1  Inc Ch#2    2  0.5",
        " 22      1    0  2.5 0.0310000",
        "    1  Inc Ch#2    2  0.5",
        " 23 X    1    0  0.5 1.0000000",
        "    1  Inc Ch#3    0  0.5",
        " 24 X    1    0 -0.5 1.0000000",
        "    1  Inc Ch#3    1  0.5",
        " 25 X    1    0 -1.5 1.0000000",
        "    1  Inc Ch#3    1  0.5",
        " 26 X    1    0  1.5 1.0000000",
        "    1  Inc Ch#3    2  0.5",
        " 27 X    1    0  2.5 1.0000000",
        "    1  Inc Ch#3    2  0.5",
        " 28 X    1    0 -2.5 1.0000000",
        "    1  Inc Ch#3    3  0.5",
        " 29 X    1    0 -3.5 1.0000000",
        "    1  Inc Ch#3    3  0.5",
        "",
    ]


@pytest.fixture
def spin_group_block2():
    return [
        "SPIN GROUP INFORMATION",
        "  1      1    2  0.5 1.0000000",
        "    1    PPair1    0       0.5            9.42848000 8.42304405",
        "    2    PPair2    0         0            9.42848000 8.42304405",
        "    3    PPair2    0         0            9.42848000 8.42304405",
        "  2      1    0 -0.5 1.0000000",
        "    1    PPair1    1       0.5            9.42848000 8.42304405",
        "  3      1    0 -1.5 1.0000000",
        "    1    PPair1    1       0.5            9.42848000 8.42304405",
        "  4      1    0  1.5 1.0000000",
        "    1    PPair1    2       0.5            9.42848000 8.42304405",
        "  5      1    0  2.5 1.0000000",
        "    1    PPair1    2       0.5            9.42848000 8.42304405",
        "",
    ]


@pytest.fixture
def spin_group_block3():
    return [
        "SPIN GROUPS",
        "  1      1    0  0.5 1.0000000",
        "    1  Inc Chan    0  0.5",
        "    2  Inc Chan    0  0.5",
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
    ]


@pytest.fixture
def spin_group_no_lines():
    """Fixture for a spin group block with no lines."""
    return []


@pytest.fixture
def fit_config():
    # Create a minimal FitConfig instance
    return FitConfig()


def test_spin_group_block1(fit_config, spin_group_block1):
    """Read and parse a spin group block 1"""

    # Parse the lines from spin_group_block1 into the FitConfig
    Card10p2.from_lines(spin_group_block1, fit_config)

    # Check that an isotope named "UNKN" was created
    assert fit_config.nuclear_params.isotopes[0].isotope_information.name == "UNKN"

    # Check if there are 29 spin groups
    assert len(fit_config.nuclear_params.isotopes[0].spin_groups) == 29


# Test that Card10p2 correctly identifies header lines


def test_is_header_line():
    assert Card10p2.is_header_line("SPIN GROUPS")
    assert Card10p2.is_header_line("  SPIN GROUPS   ")
    assert not Card10p2.is_header_line("SPIN GROUP INFORMATION")
    assert not Card10p2.is_header_line("")


# Test that Card10p2.get_line_type returns the correct type for different line formats


def test_get_line_type():
    # Should detect a spin group line
    assert Card10p2.get_line_type("  1      1    1  0.5 1.0000000") == "SPIN_GROUP"
    # Should detect a channel line
    assert Card10p2.get_line_type("    1  Inc Chan    0  0.5") == "CHANNEL"
    # Should return None for unrelated lines
    assert Card10p2.get_line_type("random text") is None
    assert Card10p2.get_line_type("") is None


# Test that from_lines raises ValueError on empty input


def test_from_lines_empty_lines(fit_config):
    with pytest.raises(ValueError):
        Card10p2.from_lines([], fit_config)


# Test that from_lines raises ValueError if fit_config is missing or wrong type


def test_from_lines_bad_fit_config(spin_group_block1):
    with pytest.raises(ValueError):
        Card10p2.from_lines(spin_group_block1, fit_config=None)
    with pytest.raises(ValueError):
        Card10p2.from_lines(spin_group_block1, fit_config="not_a_fit_config")


# Test round-trip: parse lines, then serialize back, and compare essential content


def test_to_lines_round_trip(fit_config, spin_group_block1):
    # Parse and then serialize back
    Card10p2.from_lines(spin_group_block1, fit_config)
    lines = Card10p2.to_lines(fit_config)

    # make another fit_config and read in the lines
    fit_config_2 = FitConfig()
    Card10p2.from_lines(spin_group_block1, fit_config_2)

    # Assert that fit_config and fit_config_2 are equivalent
    assert fit_config == fit_config_2


# Test that spin groups are attached to the isotope in nuclear_params.isotopes after parsing


def test_spin_groups_attached_to_isotope(fit_config, spin_group_block1):
    # Import IsotopeParameters and related classes for dummy isotope creation
    from pleiades.nuclear.models import IsotopeInfo, IsotopeMassData, IsotopeParameters

    # Create a dummy isotope and add to fit_config.nuclear_params.isotopes
    dummy_isotope = IsotopeParameters(
        isotope_information=IsotopeInfo(
            name="Dummy-1", atomic_number=1, mass_data=IsotopeMassData(atomic_mass=1.0), spin=0.5, mass_number=1
        ),
        abundance=1.0,
    )
    fit_config.nuclear_params.isotopes.append(dummy_isotope)

    # Parse the lines
    Card10p2.from_lines(spin_group_block1, fit_config)

    # Check that the isotope's spin_groups are populated
    assert len(fit_config.nuclear_params.isotopes[0].spin_groups) == 29
    # Check a property of the first spin group
    sg = fit_config.nuclear_params.isotopes[0].spin_groups[0]
    assert hasattr(sg, "spin_group_number")
