#!/usr/bin/env python
"""Unit tests for Card Set 12 (Paramagnetic Cross Section Parameters) parsing."""

import pytest

from pleiades.sammy.parameters.paramagnetic import NuclideType, ParamagneticParameters
from pleiades.utils.helper import VaryFlag


class TestParamagneticParameters:
    """Test suite for Card Set 12 (Paramagnetic) parameter parsing and formatting.

    Format from Table VI B.2:
    Line 1: Header - "PARAMagnetic cross section parameters follow"

    Line 2: Main parameters
    Cols    Format  Variable    Description
    1-5     A      Nuclide     "TM ", "ER ", "HO " (2 letters + 3 spaces)
    7       I      IFA         Flag to vary A (0=fixed, 1=vary, 3=PUP)
    9       I      IFB         Flag to vary B
    10      I      IFP         Flag to vary P
    11-20   F      A           A parameter value
    21-30   F      dA          Uncertainty on A
    31-40   F      B           B parameter value
    41-50   F      dB          Uncertainty on B
    51-60   F      P           P parameter value
    61-70   F      dP          Uncertainty on P

    Line 3: Additional parameters
    7       I      ISO         Isotope (nuclide) number
    9       I      IFC         Flag to vary C (0=fixed, 1=vary, 3=PUP)
    11-20   F      C           C parameter value
    21-30   F      dC          Uncertainty on C

    Line 4: Blank terminator line
    """

    @pytest.fixture
    def valid_tm_lines(self):
        """Valid parameter set for TM nuclide."""
        return [
            "PARAMagnetic cross section parameters follow",
            "TM    1 111.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",
            "      1 1 1.234E+00 2.345E-03",
            "",
        ]

    @pytest.fixture
    def valid_er_lines(self):
        """Valid parameter set for ER nuclide."""
        return [
            "PARAMagnetic cross section parameters follow",
            "ER    1 112.345E+00 3.456E-03 4.567E+00 5.678E-03 6.789E+00 7.890E-03",
            "      2 1 2.345E+00 3.456E-03",
            "",
        ]

    @pytest.fixture
    def valid_ho_lines(self):
        """Valid parameter set for HO nuclide."""
        return [
            "PARAMagnetic cross section parameters follow",
            "HO    1 113.456E+00 4.567E-03 5.678E+00 6.789E-03 7.890E+00 8.901E-03",
            "      3 1 3.456E+00 4.567E-03",
            "",
        ]

    @pytest.fixture
    def valid_tm_params(self):
        """Valid parameter object for TM nuclide."""
        return ParamagneticParameters(
            nuclide_type=NuclideType.TM,
            a_value=1.234,
            a_uncertainty=2.345e-3,
            b_value=3.456,
            b_uncertainty=4.567e-3,
            p_value=5.678,
            p_uncertainty=6.789e-3,
            a_flag=VaryFlag.YES,
            b_flag=VaryFlag.YES,
            p_flag=VaryFlag.YES,
            isotope_number=1,
            c_value=1.234,
            c_uncertainty=2.345e-3,
            c_flag=VaryFlag.YES,
        )

    def test_parse_valid_tm(self, valid_tm_lines):
        """Test parsing of valid TM parameter set."""
        # Print column positions for debugging
        for i, line in enumerate(valid_tm_lines):
            print(f"\nLine {i + 1}:")
            for j, char in enumerate(line):
                print(f"{j + 1}: {char}")

        params = ParamagneticParameters.from_lines(valid_tm_lines)
        assert params.nuclide_type == NuclideType.TM
        assert params.a_value == pytest.approx(1.234)
        assert params.a_uncertainty == pytest.approx(2.345e-3)
        assert params.b_value == pytest.approx(3.456)
        assert params.b_uncertainty == pytest.approx(4.567e-3)
        assert params.p_value == pytest.approx(5.678)
        assert params.p_uncertainty == pytest.approx(6.789e-3)
        assert params.isotope_number == 1
        assert params.c_value == pytest.approx(1.234)
        assert params.c_uncertainty == pytest.approx(2.345e-3)

    def test_round_trip(self, valid_tm_params):
        """Test round-trip parsing and formatting."""
        lines = valid_tm_params.to_lines()
        assert len(lines) == 4  # Header, main params, iso params, blank
        params = ParamagneticParameters.from_lines(lines)
        assert params == valid_tm_params

    @pytest.mark.parametrize(
        "invalid_lines",
        [
            [],  # Empty
            ["PARAMagnetic cross section parameters follow"],  # Header only
            # Invalid nuclide type
            [
                "PARAMagnetic cross section parameters follow",
                "XX   1 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",
                "     1 1 1.234E+00 2.345E-03",
                "",
            ],
            # Missing header
            [
                "TM   1 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",
                "     1 1 1.234E+00 2.345E-03",
                "",
            ],
            # Missing terminator
            [
                "PARAMagnetic cross section parameters follow",
                "TM   1 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",
                "     1 1 1.234E+00 2.345E-03",
            ],
            # Invalid flags
            [
                "PARAMagnetic cross section parameters follow",
                "TM   x 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",
                "     1 1 1.234E+00 2.345E-03",
                "",
            ],
        ],
    )
    def test_parse_invalid(self, invalid_lines):
        """Test parsing of invalid parameter sets."""
        with pytest.raises(ValueError):
            ParamagneticParameters.from_lines(invalid_lines)

    def test_required_values(self):
        """Test validation of required values."""
        with pytest.raises(ValueError):
            ParamagneticParameters(
                nuclide_type=NuclideType.TM,
                a_value=None,  # Required
                b_value=3.456,
                p_value=5.678,
                isotope_number=1,
                c_value=1.234,
            )

    def test_optional_uncertainties(self):
        """Test that uncertainties are optional."""
        # Lines without uncertainty values
        lines = [
            "PARAMagnetic cross section parameters follow",
            "TM    1 111.234E+00           3.456E+00           5.678E+00",
            "      1 1 1.234E+00",
            "",
        ]
        params = ParamagneticParameters.from_lines(lines)
        assert params.a_uncertainty is None
        assert params.b_uncertainty is None
        assert params.p_uncertainty is None
        assert params.c_uncertainty is None

    def test_isotope_number_validation(self):
        """Test isotope number validation."""
        with pytest.raises(ValueError, match="Input should be greater than 0"):
            ParamagneticParameters(
                nuclide_type=NuclideType.TM,
                a_value=1.234,
                b_value=3.456,
                p_value=5.678,
                isotope_number=0,  # Invalid
                c_value=1.234,
            )


if __name__ == "__main__":
    pytest.main(["-v", __file__])
