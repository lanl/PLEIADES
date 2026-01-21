"""Unit tests for SAMMY INP file - Card Set 7 class."""

import pytest

from pleiades.sammy.io.card_formats.inp07_density import Card07, Card07Parameters


@pytest.fixture
def ex012_line():
    """Example from SAMMY ex012a.inp line 9."""
    return ["   4.20000  0.347162"]


@pytest.fixture
def default_line():
    """Default configuration."""
    return ["  9.000000 1.797e-03"]


@pytest.fixture
def scientific_notation_line():
    """Line with scientific notation."""
    return ["  19.300000 3.456789e-02"]


def test_parse_ex012_line(ex012_line):
    """Test parsing ex012 Card 7 line."""
    params = Card07.from_lines(ex012_line)

    assert pytest.approx(params.crfn, rel=1e-5) == 4.20000
    assert pytest.approx(params.thick, rel=1e-6) == 0.347162


def test_parse_default_line(default_line):
    """Test parsing default Card 7 line."""
    params = Card07.from_lines(default_line)

    assert pytest.approx(params.crfn, rel=1e-6) == 9.0
    assert pytest.approx(params.thick, rel=1e-6) == 1.797e-03


def test_parse_scientific_notation_line(scientific_notation_line):
    """Test parsing line with scientific notation."""
    params = Card07.from_lines(scientific_notation_line)

    assert pytest.approx(params.crfn, rel=1e-5) == 19.3
    assert pytest.approx(params.thick, rel=1e-6) == 3.456789e-02


def test_parse_empty_line():
    """Test that empty line raises ValueError."""
    with pytest.raises(ValueError, match="No valid Card 7 line"):
        Card07.from_lines([""])


def test_parse_no_lines():
    """Test that empty list raises ValueError."""
    with pytest.raises(ValueError, match="No valid Card 7 line"):
        Card07.from_lines([])


def test_parse_insufficient_fields():
    """Test that line with only one field raises ValueError."""
    with pytest.raises(ValueError, match="Card 7 line must have at least 2 fields"):
        Card07.from_lines(["4.2"])


def test_parse_invalid_format():
    """Test that invalid numeric format raises ValueError."""
    with pytest.raises(ValueError, match="Failed to parse Card 7 line"):
        Card07.from_lines(["InvalidData MoreInvalidData"])


def test_to_lines_ex012():
    """Test generating ex012-style line."""
    params = Card07Parameters(crfn=4.20000, thick=0.347162)

    lines = Card07.to_lines(params)

    assert len(lines) == 1
    assert "4.200000" in lines[0]
    assert "3.471620e-01" in lines[0] or "3.47162e-01" in lines[0]


def test_to_lines_default():
    """Test generating default line."""
    params = Card07Parameters(crfn=9.0, thick=1.797e-03)

    lines = Card07.to_lines(params)

    assert len(lines) == 1
    assert "9.000000" in lines[0]
    assert "1.797" in lines[0]
    assert "e-03" in lines[0]


def test_to_lines_scientific():
    """Test generating line with scientific notation."""
    params = Card07Parameters(crfn=19.3, thick=3.456789e-02)

    lines = Card07.to_lines(params)

    assert len(lines) == 1
    assert "19.300000" in lines[0]
    assert "3.456789e-02" in lines[0] or "3.45678" in lines[0]


def test_roundtrip_ex012(ex012_line):
    """Test parse and regenerate produces consistent result."""
    params = Card07.from_lines(ex012_line)
    regenerated_lines = Card07.to_lines(params)

    reparsed = Card07.from_lines(regenerated_lines)

    assert pytest.approx(reparsed.crfn, rel=1e-5) == params.crfn
    assert pytest.approx(reparsed.thick, rel=1e-5) == params.thick


def test_card07_validation_negative_crfn():
    """Test that CRFN must be non-negative."""
    with pytest.raises(ValueError):
        Card07Parameters(crfn=-9.0, thick=0.001)


def test_card07_validation_negative_thick():
    """Test that THICK must be non-negative."""
    with pytest.raises(ValueError):
        Card07Parameters(crfn=9.0, thick=-0.001)


def test_to_lines_invalid_input():
    """Test that to_lines rejects non-Card07Parameters input."""
    with pytest.raises(ValueError, match="params must be an instance of Card07Parameters"):
        Card07.to_lines("not a Card07Parameters object")


def test_typical_values():
    """Test typical material density values."""
    params = Card07Parameters(crfn=19.3, thick=0.059)

    assert params.crfn == 19.3
    assert params.thick == 0.059


def test_small_number_density():
    """Test very small number density values."""
    params = Card07Parameters(crfn=0.001, thick=1e-10)

    lines = Card07.to_lines(params)
    assert len(lines) == 1
    assert "0.001000" in lines[0]
    assert "e-10" in lines[0]
