#!/usr/bin/env python
"""Unit tests for card 05::unused but correlated variables."""

import pytest

from pleiades.sammy.parameters.unused_var import UnusedCorrelatedCard, UnusedCorrelatedParameters, UnusedVariable


def test_unused_variable_validation():
    """Test UnusedVariable name formatting and validation."""
    # Test exact 5-char name
    var = UnusedVariable(name="NVAR1", value=1.234)
    assert len(var.name) == 5
    assert var.name == "NVAR1"

    # Test name padding
    var = UnusedVariable(name="NV1", value=1.234)
    assert len(var.name) == 5
    assert var.name == "NV1  "


def test_parameters_parsing():
    """Test parsing of parameter lines with proper fixed-width format."""
    test_lines = [
        (" " * 5).join([f"NVAR{i}" for i in range(1, 4)]),
        "1.2304E+002.9800E+021.5000E-01",
        (" " * 5).join([f"NVAR{i}" for i in range(4, 6)]),
        "2.5000E-021.0000E+00",
    ]

    params = UnusedCorrelatedParameters.from_lines(test_lines)

    # Verify number of variables parsed
    assert len(params.variables) == 5

    # Verify specific values
    assert params.variables[0].name == "NVAR1"
    assert params.variables[0].value == pytest.approx(1.2304)
    assert params.variables[1].name == "NVAR2"
    assert params.variables[1].value == pytest.approx(298.0)


def test_parameters_formatting():
    """Test formatting output with proper fixed-width spacing."""
    variables = [
        UnusedVariable(name="NVAR1", value=1.2304),
        UnusedVariable(name="NVAR2", value=298.0),
        UnusedVariable(name="NVAR3", value=0.15),
    ]

    params = UnusedCorrelatedParameters(variables=variables)
    lines = params.to_lines()

    # Should produce exactly 2 lines (names and values)
    assert len(lines) == 2

    # Verify name line format (5 chars + 5 spaces between)
    expected_name_line = "NVAR1     NVAR2     NVAR3"
    assert lines[0] == expected_name_line

    # Verify value line format (exactly 10 chars each, no spaces)
    expected_value_line = "1.2304E+002.9800E+021.5000E-01"
    assert lines[1] == expected_value_line


def test_full_card_parsing():
    """Test parsing of a complete card including header."""
    card_lines = [
        "UNUSEd but correlated variables come next",
        (" " * 5).join([f"NVAR{i}" for i in range(1, 4)]),
        "1.2304E+002.9800E+021.5000E-01",
        "",
    ]

    card = UnusedCorrelatedCard.from_lines(card_lines)

    # Verify header recognition
    assert UnusedCorrelatedCard.is_header_line(card_lines[0])

    # Verify parameter parsing
    assert len(card.parameters.variables) == 3


def test_error_handling():
    """Test error conditions and validation."""
    # Test invalid header
    with pytest.raises(ValueError, match="Invalid header line"):
        UnusedCorrelatedCard.from_lines(["WRONG header", "NVAR1", "1.2340E+00"])

    # Test missing value line
    with pytest.raises(ValueError, match="At least one pair of name/value lines required"):
        UnusedCorrelatedParameters.from_lines(["NVAR1"])

    # Test empty input
    with pytest.raises(ValueError, match="No lines provided"):
        UnusedCorrelatedCard.from_lines([])


def test_multiple_variable_groups():
    """Test handling of multiple groups of variables (>8 variables)."""
    # Create test data with 10 variables (should span multiple lines)
    names = [f"NVAR{i}" for i in range(1, 11)]
    values = [float(i) for i in range(1, 11)]
    variables = [UnusedVariable(name=name, value=value) for name, value in zip(names, values)]

    params = UnusedCorrelatedParameters(variables=variables)
    lines = params.to_lines()

    # Should produce 4 lines (2 pairs of name/value lines)
    assert len(lines) == 4

    # First group should have 8 variables
    assert len(lines[0].split()) == 8
    # Second group should have 2 variables
    assert len(lines[2].split()) == 2


def test_roundtrip_consistency():
    """Test that parsing and then formatting produces consistent results."""
    original_lines = [(" " * 5).join([f"NVAR{i}" for i in range(1, 4)]), "1.2304E+002.9800E+021.5000E-01"]

    # Parse and then format
    params = UnusedCorrelatedParameters.from_lines(original_lines)
    output_lines = params.to_lines()

    # Parse the output again
    params2 = UnusedCorrelatedParameters.from_lines(output_lines)

    # Compare variables
    assert len(params.variables) == len(params2.variables)
    for var1, var2 in zip(params.variables, params2.variables):
        assert var1.name == var2.name
        assert var1.value == pytest.approx(var2.value)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
