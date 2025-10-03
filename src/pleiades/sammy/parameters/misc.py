#!/usr/bin/env python
"""Parsers and containers for SAMMY's Card Set 11 parameters.

This module implements parsers and containers for SAMMY's Card Set 11 miscellaneous
parameters which can appear in either the PARameter or INPut file.

Format specification from Table VI B.2:
Card Set 11 contains optional parameter sets with distinct formats:

1. DELTA - Length-dependent flight path parameters
2. ETA - Normalization coefficients for ETA data
3. FINIT - Finite-size corrections for angular distributions
4. GAMMA - Radiation width specifications
5. TZERO - Time offset parameters
...etc.

The card set starts with header "MISCEllaneous parameters follow".
Each parameter type has a specific identifier in columns 1-5 and its own fixed-width format.
Parameters can be omitted when not needed.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from pleiades.utils.helper import VaryFlag, format_float, format_vary, safe_parse
from pleiades.utils.logger import loguru_logger

# Format definitions - column positions for each parameter type
FORMAT_SPECS = {
    "DELTA": {
        "identifier": slice(0, 5),
        "flag1": slice(6, 7),
        "flag0": slice(8, 9),
        "l1_coeff": slice(10, 20),
        "l1_unc": slice(20, 30),
        "l0_const": slice(30, 40),
        "l0_unc": slice(40, 50),
    },
    "ETA": {
        "identifier": slice(0, 5),
        "flag": slice(6, 7),
        "nu_value": slice(10, 20),
        "nu_unc": slice(20, 30),
        "energy": slice(30, 40),
    },
    "FINIT": {
        "identifier": slice(0, 5),
        "flag_i": slice(6, 7),
        "flag_o": slice(8, 9),
        "attni": slice(10, 20),
        "dttni": slice(20, 30),
        "attno": slice(30, 40),
        "dttno": slice(40, 50),
    },
    "GAMMA": {
        "identifier": slice(0, 5),
        "group": slice(5, 7),
        "flag": slice(7, 9),
        "width": slice(10, 20),
        "uncertainty": slice(20, 30),
    },
    "TZERO": {
        "identifier": slice(0, 5),
        "flag_t0": slice(6, 7),
        "flag_l0": slice(8, 9),
        "t0_value": slice(10, 20),
        "t0_unc": slice(20, 30),
        "l0_value": slice(30, 40),
        "l0_unc": slice(40, 50),
        "fpl": slice(50, 60),
    },
    "SIABN": {
        "identifier": slice(0, 5),
        "flag1": slice(6, 7),
        "flag2": slice(8, 9),
        "flag3": slice(9, 10),
        "abundance1": slice(10, 20),
        "uncertainty1": slice(20, 30),
        "abundance2": slice(30, 40),
        "uncertainty2": slice(40, 50),
        "abundance3": slice(50, 60),
        "uncertainty3": slice(60, 70),
    },
    "SELFI": {
        "identifier": slice(0, 5),
        "flag_temp": slice(6, 7),
        "flag_thick": slice(8, 9),
        "temperature": slice(10, 20),
        "temp_unc": slice(20, 30),
        "thickness": slice(30, 40),
        "thick_unc": slice(40, 50),
    },
    "EFFIC": {
        "identifier": slice(0, 5),
        "flag_cap": slice(6, 7),
        "flag_fis": slice(8, 9),
        "eff_cap": slice(10, 20),
        "eff_fis": slice(20, 30),
        "eff_cap_unc": slice(30, 40),
        "eff_fis_unc": slice(40, 50),
    },
    "DELTE": {
        "identifier": slice(0, 5),
        "flag1": slice(6, 7),
        "flag0": slice(8, 9),
        "flagl": slice(9, 10),
        "dele1": slice(10, 20),
        "dd1": slice(20, 30),
        "dele0": slice(30, 40),
        "dd0": slice(40, 50),
        "delel": slice(50, 60),
        "ddl": slice(60, 70),
    },
    "DRCAP": {
        "identifier": slice(0, 5),
        "flag": slice(6, 7),
        "nuc": slice(8, 9),
        "coef": slice(10, 20),
        "dcoef": slice(20, 30),
    },
    "NONUN": {
        "identifier": slice(0, 5),
        "radius": slice(20, 30),
        "thickness": slice(30, 40),
        "uncertainty": slice(40, 50),
    },
}


class Card11ParameterType(str, Enum):
    """Enumeration of Card 11 parameter types."""

    DELTA = "DELTA"
    ETA = "ETA"
    FINIT = "FINIT"
    GAMMA = "GAMMA"
    TZERO = "TZERO"
    SIABN = "SIABN"
    SELFI = "SELFI"
    EFFIC = "EFFIC"
    DELTE = "DELTE"
    DRCAP = "DRCAP"
    NONUN = "NONUN"


class Card11Parameter(BaseModel):
    """Base class for Card 11 parameter types.

    This class provides common functionality for all Card 11 parameter types
    including parsing and formatting of fixed-width formats.

    Attributes:
        type (Card11ParameterType): Parameter type identifier
    """

    type: Card11ParameterType

    @classmethod
    def identify_type(cls, line: str) -> Optional[Card11ParameterType]:
        """Identify parameter type from input line.

        Args:
            line: Input line starting with parameter identifier

        Returns:
            Parameter type or None if not recognized
        """
        if not line or len(line) < 5:
            return None

        identifier = line[0:5].strip()
        try:
            return Card11ParameterType(identifier)
        except ValueError:
            return None

    @classmethod
    def from_lines(cls, lines: List[str]) -> Optional["Card11Parameter"]:
        """Factory method to create appropriate parameter object.

        Args:
            lines: Input lines for parameter

        Returns:
            Parsed parameter object or None if invalid

        Raises:
            ValueError: If format is invalid
        """
        if not lines:
            return None

        param_type = cls.identify_type(lines[0])
        if param_type is None:
            return None

        # Dispatch to appropriate parameter class based on type
        parameter_classes = {
            Card11ParameterType.DELTA: DeltaParameters,
            Card11ParameterType.ETA: EtaParameters,
            Card11ParameterType.FINIT: FinitParameters,
            Card11ParameterType.GAMMA: GammaParameters,
            Card11ParameterType.TZERO: TzeroParameters,
            Card11ParameterType.SIABN: SiabnParameters,
            Card11ParameterType.SELFI: SelfiParameters,
            Card11ParameterType.EFFIC: EfficParameters,
            Card11ParameterType.DELTE: DelteParameters,
            Card11ParameterType.DRCAP: DrcapParameters,
            Card11ParameterType.NONUN: NonunParameters,
        }

        parser_class = parameter_classes.get(param_type)
        if parser_class is None:
            loguru_logger.warning(f"Parser not yet implemented for parameter type: {param_type}")
            return None

        return parser_class.from_lines(lines)

    def to_lines(self) -> List[str]:
        """Convert parameter to fixed-width format lines.

        Returns:
            List of formatted lines

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError


