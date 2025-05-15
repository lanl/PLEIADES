#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

# Format definitions for standard format (<99 spin groups)
# Each numeric field has specific width requirements
FORMAT_STANDARD = {
    "mass": slice(0, 10),  # AMUISO: Atomic mass (amu)
    "abundance": slice(10, 20),  # PARISO: Fractional abundance
    "uncertainty": slice(20, 30),  # DELISO: Uncertainty on abundance
    "flag": slice(30, 32),  # IFLISO: Treatment flag
}

# Spin group number positions
# Standard format: 2 columns per group starting at col 33
SPIN_GROUP_STANDARD = {
    "width": 2,  # Character width of each group number
    "start": 32,  # Start of first group
    "per_line": 24,  # Max groups per line
    "cont_marker": slice(78, 80),  # "-1" indicates continuation
}

# Format for extended format (>99 spin groups)
FORMAT_EXTENDED = {
    "mass": slice(0, 10),  # AMUISO: Atomic mass (amu)
    "abundance": slice(10, 20),  # PARISO: Fractional abundance
    "uncertainty": slice(20, 30),  # DELISO: Uncertainty on abundance
    "flag": slice(30, 35),  # IFLISO: Treatment flag
}

SPIN_GROUP_EXTENDED = {
    "width": 5,
    "start": 35,
    "per_line": 9,  # Max groups per line
    "cont_marker": slice(79, 80),  # "-1" indicates continuation
}

# Valid header strings
CARD_10_HEADERS = ["ISOTOpic abundances and masses", "NUCLIde abundances and masses"]


class Card10(BaseModel):
    """Container for a complete isotope parameter card set (Card Set 10).

    This class handles a complete Card Set 10, including:
    - Header line validation
    - Multiple isotope entries
    - Total abundance validation
    - Format selection (standard vs extended)

    NOTE:   Fixed formats for both standard and extended are defined in the
            IsotopeParameters class. But only using the standard format for now.
    """

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if the first 5 characters of the line are 'ISOTO'
        """

        return line.strip().upper().startswith("ISOTO") or line.strip().upper().startswith("NUCLI")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "Card10":
        """Parse a complete isotope parameter card set from lines.

        Args:
            lines: List of input lines including header and blank terminator

        Returns:
            Card10: Parsed card set

        Raises:
            ValueError: If no valid header found or invalid format
        """

        if not lines:
            logger.error("No lines provided")
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            logger.error(f"Invalid header line: {lines[0]}")
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Remove header and trailing blank lines
        content_lines = [line for line in lines[1:] if line.strip()]
        if not content_lines:
            logger.error("No parameter lines found")
            raise ValueError("No parameter lines found")

        # Check if we need extended format
        extended = False
