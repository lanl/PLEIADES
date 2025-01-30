#!/usr/bin/env python
"""Unit tests for Card Set 11 (Miscellaneous Parameters) parsing."""

import pytest

from pleiades.sammy.parameters.helper import VaryFlag
from pleiades.sammy.parameters.misc import (
    DeltaParameters,
    EtaParameters,
)


class TestDeltaParameters:
    """Test suite for DELTA parameter parsing and formatting."""

    @pytest.fixture
    def valid_delta_line(self):
        """Sample valid DELTA parameter line."""
        return "DELTA 1 0 1.234E+00 2.345E-03 3.456E+00 4.567E-03"

    @pytest.fixture
    def valid_delta_params(self):
        """Sample valid DELTA parameters."""
        return DeltaParameters(
            l1_coefficient=1.234,
            l1_uncertainty=2.345e-3,
            l0_constant=3.456,
            l0_uncertainty=4.567e-3,
            l1_flag=VaryFlag.YES,
            l0_flag=VaryFlag.NO,
        )

    def test_parse_valid_line(self, valid_delta_line):
        """Test parsing of valid DELTA parameter line."""
        # check col number for each char
        for i, char in enumerate(valid_delta_line):
            print(f"{i}: {char}")

        params = DeltaParameters.from_lines([valid_delta_line])
        assert params.l1_coefficient == pytest.approx(1.234)
        assert params.l1_uncertainty == pytest.approx(2.345e-3)
        assert params.l0_constant == pytest.approx(3.456)
        assert params.l0_uncertainty == pytest.approx(4.567e-3)
        assert params.l1_flag == VaryFlag.YES
        assert params.l0_flag == VaryFlag.NO

    def test_round_trip(self, valid_delta_params):
        """Test round-trip parsing and formatting of DELTA parameters."""
        lines = valid_delta_params.to_lines()
        assert len(lines) == 1

        params = DeltaParameters.from_lines(lines)
        assert params == valid_delta_params

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "WRONG 1 0  1.234E+00  2.345E-03  3.456E+00  4.567E-03",  # Wrong identifier
            "DELTA x 0  1.234E+00  2.345E-03  3.456E+00  4.567E-03",  # Invalid flag
            "DELTA 1 0  invalid     2.345E-03  3.456E+00  4.567E-03",  # Invalid number
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid DELTA parameter lines."""
        with pytest.raises(ValueError):
            DeltaParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that required values must be provided."""
        with pytest.raises(ValueError):
            DeltaParameters(
                l1_coefficient=None,  # Required
                l0_constant=3.456,
            )


class TestEtaParameters:
    """Test suite for ETA parameter parsing and formatting.

    ETA parameters define normalization coefficients and have format:
    1-5     A       "ETA "      Parameter identifier ("eta" + 2 spaces)
    7       I       IFLAGN      Flag for parameter ν
    11-20   F       NU          Normalization coefficient ν
    21-30   F       DNU         Uncertainty on NU
    31-40   F       ENU         Energy for which this value applies (eV)
    """

    @pytest.fixture
    def valid_eta_line(self):
        """Sample valid ETA parameter line."""
        return "ETA   1    1.234E+00 2.345E-03 5.678E+01"
        #       |     |    |         |         |
        #       |     |    |         |         31-40: Energy (eV)
        #       |     |    |         21-30: Uncertainty
        #       |     |    11-20: Nu value
        #       |     7: Flag
        #       1-5: "ETA "

    @pytest.fixture
    def valid_eta_params(self):
        """Sample valid ETA parameters."""
        return EtaParameters(nu_value=1.234, nu_uncertainty=2.345e-3, energy=56.78, flag=VaryFlag.YES)

    def test_parse_valid_line(self, valid_eta_line):
        """Test parsing of valid ETA parameter line."""
        # check col number for each char
        for i, char in enumerate(valid_eta_line):
            print(f"{i+1}: {char}")

        params = EtaParameters.from_lines([valid_eta_line])
        assert params.nu_value == pytest.approx(1.234)
        assert params.nu_uncertainty == pytest.approx(2.345e-3)
        assert params.energy == pytest.approx(56.78)
        assert params.flag == VaryFlag.YES

    def test_round_trip(self, valid_eta_params):
        """Test round-trip parsing and formatting of ETA parameters."""
        lines = valid_eta_params.to_lines()
        assert len(lines) == 1
        params = EtaParameters.from_lines(lines)
        assert params == valid_eta_params

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "ETA   x    1.234E+00 2.345E-03 5.678E+01",  # Invalid flag
            "ETA   1    invalid   2.345E-03 5.678E+01",  # Invalid nu value
            "ETAX  1    1.234E+00 2.345E-03 5.678E+01",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid ETA parameter lines."""
        with pytest.raises(ValueError):
            EtaParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that required values must be provided."""
        with pytest.raises(ValueError):
            EtaParameters(
                nu_value=None,  # Required
                energy=56.78,
            )

    def test_energy_optional(self):
        """Test that energy value is optional."""
        line = "ETA   1    1.234E+00 2.345E-03"  # No energy value
        params = EtaParameters.from_lines([line])
        assert params.energy is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
