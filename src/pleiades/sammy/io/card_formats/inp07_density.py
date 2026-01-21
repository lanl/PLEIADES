#!/usr/bin/env python
"""
Card Set 7 (Sample Thickness) for SAMMY INP files.

This module provides the Card07 class for parsing and generating the Card Set 7
line in SAMMY input files. This line appears after the broadening constants and
defines the matching radius and sample thickness.

Format specification (Card Set 7):
    The line contains two floating-point values:
    - CRFN: Matching radius (F)
    - THICK: Sample thickness (atoms/barn)

Example:
       4.20000  0.347162
"""

from typing import List

from pydantic import BaseModel, Field

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class Card07Parameters(BaseModel):
    """Pydantic model for Card Set 7 parameters."""

    crfn: float = Field(..., description="Matching radius (F)", ge=0)
    thick: float = Field(..., description="Sample thickness (atoms/barn)", ge=0)


class Card07(BaseModel):
    """Class representing Card Set 7 line in SAMMY INP files."""

    @classmethod
    def from_lines(cls, lines: List[str]) -> Card07Parameters:
        """Parse Card Set 7 parameters from line.

        Args:
            lines: List of input lines (expects single line)

        Returns:
            Card07Parameters: Parsed Card Set 7 parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            message = "No valid Card 7 line provided"
            logger.error(message)
            raise ValueError(message)

        line = lines[0].strip()
        fields = line.split()

        if len(fields) < 2:
            message = f"Card 7 line must have at least 2 fields (CRFN, THICK), got {len(fields)}"
            logger.error(message)
            raise ValueError(message)

        try:
            crfn = float(fields[0])
            thick = float(fields[1])
        except (ValueError, IndexError) as e:
            message = f"Failed to parse Card 7 line: {e}"
            logger.error(message)
            raise ValueError(message)

        return Card07Parameters(
            crfn=crfn,
            thick=thick,
        )

    @classmethod
    def to_lines(cls, params: Card07Parameters) -> List[str]:
        """Convert Card Set 7 parameters to formatted line.

        Args:
            params: Card07Parameters object containing CRFN/THICK values

        Returns:
            List containing single formatted line
        """
        if not isinstance(params, Card07Parameters):
            message = "params must be an instance of Card07Parameters"
            logger.error(message)
            raise ValueError(message)

        line = f"  {params.crfn:8.6f} {params.thick:.6e}"

        return [line]
