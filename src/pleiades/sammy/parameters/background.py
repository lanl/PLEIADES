#!/usr/bin/env python
"""Parsers and containers for SAMMY's Card Set 13 background function parameters.

This module implements parsers and containers for Card Set 13 background parameters
which can appear in either the PARameter or INPut file.

Format specification from Table VI B.2:
Card Set 13 contains background function parameters with distinct formats:
1. CONST - Constant background
2. EXPON - Exponential background
3. POWER - Power law background
4. EXPLN - Exponential with logarithmic terms
5. T-PNT - Point-wise linear function of time
6. E-PNT - Point-wise linear function of energy
7. TFILE - File-based time function
8. EFILE - File-based energy function
9. AETOB - Power of energy

Currently unimplemented - placeholder for future development.
"""

from enum import Enum
from typing import List

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
        # TODO: Implement Card Set 13 background parameter parsing
        raise NotImplementedError("Card Set 13 background parameter parsing is not yet implemented")

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines.

        Raises:
            NotImplementedError: This class is not yet implemented
        """
        # TODO: Implement Card Set 13 background parameter formatting
        raise NotImplementedError("Card Set 13 background parameter formatting is not yet implemented")
