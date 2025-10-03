import pytest

from pleiades.sammy.parameters.data_reduction import DataReductionCard, DataReductionParameter
from pleiades.utils.helper import VaryFlag


def test_parameter_parsing():
    """Test parsing single parameter line."""
    line = "PAR1  1   1.234E+00 5.000E-02 1.234E+00"
    param = DataReductionParameter.from_line(line)

    assert param.name == "PAR1"
    assert param.flag == VaryFlag.YES
    assert pytest.approx(param.value) == 1.234
    assert pytest.approx(param.uncertainty) == 0.05
    assert pytest.approx(param.derivative_value) == 1.234


def test_parameter_optional_fields():
    """Test parsing parameter with missing optional fields."""
    line = "PAR1  1   1.234E+00"
    param = DataReductionParameter.from_line(line)

    assert param.name == "PAR1"
    assert param.flag == VaryFlag.YES
    assert pytest.approx(param.value) == 1.234
    assert param.uncertainty is None
    assert param.derivative_value is None


def test_parameter_formatting():
    """Test parameter line formatting."""
    param = DataReductionParameter(
        name="PAR1", value=1.234, flag=VaryFlag.YES, uncertainty=0.05, derivative_value=1.234
    )
    line = param.to_line()

    # Parse back to verify format
    parsed = DataReductionParameter.from_line(line)
    assert parsed.name == param.name
    assert parsed.flag == param.flag
    assert pytest.approx(parsed.value) == param.value
    assert pytest.approx(parsed.uncertainty) == param.uncertainty
    assert pytest.approx(parsed.derivative_value) == param.derivative_value


def test_card_parsing():
    """Test parsing complete card set."""
    lines = [
        "DATA reduction parameters are next",
        "PAR1  1   1.234E+00 5.000E-02 1.234E+00",
        "PAR2  0   2.345E+00 1.000E-02",
        "PAR3  3   3.456E+00",
        "",
    ]

    card = DataReductionCard.from_lines(lines)
    assert len(card.parameters) == 3

    # Check first parameter
    assert card.parameters[0].name == "PAR1"
    assert card.parameters[0].flag == VaryFlag.YES
    assert pytest.approx(card.parameters[0].value) == 1.234

    # Check PUP parameter
    assert card.parameters[2].name == "PAR3"
    assert card.parameters[2].flag == VaryFlag.PUP
    assert pytest.approx(card.parameters[2].value) == 3.456


def test_card_formatting():
    """Test card set formatting."""
    params = [
        DataReductionParameter(name="PAR1", value=1.234, flag=VaryFlag.YES, uncertainty=0.05, derivative_value=1.234),
        DataReductionParameter(name="PAR2", value=2.345, flag=VaryFlag.NO, uncertainty=0.01),
        DataReductionParameter(name="PAR3", value=3.456, flag=VaryFlag.PUP),
    ]
    card = DataReductionCard(parameters=params)
    lines = card.to_lines()

    # Parse back to verify format
    parsed = DataReductionCard.from_lines(lines)
    assert len(parsed.parameters) == len(card.parameters)
    for orig, new in zip(card.parameters, parsed.parameters):
        assert new.name == orig.name
        assert new.flag == orig.flag
        assert pytest.approx(new.value) == orig.value
        if orig.uncertainty is not None:
            assert pytest.approx(new.uncertainty) == orig.uncertainty
        if orig.derivative_value is not None:
            assert pytest.approx(new.derivative_value) == orig.derivative_value


def test_invalid_parameter():
    """Test error handling for invalid parameter lines."""
    with pytest.raises(ValueError):
        DataReductionParameter.from_line("")  # Empty line

    with pytest.raises(ValueError):
        DataReductionParameter.from_line("PAR1  X invalid")  # Invalid value

    with pytest.raises(ValueError):
        DataReductionParameter(name="TOOLONG", value=1.0)  # Name too long


def test_invalid_card():
    """Test error handling for invalid card sets."""
    with pytest.raises(ValueError):
        DataReductionCard.from_lines([])  # Empty lines

    with pytest.raises(ValueError):
        DataReductionCard.from_lines(["WRONG HEADER"])  # Invalid header

    with pytest.raises(ValueError):
        DataReductionCard.from_lines(["DATA reduction parameters are next", ""])  # No parameters


if __name__ == "__main__":
    pytest.main(["-v", __file__])
