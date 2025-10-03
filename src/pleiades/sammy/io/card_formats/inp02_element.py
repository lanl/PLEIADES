#!/usr/bin/env python
"""
Card Set 2 (Element Information) for SAMMY INP files.

This module provides the Card02 class for parsing and generating the element
information line in SAMMY input files. This card appears early in the INP file
and defines the sample element, atomic weight, and energy range.

Format specification (Card Set 2):
    Cols    Format  Variable    Description
    1-10    A       ELMNT       Sample element's name (left-aligned)
    11-20   F       AW          Atomic weight (amu)
    21-30   F       EMIN        Minimum energy for dataset (eV)
    31-40   F       EMAX        Maximum energy (eV)

Example:
    Si        27.976928 300000.   1800000.
"""

from typing import List

from pydantic import BaseModel, Field

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

# Format specification for Card Set 2
CARD02_FORMAT = {
    "element": slice(0, 10),
    "atomic_weight": slice(10, 20),
    "min_energy": slice(20, 30),
    "max_energy": slice(30, 40),
}


class ElementInfo(BaseModel):
    """Pydantic model for element information in Card Set 2.

    Attributes:
        element: Sample element's name (up to 10 characters)
        atomic_weight: Atomic weight in amu
        min_energy: Minimum energy for dataset in eV
        max_energy: Maximum energy in eV
    """

    element: str = Field(..., description="Sample element's name", max_length=10)
    atomic_weight: float = Field(..., description="Atomic weight (amu)", gt=0)
    min_energy: float = Field(..., description="Minimum energy (eV)", ge=0)
    max_energy: float = Field(..., description="Maximum energy (eV)", gt=0)

    def model_post_init(self, __context) -> None:
        """Validate that max_energy > min_energy."""
        if self.max_energy <= self.min_energy:
            raise ValueError(f"max_energy ({self.max_energy}) must be greater than min_energy ({self.min_energy})")


class Card02(BaseModel):
    """
    Class representing Card Set 2 (element information) in SAMMY INP files.

    This card defines the sample element, atomic weight, and energy range for the analysis.
    """

    @classmethod
    def from_lines(cls, lines: List[str]) -> ElementInfo:
        """Parse element information from Card Set 2 line.

        Args:
            lines: List of input lines (expects single line for Card 2)

        Returns:
            ElementInfo: Parsed element information

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            message = "No valid Card 2 line provided"
            logger.error(message)
            raise ValueError(message)

        line = lines[0]
        if len(line) < 40:
            line = f"{line:<40}"

        try:
            element = line[CARD02_FORMAT["element"]].strip()
            atomic_weight = float(line[CARD02_FORMAT["atomic_weight"]].strip())
            min_energy = float(line[CARD02_FORMAT["min_energy"]].strip())
            max_energy = float(line[CARD02_FORMAT["max_energy"]].strip())
        except (ValueError, IndexError) as e:
            message = f"Failed to parse Card 2 line: {e}"
            logger.error(message)
            raise ValueError(message)

        if not element:
            message = "Element name cannot be empty"
            logger.error(message)
            raise ValueError(message)

        return ElementInfo(
            element=element,
            atomic_weight=atomic_weight,
            min_energy=min_energy,
            max_energy=max_energy,
        )

    @classmethod
    def to_lines(cls, element_info: ElementInfo) -> List[str]:
        """Convert element information to Card Set 2 formatted line.

        Args:
            element_info: ElementInfo object containing element data

        Returns:
            List containing single formatted line for Card Set 2
        """
        if not isinstance(element_info, ElementInfo):
            message = "element_info must be an instance of ElementInfo"
            logger.error(message)
            raise ValueError(message)

        line = (
            f"{element_info.element:<10s}"
            f"{element_info.atomic_weight:10.6f}"
            f"{element_info.min_energy:10.3f}"
            f"{element_info.max_energy:10.1f}"
        )

        return [line]
