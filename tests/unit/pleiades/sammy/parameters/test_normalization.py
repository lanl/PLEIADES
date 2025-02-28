#!/usr/bin/env python
"""Unit tests for card 06::normalization and background parameters."""

import pytest

from pleiades.utils.helper import VaryFlag
from pleiades.sammy.parameters.normalization import NormalizationBackgroundCard, NormalizationParameters

# Test data with proper 10-char width formatting
MAIN_ONLY_LINE = "1.000E+00 2.000E-02 3.000E-03 4.000E-04 5.000E-05 6.000E-06  1 0 1 0 1 0"

WITH_UNC_LINES = [
    "1.000E+00 2.000E-02 3.000E-03 4.000E-04 5.000E-05 6.000E-06  1 0 1 0 1 0",
    "1.000E-02 2.000E-03 3.000E-04 4.000E-05 5.000E-06 6.000E-07",
]

COMPLETE_CARD = [
    "NORMAlization and background are next",
    "1.000E+00 2.000E-02 3.000E-03 4.000E-04 5.000E-05 6.000E-06  1 0 1 0 1 0",
    "1.000E-02 2.000E-03 3.000E-04 4.000E-05 5.000E-06 6.000E-07",
    "2.000E+00 3.000E-02 4.000E-03 5.000E-04 6.000E-05 7.000E-06  0 1 0 1 0 1",
    "",
]


def test_main_parameters_parsing():
    """Test parsing of main parameters only."""
    params = NormalizationParameters.from_lines([MAIN_ONLY_LINE])

    # Check values
    assert params.anorm == pytest.approx(1.0)
    assert params.backa == pytest.approx(0.02)
    assert params.backb == pytest.approx(0.003)
    assert params.backc == pytest.approx(0.0004)
    assert params.backd == pytest.approx(0.00005)
    assert params.backf == pytest.approx(0.000006)

    # Check flags
    assert params.flag_anorm == VaryFlag.YES
    assert params.flag_backa == VaryFlag.NO
    assert params.flag_backb == VaryFlag.YES
    assert params.flag_backc == VaryFlag.NO
    assert params.flag_backd == VaryFlag.YES
    assert params.flag_backf == VaryFlag.NO

    # Check optional uncertainties are None
    assert params.d_anorm is None
    assert params.d_backa is None
    assert params.d_backb is None


def test_parameters_with_uncertainties():
    """Test parsing of parameters with uncertainties."""
    params = NormalizationParameters.from_lines(WITH_UNC_LINES)

    # Check main values
    assert params.anorm == pytest.approx(1.0)
    assert params.backa == pytest.approx(0.02)

    # Check uncertainties
    assert params.d_anorm == pytest.approx(0.01)
    assert params.d_backa == pytest.approx(0.002)
    assert params.d_backb == pytest.approx(0.0003)
    assert params.d_backc == pytest.approx(0.00004)
    assert params.d_backd == pytest.approx(0.000005)
    assert params.d_backf == pytest.approx(0.0000006)


def test_format_compliance():
    """Test that output lines comply with fixed-width format."""
    params = NormalizationParameters.from_lines(WITH_UNC_LINES)
    output_lines = params.to_lines()

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
    card = NormalizationBackgroundCard.from_lines(COMPLETE_CARD)
    output_lines = card.to_lines()

    # Check header
    assert output_lines[0].startswith("NORMA")

    # Check number of lines
    assert len(output_lines) == 5  # Header + 3 data lines + blank

    # Check number of angle sets
    assert len(card.angle_sets) == 2

    # Check last line is blank
    assert output_lines[-1].strip() == ""


def test_multiple_angle_sets():
    """Test parsing of multiple angle sets."""
    card = NormalizationBackgroundCard.from_lines(COMPLETE_CARD)

    # Check first angle set
    assert card.angle_sets[0].anorm == pytest.approx(1.0)
    assert card.angle_sets[0].d_anorm == pytest.approx(0.01)

    # Check second angle set
    assert card.angle_sets[1].anorm == pytest.approx(2.0)
    assert card.angle_sets[1].flag_backa == VaryFlag.YES


def test_invalid_header():
    """Test error handling for invalid header."""
    bad_lines = ["WRONG header", MAIN_ONLY_LINE]
    with pytest.raises(ValueError, match="Invalid header"):
        NormalizationBackgroundCard.from_lines(bad_lines)


def test_empty_input():
    """Test error handling for empty input."""
    with pytest.raises(ValueError, match="No valid parameter line provided"):
        NormalizationParameters.from_lines([])


def test_roundtrip():
    """Test that parsing and then formatting produces identical output."""
    card = NormalizationBackgroundCard.from_lines(COMPLETE_CARD)
    output_lines = card.to_lines()

    # Parse the output again
    reparsed_card = NormalizationBackgroundCard.from_lines(output_lines)

    # Compare attributes of first angle set
    first_set = card.angle_sets[0]
    reparsed_first_set = reparsed_card.angle_sets[0]
    assert first_set.anorm == reparsed_first_set.anorm
    assert first_set.backa == reparsed_first_set.backa
    assert first_set.flag_anorm == reparsed_first_set.flag_anorm
    assert first_set.d_anorm == reparsed_first_set.d_anorm


if __name__ == "__main__":
    pytest.main(["-v", __file__])
