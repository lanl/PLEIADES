"""Unit tests for SAMMY INP file - Sample Density class."""

import pytest

from pleiades.sammy.io.card_formats.inp03_density import Card03Density, SampleDensity


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
    """Test parsing ex012 density line."""
    density = Card03Density.from_lines(ex012_line)

    assert pytest.approx(density.density, rel=1e-5) == 4.20000
    assert pytest.approx(density.number_density, rel=1e-6) == 0.347162


def test_parse_default_line(default_line):
    """Test parsing default density line."""
    density = Card03Density.from_lines(default_line)

    assert pytest.approx(density.density, rel=1e-6) == 9.0
    assert pytest.approx(density.number_density, rel=1e-6) == 1.797e-03


def test_parse_scientific_notation_line(scientific_notation_line):
    """Test parsing line with scientific notation."""
    density = Card03Density.from_lines(scientific_notation_line)

    assert pytest.approx(density.density, rel=1e-5) == 19.3
    assert pytest.approx(density.number_density, rel=1e-6) == 3.456789e-02


def test_parse_empty_line():
    """Test that empty line raises ValueError."""
    with pytest.raises(ValueError, match="No valid density line"):
        Card03Density.from_lines([""])


def test_parse_no_lines():
    """Test that empty list raises ValueError."""
    with pytest.raises(ValueError, match="No valid density line"):
        Card03Density.from_lines([])


def test_parse_insufficient_fields():
    """Test that line with only one field raises ValueError."""
    with pytest.raises(ValueError, match="Density line must have 2 fields"):
        Card03Density.from_lines(["4.2"])


def test_parse_invalid_format():
    """Test that invalid numeric format raises ValueError."""
    with pytest.raises(ValueError, match="Failed to parse density line"):
        Card03Density.from_lines(["InvalidData MoreInvalidData"])


def test_to_lines_ex012():
    """Test generating ex012-style line."""
    density = SampleDensity(density=4.20000, number_density=0.347162)

    lines = Card03Density.to_lines(density)

    assert len(lines) == 1
    assert "4.200000" in lines[0]
    assert "3.471620e-01" in lines[0] or "3.47162e-01" in lines[0]


def test_to_lines_default():
    """Test generating default line."""
    density = SampleDensity(density=9.0, number_density=1.797e-03)

    lines = Card03Density.to_lines(density)

    assert len(lines) == 1
    assert "9.000000" in lines[0]
    assert "1.797" in lines[0]
    assert "e-03" in lines[0]


def test_to_lines_scientific():
    """Test generating line with scientific notation."""
    density = SampleDensity(density=19.3, number_density=3.456789e-02)

    lines = Card03Density.to_lines(density)

    assert len(lines) == 1
    assert "19.300000" in lines[0]
    assert "3.456789e-02" in lines[0] or "3.45678" in lines[0]


def test_roundtrip_ex012(ex012_line):
    """Test parse and regenerate produces consistent result."""
    density = Card03Density.from_lines(ex012_line)
    regenerated_lines = Card03Density.to_lines(density)

    reparsed_density = Card03Density.from_lines(regenerated_lines)

    assert pytest.approx(reparsed_density.density, rel=1e-5) == density.density
    assert pytest.approx(reparsed_density.number_density, rel=1e-5) == density.number_density


def test_sample_density_validation_negative_density():
    """Test that density must be positive."""
    with pytest.raises(ValueError):
        SampleDensity(density=-9.0, number_density=0.001)


def test_sample_density_validation_zero_density():
    """Test that density must be positive (not zero)."""
    with pytest.raises(ValueError):
        SampleDensity(density=0.0, number_density=0.001)


def test_sample_density_validation_negative_number_density():
    """Test that number_density must be positive."""
    with pytest.raises(ValueError):
        SampleDensity(density=9.0, number_density=-0.001)


def test_sample_density_validation_zero_number_density():
    """Test that number_density must be positive (not zero)."""
    with pytest.raises(ValueError):
        SampleDensity(density=9.0, number_density=0.0)


def test_to_lines_invalid_input():
    """Test that to_lines rejects non-SampleDensity input."""
    with pytest.raises(ValueError, match="sample_density must be an instance of SampleDensity"):
        Card03Density.to_lines("not a SampleDensity object")


def test_typical_values():
    """Test typical material density values."""
    gold_density = SampleDensity(density=19.3, number_density=0.059)

    assert gold_density.density == 19.3
    assert gold_density.number_density == 0.059


def test_small_number_density():
    """Test very small number density values."""
    density = SampleDensity(density=0.001, number_density=1e-10)

    lines = Card03Density.to_lines(density)
    assert len(lines) == 1
    assert "0.001000" in lines[0]
    assert "e-10" in lines[0]
