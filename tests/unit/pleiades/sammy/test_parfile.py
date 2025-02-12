#!/usr/bin/env python
"""Unit tests for SAMMY parameter file parsing."""

import pytest

from pleiades.sammy.parameters.helper import VaryFlag
from pleiades.sammy.parfile import SammyParameterFile


@pytest.fixture
def basic_fudge_input():
    """Sample input with just fudge factor."""
    return "0.1000\n"


@pytest.fixture
def single_card_input():
    """Sample input with fudge factor and single broadening card."""
    return (
        "0.1000\n"
        "BROADening parameters may be varied\n"
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0\n"
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02\n"
        "\n"
    )


@pytest.fixture
def multi_card_input():
    """Sample input with multiple cards."""
    return (
        "0.1000\n"
        "BROADening parameters may be varied\n"
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0\n"
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02\n"
        "\n"
        "NORMAlization and background are next\n"
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0\n"
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02\n"
        "\n"
    )


def test_parse_fudge_only(basic_fudge_input):
    """Test parsing file with only fudge factor."""
    parfile = SammyParameterFile.from_string(basic_fudge_input)
    assert parfile.fudge == pytest.approx(0.1)
    assert parfile.broadening is None
    assert parfile.resonance is None
    assert parfile.normalization is None


def test_parse_single_card(single_card_input):
    """Test parsing file with fudge factor and single broadening card."""
    parfile = SammyParameterFile.from_string(single_card_input)

    # Check fudge factor
    assert parfile.fudge == pytest.approx(0.1)

    # Check broadening card parsed correctly
    assert parfile.broadening is not None
    assert parfile.broadening.parameters.crfn == pytest.approx(1.234)
    assert parfile.broadening.parameters.temp == pytest.approx(298.0)
    assert parfile.broadening.parameters.flag_crfn == VaryFlag.YES

    # Verify other cards are None
    assert parfile.resonance is None
    assert parfile.normalization is None
    assert parfile.radius is None


def test_parse_multi_card(multi_card_input):
    """Test parsing file with multiple cards."""
    parfile = SammyParameterFile.from_string(multi_card_input)

    # Check fudge factor
    assert parfile.fudge == pytest.approx(0.1)

    # Check broadening card
    assert parfile.broadening is not None
    assert parfile.broadening.parameters.crfn == pytest.approx(1.234)

    # Check normalization card
    assert parfile.normalization is not None
    assert parfile.normalization.angle_sets[0].anorm == pytest.approx(1.234)


def test_roundtrip_single_card(single_card_input):
    """Test round-trip parsing and formatting of single card file."""
    parfile = SammyParameterFile.from_string(single_card_input)
    output = parfile.to_string()
    reparsed = SammyParameterFile.from_string(output)

    # Compare original and reparsed objects
    assert parfile.fudge == reparsed.fudge
    assert parfile.broadening.parameters.crfn == reparsed.broadening.parameters.crfn
    assert parfile.broadening.parameters.temp == reparsed.broadening.parameters.temp
    assert parfile.broadening.parameters.flag_crfn == reparsed.broadening.parameters.flag_crfn


@pytest.mark.parametrize(
    "invalid_input,error_pattern",
    [
        ("", "Empty parameter file content"),
        ("abc\n", "Invalid content"),
        ("0.1\nINVALID card header\n", "Invalid content"),
        ("0.1\nBROADening parameters may be varied\nINVALID DATA\n", "Failed to parse BROADENING card"),
    ],
)
def test_parse_errors(invalid_input, error_pattern):
    """Test error handling for invalid inputs."""
    with pytest.raises(ValueError, match=error_pattern):
        tmp = SammyParameterFile.from_string(invalid_input)
        print(tmp)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
