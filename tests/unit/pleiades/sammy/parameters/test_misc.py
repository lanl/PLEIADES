#!/usr/bin/env python
"""Unit tests for Card Set 11 (Miscellaneous Parameters) parsing."""

import pytest

from pleiades.sammy.parameters.misc import (
    DeltaParameters,
    DelteParameters,
    DrcapParameters,
    EfficParameters,
    EtaParameters,
    FinitParameters,
    GammaParameters,
    NonunParameters,
    SelfiParameters,
    SiabnParameters,
    TzeroParameters,
)
from pleiades.utils.helper import VaryFlag


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
    7     I       IFTZER      Flag for t
    9     I       IFLZER      Flag for L
    11-20 F       TZERO       t (μs)
    21-30 F       DTZERO      Uncertainty on t (μs)
    31-40 F       LZERO       L (dimensionless)
    41-50 F       DLZERO      Uncertainty on L
    51-60 F       FPL         Flight-path length (m)
    """

    @pytest.fixture
    def valid_tzero_line(self):
        """Sample valid TZERO parameter line."""
        return "TZERO 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+01"
        #       |     | | |         |         |         |         |
        #       |     | | |         |         |         |         51-60: Flight-path length
        #       |     | | |         |         |         41-50: L uncertainty
        #       |     | | |         |         31-40: L value
        #       |     | | |         21-30: t uncertainty
        #       |     | | 11-20: t value
        #       |     | 9: L flag
        #       |     7: t flag
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
            "TZERO x 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+01",  # Invalid t flag
            "TZERO 1 x 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+01",  # Invalid L flag
            "TZERO 1 1 invalid   2.345E-03 3.456E+00 4.567E-03 5.678E+01",  # Invalid t value
            "TZERO 1 1 1.234E+00 2.345E-03 invalid   4.567E-03 5.678E+01",  # Invalid L value
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


class TestSiabnParameters:
    """Test suite for SIABN parameter parsing and formatting.

    SIABN parameters specify abundances for self-indication transmission sample:
    Cols  Format  Variable    Description
    1-5   A       "SIABN"     Parameter identifier
    7     I       IF1         Flag for SIABN(1)
    9     I       IF2         Flag for SIABN(2)
    10    I       IF3         Flag for SIABN(3)
    11-20 F       SIABN(1)    Abundance for nuclide #1
    21-30 F       DS(1)       Uncertainty on SIABN(1)
    31-40 F       SIABN(2)    Abundance for nuclide #2
    41-50 F       DS(2)       Uncertainty on SIABN(2)
    51-60 F       SIABN(3)    Abundance for nuclide #3
    61-70 F       DS(3)       Uncertainty on SIABN(3)

    Notes:
    - Repeat lines until all nuclides have been included
    - Nuclides must be defined in card set 10 before card set 11
    """

    @pytest.fixture
    def valid_siabn_line(self):
        """Sample valid SIABN parameter line."""
        return "SIABN 1 111.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03"
        #       |     | |||         |         |         |         |         |
        #       |     | |||         |         |         |         |         61-70: Uncertainty 3
        #       |     | |||         |         |         |         51-60: Abundance 3
        #       |     | |||         |         |         41-50: Uncertainty 2
        #       |     | |||         |         31-40: Abundance 2
        #       |     | |||         21-30: Uncertainty 1
        #       |     | ||11-20: Abundance 1
        #       |     | |10: Flag 3
        #       |     | 9: Flag 2
        #       |     7: Flag 1
        #       1-5: "SIABN"

    @pytest.fixture
    def valid_siabn_params(self):
        """Sample valid SIABN parameters."""
        return SiabnParameters(
            abundances=[1.234, 3.456, 5.678], uncertainties=[2.345e-3, 4.567e-3, 6.789e-3], flags=[VaryFlag.YES, VaryFlag.YES, VaryFlag.YES]
        )

    def test_parse_valid_line(self, valid_siabn_line):
        """Test parsing of valid SIABN parameter line."""
        # Check column number for each char
        for i, char in enumerate(valid_siabn_line):
            print(f"{i+1}: {char}")

        params = SiabnParameters.from_lines([valid_siabn_line])
        assert params.abundances[0] == pytest.approx(1.234)
        assert params.abundances[1] == pytest.approx(3.456)
        assert params.abundances[2] == pytest.approx(5.678)
        assert params.uncertainties[0] == pytest.approx(2.345e-3)
        assert params.uncertainties[1] == pytest.approx(4.567e-3)
        assert params.uncertainties[2] == pytest.approx(6.789e-3)
        assert params.flags[0] == VaryFlag.YES
        assert params.flags[1] == VaryFlag.YES
        assert params.flags[2] == VaryFlag.YES

    def test_round_trip(self, valid_siabn_params):
        """Test round-trip parsing and formatting of SIABN parameters."""
        lines = valid_siabn_params.to_lines()
        assert len(lines) == 1

        for i, char in enumerate(lines[0]):
            print(f"{i+1}: {char}")

        params = SiabnParameters.from_lines(lines)
        assert params == valid_siabn_params

    def test_partial_data(self):
        """Test parsing with only some abundances present."""
        # Line with only 2 abundances
        line = "SIABN 1 101.234E+00 2.345E-03 3.456E+00 4.567E-03"
        params = SiabnParameters.from_lines([line])
        assert len(params.abundances) == 2
        assert len(params.uncertainties) == 2
        assert len(params.flags) == 2

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "SIABN x 111.234E+00 2.345E-03 3.456E+00 4.567E-03",  # Invalid flag 1
            "SIABN 1 x11.234E+00 2.345E-03 3.456E+00 4.567E-03",  # Invalid flag 2
            "SIABN 1 1x1.234E+00 2.345E-03 3.456E+00 4.567E-03",  # Invalid flag 3
            "SIABN 1 11invalid   2.345E-03 3.456E+00 4.567E-03",  # Invalid abundance 1
            "SIABX 1 111.234E+00 2.345E-03 3.456E+00 4.567E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid SIABN parameter lines."""
        with pytest.raises(ValueError):
            SiabnParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that at least one abundance set must be provided."""
        with pytest.raises(ValueError):
            SiabnParameters(abundances=[], uncertainties=[], flags=[])

        # Test that abundances and flags must match in length
        with pytest.raises(ValueError):
            SiabnParameters(
                abundances=[1.234, 3.456],
                uncertainties=[2.345e-3, 4.567e-3],
                flags=[VaryFlag.YES],  # Only one flag for two abundances
            )


class TestSelfiParameters:
    """Test suite for SELFI parameter parsing and formatting.

    SELFI parameters specify temperature and thickness for self-indication transmission:
    Cols  Format  Variable    Description
    1-5   A       "SELFI"     Parameter identifier
    7     I       IFTEMP      Flag for temperature
    9     I       IFTHCK      Flag for thickness
    11-20 F       SITEM       Effective temperature (K)
    21-30 F       dSITEM      Uncertainty on SITEM
    31-40 F       SITHC       Thickness (atoms/barn)
    41-50 F       dSITHC      Uncertainty on SITHC
    """

    @pytest.fixture
    def valid_selfi_line(self):
        """Sample valid SELFI parameter line."""
        return "SELFI 1 1 1.234E+02 2.345E-03 3.456E-01 4.567E-03"
        #       |     | | |         |         |         |
        #       |     | | |         |         |         41-50: Thickness uncertainty
        #       |     | | |         |         31-40: Thickness
        #       |     | | |         21-30: Temperature uncertainty
        #       |     | | 11-20: Temperature
        #       |     | 9: Thickness flag
        #       |     7: Temperature flag
        #       1-5: "SELFI"

    @pytest.fixture
    def valid_selfi_params(self):
        """Sample valid SELFI parameters."""
        return SelfiParameters(
            temperature=123.4,
            temperature_uncertainty=2.345e-3,
            thickness=0.3456,
            thickness_uncertainty=4.567e-3,
            temperature_flag=VaryFlag.YES,
            thickness_flag=VaryFlag.YES,
        )

    def test_parse_valid_line(self, valid_selfi_line):
        """Test parsing of valid SELFI parameter line."""
        # Check column number for each char
        for i, char in enumerate(valid_selfi_line):
            print(f"{i+1}: {char}")

        params = SelfiParameters.from_lines([valid_selfi_line])
        assert params.temperature == pytest.approx(123.4)
        assert params.temperature_uncertainty == pytest.approx(2.345e-3)
        assert params.thickness == pytest.approx(0.3456)
        assert params.thickness_uncertainty == pytest.approx(4.567e-3)
        assert params.temperature_flag == VaryFlag.YES
        assert params.thickness_flag == VaryFlag.YES

    def test_round_trip(self, valid_selfi_params):
        """Test round-trip parsing and formatting of SELFI parameters."""
        lines = valid_selfi_params.to_lines()
        assert len(lines) == 1
        params = SelfiParameters.from_lines(lines)
        assert params == valid_selfi_params

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "SELFI x 1 1.234E+02 2.345E-03 3.456E-01 4.567E-03",  # Invalid temperature flag
            "SELFI 1 x 1.234E+02 2.345E-03 3.456E-01 4.567E-03",  # Invalid thickness flag
            "SELFI 1 1 invalid    2.345E-03 3.456E-01 4.567E-03",  # Invalid temperature
            "SELFI 1 1 1.234E+02  2.345E-03 invalid   4.567E-03",  # Invalid thickness
            "SELFX 1 1 1.234E+02  2.345E-03 3.456E-01 4.567E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid SELFI parameter lines."""
        with pytest.raises(ValueError):
            SelfiParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that required values must be provided."""
        with pytest.raises(ValueError):
            SelfiParameters(
                temperature=None,  # Required
                thickness=0.3456,
                temperature_flag=VaryFlag.YES,
                thickness_flag=VaryFlag.YES,
            )

        with pytest.raises(ValueError):
            SelfiParameters(
                temperature=123.4,
                thickness=None,  # Required
                temperature_flag=VaryFlag.YES,
                thickness_flag=VaryFlag.YES,
            )

    def test_optional_uncertainties(self):
        """Test that uncertainties are optional."""
        line = "SELFI 1 1 1.234E+02           3.456E-01"  # No uncertainties

        params = SelfiParameters.from_lines([line])
        assert params.temperature == pytest.approx(123.4)
        assert params.thickness == pytest.approx(0.3456)
        assert params.temperature_uncertainty is None
        assert params.thickness_uncertainty is None


class TestEfficParameters:
    """Test suite for EFFIC parameter parsing and formatting.

    EFFIC parameters specify efficiencies for capture and fission detection:
    Cols  Format  Variable    Description
    1-5   A       "EFFIC"     Parameter identifier
    7     I       IFCAPE      Flag for capture efficiency
    9     I       IFFISE      Flag for fission efficiency
    11-20 F       EFCAP       Efficiency for detecting capture events
    21-30 F       EFFIS       Efficiency for detecting fission events
    31-40 F       dEFCAP      Uncertainty on EFCAP
    41-50 F       dEFFIS      Uncertainty on EFFIS
    """

    @pytest.fixture
    def valid_effic_line(self):
        """Sample valid EFFIC parameter line."""
        return "EFFIC 1 1 1.234E+00 2.345E+00 3.456E-03 4.567E-03"
        #       |     | | |         |         |         |
        #       |     | | |         |         |         41-50: Fission efficiency uncertainty
        #       |     | | |         |         31-40: Capture efficiency uncertainty
        #       |     | | |         21-30: Fission efficiency
        #       |     | | 11-20: Capture efficiency
        #       |     | 9: Fission flag
        #       |     7: Capture flag
        #       1-5: "EFFIC"

    @pytest.fixture
    def valid_effic_params(self):
        """Sample valid EFFIC parameters."""
        return EfficParameters(
            capture_efficiency=1.234,
            fission_efficiency=2.345,
            capture_uncertainty=3.456e-3,
            fission_uncertainty=4.567e-3,
            capture_flag=VaryFlag.YES,
            fission_flag=VaryFlag.YES,
        )

    def test_parse_valid_line(self, valid_effic_line):
        """Test parsing of valid EFFIC parameter line."""
        # Check column number for each char
        for i, char in enumerate(valid_effic_line):
            print(f"{i+1}: {char}")

        params = EfficParameters.from_lines([valid_effic_line])
        assert params.capture_efficiency == pytest.approx(1.234)
        assert params.fission_efficiency == pytest.approx(2.345)
        assert params.capture_uncertainty == pytest.approx(3.456e-3)
        assert params.fission_uncertainty == pytest.approx(4.567e-3)
        assert params.capture_flag == VaryFlag.YES
        assert params.fission_flag == VaryFlag.YES

    def test_round_trip(self, valid_effic_params):
        """Test round-trip parsing and formatting of EFFIC parameters."""
        lines = valid_effic_params.to_lines()
        assert len(lines) == 1
        params = EfficParameters.from_lines(lines)
        assert params == valid_effic_params

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "EFFIC x 1 1.234E+00 2.345E+00 3.456E-03 4.567E-03",  # Invalid capture flag
            "EFFIC 1 x 1.234E+00 2.345E+00 3.456E-03 4.567E-03",  # Invalid fission flag
            "EFFIC 1 1 invalid   2.345E+00 3.456E-03 4.567E-03",  # Invalid capture efficiency
            "EFFIC 1 1 1.234E+00 invalid   3.456E-03 4.567E-03",  # Invalid fission efficiency
            "EFFIX 1 1 1.234E+00 2.345E+00 3.456E-03 4.567E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid EFFIC parameter lines."""
        with pytest.raises(ValueError):
            EfficParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that required values must be provided."""
        with pytest.raises(ValueError):
            EfficParameters(
                capture_efficiency=None,  # Required
                fission_efficiency=2.345,
                capture_flag=VaryFlag.YES,
                fission_flag=VaryFlag.YES,
            )

        with pytest.raises(ValueError):
            EfficParameters(
                capture_efficiency=1.234,
                fission_efficiency=None,  # Required
                capture_flag=VaryFlag.YES,
                fission_flag=VaryFlag.YES,
            )

    def test_optional_uncertainties(self):
        """Test that uncertainties are optional."""
        line = "EFFIC 1 1 1.234E+00 2.345E+00"  # No uncertainties
        params = EfficParameters.from_lines([line])
        assert params.capture_efficiency == pytest.approx(1.234)
        assert params.fission_efficiency == pytest.approx(2.345)
        assert params.capture_uncertainty is None
        assert params.fission_uncertainty is None


class TestDelteParameters:
    """Test suite for DELTE parameter parsing and formatting.

    DELTE parameters specify energy-dependent delta E parameters:
    Cols  Format  Variable    Description
    1-5   A       "DELTE"     Parameter identifier
    7     I       IFLAG1      Flag for DELE1
    9     I       IFLAG0      Flag for DELE0
    10    I       IFLAGL      Flag for DELEL
    11-20 F       DELE1       Coefficient of E (m/eV)
    21-30 F       DD1         Uncertainty on DELE1
    31-40 F       DELE0       Constant term (m)
    41-50 F       DD0         Uncertainty on DELE0
    51-60 F       DELEL       Coefficient of log term (m/ln(eV))
    61-70 F       DDL         Uncertainty on DELEL
    """

    @pytest.fixture
    def valid_delte_line(self):
        """Sample valid DELTE parameter line."""
        return "DELTE 1 111.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03"
        #       |     | |||         |         |         |         |         |
        #       |     | |||         |         |         |         |         61-70: Log coef uncertainty
        #       |     | |||         |         |         |         51-60: Log coefficient
        #       |     | |||         |         |         41-50: Constant term uncertainty
        #       |     | |||         |         31-40: Constant term
        #       |     | |||         21-30: E coef uncertainty
        #       |     | ||11-20: E coefficient
        #       |     | |10: Log term flag
        #       |     | 9: Constant term flag
        #       |     7: E coefficient flag
        #       1-5: "DELTE"

    @pytest.fixture
    def valid_delte_params(self):
        """Sample valid DELTE parameters."""
        return DelteParameters(
            e_coefficient=1.234,
            e_uncertainty=2.345e-3,
            constant_term=3.456,
            constant_uncertainty=4.567e-3,
            log_coefficient=5.678,
            log_uncertainty=6.789e-3,
            e_flag=VaryFlag.YES,
            constant_flag=VaryFlag.YES,
            log_flag=VaryFlag.YES,
        )

    def test_parse_valid_line(self, valid_delte_line):
        """Test parsing of valid DELTE parameter line."""
        # Check column number for each char
        for i, char in enumerate(valid_delte_line):
            print(f"{i+1}: {char}")

        params = DelteParameters.from_lines([valid_delte_line])
        assert params.e_coefficient == pytest.approx(1.234)
        assert params.e_uncertainty == pytest.approx(2.345e-3)
        assert params.constant_term == pytest.approx(3.456)
        assert params.constant_uncertainty == pytest.approx(4.567e-3)
        assert params.log_coefficient == pytest.approx(5.678)
        assert params.log_uncertainty == pytest.approx(6.789e-3)
        assert params.e_flag == VaryFlag.YES
        assert params.constant_flag == VaryFlag.YES
        assert params.log_flag == VaryFlag.YES

    def test_round_trip(self, valid_delte_params):
        """Test round-trip parsing and formatting of DELTE parameters."""
        lines = valid_delte_params.to_lines()
        assert len(lines) == 1
        params = DelteParameters.from_lines(lines)
        assert params == valid_delte_params

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "DELTE x 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",  # Invalid E flag
            "DELTE 1 x 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",  # Invalid constant flag
            "DELTE 1 1 x 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",  # Invalid log flag
            "DELTE 1 1 1 invalid   2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",  # Invalid E coefficient
            "DELTX 1 1 1 1.234E+00 2.345E-03 3.456E+00 4.567E-03 5.678E+00 6.789E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid DELTE parameter lines."""
        with pytest.raises(ValueError):
            DelteParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that required values must be provided."""
        with pytest.raises(ValueError):
            DelteParameters(
                e_coefficient=None,  # Required
                constant_term=3.456,
                log_coefficient=5.678,
            )

        with pytest.raises(ValueError):
            DelteParameters(
                e_coefficient=1.234,
                constant_term=None,  # Required
                log_coefficient=5.678,
            )

        with pytest.raises(ValueError):
            DelteParameters(
                e_coefficient=1.234,
                constant_term=3.456,
                log_coefficient=None,  # Required
            )

    def test_optional_uncertainties(self):
        """Test that uncertainties are optional."""
        line = "DELTE 1 111.234E+00           3.456E+00           5.678E+00"  # No uncertainties

        for i, char in enumerate(line):
            print(f"{i+1}: {char}")

        params = DelteParameters.from_lines([line])
        assert params.e_coefficient == pytest.approx(1.234)
        assert params.constant_term == pytest.approx(3.456)
        assert params.log_coefficient == pytest.approx(5.678)
        assert params.e_uncertainty is None
        assert params.constant_uncertainty is None
        assert params.log_uncertainty is None


class TestDrcapParameters:
    """Test suite for DRCAP parameter parsing and formatting.

    DRCAP parameters specify direct capture component coefficients:
    Cols  Format  Variable    Description
    1-5   A       "DRCAP"     Parameter identifier
    7     I       IFLAG1      Flag to vary COEF
    9     I       NUC         Nuclide Number
    11-20 F       COEF        Coefficient of DRC file value
    21-30 F       dCOEF       Uncertainty on COEF

    Notes:
    - May be included multiple times, once per nuclide
    - Numerical direct capture component is read from DRC file
    - COEF multiplies the value from DRC file
    """

    @pytest.fixture
    def valid_drcap_line(self):
        """Sample valid DRCAP parameter line."""
        return "DRCAP 1 1 1.234E+00 2.345E-03"
        #       |     | | |         |
        #       |     | | |         21-30: Coefficient uncertainty
        #       |     | | 11-20: Coefficient value
        #       |     | 9: Nuclide number
        #       |     7: Flag
        #       1-5: "DRCAP"

    @pytest.fixture
    def valid_drcap_params(self):
        """Sample valid DRCAP parameters."""
        return DrcapParameters(
            coefficient=1.234,
            coefficient_uncertainty=2.345e-3,
            nuclide_number=1,
            flag=VaryFlag.YES,
        )

    def test_parse_valid_line(self, valid_drcap_line):
        """Test parsing of valid DRCAP parameter line."""
        # Check column number for each char
        for i, char in enumerate(valid_drcap_line):
            print(f"{i+1}: {char}")

        params = DrcapParameters.from_lines([valid_drcap_line])
        assert params.coefficient == pytest.approx(1.234)
        assert params.coefficient_uncertainty == pytest.approx(2.345e-3)
        assert params.nuclide_number == 1
        assert params.flag == VaryFlag.YES

    def test_round_trip(self, valid_drcap_params):
        """Test round-trip parsing and formatting of DRCAP parameters."""
        lines = valid_drcap_params.to_lines()
        assert len(lines) == 1
        params = DrcapParameters.from_lines(lines)
        assert params == valid_drcap_params

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "DRCAP x 1 1.234E+00 2.345E-03",  # Invalid flag
            "DRCAP 1 x 1.234E+00 2.345E-03",  # Invalid nuclide number
            "DRCAP 1 1 invalid   2.345E-03",  # Invalid coefficient
            "DRCAX 1 1 1.234E+00 2.345E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid DRCAP parameter lines."""
        with pytest.raises(ValueError):
            DrcapParameters.from_lines([invalid_line])

    def test_required_values(self):
        """Test that required values must be provided."""
        with pytest.raises(ValueError):
            DrcapParameters(
                coefficient=None,  # Required
                nuclide_number=1,
                flag=VaryFlag.YES,
            )

        with pytest.raises(ValueError):
            DrcapParameters(
                coefficient=1.234,
                nuclide_number=None,  # Required
                flag=VaryFlag.YES,
            )

    def test_nuclide_number_positive(self):
        """Test that nuclide number must be positive."""
        with pytest.raises(ValueError):
            DrcapParameters(
                coefficient=1.234,
                nuclide_number=0,  # Invalid
                flag=VaryFlag.YES,
            )

    def test_optional_uncertainty(self):
        """Test that uncertainty is optional."""
        line = "DRCAP 1 1 1.234E+00"  # No uncertainty
        params = DrcapParameters.from_lines([line])
        assert params.coefficient == pytest.approx(1.234)
        assert params.coefficient_uncertainty is None


