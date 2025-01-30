#!/usr/bin/env python
"""Unit tests for Card Set 11 (Miscellaneous Parameters) parsing."""

import pytest

from pleiades.sammy.parameters.helper import VaryFlag
from pleiades.sammy.parameters.misc import (
    DeltaParameters,
    EtaParameters,
    FinitParameters,
    GammaParameters,
    TzeroParameters,
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


class TestFinitParameters:
    """Test suite for FINIT parameter parsing and formatting.

    FINIT parameters specify finite-size corrections for angular distributions:
    Cols  Format  Variable    Description
    1-5   A       "FINIT"     Parameter identifier
    7     I       IFLAGI      Flag for ATTNI
    9     I       IFLAGO      Flag for ATTNO
    11-20  F       ATTNI       Incident-particle attenuation (atoms/barn)
    21-30  F       DTTNI       Uncertainty on ATTNI
    31-40  F       ATTNO       Exit-particle attenuation (atom/b)
    41-50  F       DTTNO       Uncertainty on ATTNO

    Notes:
    - Repeat once for each angle
    - If only one line, same attenuations used for all angles
    """

    @pytest.fixture
    def valid_finit_line(self):
        """Sample valid FINIT parameter line."""
        return "FINIT 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03"
        #       |     | | |         |         |         |
        #       |     | | |         |         |         41-50: DTTNO uncertainty
        #       |     | | |         |         31-40: ATTNO exit attenuation
        #       |     | | |         21-30: DTTNI uncertainty
        #       |     | | 11-20: ATTNI incident attenuation
        #       |     | 9: ATTNO flag
        #       |     7: ATTNI flag
        #       1-5: "FINIT"

    @pytest.fixture
    def valid_finit_params(self):
        """Sample valid FINIT parameters."""
        return FinitParameters(
            incident_attenuation=1.234,
            incident_uncertainty=2.345e-3,
            exit_attenuation=3.456,
            exit_uncertainty=4.567e-3,
            incident_flag=VaryFlag.YES,
            exit_flag=VaryFlag.YES,
        )

    def test_parse_valid_line(self, valid_finit_line):
        """Test parsing of valid FINIT parameter line."""
        # check col number for each char
        for i, char in enumerate(valid_finit_line):
            print(f"{i+1}: {char}")

        params = FinitParameters.from_lines([valid_finit_line])
        assert params.incident_attenuation == pytest.approx(1.234)
        assert params.incident_uncertainty == pytest.approx(2.345e-3)
        assert params.exit_attenuation == pytest.approx(3.456)
        assert params.exit_uncertainty == pytest.approx(4.567e-3)
        assert params.incident_flag == VaryFlag.YES
        assert params.exit_flag == VaryFlag.YES

    def test_round_trip(self, valid_finit_params):
        """Test round-trip parsing and formatting of FINIT parameters."""
        lines = valid_finit_params.to_lines()
        assert len(lines) == 1
        params = FinitParameters.from_lines(lines)
        assert params == valid_finit_params

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "FINIT x 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03",  # Invalid incident flag
            "FINIT 1 x 1.234E+00 2.345E-03 3.456E+00 4.567E-03",  # Invalid exit flag
            "FINIT 1 1 invalid   2.345E-03 3.456E+00 4.567E-03",  # Invalid incident attenuation
            "FINIT 1 1 1.234E+00 2.345E-03 invalid   4.567E-03",  # Invalid exit attenuation
            "FINIX 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid FINIT parameter lines."""
        with pytest.raises(ValueError):
            FinitParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that required values must be provided."""
        with pytest.raises(ValueError):
            FinitParameters(
                incident_attenuation=None,  # Required
                exit_attenuation=3.456,
                incident_flag=VaryFlag.YES,
                exit_flag=VaryFlag.YES,
            )


class TestGammaParameters:
    """Test suite for GAMMA parameter parsing and formatting.

    GAMMA parameters specify radiation width for spin groups:
    Cols  Format  Variable    Description
    1-5   A       "GAMMA"     Parameter identifier
    6-7   I       IG          Spin group number
    8-9   I       IFG         Flag for GAMGAM (0=fixed, 1=vary, 3=PUP)
    11-20  F       GAMGAM      Radiation width Γγ for all resonances in spin group
    21-30  F       DGAM        Uncertainty on GAMGAM

    Notes:
    - If used for any spin group, must be given for every spin group
    """

    @pytest.fixture
    def valid_gamma_line(self):
        """Sample valid GAMMA parameter line."""
        return "GAMMA 1 1 1.234E+00 2.345E-03"
        #       |     | | |         |
        #       |     | | |         21-30: Uncertainty
        #       |     | | 11-20: Width value
        #       |     | 8-9: Flag
        #       |     6-7: Spin group
        #       1-5: "GAMMA"

    @pytest.fixture
    def valid_gamma_params(self):
        """Sample valid GAMMA parameters."""
        return GammaParameters(spin_group=1, width=1.234, uncertainty=2.345e-3, flag=VaryFlag.YES)

    def test_parse_valid_line(self, valid_gamma_line):
        """Test parsing of valid GAMMA parameter line."""
        # check col number for each char
        for i, char in enumerate(valid_gamma_line):
            print(f"{i+1}: {char}")

        params = GammaParameters.from_lines([valid_gamma_line])
        assert params.spin_group == 1
        assert params.width == pytest.approx(1.234)
        assert params.uncertainty == pytest.approx(2.345e-3)
        assert params.flag == VaryFlag.YES

    def test_round_trip(self, valid_gamma_params):
        """Test round-trip parsing and formatting of GAMMA parameters."""
        lines = valid_gamma_params.to_lines()
        assert len(lines) == 1
        params = GammaParameters.from_lines(lines)
        assert params == valid_gamma_params

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "GAMMA x 1 1.234E+00 2.345E-03",  # Invalid spin group
            "GAMMA 1 x 1.234E+00 2.345E-03",  # Invalid flag
            "GAMMA 1 1 invalid   2.345E-03",  # Invalid width
            "GAMMX 1 1 1.234E+00 2.345E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid GAMMA parameter lines."""
        with pytest.raises(ValueError):
            GammaParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that required values must be provided."""
        with pytest.raises(ValueError):
            GammaParameters(
                spin_group=1,
                width=None,  # Required
                flag=VaryFlag.YES,
            )

    def test_spin_group_range(self):
        """Test spin group number validation."""
        with pytest.raises(ValueError, match="Input should be greater than 0"):
            GammaParameters(
                spin_group=0,  # Invalid
                width=1.234,
                flag=VaryFlag.YES,
            )


class TestTzeroParameters:
    """Test suite for TZERO parameter parsing and formatting.

    TZERO parameters specify time offset and flight path parameters:
    Cols  Format  Variable    Description
    1-5   A       "TZERO"     Parameter identifier
    7     I       IFTZER      Flag for t₀
    9     I       IFLZER      Flag for L₀
    11-20 F       TZERO       t₀ (μs)
    21-30 F       DTZERO      Uncertainty on t₀ (μs)
    31-40 F       LZERO       L₀ (dimensionless)
    41-50 F       DLZERO      Uncertainty on L₀
    51-60 F       FPL         Flight-path length (m)
    """

    @pytest.fixture
    def valid_tzero_line(self):
        """Sample valid TZERO parameter line."""
        return "TZERO 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+01"
        #       |     | | |         |         |         |         |
        #       |     | | |         |         |         |         51-60: Flight-path length
        #       |     | | |         |         |         41-50: L₀ uncertainty
        #       |     | | |         |         31-40: L₀ value
        #       |     | | |         21-30: t₀ uncertainty
        #       |     | | 11-20: t₀ value
        #       |     | 9: L₀ flag
        #       |     7: t₀ flag
        #       1-5: "TZERO"

    @pytest.fixture
    def valid_tzero_params(self):
        """Sample valid TZERO parameters."""
        return TzeroParameters(
            t0_value=1.234,
            t0_uncertainty=2.345e-3,
            l0_value=3.456,
            l0_uncertainty=4.567e-3,
            flight_path_length=56.78,
            t0_flag=VaryFlag.YES,
            l0_flag=VaryFlag.YES,
        )

    def test_parse_valid_line(self, valid_tzero_line):
        """Test parsing of valid TZERO parameter line."""
        # Check column number for each char
        for i, char in enumerate(valid_tzero_line):
            print(f"{i+1}: {char}")

        params = TzeroParameters.from_lines([valid_tzero_line])
        assert params.t0_value == pytest.approx(1.234)
        assert params.t0_uncertainty == pytest.approx(2.345e-3)
        assert params.l0_value == pytest.approx(3.456)
        assert params.l0_uncertainty == pytest.approx(4.567e-3)
        assert params.flight_path_length == pytest.approx(56.78)
        assert params.t0_flag == VaryFlag.YES
        assert params.l0_flag == VaryFlag.YES

    def test_round_trip(self, valid_tzero_params):
        """Test round-trip parsing and formatting of TZERO parameters."""
        lines = valid_tzero_params.to_lines()
        assert len(lines) == 1
        params = TzeroParameters.from_lines(lines)
        assert params == valid_tzero_params

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "TZERO x 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+01",  # Invalid t₀ flag
            "TZERO 1 x 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+01",  # Invalid L₀ flag
            "TZERO 1 1 invalid   2.345E-03 3.456E+00 4.567E-03 5.678E+01",  # Invalid t₀ value
            "TZERO 1 1 1.234E+00 2.345E-03 invalid   4.567E-03 5.678E+01",  # Invalid L₀ value
            "TZERX 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+01",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid TZERO parameter lines."""
        with pytest.raises(ValueError):
            TzeroParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that required values must be provided."""
        with pytest.raises(ValueError):
            TzeroParameters(
                t0_value=None,  # Required
                l0_value=3.456,
                t0_flag=VaryFlag.YES,
                l0_flag=VaryFlag.YES,
            )

        with pytest.raises(ValueError):
            TzeroParameters(
                t0_value=1.234,
                l0_value=None,  # Required
                t0_flag=VaryFlag.YES,
                l0_flag=VaryFlag.YES,
            )

    def test_flight_path_optional(self):
        """Test that flight path length is optional."""
        line = "TZERO 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03"  # No flight path
        params = TzeroParameters.from_lines([line])
        assert params.flight_path_length is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
