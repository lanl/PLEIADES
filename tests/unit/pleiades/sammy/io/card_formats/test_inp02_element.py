"""Unit tests for SAMMY INP file - Card 2 (element information) class."""

import pytest

from pleiades.sammy.io.card_formats.inp02_element import Card02, ElementInfo


@pytest.fixture
def silicon_line():
    """Example from SAMMY ex012a.inp."""
    return ["Si        27.976928 300000.   1800000."]


@pytest.fixture
def gold_line():
    """Example for Au-197 from VENUS."""
    return ["Au197     196.96657     0.001    1000.0"]


@pytest.fixture
def minimal_line():
    """Minimal valid example."""
    return ["H           1.00794     0.001      10.0"]


def test_parse_silicon_line(silicon_line):
    """Test parsing silicon element line."""
    element_info = Card02.from_lines(silicon_line)

    assert element_info.element == "Si"
    assert pytest.approx(element_info.atomic_weight, rel=1e-6) == 27.976928
    assert pytest.approx(element_info.min_energy, rel=1e-3) == 300000.0
    assert pytest.approx(element_info.max_energy, rel=1e-3) == 1800000.0


def test_parse_gold_line(gold_line):
    """Test parsing gold element line."""
    element_info = Card02.from_lines(gold_line)

    assert element_info.element == "Au197"
    assert pytest.approx(element_info.atomic_weight, rel=1e-6) == 196.96657
    assert pytest.approx(element_info.min_energy, rel=1e-3) == 0.001
    assert pytest.approx(element_info.max_energy, rel=1e-3) == 1000.0


def test_parse_minimal_line(minimal_line):
    """Test parsing minimal valid line."""
    element_info = Card02.from_lines(minimal_line)

    assert element_info.element == "H"
    assert pytest.approx(element_info.atomic_weight, rel=1e-5) == 1.00794
    assert pytest.approx(element_info.min_energy, rel=1e-3) == 0.001
    assert pytest.approx(element_info.max_energy, rel=1e-3) == 10.0


def test_parse_empty_line():
    """Test that empty line raises ValueError."""
    with pytest.raises(ValueError, match="No valid Card 2 line"):
        Card02.from_lines([""])


def test_parse_no_lines():
    """Test that empty list raises ValueError."""
    with pytest.raises(ValueError, match="No valid Card 2 line"):
        Card02.from_lines([])


def test_parse_invalid_format():
    """Test that invalid numeric format raises ValueError."""
    with pytest.raises(ValueError, match="Failed to parse Card 2 line"):
        Card02.from_lines(["InvalidDataXXXXXXXXXXXXXXXX"])


def test_to_lines_silicon():
    """Test generating silicon line."""
    element_info = ElementInfo(element="Si", atomic_weight=27.976928, min_energy=300000.0, max_energy=1800000.0)

    lines = Card02.to_lines(element_info)

    assert len(lines) == 1
    assert lines[0].startswith("Si        ")
    assert "27.976928" in lines[0]
    assert "300000.000" in lines[0]
    assert "1800000.0" in lines[0]


def test_to_lines_gold():
    """Test generating gold line."""
    element_info = ElementInfo(element="Au197", atomic_weight=196.96657, min_energy=0.001, max_energy=1000.0)

    lines = Card02.to_lines(element_info)

    assert len(lines) == 1
    assert lines[0].startswith("Au197     ")
    assert "196.966570" in lines[0]
    assert "0.001" in lines[0]
    assert "1000.0" in lines[0]


def test_roundtrip_silicon(silicon_line):
    """Test parse and regenerate produces consistent result."""
    element_info = Card02.from_lines(silicon_line)
    regenerated_lines = Card02.to_lines(element_info)

    reparsed_info = Card02.from_lines(regenerated_lines)

    assert reparsed_info.element == element_info.element
    assert pytest.approx(reparsed_info.atomic_weight, rel=1e-5) == element_info.atomic_weight
    assert pytest.approx(reparsed_info.min_energy, rel=1e-3) == element_info.min_energy
    assert pytest.approx(reparsed_info.max_energy, rel=1e-3) == element_info.max_energy


def test_element_info_validation_max_less_than_min():
    """Test that max_energy must be greater than min_energy."""
    with pytest.raises(ValueError, match="max_energy.*must be greater than min_energy"):
        ElementInfo(element="H", atomic_weight=1.0, min_energy=1000.0, max_energy=100.0)


def test_element_info_validation_negative_weight():
    """Test that atomic_weight must be positive."""
    with pytest.raises(ValueError):
        ElementInfo(element="H", atomic_weight=-1.0, min_energy=0.001, max_energy=100.0)


def test_element_info_validation_negative_min_energy():
    """Test that min_energy must be non-negative."""
    with pytest.raises(ValueError):
        ElementInfo(element="H", atomic_weight=1.0, min_energy=-1.0, max_energy=100.0)


def test_to_lines_invalid_input():
    """Test that to_lines rejects non-ElementInfo input."""
    with pytest.raises(ValueError, match="element_info must be an instance of ElementInfo"):
        Card02.to_lines("not an ElementInfo object")


def test_element_name_length():
    """Test that element name is properly left-aligned in 10-char field."""
    element_info = ElementInfo(element="X", atomic_weight=1.0, min_energy=1.0, max_energy=10.0)

    lines = Card02.to_lines(element_info)

    assert len(lines[0]) >= 40
    assert lines[0][:10] == "X         "
