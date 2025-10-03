#!/usr/bin/env python
"""Unit tests for isotope parameter handling (Card Set 10)."""

import pytest

from pleiades.nuclear.models import IsotopeParameters
from pleiades.sammy.io.card_formats.par10_isotopes import Card10
from pleiades.utils.helper import VaryFlag


# Test fixtures for common test data
@pytest.fixture
def single_isotope_lines():
    return ["ISOTOpic abundances and masses", " 16.000000 0.9983500  .0000200 0 1 2 3", ""]


@pytest.fixture
def multi_isotope_lines():
    return [
        "ISOTOpic abundances and masses",
        " 16.000000 0.9983500  .0000200 0 1 2 3",
        " 17.000000 0.0016500  .0000100 0 4 5 6",
        "",
    ]


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
        # Test valid parameters using correct API
        params = IsotopeParameters(abundance=0.99835, uncertainty=0.00002, vary_abundance=VaryFlag.NO)
        assert params.abundance == 0.99835
        assert params.uncertainty == 0.00002
        assert params.vary_abundance == VaryFlag.NO
        assert params.spin_groups == []  # Default empty list

    def test_from_lines_standard_format(self):
        """Test parsing standard format lines - method not implemented yet."""
        # This test is for future implementation of parsing functionality
        # Currently IsotopeParameters doesn't have from_lines method
        # TODO: Implement from_lines parsing method
        pass

    def test_from_lines_with_continuation(self):
        """Test parsing lines with continuation - method not implemented yet."""
        # TODO: Implement parsing with continuation lines
        pass

    def test_to_lines_formatting(self):
        """Test output formatting - method not implemented yet."""
        # TODO: Implement to_lines formatting method
        pass


class TestIsotopeCard:
    """Test suite for IsotopeCard class."""

    def test_header_validation(self):
        """Test header line validation."""
        assert Card10.is_header_line("ISOTOpic abundances and masses")
        assert Card10.is_header_line("NUCLIde abundances and masses")
        assert not Card10.is_header_line("Wrong header")

    def test_single_isotope(self, single_isotope_lines):
        """Test parsing single isotope data."""
        from pleiades.sammy.fitting.config import FitConfig

        fit_config = FitConfig()
        Card10.from_lines(single_isotope_lines, fit_config)

        # Check that isotope was added to fit_config
        assert len(fit_config.nuclear_params.isotopes) == 1
        isotope = fit_config.nuclear_params.isotopes[0]
        assert isotope.abundance == 0.9983500

    def test_multiple_isotopes(self, multi_isotope_lines):
        """Test parsing multiple isotope data."""
        from pleiades.sammy.fitting.config import FitConfig

        fit_config = FitConfig()
        Card10.from_lines(multi_isotope_lines, fit_config)

        assert len(fit_config.nuclear_params.isotopes) == 2
        total_abundance = sum(iso.abundance for iso in fit_config.nuclear_params.isotopes)
        assert total_abundance <= 1.0

    def test_roundtrip(self, single_isotope_lines):
        """Test parsing and re-generating gives equivalent results."""
        from pleiades.sammy.fitting.config import FitConfig

        # Parse original
        fit_config1 = FitConfig()
        Card10.from_lines(single_isotope_lines, fit_config1)

        # Generate lines
        output_lines = Card10.to_lines(fit_config1)

        # Parse again
        fit_config2 = FitConfig()
        Card10.from_lines(output_lines, fit_config2)

        # Compare
        assert len(fit_config1.nuclear_params.isotopes) == len(fit_config2.nuclear_params.isotopes)
        assert fit_config1.nuclear_params.isotopes[0].abundance == fit_config2.nuclear_params.isotopes[0].abundance

    @pytest.mark.parametrize(
        "bad_lines,error_pattern",
        [
            (["Wrong header", "16.000 0.5"], "Invalid header"),
            ([], "No lines provided"),
            (["ISOTOpic abundances and masses"], "No content lines found"),
        ],
    )
    def test_error_handling(self, bad_lines, error_pattern):
        """Test error handling for various invalid inputs."""
        with pytest.raises(ValueError, match=error_pattern):
            Card10.from_lines(bad_lines)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
