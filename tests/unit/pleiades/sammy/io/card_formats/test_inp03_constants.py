"""Unit tests for SAMMY INP file - Card 3 (physical constants) class."""

import pytest

from pleiades.sammy.io.card_formats.inp03_constants import Card03, PhysicalConstants


@pytest.fixture
def ex012_line():
    """Example from SAMMY ex012a.inp line 8."""
    return ["      300.  200.0000  0.182233       0.0  0.002518"]


@pytest.fixture
def venus_default_line():
    """Default VENUS configuration."""
    return ["    293.6    25.0    0.0       0.0     0.0"]


@pytest.fixture
def minimal_line():
    """Minimal valid example with only required fields."""
    return ["300.0 25.0"]


def test_parse_ex012_line(ex012_line):
    """Test parsing ex012 physical constants line."""
    constants = Card03.from_lines(ex012_line)

    assert pytest.approx(constants.temperature, rel=1e-3) == 300.0
    assert pytest.approx(constants.flight_path_length, rel=1e-4) == 200.0
    assert pytest.approx(constants.delta_l, rel=1e-6) == 0.182233
    assert pytest.approx(constants.delta_g, rel=1e-3) == 0.0
    assert pytest.approx(constants.delta_e, rel=1e-6) == 0.002518


def test_parse_venus_default_line(venus_default_line):
    """Test parsing VENUS default configuration."""
    constants = Card03.from_lines(venus_default_line)

    assert pytest.approx(constants.temperature, rel=1e-3) == 293.6
    assert pytest.approx(constants.flight_path_length, rel=1e-3) == 25.0
    assert pytest.approx(constants.delta_l, rel=1e-3) == 0.0
    assert pytest.approx(constants.delta_g, rel=1e-3) == 0.0
    assert pytest.approx(constants.delta_e, rel=1e-3) == 0.0


def test_parse_minimal_line(minimal_line):
    """Test parsing minimal valid line (only TEMP and FPL)."""
    constants = Card03.from_lines(minimal_line)

    assert pytest.approx(constants.temperature, rel=1e-3) == 300.0
    assert pytest.approx(constants.flight_path_length, rel=1e-3) == 25.0
    assert pytest.approx(constants.delta_l, rel=1e-3) == 0.0
    assert pytest.approx(constants.delta_g, rel=1e-3) == 0.0
    assert pytest.approx(constants.delta_e, rel=1e-3) == 0.0


def test_parse_empty_line():
    """Test that empty line raises ValueError."""
    with pytest.raises(ValueError, match="No valid Card 3 line"):
        Card03.from_lines([""])


def test_parse_no_lines():
    """Test that empty list raises ValueError."""
    with pytest.raises(ValueError, match="No valid Card 3 line"):
        Card03.from_lines([])


def test_parse_insufficient_fields():
    """Test that line with only one field raises ValueError."""
    with pytest.raises(ValueError, match="Card 3 line must have at least 2 fields"):
        Card03.from_lines(["300.0"])


def test_parse_invalid_format():
    """Test that invalid numeric format raises ValueError."""
    with pytest.raises(ValueError, match="Failed to parse Card 3 line"):
        Card03.from_lines(["InvalidData MoreInvalidData"])


def test_to_lines_ex012():
    """Test generating ex012-style line."""
    constants = PhysicalConstants(
        temperature=300.0, flight_path_length=200.0, delta_l=0.182233, delta_g=0.0, delta_e=0.002518
    )

    lines = Card03.to_lines(constants)

    assert len(lines) == 1
    assert "300.0" in lines[0]
    assert "200.0000" in lines[0]
    assert "0.182233" in lines[0]
    assert "0.0" in lines[0]
    assert "0.002518" in lines[0]


def test_to_lines_venus_default():
    """Test generating VENUS default line."""
    constants = PhysicalConstants(temperature=293.6, flight_path_length=25.0, delta_l=0.0, delta_g=0.0, delta_e=0.0)

    lines = Card03.to_lines(constants)

    assert len(lines) == 1
    assert "293.6" in lines[0]
    assert "25.0000" in lines[0]
    assert "0.000000" in lines[0]


def test_to_lines_minimal():
    """Test generating minimal line with defaults."""
    constants = PhysicalConstants(temperature=300.0, flight_path_length=25.0)

    lines = Card03.to_lines(constants)

    assert len(lines) == 1
    assert "300.0" in lines[0]
    assert "25.0000" in lines[0]


def test_roundtrip_ex012(ex012_line):
    """Test parse and regenerate produces consistent result."""
    constants = Card03.from_lines(ex012_line)
    regenerated_lines = Card03.to_lines(constants)

    reparsed_constants = Card03.from_lines(regenerated_lines)

    assert pytest.approx(reparsed_constants.temperature, rel=1e-3) == constants.temperature
    assert pytest.approx(reparsed_constants.flight_path_length, rel=1e-3) == constants.flight_path_length
    assert pytest.approx(reparsed_constants.delta_l, rel=1e-5) == constants.delta_l
    assert pytest.approx(reparsed_constants.delta_g, rel=1e-3) == constants.delta_g
    assert pytest.approx(reparsed_constants.delta_e, rel=1e-5) == constants.delta_e


def test_physical_constants_validation_negative_temperature():
    """Test that temperature must be positive."""
    with pytest.raises(ValueError):
        PhysicalConstants(temperature=-273.0, flight_path_length=25.0)


def test_physical_constants_validation_zero_temperature():
    """Test that temperature must be positive (not zero)."""
    with pytest.raises(ValueError):
        PhysicalConstants(temperature=0.0, flight_path_length=25.0)


def test_physical_constants_validation_negative_flight_path():
    """Test that flight_path_length must be positive."""
    with pytest.raises(ValueError):
        PhysicalConstants(temperature=300.0, flight_path_length=-25.0)


def test_physical_constants_validation_negative_delta_l():
    """Test that delta_l must be non-negative."""
    with pytest.raises(ValueError):
        PhysicalConstants(temperature=300.0, flight_path_length=25.0, delta_l=-0.1)


def test_physical_constants_validation_negative_delta_g():
    """Test that delta_g must be non-negative."""
    with pytest.raises(ValueError):
        PhysicalConstants(temperature=300.0, flight_path_length=25.0, delta_g=-0.1)


def test_physical_constants_validation_negative_delta_e():
    """Test that delta_e must be non-negative."""
    with pytest.raises(ValueError):
        PhysicalConstants(temperature=300.0, flight_path_length=25.0, delta_e=-0.1)


def test_to_lines_invalid_input():
    """Test that to_lines rejects non-PhysicalConstants input."""
    with pytest.raises(ValueError, match="constants must be an instance of PhysicalConstants"):
        Card03.to_lines("not a PhysicalConstants object")


def test_default_values():
    """Test that optional parameters default to 0.0."""
    constants = PhysicalConstants(temperature=300.0, flight_path_length=25.0)

    assert constants.delta_l == 0.0
    assert constants.delta_g == 0.0
    assert constants.delta_e == 0.0