class TestNonunParameters:
    """Test suite for NONUN parameter parsing and formatting.

    NONUN parameters specify non-uniform sample thickness:
    Cols  Format  Variable    Description
    1-5   A       "NONUN"     Parameter identifier
    21-30 F       R           Radius at which thickness is given
    31-40 F       Z           Positive value for sample thickness at radius
    41-50 F       dZ          Uncertainty on thickness

    Notes:
    - At least two lines must be given (center and outer edge)
    - First line must have zero radius (center)
    - Last line must be at outer edge
    - Lines must be in increasing radius order
    - No fitting parameters yet permitted
    """

    @pytest.fixture
    def valid_nonun_lines(self):
        """Sample valid NONUN parameter lines."""
        return [
            "NONUN               0.000E+00 1.234E+00 2.345E-03",  # Center
            "NONUN               5.000E+00 3.456E+00 4.567E-03",  # Intermediate
            "NONUN               1.000E+01 5.678E+00 6.789E-03",  # Edge
        ]

    @pytest.fixture
    def valid_nonun_params(self):
        """Sample valid NONUN parameters."""
        return NonunParameters(
            radii=[0.0, 5.0, 10.0],
            thicknesses=[1.234, 3.456, 5.678],
            uncertainties=[2.345e-3, 4.567e-3, 6.789e-3],
        )

    def test_parse_valid_lines(self, valid_nonun_lines):
        """Test parsing of valid NONUN parameter lines."""
        # Check column number for each char in first line
        for i, char in enumerate(valid_nonun_lines[0]):
            print(f"{i+1}: {char}")

        params = NonunParameters.from_lines(valid_nonun_lines)
        assert params.radii[0] == pytest.approx(0.0)
        assert params.radii[1] == pytest.approx(5.0)
        assert params.radii[2] == pytest.approx(10.0)
        assert params.thicknesses[0] == pytest.approx(1.234)
        assert params.thicknesses[1] == pytest.approx(3.456)
        assert params.thicknesses[2] == pytest.approx(5.678)
        assert params.uncertainties[0] == pytest.approx(2.345e-3)
        assert params.uncertainties[1] == pytest.approx(4.567e-3)
        assert params.uncertainties[2] == pytest.approx(6.789e-3)

    def test_round_trip(self, valid_nonun_params):
        """Test round-trip parsing and formatting of NONUN parameters."""
        lines = valid_nonun_params.to_lines()
        assert len(lines) == 3
        params = NonunParameters.from_lines(lines)
        assert params == valid_nonun_params

    def test_minimum_two_points(self):
        """Test that at least two points are required."""
        # Single point is invalid
        with pytest.raises(ValueError):
            NonunParameters.from_lines(
                [
                    "NONUN               0.000E+00 1.234E+00 2.345E-03",
                ]
            )

        # Two points is valid
        params = NonunParameters.from_lines(
            [
                "NONUN               0.000E+00 1.234E+00 2.345E-03",
                "NONUN               1.000E+01 5.678E+00 6.789E-03",
            ]
        )
        assert len(params.radii) == 2

    def test_first_point_zero_radius(self):
        """Test that first point must have zero radius."""
        with pytest.raises(ValueError):
            NonunParameters.from_lines(
                [
                    "NONUN               1.000E+00 1.234E+00 2.345E-03",  # Non-zero first radius
                    "NONUN               1.000E+01 5.678E+00 6.789E-03",
                ]
            )

    def test_increasing_radius(self):
        """Test that radii must be in increasing order."""
        with pytest.raises(ValueError):
            NonunParameters.from_lines(
                [
                    "NONUN               0.000E+00 1.234E+00 2.345E-03",
                    "NONUN               1.000E+01 5.678E+00 6.789E-03",
                    "NONUN               5.000E+00 3.456E+00 4.567E-03",  # Out of order
                ]
            )

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "",  # Empty line
            "NONUN               invalid   1.234E+00 2.345E-03",  # Invalid radius
            "NONUN               0.000E+00 invalid   2.345E-03",  # Invalid thickness
            "NONUX               0.000E+00 1.234E+00 2.345E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_lines(self, invalid_line):
        """Test parsing of invalid NONUN parameter lines."""
        with pytest.raises(ValueError):
            NonunParameters.from_lines([invalid_line])

    def test_optional_uncertainties(self):
        """Test that uncertainties are optional."""
        lines = [
            "NONUN               0.000E+00 1.234E+00",  # No uncertainties
            "NONUN               1.000E+01 5.678E+00",
        ]
        params = NonunParameters.from_lines(lines)
        assert params.radii[0] == pytest.approx(0.0)
        assert params.thicknesses[0] == pytest.approx(1.234)
        assert params.uncertainties[0] is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