class DeltaParameters(Card11Parameter):
    """Container for DELTA (Length-dependent flight path) parameters.

    Format specification from Table VI B.2:
    Cols    Format  Variable    Description
    1-5     A       "DELTA"     Parameter identifier
    7       I       IFLAG1      Flag for L'₁ (1=vary, 3=PUP, 0=fixed)
    9       I       IFLAG0      Flag for L'₀
    11-20   F       DELL11      L'₁ coefficient of E (m/eV)
    21-30   F       D1          Uncertainty on L'₁ (m/eV)
    31-40   F       DELL00      L'₀ constant term (m)
    41-50   F       D0          Uncertainty on L'₀ (m)

    Attributes:
        l1_coefficient: L'₁ coefficient of E (m/eV)
        l1_uncertainty: Uncertainty on L'₁ (m/eV)
        l0_constant: L'₀ constant term (m)
        l0_uncertainty: Uncertainty on L'₀ (m)
        l1_flag: Flag for varying L'₁
        l0_flag: Flag for varying L'₀
    """

    type: Card11ParameterType = Card11ParameterType.DELTA
    l1_coefficient: float = Field(..., description="L'₁ coefficient of E (m/eV)")
    l1_uncertainty: Optional[float] = Field(None, description="Uncertainty on L'₁ (m/eV)")
    l0_constant: float = Field(..., description="L'₀ constant term (m)")
    l0_uncertainty: Optional[float] = Field(None, description="Uncertainty on L'₀ (m)")
    l1_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for L'₁")
    l0_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for L'₀")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "DeltaParameters":
        """Parse DELTA parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for DELTA parameters)

        Returns:
            DeltaParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        # Verify identifier
        line = f"{lines[0]:<80}"  # Pad to full width
        identifier = line[FORMAT_SPECS["DELTA"]["identifier"]].strip()
        if identifier != "DELTA":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse flags
        try:
            l1_flag = VaryFlag(int(line[FORMAT_SPECS["DELTA"]["flag1"]].strip() or "0"))
            l0_flag = VaryFlag(int(line[FORMAT_SPECS["DELTA"]["flag0"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value: {e}")

        # Parse required numeric values
        l1_coeff = safe_parse(line[FORMAT_SPECS["DELTA"]["l1_coeff"]])
        l0_const = safe_parse(line[FORMAT_SPECS["DELTA"]["l0_const"]])

        if l1_coeff is None or l0_const is None:
            raise ValueError("Missing required numeric values")

        # Parse optional uncertainties
        l1_unc = safe_parse(line[FORMAT_SPECS["DELTA"]["l1_unc"]])
        l0_unc = safe_parse(line[FORMAT_SPECS["DELTA"]["l0_unc"]])

        return cls(
            l1_coefficient=l1_coeff,
            l1_uncertainty=l1_unc,
            l0_constant=l0_const,
            l0_uncertainty=l0_unc,
            l1_flag=l1_flag,
            l0_flag=l0_flag,
        )

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "DELTA".ljust(5),
            " ",  # Column 6 spacing
            format_vary(self.l1_flag),
            " ",  # Column 8 spacing
            format_vary(self.l0_flag),
            " ",  # Column 10 spacing
            format_float(self.l1_coefficient, width=10),
            format_float(self.l1_uncertainty, width=10),
            format_float(self.l0_constant, width=10),
            format_float(self.l0_uncertainty, width=10),
        ]
        return ["".join(parts)]


class EtaParameters(Card11Parameter):
    """Container for ETA (normalization coefficient) parameters.

    Format specification from Table VI B.2:
    Cols    Format  Variable    Description
    1-5     A       "ETA "      Parameter identifier ("eta" + 2 spaces)
    7       I       IFLAGN      Flag for parameter ν (0=fixed, 1=vary, 3=PUP)
    11-20   F       NU          Normalization coefficient ν (dimensionless)
    21-30   F       DNU         Uncertainty on NU
    31-40   F       ENU         Energy for which this value applies (eV)

    Notes:
    - If a constant value of NU is wanted, the energy value can be omitted
    - If more than one ETA line is present, all must be together in increasing energy order
    - SAMMY will linearly interpolate to obtain values between specified energies

    Attributes:
        nu_value: Normalization coefficient ν (dimensionless)
        nu_uncertainty: Uncertainty on ν
        energy: Energy for which this value applies (eV), optional
        flag: Flag for varying ν
    """

    type: Card11ParameterType = Card11ParameterType.ETA
    nu_value: float = Field(..., description="Normalization coefficient ν")
    nu_uncertainty: Optional[float] = Field(None, description="Uncertainty on ν")
    energy: Optional[float] = Field(None, description="Energy value (eV)")
    flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for ν")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "EtaParameters":
        """Parse ETA parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for ETA parameters)

        Returns:
            EtaParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<80}"  # Pad to full width

        # Verify identifier is "ETA " (including 2 spaces)
        identifier = line[FORMAT_SPECS["ETA"]["identifier"]].strip()
        if identifier != "ETA":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse flag
        try:
            flag = VaryFlag(int(line[FORMAT_SPECS["ETA"]["flag"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value: {e}")

        # Parse required nu value
        nu_value = safe_parse(line[FORMAT_SPECS["ETA"]["nu_value"]])
        if nu_value is None:
            raise ValueError("Missing required nu value")

        # Parse optional values
        nu_unc = safe_parse(line[FORMAT_SPECS["ETA"]["nu_unc"]])
        energy = safe_parse(line[FORMAT_SPECS["ETA"]["energy"]])

        return cls(nu_value=nu_value, nu_uncertainty=nu_unc, energy=energy, flag=flag)

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "ETA ".ljust(5),  # Identifier with required 2 spaces
            " ",  # Column 6 spacing
            format_vary(self.flag),
            "   ",  # Columns 8-10 spacing
            format_float(self.nu_value, width=10),
            format_float(self.nu_uncertainty, width=10),
            format_float(self.energy, width=10) if self.energy is not None else " " * 10,
        ]
        return ["".join(parts)]


class FinitParameters(Card11Parameter):
    """Container for FINIT (finite-size corrections) parameters.

    Format specification from Table VI B.2:
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

    Attributes:
        incident_attenuation: Incident-particle attenuation (atoms/barn)
        incident_uncertainty: Uncertainty on incident attenuation
        exit_attenuation: Exit-particle attenuation (atom/b)
        exit_uncertainty: Uncertainty on exit attenuation
        incident_flag: Flag for incident attenuation
        exit_flag: Flag for exit attenuation
    """

    type: Card11ParameterType = Card11ParameterType.FINIT
    incident_attenuation: float = Field(..., description="Incident-particle attenuation (atoms/barn)")
    incident_uncertainty: Optional[float] = Field(None, description="Uncertainty on incident attenuation")
    exit_attenuation: float = Field(..., description="Exit-particle attenuation (atom/b)")
    exit_uncertainty: Optional[float] = Field(None, description="Uncertainty on exit attenuation")
    incident_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for incident attenuation")
    exit_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for exit attenuation")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "FinitParameters":
        """Parse FINIT parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for FINIT parameters)

        Returns:
            FinitParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<80}"  # Pad to full width

        # Verify identifier
        identifier = line[FORMAT_SPECS["FINIT"]["identifier"]].strip()
        if identifier != "FINIT":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse flags
        try:
            incident_flag = VaryFlag(int(line[FORMAT_SPECS["FINIT"]["flag_i"]].strip() or "0"))
            exit_flag = VaryFlag(int(line[FORMAT_SPECS["FINIT"]["flag_o"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value: {e}")

        # Parse required attenuations
        incident_att = safe_parse(line[FORMAT_SPECS["FINIT"]["attni"]])
        exit_att = safe_parse(line[FORMAT_SPECS["FINIT"]["attno"]])

        if incident_att is None or exit_att is None:
            raise ValueError("Missing required attenuation values")

        # Parse optional uncertainties
        incident_unc = safe_parse(line[FORMAT_SPECS["FINIT"]["dttni"]])
        exit_unc = safe_parse(line[FORMAT_SPECS["FINIT"]["dttno"]])

        return cls(
            incident_attenuation=incident_att,
            incident_uncertainty=incident_unc,
            exit_attenuation=exit_att,
            exit_uncertainty=exit_unc,
            incident_flag=incident_flag,
            exit_flag=exit_flag,
        )

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "FINIT",  # Identifier
            " ",  # Column 6 spacing
            format_vary(self.incident_flag),  # Col 7
            " ",  # Column 8 spacing
            format_vary(self.exit_flag),  # Col 9
            " ",  # Column 10 spacing
            format_float(self.incident_attenuation, width=10),
            format_float(self.incident_uncertainty, width=10),
            format_float(self.exit_attenuation, width=10),
            format_float(self.exit_uncertainty, width=10),
        ]
        return ["".join(parts)]


class GammaParameters(Card11Parameter):
    """Container for GAMMA (radiation width) parameters.

    Format specification from Table VI B.2:
    Cols  Format  Variable    Description
    1-5   A       "GAMMA"     Parameter identifier
    6-7   I       IG          Spin group number
    8-9   I       IFG         Flag for GAMGAM (0=fixed, 1=vary, 3=PUP)
    11-20  F       GAMGAM      Radiation width Γγ for all resonances in spin group
    21-30  F       DGAM        Uncertainty on GAMGAM

    Notes:
    - If used for any spin group, must be given for every spin group

    Attributes:
        spin_group: Spin group number (must be positive)
        width: Radiation width Γγ for all resonances in group
        uncertainty: Uncertainty on width (optional)
        flag: Flag for varying width
    """

    type: Card11ParameterType = Card11ParameterType.GAMMA
    spin_group: int = Field(..., gt=0, description="Spin group number")
    width: float = Field(..., description="Radiation width Γγ")
    uncertainty: Optional[float] = Field(None, description="Uncertainty on width")
    flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for width")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "GammaParameters":
        """Parse GAMMA parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for GAMMA parameters)

        Returns:
            GammaParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<80}"  # Pad to full width

        # Verify identifier
        identifier = line[FORMAT_SPECS["GAMMA"]["identifier"]].strip()
        if identifier != "GAMMA":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse spin group (required)
        spin_group = safe_parse(line[FORMAT_SPECS["GAMMA"]["group"]], as_int=True)
        if spin_group is None:
            raise ValueError("Missing or invalid spin group number")
        if spin_group <= 0:
            raise ValueError("Spin group must be positive")

        # Parse flag
        try:
            flag = VaryFlag(int(line[FORMAT_SPECS["GAMMA"]["flag"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value: {e}")

        # Parse width (required)
        width = safe_parse(line[FORMAT_SPECS["GAMMA"]["width"]])
        if width is None:
            raise ValueError("Missing required width value")

        # Parse optional uncertainty
        uncertainty = safe_parse(line[FORMAT_SPECS["GAMMA"]["uncertainty"]])

        return cls(spin_group=spin_group, width=width, uncertainty=uncertainty, flag=flag)

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "GAMMA",  # Identifier
            str(self.spin_group).rjust(2),  # Spin group (cols 6-7)
            format_vary(self.flag).rjust(2),  # Flag (cols 8-9)
            " ",  # Column 10 spacing
            format_float(self.width, width=10),  # Width (cols 11-20)
            format_float(self.uncertainty, width=10),  # Uncertainty (cols 21-30)
        ]
        return ["".join(parts)]


class TzeroParameters(Card11Parameter):
    """Container for TZERO (time offset) parameters.

    Format specification from Table VI B.2:
    Cols  Format  Variable    Description
    1-5   A       "TZERO"     Parameter identifier
    7     I       IFTZER      Flag for t
    9     I       IFLZER      Flag for L
    11-20 F       TZERO       t (μs)
    21-30 F       DTZERO      Uncertainty on t (μs)
    31-40 F       LZERO       L (dimensionless)
    41-50 F       DLZERO      Uncertainty on L
    51-60 F       FPL         Flight-path length (m)

    Attributes:
        t0_value: Time offset t (μs)
        t0_uncertainty: Uncertainty on t (μs)
        l0_value: L value (dimensionless)
        l0_uncertainty: Uncertainty on L
        flight_path_length: Flight path length (m), optional
        t0_flag: Flag for varying t
        l0_flag: Flag for varying L
    """

    type: Card11ParameterType = Card11ParameterType.TZERO
    t0_value: float = Field(..., description="Time offset t (μs)")
    t0_uncertainty: Optional[float] = Field(None, description="Uncertainty on t (μs)")
    l0_value: float = Field(..., description="L value (dimensionless)")
    l0_uncertainty: Optional[float] = Field(None, description="Uncertainty on L")
    flight_path_length: Optional[float] = Field(None, description="Flight path length (m)")
    t0_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for t")
    l0_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for L")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "TzeroParameters":
        """Parse TZERO parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for TZERO parameters)

        Returns:
            TzeroParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<80}"  # Pad to full width

        # Verify identifier
        identifier = line[FORMAT_SPECS["TZERO"]["identifier"]].strip()
        if identifier != "TZERO":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse flags
        try:
            t0_flag = VaryFlag(int(line[FORMAT_SPECS["TZERO"]["flag_t0"]].strip() or "0"))
            l0_flag = VaryFlag(int(line[FORMAT_SPECS["TZERO"]["flag_l0"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value: {e}")

        # Parse required values
        t0_value = safe_parse(line[FORMAT_SPECS["TZERO"]["t0_value"]])
        l0_value = safe_parse(line[FORMAT_SPECS["TZERO"]["l0_value"]])

        if t0_value is None or l0_value is None:
            raise ValueError("Missing required t₀ or L₀ value")

        # Parse optional values
        t0_unc = safe_parse(line[FORMAT_SPECS["TZERO"]["t0_unc"]])
        l0_unc = safe_parse(line[FORMAT_SPECS["TZERO"]["l0_unc"]])
        fpl = safe_parse(line[FORMAT_SPECS["TZERO"]["fpl"]])

        return cls(
            t0_value=t0_value,
            t0_uncertainty=t0_unc,
            l0_value=l0_value,
            l0_uncertainty=l0_unc,
            flight_path_length=fpl,
            t0_flag=t0_flag,
            l0_flag=l0_flag,
        )

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "TZERO",  # Identifier
            " ",  # Column 6 spacing
            format_vary(self.t0_flag),  # Col 7
            " ",  # Column 8 spacing
            format_vary(self.l0_flag),  # Col 9
            " ",  # Column 10 spacing
            format_float(self.t0_value, width=10),  # t value
            format_float(self.t0_uncertainty, width=10),  # t uncertainty
            format_float(self.l0_value, width=10),  # L value
            format_float(self.l0_uncertainty, width=10),  # L uncertainty
            format_float(self.flight_path_length, width=10),  # Flight path length
        ]
        return ["".join(parts)]


class SiabnParameters(Card11Parameter):
    """Container for SIABN (self-indication abundance) parameters.

    Format specification from Table VI B.2:
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
    - Nuclides must be defined in card set 10 before card set 11
    - At least one abundance must be provided
    - Number of flags must match number of abundances
    """

    type: Card11ParameterType = Card11ParameterType.SIABN
    abundances: List[float] = Field(..., min_length=1, max_length=3, description="Abundance values for nuclides")
    uncertainties: List[Optional[float]] = Field(..., max_length=3, description="Uncertainties on abundances")
    flags: List[VaryFlag] = Field(..., max_length=3, description="Flags for varying abundances")

    @model_validator(mode="after")
    def validate_list_lengths(self) -> "SiabnParameters":
        """Validate that all lists have matching lengths."""
        if len(self.abundances) != len(self.uncertainties) or len(self.abundances) != len(self.flags):
            raise ValueError("Number of abundances, uncertainties, and flags must match")
        return self

    @classmethod
    def from_lines(cls, lines: List[str]) -> "SiabnParameters":
        """Parse SIABN parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for SIABN parameters)

        Returns:
            SiabnParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<80}"  # Pad to full width

        # Verify identifier
        identifier = line[FORMAT_SPECS["SIABN"]["identifier"]].strip()
        if identifier != "SIABN":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse flags
        flags = []
        for i, flag_slice in enumerate(
            [FORMAT_SPECS["SIABN"]["flag1"], FORMAT_SPECS["SIABN"]["flag2"], FORMAT_SPECS["SIABN"]["flag3"]]
        ):
            flag_str = line[flag_slice].strip()
            if flag_str:
                try:
                    flags.append(VaryFlag(int(flag_str)))
                except ValueError as e:
                    raise ValueError(f"Invalid flag value for flag {i + 1}: {e}")

        # Parse abundance-uncertainty pairs
        abundances = []
        uncertainties = []
        for i in range(1, 4):  # Up to 3 pairs
            abund = safe_parse(line[FORMAT_SPECS["SIABN"][f"abundance{i}"]])
            uncert = safe_parse(line[FORMAT_SPECS["SIABN"][f"uncertainty{i}"]])

            if abund is not None:  # Found a valid abundance
                abundances.append(abund)
                uncertainties.append(uncert)
            elif i == 1:  # First abundance is required
                raise ValueError("At least one abundance value is required")
            else:
                break  # Stop parsing pairs if abundance is missing

        # Trim flags to match number of abundances found
        flags = flags[: len(abundances)]

        if not abundances:
            raise ValueError("At least one abundance value is required")

        return cls(abundances=abundances, uncertainties=uncertainties, flags=flags)

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "SIABN",  # Identifier
            " ",  # Column 6 spacing
            str(self.flags[0].value),  # Flag for abundance 1
            " ",  # Column 8 spacing
            str(self.flags[1].value),  # Flag for abundance 2
            str(self.flags[2].value),  # Flag for abundance 3
        ]

        # Add abundance-uncertainty pairs
        for i in range(3):
            if i < len(self.abundances):
                parts.extend(
                    [
                        format_float(self.abundances[i], width=10),
                        format_float(self.uncertainties[i], width=10),
                    ]
                )
            else:
                parts.extend([" " * 10, " " * 10])  # Pad with spaces if fewer than 3 pairs

        return ["".join(parts)]


class SelfiParameters(Card11Parameter):
    """Container for SELFI (self-indication temperature/thickness) parameters.

    Format specification from Table VI B.2:
    Cols  Format  Variable    Description
    1-5   A       "SELFI"     Parameter identifier
    7     I       IFTEMP      Flag for temperature
    9     I       IFTHCK      Flag for thickness
    11-20 F       SITEM       Effective temperature (K)
    21-30 F       dSITEM      Uncertainty on SITEM
    31-40 F       SITHC       Thickness (atoms/barn)
    41-50 F       dSITHC      Uncertainty on SITHC

    Attributes:
        temperature: Effective temperature (K) for transmission sample
        temperature_uncertainty: Uncertainty on temperature
        thickness: Sample thickness (atoms/barn)
        thickness_uncertainty: Uncertainty on thickness
        temperature_flag: Flag for varying temperature
        thickness_flag: Flag for varying thickness
    """

    type: Card11ParameterType = Card11ParameterType.SELFI
    temperature: float = Field(..., description="Effective temperature (K)")
    temperature_uncertainty: Optional[float] = Field(None, description="Uncertainty on temperature")
    thickness: float = Field(..., description="Sample thickness (atoms/barn)")
    thickness_uncertainty: Optional[float] = Field(None, description="Uncertainty on thickness")
    temperature_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for temperature")
    thickness_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for thickness")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "SelfiParameters":
        """Parse SELFI parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for SELFI parameters)

        Returns:
            SelfiParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<80}"  # Pad to full width

        # Verify identifier
        identifier = line[FORMAT_SPECS["SELFI"]["identifier"]].strip()
        if identifier != "SELFI":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse flags
        try:
            temp_flag = VaryFlag(int(line[FORMAT_SPECS["SELFI"]["flag_temp"]].strip() or "0"))
            thick_flag = VaryFlag(int(line[FORMAT_SPECS["SELFI"]["flag_thick"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value: {e}")

        # Parse required values
        temp = safe_parse(line[FORMAT_SPECS["SELFI"]["temperature"]])
        thick = safe_parse(line[FORMAT_SPECS["SELFI"]["thickness"]])

        if temp is None or thick is None:
            raise ValueError("Missing required temperature or thickness value")

        # Parse optional uncertainties
        temp_unc = safe_parse(line[FORMAT_SPECS["SELFI"]["temp_unc"]])
        thick_unc = safe_parse(line[FORMAT_SPECS["SELFI"]["thick_unc"]])

        return cls(
            temperature=temp,
            temperature_uncertainty=temp_unc,
            thickness=thick,
            thickness_uncertainty=thick_unc,
            temperature_flag=temp_flag,
            thickness_flag=thick_flag,
        )

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "SELFI",  # Identifier
            " ",  # Column 6 spacing
            format_vary(self.temperature_flag),  # Col 7
            " ",  # Column 8 spacing
            format_vary(self.thickness_flag),  # Col 9
            " ",  # Column 10 spacing
            format_float(self.temperature, width=10),
            format_float(self.temperature_uncertainty, width=10),
            format_float(self.thickness, width=10),
            format_float(self.thickness_uncertainty, width=10),
        ]
        return ["".join(parts)]


class EfficParameters(Card11Parameter):
    """Container for EFFIC (detection efficiency) parameters.

    Format specification from Table VI B.2:
    Cols  Format  Variable    Description
    1-5   A       "EFFIC"     Parameter identifier
    7     I       IFCAPE      Flag for capture efficiency
    9     I       IFFISE      Flag for fission efficiency
    11-20 F       EFCAP       Efficiency for detecting capture events
    21-30 F       EFFIS       Efficiency for detecting fission events
    31-40 F       dEFCAP      Uncertainty on EFCAP
    41-50 F       dEFFIS      Uncertainty on EFFIS

    Attributes:
        capture_efficiency: Efficiency for detecting capture events
        fission_efficiency: Efficiency for detecting fission events
        capture_uncertainty: Uncertainty on capture efficiency
        fission_uncertainty: Uncertainty on fission efficiency
        capture_flag: Flag for varying capture efficiency
        fission_flag: Flag for varying fission efficiency
    """

    type: Card11ParameterType = Card11ParameterType.EFFIC
    capture_efficiency: float = Field(..., description="Capture detection efficiency")
    fission_efficiency: float = Field(..., description="Fission detection efficiency")
    capture_uncertainty: Optional[float] = Field(None, description="Uncertainty on capture efficiency")
    fission_uncertainty: Optional[float] = Field(None, description="Uncertainty on fission efficiency")
    capture_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for capture efficiency")
    fission_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for fission efficiency")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "EfficParameters":
        """Parse EFFIC parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for EFFIC parameters)

        Returns:
            EfficParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<80}"  # Pad to full width

        # Verify identifier
        identifier = line[FORMAT_SPECS["EFFIC"]["identifier"]].strip()
        if identifier != "EFFIC":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse flags
        try:
            cap_flag = VaryFlag(int(line[FORMAT_SPECS["EFFIC"]["flag_cap"]].strip() or "0"))
            fis_flag = VaryFlag(int(line[FORMAT_SPECS["EFFIC"]["flag_fis"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value: {e}")

        # Parse required values
        cap_eff = safe_parse(line[FORMAT_SPECS["EFFIC"]["eff_cap"]])
        fis_eff = safe_parse(line[FORMAT_SPECS["EFFIC"]["eff_fis"]])

        if cap_eff is None or fis_eff is None:
            raise ValueError("Missing required efficiency values")

        # Parse optional uncertainties
        cap_unc = safe_parse(line[FORMAT_SPECS["EFFIC"]["eff_cap_unc"]])
        fis_unc = safe_parse(line[FORMAT_SPECS["EFFIC"]["eff_fis_unc"]])

        return cls(
            capture_efficiency=cap_eff,
            fission_efficiency=fis_eff,
            capture_uncertainty=cap_unc,
            fission_uncertainty=fis_unc,
            capture_flag=cap_flag,
            fission_flag=fis_flag,
        )

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "EFFIC",  # Identifier
            " ",  # Column 6 spacing
            format_vary(self.capture_flag),  # Col 7
            " ",  # Column 8 spacing
            format_vary(self.fission_flag),  # Col 9
            " ",  # Column 10 spacing
            format_float(self.capture_efficiency, width=10),
            format_float(self.fission_efficiency, width=10),
            format_float(self.capture_uncertainty, width=10),
            format_float(self.fission_uncertainty, width=10),
        ]
        return ["".join(parts)]


class DelteParameters(Card11Parameter):
    """Container for DELTE (energy-dependent delta E) parameters.

    Format specification from Table VI B.2:
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

    Attributes:
        e_coefficient: Coefficient of E (m/eV)
        e_uncertainty: Uncertainty on E coefficient
        constant_term: Constant term (m)
        constant_uncertainty: Uncertainty on constant term
        log_coefficient: Coefficient of log term (m/ln(eV))
        log_uncertainty: Uncertainty on log coefficient
        e_flag: Flag for varying E coefficient
        constant_flag: Flag for varying constant term
        log_flag: Flag for varying log coefficient
    """

    type: Card11ParameterType = Card11ParameterType.DELTE
    e_coefficient: float = Field(..., description="Coefficient of E (m/eV)")
    e_uncertainty: Optional[float] = Field(None, description="Uncertainty on E coefficient")
    constant_term: float = Field(..., description="Constant term (m)")
    constant_uncertainty: Optional[float] = Field(None, description="Uncertainty on constant term")
    log_coefficient: float = Field(..., description="Coefficient of log term (m/ln(eV))")
    log_uncertainty: Optional[float] = Field(None, description="Uncertainty on log coefficient")
    e_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for E coefficient")
    constant_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for constant term")
    log_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for log coefficient")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "DelteParameters":
        """Parse DELTE parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for DELTE parameters)

        Returns:
            DelteParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<80}"  # Pad to full width

        # Verify identifier
        identifier = line[FORMAT_SPECS["DELTE"]["identifier"]].strip()
        if identifier != "DELTE":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse flags
        try:
            e_flag = VaryFlag(int(line[FORMAT_SPECS["DELTE"]["flag1"]].strip() or "0"))
            constant_flag = VaryFlag(int(line[FORMAT_SPECS["DELTE"]["flag0"]].strip() or "0"))
            log_flag = VaryFlag(int(line[FORMAT_SPECS["DELTE"]["flagl"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value: {e}")

        # Parse required values
        e_coef = safe_parse(line[FORMAT_SPECS["DELTE"]["dele1"]])
        const_term = safe_parse(line[FORMAT_SPECS["DELTE"]["dele0"]])
        log_coef = safe_parse(line[FORMAT_SPECS["DELTE"]["delel"]])

        if e_coef is None or const_term is None or log_coef is None:
            raise ValueError("Missing required coefficient values")

        # Parse optional uncertainties
        e_unc = safe_parse(line[FORMAT_SPECS["DELTE"]["dd1"]])
        const_unc = safe_parse(line[FORMAT_SPECS["DELTE"]["dd0"]])
        log_unc = safe_parse(line[FORMAT_SPECS["DELTE"]["ddl"]])

        return cls(
            e_coefficient=e_coef,
            e_uncertainty=e_unc,
            constant_term=const_term,
            constant_uncertainty=const_unc,
            log_coefficient=log_coef,
            log_uncertainty=log_unc,
            e_flag=e_flag,
            constant_flag=constant_flag,
            log_flag=log_flag,
        )

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "DELTE",  # Identifier
            " ",  # Column 6 spacing
            format_vary(self.e_flag),  # Col 7
            " ",  # Column 8 spacing
            format_vary(self.constant_flag),  # Col 9
            format_vary(self.log_flag),  # Col 10
            format_float(self.e_coefficient, width=10),
            format_float(self.e_uncertainty, width=10),
            format_float(self.constant_term, width=10),
            format_float(self.constant_uncertainty, width=10),
            format_float(self.log_coefficient, width=10),
            format_float(self.log_uncertainty, width=10),
        ]
        return ["".join(parts)]


class DrcapParameters(Card11Parameter):
    """Container for DRCAP (direct capture component) parameters.

    Format specification from Table VI B.2:
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

    Attributes:
        coefficient: Coefficient of the DRC file value
        coefficient_uncertainty: Uncertainty on coefficient
        nuclide_number: Nuclide number (must be positive)
        flag: Flag for varying coefficient
    """

    type: Card11ParameterType = Card11ParameterType.DRCAP
    coefficient: float = Field(..., description="Coefficient of DRC file value")
    coefficient_uncertainty: Optional[float] = Field(None, description="Uncertainty on coefficient")
    nuclide_number: int = Field(..., gt=0, description="Nuclide number")
    flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for coefficient")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "DrcapParameters":
        """Parse DRCAP parameters from fixed-width format lines.

        Args:
            lines: List of input lines (expects single line for DRCAP parameters)

        Returns:
            DrcapParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<80}"  # Pad to full width

        # Verify identifier
        identifier = line[FORMAT_SPECS["DRCAP"]["identifier"]].strip()
        if identifier != "DRCAP":
            raise ValueError(f"Invalid identifier: {identifier}")

        # Parse flag
        try:
            flag = VaryFlag(int(line[FORMAT_SPECS["DRCAP"]["flag"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value: {e}")

        # Parse nuclide number
        nuc_num = safe_parse(line[FORMAT_SPECS["DRCAP"]["nuc"]], as_int=True)
        if nuc_num is None:
            raise ValueError("Missing required nuclide number")
        if nuc_num <= 0:
            raise ValueError("Nuclide number must be positive")

        # Parse coefficient
        coef = safe_parse(line[FORMAT_SPECS["DRCAP"]["coef"]])
        if coef is None:
            raise ValueError("Missing required coefficient value")

        # Parse optional uncertainty
        coef_unc = safe_parse(line[FORMAT_SPECS["DRCAP"]["dcoef"]])

        return cls(
            coefficient=coef,
            coefficient_uncertainty=coef_unc,
            nuclide_number=nuc_num,
            flag=flag,
        )

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format line.

        Returns:
            List containing single formatted line
        """
        parts = [
            "DRCAP",  # Identifier
            " ",  # Column 6 spacing
            format_vary(self.flag),  # Col 7
            " ",  # Column 8 spacing
            f"{self.nuclide_number:1d}",  # Col 9
            " ",  # Column 10 spacing
            format_float(self.coefficient, width=10),
            format_float(self.coefficient_uncertainty, width=10),
        ]
        return ["".join(parts)]


class NonunParameters(Card11Parameter):
    """Container for NONUN (non-uniform sample thickness) parameters.

    Format specification from Table VI B.2:
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

    Attributes:
        radii: List of radii values (must start with 0)
        thicknesses: List of thickness values at each radius
        uncertainties: List of uncertainties on thicknesses (optional)
    """

    type: Card11ParameterType = Card11ParameterType.NONUN
    radii: List[float] = Field(..., min_length=2, description="Radii values")
    thicknesses: List[float] = Field(..., min_length=2, description="Thickness values")
    uncertainties: List[Optional[float]] = Field(..., min_length=2, description="Uncertainties")

    @model_validator(mode="after")
    def validate_arrays(self) -> "NonunParameters":
        """Validate array lengths and values."""
        if len(self.radii) != len(self.thicknesses) or len(self.radii) != len(self.uncertainties):
            raise ValueError("All arrays must have same length")

        if self.radii[0] != 0.0:
            raise ValueError("First radius must be zero (center point)")

        # Check increasing radius order
        for i in range(1, len(self.radii)):
            if self.radii[i] <= self.radii[i - 1]:
                raise ValueError("Radii must be in strictly increasing order")

        return self

    @classmethod
    def from_lines(cls, lines: List[str]) -> "NonunParameters":
        """Parse NONUN parameters from fixed-width format lines.

        Args:
            lines: List of input lines (minimum 2 lines required)

        Returns:
            NonunParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or len(lines) < 2:
            raise ValueError("At least two lines required (center and edge)")

        radii = []
        thicknesses = []
        uncertainties = []

        for line in lines:
            line = f"{line:<80}"  # Pad to full width

            # Verify identifier
            identifier = line[FORMAT_SPECS["NONUN"]["identifier"]].strip()
            if identifier != "NONUN":
                raise ValueError(f"Invalid identifier: {identifier}")

            # Parse values
            radius = safe_parse(line[FORMAT_SPECS["NONUN"]["radius"]])
            thickness = safe_parse(line[FORMAT_SPECS["NONUN"]["thickness"]])
            uncertainty = safe_parse(line[FORMAT_SPECS["NONUN"]["uncertainty"]])

            if radius is None or thickness is None:
                raise ValueError("Missing required radius or thickness value")

            radii.append(radius)
            thicknesses.append(thickness)
            uncertainties.append(uncertainty)

        return cls(
            radii=radii,
            thicknesses=thicknesses,
            uncertainties=uncertainties,
        )

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines.

        Returns:
            List containing formatted lines for each radius point
        """
        lines = []
        for i in range(len(self.radii)):
            parts = [
                "NONUN",  # Identifier
                " " * 15,  # Columns 6-20 spacing
                format_float(self.radii[i], width=10),
                format_float(self.thicknesses[i], width=10),
                format_float(self.uncertainties[i], width=10),
            ]
            lines.append("".join(parts))
        return lines


if __name__ == "__main__":
    from pleiades.utils.logger import configure_logger

    configure_logger(console_level="DEBUG")
    logger = loguru_logger.bind(name=__name__)
    logger.info("Refer to unit tests for usage examples.")
