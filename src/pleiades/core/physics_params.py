from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class BackgroundType(str, Enum):
    """Types of background functions available."""

    CONST = "CONST"  # Constant background
    EXPON = "EXPON"  # Exponential background
    POWER = "POWER"  # Power law background
    EXPLN = "EXPLN"  # Exponential with logarithmic terms
    T_PNT = "T-PNT"  # Point-wise linear in time
    E_PNT = "E-PNT"  # Point-wise linear in energy
    TFILE = "TFILE"  # Time function from file
    EFILE = "EFILE"  # Energy function from file
    AETOB = "AETOB"  # Power of energy


class BackgroundParameters(BaseModel):
    """Container for Card Set 13 background function parameters.

    Currently unimplemented - placeholder for future development.

    Format specification from Table VI B.2:
    Cols    Format  Variable    Description
    1-80    A       WHAT        "BACKGround functions"

    Followed by one or more background function definitions.
    """

    type: BackgroundType = Field(..., description="Type of background function")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "BackgroundParameters":
        """Parse background parameters from fixed-width format lines.

        Args:
            lines: List of input lines for background parameters

        Raises:
            NotImplementedError: This class is not yet implemented
        """
        raise NotImplementedError("Card Set 13 background parameter parsing is not yet implemented")

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines.

        Raises:
            NotImplementedError: This class is not yet implemented
        """
        raise NotImplementedError("Card Set 13 background parameter formatting is not yet implemented")


class BroadeningParameters(BaseModel):
    """Container for a single set of broadening parameters.

    Contains all parameters from a single card set 4 entry including:
    - Main parameters (CRFN, TEMP, etc.)
    - Their uncertainties
    - Additional Gaussian parameters
    - Flags indicating whether each parameter should be varied

    Note on fixed-width format:
    Each numeric field in the file uses a 10-column width with a 9+1 pattern:
    - 9 characters for the actual numeric data (e.g. "1.2340E+00")
    - 1 character for space separator
    This format ensures human readability while maintaining proper fixed-width alignment.
    """

    # Main parameters
    crfn: float = Field(description="Matching radius (F)")
    temp: float = Field(description="Effective temperature (K)")
    thick: float = Field(description="Sample thickness (atoms/barn)")
    deltal: float = Field(description="Spread in flight-path length (m)")
    deltag: float = Field(description="Gaussian resolution width (μs)")
    deltae: float = Field(description="e-folding width of exponential resolution (μs)")

    # Optional uncertainties for main parameters
    d_crfn: Optional[float] = Field(None, description="Uncertainty on CRFN")
    d_temp: Optional[float] = Field(None, description="Uncertainty on TEMP")
    d_thick: Optional[float] = Field(None, description="Uncertainty on THICK")
    d_deltal: Optional[float] = Field(None, description="Uncertainty on DELTAL")
    d_deltag: Optional[float] = Field(None, description="Uncertainty on DELTAG")
    d_deltae: Optional[float] = Field(None, description="Uncertainty on DELTAE")

    # Optional additional Gaussian parameters
    deltc1: Optional[float] = Field(None, description="Width of Gaussian, constant in energy (eV)")
    deltc2: Optional[float] = Field(None, description="Width of Gaussian, linear in energy (unitless)")
    d_deltc1: Optional[float] = Field(None, description="Uncertainty on DELTC1")
    d_deltc2: Optional[float] = Field(None, description="Uncertainty on DELTC2")

    # Vary flags for all parameters
    flag_crfn: VaryFlag = Field(default=VaryFlag.NO)
    flag_temp: VaryFlag = Field(default=VaryFlag.NO)
    flag_thick: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltal: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltag: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltae: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltc1: Optional[VaryFlag] = Field(None)
    flag_deltc2: Optional[VaryFlag] = Field(None)

    @model_validator(mode="after")
    def validate_gaussian_parameters(self) -> "BroadeningParameters":
        """Validate that if any Gaussian parameter is present, both are present."""
        has_deltc1 = self.deltc1 is not None
        has_deltc2 = self.deltc2 is not None
        if has_deltc1 != has_deltc2:
            raise ValueError("Both DELTC1 and DELTC2 must be present if either is present")
        if has_deltc1:
            if self.flag_deltc1 is None or self.flag_deltc2 is None:
                raise ValueError("Flags must be specified for DELTC1 and DELTC2 if present")
        return self