#!/usr/bin/env python
"""Data classes for card 10::isotopic abundances and masses.

This module implements parsers and containers for SAMMY's Card Set 10 parameters,
which specify isotopic abundances, masses and spin group assignments.

Format specification from Table VI B.2:
Card Set 10 has a fixed-width format with possible continuation lines:

Header line: "ISOTOpic abundances and masses" or "NUCLIde abundances and masses"

For standard format (<99 total spin groups):
Cols    Format  Variable    Description
1-10    F       AMUISO     Atomic mass (amu)
11-20   F       PARISO     Fractional abundance (dimensionless)
21-30   F       DELISO     Uncertainty on abundance (dimensionless)
31-32   I       IFLISO     Flag for abundance treatment:
                           -2 = use value from INPut file
                            0 = do not vary
                            1 = vary
                            3 = treat as PUP
33-34   I       IGRISO     First spin group number
35-36   I       IGRISO     Second spin group number
...etc for up to 24 groups per line

For extended format (>99 total spin groups):
Cols    Format  Variable    Description
1-10    F       AMUISO     Atomic mass (amu)
11-20   F       PARISO     Fractional abundance (dimensionless)
21-30   F       DELISO     Uncertainty on abundance (dimensionless)
31-35   I       IFLISO     Flag for abundance treatment
36-40   I       IGRISO     First spin group number
41-45   I       IGRISO     Second spin group number
...etc for up to 9 groups per line

NOTE: the extended format is currently not supported with pleiades.

Continuation lines are indicated by "-1" in columns 79-80 (standard format)
or column 80 (extended format). These lines contain only additional spin
group numbers in the same format as the parent line.

Notes:
- All isotopes in the sample should have entries
- Abundances must sum to ≤ 1.0
- Masses must be > 0
- Spin groups must be valid for the model
"""

import os
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from pleiades.core.helper import VaryFlag, format_float, format_vary, safe_parse
from pleiades.utils.logger import Logger, _log_and_raise_error

# Initialize logger with file logging
log_file_path = os.path.join(os.getcwd(), "pleiades-par.log")
logger = Logger(__name__, log_file=log_file_path)

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


class IsotopeCard(BaseModel):
    """Container for a complete isotope parameter card set (Card Set 10).

    This class handles a complete Card Set 10, including:
    - Header line validation
    - Multiple isotope entries
    - Total abundance validation
    - Format selection (standard vs extended)

    Attributes:
        isotopes (List[IsotopeParameters]): List of isotope parameter sets
        extended (bool): Whether to use extended format for >99 spin groups

    NOTE:   Fixed formats for both standard and extended are defined in the
            IsotopeParameters class. But only using the standard format for now.
    """

    isotopes: List["IsotopeParameters"] = Field(default_factory=list)
    extended: bool = Field(default=False, description="Use extended format for >99 spin groups")

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if the first 5 characters of the line are 'ISOTO'
        """
        where_am_i = "IsotopeCard.is_header_line()"
        logger.info(f"{where_am_i}: Checking if valid header line: {line}")
        return line.strip().upper().startswith("ISOTO") or line.strip().upper().startswith("NUCLI")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "IsotopeCard":
        """Parse a complete isotope parameter card set from lines.

        Args:
            lines: List of input lines including header and blank terminator

        Returns:
            IsotopeCard: Parsed card set

        Raises:
            ValueError: If no valid header found or invalid format
        """
        where_am_i = "IsotopeCard.from_lines()"
        logger.info(f"{where_am_i}: Attempting to parse isotope card from lines")

        if not lines:
            _log_and_raise_error(logger, "No lines provided", ValueError)

        # Validate header
        if not cls.is_header_line(lines[0]):
            _log_and_raise_error(logger, f"Invalid header line: {lines[0]}", ValueError)

        # Remove header and trailing blank lines
        content_lines = [line for line in lines[1:] if line.strip()]
        if not content_lines:
            _log_and_raise_error(logger, "No parameter lines found", ValueError)

        # Check if we need extended format
        extended = False

        # Parse isotopes
        isotopes = []
        current_lines = []

        for line in content_lines:
            current_lines.append(line)

            # check if characters 79-80 is a "-1". this means that there are more spin groups in the next line.
            if line[78:80] == "-1":
                continue

            # Otherwise the are no more lines for spin groups, so process the current lines.
            else:
                from pleiades.core.nuclear_params import IsotopeParameters  # Delayed import to avoid circular import
                isotopes.append(IsotopeParameters.from_lines(current_lines, extended=extended))
                current_lines = []

        return cls(isotopes=isotopes, extended=extended)

    def to_lines(self) -> List[str]:
        """Convert the card set to a list of lines.

        Returns:
            List[str]: Lines including header, parameters, and blank terminator
        """
        lines = [CARD_10_HEADERS[0]]  # Use first header format by default

        for isotope in self.isotopes:
            iso_lines = isotope.to_lines(extended=self.extended)
            lines.extend(iso_lines)

        lines.append("")  # Terminating blank line
        return lines


if __name__ == "__main__":
    print("Refer to unit tests for usage examples.")