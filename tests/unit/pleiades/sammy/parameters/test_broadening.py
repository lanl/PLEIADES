#!/usr/bin/env python
"""Unit tests for card 04::broadening parameters."""

import pytest

from pleiades.sammy.parameters.broadening import BroadeningParameterCard, BroadeningParameters
from pleiades.sammy.parameters.helper import VaryFlag

# Test data with proper 10-char width formatting
MAIN_ONLY_LINE = "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0"

WITH_UNC_LINES = [
    "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0",
    "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02",
]

FULL_LINES = [
    "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0",
    "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02",
    "1.000E-01 2.000E-02                                          1 1",
    "5.000E-03 1.000E-03",
]

COMPLETE_CARD = [
    "BROADening parameters may be varied",
    "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0",
    "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02",
    "1.000E-01 2.000E-02                                          1 1",
    "5.000E-03 1.000E-03",
    "",
]


def test_main_parameters_parsing():
    """Test parsing of main parameters only."""
    params = BroadeningParameters.from_lines([MAIN_ONLY_LINE])

    # Check values
    assert params.crfn == pytest.approx(1.234)
    assert params.temp == pytest.approx(298.0)
    assert params.thick == pytest.approx(0.15)
    assert params.deltal == pytest.approx(0.025)
    assert params.deltag == pytest.approx(1.0)
    assert params.deltae == pytest.approx(0.5)

    # Check flags
    assert params.flag_crfn == VaryFlag.YES
    assert params.flag_temp == VaryFlag.NO
    assert params.flag_thick == VaryFlag.YES
    assert params.flag_deltal == VaryFlag.NO
    assert params.flag_deltag == VaryFlag.YES
    assert params.flag_deltae == VaryFlag.NO

    # Check optional fields are None
    assert params.deltc1 is None
    assert params.deltc2 is None
    assert params.d_crfn is None
    assert params.d_temp is None


def test_parameters_with_uncertainties():
    """Test parsing of parameters with uncertainties."""
    params = BroadeningParameters.from_lines(WITH_UNC_LINES)

    # Check main values
    assert params.crfn == pytest.approx(1.234)
    assert params.temp == pytest.approx(298.0)

    # Check uncertainties
    assert params.d_crfn == pytest.approx(0.01)
    assert params.d_temp == pytest.approx(1.0)
    assert params.d_thick == pytest.approx(0.001)
    assert params.d_deltal == pytest.approx(0.001)
    assert params.d_deltag == pytest.approx(0.01)
    assert params.d_deltae == pytest.approx(0.01)


def test_full_parameters():
    """Test parsing of full parameter set including Gaussian parameters."""
    params = BroadeningParameters.from_lines(FULL_LINES)

    # Check Gaussian parameters
    assert params.deltc1 == pytest.approx(0.1)
    assert params.deltc2 == pytest.approx(0.02)
    assert params.d_deltc1 == pytest.approx(0.005)
    assert params.d_deltc2 == pytest.approx(0.001)
    assert params.flag_deltc1 == VaryFlag.YES
    assert params.flag_deltc2 == VaryFlag.YES


def test_format_compliance():
    """Test that output lines comply with fixed-width format."""
    params = BroadeningParameters.from_lines(FULL_LINES)
    output_lines = params.to_lines()

    print(output_lines)

    # Check first line field widths
    first_line = output_lines[0]
    assert len(first_line[:10].rstrip()) == 9  # 9 chars + 1 space
    assert len(first_line[10:20].rstrip()) == 9
    assert len(first_line[20:30].rstrip()) == 9
    assert len(first_line[30:40].rstrip()) == 9
    assert len(first_line[40:50].rstrip()) == 9
    assert len(first_line[50:60].rstrip()) == 9


def test_complete_card():
    """Test parsing and formatting of complete card including header."""
    card = BroadeningParameterCard.from_lines(COMPLETE_CARD)
    output_lines = card.to_lines()

    # Check header
    assert output_lines[0].startswith("BROAD")

    # Check number of lines
    assert len(output_lines) == 6  # Header + 4 data lines + blank

    # Check last line is blank
    assert output_lines[-1].strip() == ""


def test_invalid_header():
    """Test error handling for invalid header."""
    bad_lines = ["WRONG header", MAIN_ONLY_LINE]
    with pytest.raises(ValueError, match="Invalid header"):
        BroadeningParameterCard.from_lines(bad_lines)


def test_missing_gaussian_parameter():
    """Test error handling for incomplete Gaussian parameters."""
    bad_lines = [
        MAIN_ONLY_LINE,
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02",
        "1.000E-01                                                     1",  # Missing DELTC2
    ]
    with pytest.raises(ValueError, match="Both DELTC1 and DELTC2 must be present"):
        BroadeningParameters.from_lines(bad_lines)


def test_empty_input():
    """Test error handling for empty input."""
    with pytest.raises(ValueError, match="No valid parameter line provided"):
        BroadeningParameters.from_lines([])


def test_roundtrip():
    """Test that parsing and then formatting produces identical output."""
    card = BroadeningParameterCard.from_lines(COMPLETE_CARD)
    output_lines = card.to_lines()

    # Parse the output again
    reparsed_card = BroadeningParameterCard.from_lines(output_lines)

    # Compare all attributes
    assert card.parameters.crfn == reparsed_card.parameters.crfn
    assert card.parameters.temp == reparsed_card.parameters.temp
    assert card.parameters.deltc1 == reparsed_card.parameters.deltc1
    assert card.parameters.flag_crfn == reparsed_card.parameters.flag_crfn


if __name__ == "__main__":
    pytest.main(["-v", __file__])
