#!/usr/bin/env python
"""Unit tests for isotope parameter handling (Card Set 10)."""

import pytest

from pleiades.utils.helper import VaryFlag
from pleiades.sammy.parameters.isotope import IsotopeCard, IsotopeParameters


# Test fixtures for common test data
@pytest.fixture
def single_isotope_lines():
    return ["ISOTOpic abundances and masses", "16.000    0.99835   0.00002    0  1  2  3", ""]


@pytest.fixture
def multi_isotope_lines():
    return ["ISOTOpic abundances and masses", "16.000    0.99835   0.00002    0  1  2  3", "17.000    0.00165   0.00001    0  4  5  6", ""]


@pytest.fixture
def continuation_lines():
    return [
        "ISOTOpic abundances and masses",
        "16.000    0.99835   0.00002    0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21-1",
        "22 23 24 25",
        "",
    ]


@pytest.fixture
def extended_format_lines():
    return [
        "ISOTOpic abundances and masses",
        "16.000    0.99835   0.00002       0  101  102  103  104  105  106  107  108   -1",
        "  110  111  112",
        "",
    ]


class TestIsotopeParameters:
    """Test suite for IsotopeParameters class."""

    def test_basic_validation(self):
        """Test basic parameter validation."""
        # Test valid parameters
        params = IsotopeParameters(mass=16.0, abundance=0.99835, uncertainty=0.00002, flag=VaryFlag.NO, spin_groups=[1, 2, 3])
        assert params.mass == 16.0
        assert params.abundance == 0.99835
        assert params.uncertainty == 0.00002
        assert params.flag == VaryFlag.NO
        assert params.spin_groups == [1, 2, 3]

        # Test invalid mass
        with pytest.raises(ValueError, match="Input should be greater than 0"):
            IsotopeParameters(mass=-1.0, abundance=0.5)

        # Test invalid abundance
        with pytest.raises(ValueError, match="Input should be less than or equal to 1"):
            IsotopeParameters(mass=16.0, abundance=1.5)

        # Test invalid spin group
        with pytest.raises(ValueError, match="Spin group number cannot be 0"):
            IsotopeParameters(mass=16.0, abundance=0.5, spin_groups=[0])

    def test_from_lines_standard_format(self):
        """Test parsing standard format lines."""
        lines = ["16.000    0.99835   0.00002    0  1  2  3"]
        params = IsotopeParameters.from_lines(lines)

        assert params.mass == 16.0
        assert params.abundance == 0.99835
        assert params.uncertainty == 0.00002
        assert params.flag == VaryFlag.NO
        assert params.spin_groups == [1, 2, 3]

    def test_from_lines_with_continuation(self):
        """Test parsing lines with continuation."""
        lines = ["16.000    0.99835   0.00002   0 1 2 3 4 5 6 7 8 9 1011121314151617181920212223-1", "24   25   26   27"]
        params = IsotopeParameters.from_lines(lines)
        print(params)
        assert params.spin_groups == list(range(1, 28))  # Numbers 1-27

    def test_to_lines_formatting(self):
        """Test output formatting."""
        params = IsotopeParameters(mass=16.0, abundance=0.99835, uncertainty=0.00002, flag=VaryFlag.NO, spin_groups=[1, 2, 3])
        lines = params.to_lines()
        assert len(lines) == 1
        assert lines[0].startswith("1.6000E+019.9835E-012.0000E-05 0 1 2 3")


class TestIsotopeCard:
    """Test suite for IsotopeCard class."""

    def test_header_validation(self):
        """Test header line validation."""
        assert IsotopeCard.is_header_line("ISOTOpic abundances and masses")
        assert IsotopeCard.is_header_line("NUCLIde abundances and masses")
        assert not IsotopeCard.is_header_line("Wrong header")

    def test_single_isotope(self, single_isotope_lines):
        """Test parsing single isotope data."""
        card = IsotopeCard.from_lines(single_isotope_lines)
        assert len(card.isotopes) == 1
        assert card.isotopes[0].mass == 16.0
        assert card.isotopes[0].abundance == 0.99835

    def test_multiple_isotopes(self, multi_isotope_lines):
        """Test parsing multiple isotope data."""
        card = IsotopeCard.from_lines(multi_isotope_lines)
        assert len(card.isotopes) == 2
        assert sum(iso.abundance for iso in card.isotopes) <= 1.0

    def test_roundtrip(self, single_isotope_lines):
        """Test parsing and re-generating gives equivalent results."""
        card = IsotopeCard.from_lines(single_isotope_lines)
        output_lines = card.to_lines()
        card2 = IsotopeCard.from_lines(output_lines)

        assert len(card.isotopes) == len(card2.isotopes)
        assert card.isotopes[0].mass == card2.isotopes[0].mass
        assert card.isotopes[0].abundance == card2.isotopes[0].abundance

    @pytest.mark.parametrize(
        "bad_lines,error_pattern",
        [
            (["Wrong header", "16.000 0.5"], "Invalid header"),
            ([], "No lines provided"),
            (["ISOTOpic abundances and masses"], "No parameter lines found"),
        ],
    )
    def test_error_handling(self, bad_lines, error_pattern):
        """Test error handling for various invalid inputs."""
        with pytest.raises(ValueError, match=error_pattern):
            IsotopeCard.from_lines(bad_lines)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
