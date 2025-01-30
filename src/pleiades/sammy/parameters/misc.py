#!/usr/bin/env python
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

import logging
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from pleiades.sammy.parameters.helper import VaryFlag, format_float, format_vary, safe_parse

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
    "ETA": {"identifier": slice(0, 5), "flag": slice(6, 7), "nu_value": slice(10, 20), "nu_unc": slice(20, 30), "energy": slice(30, 40)},
    "FINIT": {
        "identifier": slice(0, 5),
        "flag_i": slice(6, 7),
        "flag_o": slice(8, 9),
        "attni": slice(10, 20),
        "dttni": slice(20, 30),
        "attno": slice(30, 40),
        "dttno": slice(40, 50),
    },
    "GAMMA": {"identifier": slice(0, 5), "group": slice(5, 7), "flag": slice(7, 9), "width": slice(10, 20), "uncertainty": slice(20, 30)},
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
        "flag1": slice(6, 7),
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
            # Card11ParameterType.ETA: EtaParameters,
            # Card11ParameterType.GAMMA: GammaParameters,
            # Card11ParameterType.TZERO: TzeroParameters,
            # Add other parameter classes as implemented
        }

        parser_class = parameter_classes.get(param_type)
        if parser_class is None:
            logging.warning(f"Parser not yet implemented for parameter type: {param_type}")
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
            l1_coefficient=l1_coeff, l1_uncertainty=l1_unc, l0_constant=l0_const, l0_uncertainty=l0_unc, l1_flag=l1_flag, l0_flag=l0_flag
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


if __name__ == "__main__":
    print("Refer to unit tests for usage examples.")
