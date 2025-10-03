#!/usr/bin/env python
"""Parsers and containers for SAMMY's Card Set 12 paramagnetic cross section parameters.

This module implements parsers and containers for Card Set 12 paramagnetic parameters
which can appear in either the PARameter or INPut file.

Format specification from Table VI B.2:
Card Set 12 contains paramagnetic cross section parameters with distinct format:
- Header line with "PARAMagnetic cross section parameters follow"
- Main parameter line with nuclide type and A,B,P values
- Additional line with isotope and C parameter values
- Blank terminator line

The main parameter line has nuclide-specific parameters (TM, ER, or HO)
with corresponding A,B,P values and flags. The isotope line contains
additional C parameter values.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from pleiades.utils.helper import VaryFlag, format_float, format_vary, safe_parse

# Format definitions - column positions for each line type
FORMAT_SPECS = {
    "PARAMAG_HEADER": {
        "identifier": slice(0, 80),  # Full line for header matching
    },
    "PARAMAG_MAIN": {
        "nuclide": slice(0, 5),  # TM/ER/HO type (2 chars + 3 spaces)
        "flag_a": slice(6, 7),  # Flag for A parameter
        "flag_b": slice(8, 9),  # Flag for B parameter
        "flag_p": slice(9, 10),  # Flag for P parameter
        "a_value": slice(10, 20),  # A value
        "a_unc": slice(20, 30),  # A uncertainty
        "b_value": slice(30, 40),  # B value
        "b_unc": slice(40, 50),  # B uncertainty
        "p_value": slice(50, 60),  # P value
        "p_unc": slice(60, 70),  # P uncertainty
    },
    "PARAMAG_ISO": {
        "iso": slice(6, 7),  # Isotope number
        "flag_c": slice(8, 9),  # Flag for C parameter
        "c_value": slice(10, 20),  # C value
        "c_unc": slice(20, 30),  # C uncertainty
    },
}


class NuclideType(str, Enum):
    """Valid nuclide types for paramagnetic parameters."""

    TM = "TM"  # Thulium
    ER = "ER"  # Erbium
    HO = "HO"  # Holmium


class ParamagneticParameters(BaseModel):
    """Container for Card Set 12 paramagnetic parameters.

    Format specification from Table VI B.2:
    Card Set 12 requires multiple lines:
    1. Header line with "PARAMagnetic cross section parameters follow"
    2. Main parameter line with format:
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
    3. Additional parameter line:
       7       I      ISO         Isotope number
       9       I      IFC         Flag to vary C
       11-20   F      C           C parameter value
       21-30   F      dC          Uncertainty on C
    4. Blank terminator line

    Attributes:
        nuclide_type: Type of nuclide (TM, ER, or HO)
        a_value: A parameter value
        a_uncertainty: Uncertainty on A parameter
        b_value: B parameter value
        b_uncertainty: Uncertainty on B parameter
        p_value: P parameter value
        p_uncertainty: Uncertainty on P parameter
        isotope_number: Isotope number (must be positive)
        c_value: C parameter value
        c_uncertainty: Uncertainty on C parameter
        a_flag: Flag for varying A parameter
        b_flag: Flag for varying B parameter
        p_flag: Flag for varying P parameter
        c_flag: Flag for varying C parameter
    """

    nuclide_type: NuclideType = Field(..., description="Type of nuclide")
    a_value: float = Field(..., description="A parameter value")
    a_uncertainty: Optional[float] = Field(None, description="Uncertainty on A")
    b_value: float = Field(..., description="B parameter value")
    b_uncertainty: Optional[float] = Field(None, description="Uncertainty on B")
    p_value: float = Field(..., description="P parameter value")
    p_uncertainty: Optional[float] = Field(None, description="Uncertainty on P")
    isotope_number: int = Field(..., gt=0, description="Isotope number")
    c_value: float = Field(..., description="C parameter value")
    c_uncertainty: Optional[float] = Field(None, description="Uncertainty on C")
    a_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for A")
    b_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for B")
    p_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for P")
    c_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for C")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "ParamagneticParameters":
        """Parse paramagnetic parameters from fixed-width format lines.

        Args:
            lines: List containing header, parameter lines, and blank terminator

        Returns:
            ParamagneticParameters: Parsed parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or len(lines) != 4:
            raise ValueError("Paramagnetic parameters require exactly 4 lines")

        # Verify header line
        header = lines[0].strip()
        if not header.startswith("PARAMagnetic cross section parameters"):
            raise ValueError(f"Invalid header line: {header}")

        # Verify blank terminator
        if lines[3].strip():
            raise ValueError("Last line must be blank")

        # Parse main parameter line
        main_line = f"{lines[1]:<80}"  # Pad to full width

        # Verify and parse nuclide type
        nuclide = main_line[FORMAT_SPECS["PARAMAG_MAIN"]["nuclide"]].strip()
        try:
            nuclide_type = NuclideType(nuclide.rstrip())
        except ValueError:
            raise ValueError(f"Invalid nuclide type: {nuclide}")

        # Parse flags
        try:
            a_flag = VaryFlag(int(main_line[FORMAT_SPECS["PARAMAG_MAIN"]["flag_a"]].strip() or "0"))
            b_flag = VaryFlag(int(main_line[FORMAT_SPECS["PARAMAG_MAIN"]["flag_b"]].strip() or "0"))
            p_flag = VaryFlag(int(main_line[FORMAT_SPECS["PARAMAG_MAIN"]["flag_p"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid flag value in main line: {e}")

        # Parse required main values
        a_value = safe_parse(main_line[FORMAT_SPECS["PARAMAG_MAIN"]["a_value"]])
        b_value = safe_parse(main_line[FORMAT_SPECS["PARAMAG_MAIN"]["b_value"]])
        p_value = safe_parse(main_line[FORMAT_SPECS["PARAMAG_MAIN"]["p_value"]])

        if any(v is None for v in [a_value, b_value, p_value]):
            raise ValueError("Missing required A, B, or P value")

        # Parse optional uncertainties
        a_unc = safe_parse(main_line[FORMAT_SPECS["PARAMAG_MAIN"]["a_unc"]])
        b_unc = safe_parse(main_line[FORMAT_SPECS["PARAMAG_MAIN"]["b_unc"]])
        p_unc = safe_parse(main_line[FORMAT_SPECS["PARAMAG_MAIN"]["p_unc"]])

        # Parse isotope line
        iso_line = f"{lines[2]:<80}"  # Pad to full width

        # Parse isotope number
        iso_num = safe_parse(iso_line[FORMAT_SPECS["PARAMAG_ISO"]["iso"]], as_int=True)
        if iso_num is None or iso_num <= 0:
            raise ValueError("Invalid or missing isotope number")

        # Parse C parameter flag and values
        try:
            c_flag = VaryFlag(int(iso_line[FORMAT_SPECS["PARAMAG_ISO"]["flag_c"]].strip() or "0"))
        except ValueError as e:
            raise ValueError(f"Invalid C flag value: {e}")

        c_value = safe_parse(iso_line[FORMAT_SPECS["PARAMAG_ISO"]["c_value"]])
        if c_value is None:
            raise ValueError("Missing required C value")

        c_unc = safe_parse(iso_line[FORMAT_SPECS["PARAMAG_ISO"]["c_unc"]])

        return cls(
            nuclide_type=nuclide_type,
            a_value=a_value,
            a_uncertainty=a_unc,
            b_value=b_value,
            b_uncertainty=b_unc,
            p_value=p_value,
            p_uncertainty=p_unc,
            isotope_number=iso_num,
            c_value=c_value,
            c_uncertainty=c_unc,
            a_flag=a_flag,
            b_flag=b_flag,
            p_flag=p_flag,
            c_flag=c_flag,
        )

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines.

        Returns:
            List containing header, parameter lines, and blank terminator
        """
        # Header line
        lines = ["PARAMagnetic cross section parameters follow"]

        # Main parameter line
        main_parts = [
            f"{self.nuclide_type.value} ".ljust(5),  # Nuclide with required spaces
            " ",  # Column 6 spacing
            format_vary(self.a_flag),
            " ",  # Column 8 spacing
            format_vary(self.b_flag),
            format_vary(self.p_flag),
            format_float(self.a_value, width=10),
            format_float(self.a_uncertainty, width=10),
            format_float(self.b_value, width=10),
            format_float(self.b_uncertainty, width=10),
            format_float(self.p_value, width=10),
            format_float(self.p_uncertainty, width=10),
        ]
        lines.append("".join(main_parts))

        # Isotope parameter line
        iso_parts = [
            "     ",  # First 5 columns blank
            " ",  # Column 6 spacing
            f"{self.isotope_number:1d}",
            " ",  # Column 8 spacing
            format_vary(self.c_flag),
            " ",  # Column 10 spacing
            format_float(self.c_value, width=10),
            format_float(self.c_uncertainty, width=10),
        ]
        lines.append("".join(iso_parts))

        # Blank terminator
        lines.append("")

        return lines


if __name__ == "__main__":
    print("Refer to tests for usage examples.")
