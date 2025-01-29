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

Continuation lines are indicated by "-1" in columns 79-80 (standard format)
or column 80 (extended format). These lines contain only additional spin
group numbers in the same format as the parent line.

Notes:
- All isotopes in the sample should have entries
- Abundances must sum to ≤ 1.0
- Masses must be > 0
- Spin groups must be valid for the model
"""

import logging
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from pleiades.sammy.parameters.helper import VaryFlag, format_float, format_vary, safe_parse

# Format definitions for standard format (<99 spin groups)
# Each numeric field has specific width requirements
FORMAT_STANDARD = {
    "mass": slice(0, 10),  # AMUISO: Atomic mass (amu)
    "abundance": slice(10, 20),  # PARISO: Fractional abundance
    "uncertainty": slice(20, 30),  # DELISO: Uncertainty on abundance
    "flag": slice(30, 32),  # IFLISO: Treatment flag
}

# Format for extended format (>99 spin groups)
FORMAT_EXTENDED = {
    "mass": slice(0, 10),  # AMUISO: Atomic mass (amu)
    "abundance": slice(10, 20),  # PARISO: Fractional abundance
    "uncertainty": slice(20, 30),  # DELISO: Uncertainty on abundance
    "flag": slice(30, 35),  # IFLISO: Treatment flag
}

# Spin group number positions
# Standard format: 2 columns per group starting at col 33
# Extended format: 5 columns per group starting at col 36
SPIN_GROUP_STANDARD = {
    "width": 2,
    "start": 32,
    "per_line": 24,  # Max groups per line
    "cont_marker": slice(78, 80),  # "-1" indicates continuation
}

SPIN_GROUP_EXTENDED = {
    "width": 5,
    "start": 35,
    "per_line": 9,  # Max groups per line
    "cont_marker": slice(79, 80),  # "-1" indicates continuation
}

# Valid header strings
CARD_10_HEADERS = ["ISOTOpic abundances and masses", "NUCLIde abundances and masses"]


class IsotopeParameters(BaseModel):
    """Container for a single isotope's parameters.

    This class handles the parameters for one isotope entry in Card Set 10,
    including mass, abundance, uncertainty, treatment flag, and associated
    spin groups.

    The fixed-width format uses:
    - Standard format (<99 groups): 2 columns per group starting at col 33
    - Extended format (>99 groups): 5 columns per group starting at col 36

    Attributes:
        mass (float): Atomic mass in atomic mass units (amu)
        abundance (float): Fractional abundance (dimensionless)
        uncertainty (Optional[float]): Uncertainty on abundance (dimensionless)
        flag (VaryFlag): Treatment flag for abundance (-2=use input, 0=fixed, 1=vary, 3=PUP)
        spin_groups (List[int]): List of spin group numbers (negative values indicate omitted resonances)

    Example:
        Standard format line:
        "16.000    0.99835   0.00002    0  1  2  3"
                                          ^  ^  ^  ^ spin groups (2 cols each)
                                       ^^ flag
                              ^^^^^^^ uncertainty
                     ^^^^^^^ abundance
            ^^^^^^^ mass
    """

    mass: float = Field(description="Atomic mass in amu", gt=0)
    abundance: float = Field(description="Fractional abundance", ge=0, le=1)
    uncertainty: Optional[float] = Field(None, description="Uncertainty on abundance")
    flag: VaryFlag = Field(default=VaryFlag.NO, description="Treatment flag for abundance")
    spin_groups: List[int] = Field(default_factory=list, description="Spin group numbers")

    @model_validator(mode="after")
    def validate_groups(self) -> "IsotopeParameters":
        """Validate spin group constraints.

        Validates:
        - Group numbers are non-zero
        - Negative groups only used to indicate omitted resonances
        - Group numbers are within valid range for format

        Returns:
            IsotopeParameters: Self if validation passes

        Raises:
            ValueError: If spin group validation fails
        """
        max_standard = 99  # Maximum group number for standard format

        for group in self.spin_groups:
            if group == 0:
                raise ValueError("Spin group number cannot be 0")

            # Check if we need extended format
            if abs(group) > max_standard:
                logging.debug(f"Group number {group} requires extended format")

        return self

    @classmethod
    def from_lines(cls, lines: List[str], extended: bool = False) -> "IsotopeParameters":
        """Parse isotope parameters from fixed-width format lines.

        Args:
            lines: List of input lines (first line contains main parameters,
                  subsequent lines are continuation lines for spin groups)
            extended: Whether to use extended format for >99 spin groups
                     (affects field widths and positions)

        Returns:
            IsotopeParameters: Parsed parameters with validated values

        Raises:
            ValueError: If lines are invalid, required data is missing,
                       or values fail validation

        Example:
            >>> lines = [
            ...     "16.000    0.99835   0.00002    0  1  2  3",
            ...     "  4  5  6 -1"  # Continuation line with -1 marker
            ... ]
            >>> params = IsotopeParameters.from_lines(lines)
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        # Parse main parameters from first line
        format_dict = FORMAT_EXTENDED if extended else FORMAT_STANDARD
        main_line = f"{lines[0]:<80}"  # Pad to full width

        params = {}

        # Parse required numeric fields
        for field in ["mass", "abundance"]:
            value = safe_parse(main_line[format_dict[field]])
            if value is None:
                raise ValueError(f"Failed to parse required field: {field}")
            params[field] = value

        # Parse optional uncertainty
        params["uncertainty"] = safe_parse(main_line[format_dict["uncertainty"]])

        # Parse flag
        flag_str = main_line[format_dict["flag"]].strip() or "0"
        try:
            params["flag"] = VaryFlag(int(flag_str))
        except (ValueError, TypeError):
            params["flag"] = VaryFlag.NO

        # Parse spin groups
        spin_groups = []
        group_format = SPIN_GROUP_EXTENDED if extended else SPIN_GROUP_STANDARD

        # Helper function to parse groups from a line
        def parse_groups(line: str, start_pos: int = None, continuation: bool = False) -> List[int]:
            """Parse spin groups from a line.

            Args:
                line: Input line
                start_pos: Starting position for parsing
                continuation: Whether this is a continuation line (always 5 cols)

            Returns:
                List of parsed group numbers
            """
            groups = []
            pos = start_pos if start_pos is not None else group_format["start"]

            # Always use 5 columns for continuation lines
            width = 5 if continuation else group_format["width"]

            while pos + width <= len(line):
                # Check for continuation marker in main line
                if not continuation and pos + width > group_format["cont_marker"].start:
                    break

                group_str = line[pos : pos + width].strip()
                if group_str:
                    group = safe_parse(group_str, as_int=True)
                    if group is not None:
                        groups.append(group)
                pos += width
            return groups

        # Parse groups from first line
        spin_groups.extend(parse_groups(main_line))

        # Parse continuation lines with 5-col format
        for line in lines[1:]:
            if not line.strip():
                continue
            line = f"{line:<80}"  # Pad to full width
            spin_groups.extend(parse_groups(line, start_pos=0, continuation=True))

        params["spin_groups"] = spin_groups
        return cls(**params)

    def to_lines(self, extended: bool = False) -> List[str]:
        """Convert the parameters to fixed-width format lines.

        Args:
            extended: Whether to use extended format for >99 spin groups

        Returns:
            List[str]: Formatted lines with proper fixed-width spacing

        Example:
            >>> params = IsotopeParameters(mass=16.0, abundance=0.99835,
            ...                           uncertainty=0.00002, flag=VaryFlag.NO,
            ...                           spin_groups=[1, 2, 3, 4, 5, 6])
            >>> lines = params.to_lines()
            >>> print(lines[0])
            "16.000    0.99835   0.00002    0  1  2  3"
        """
        # Select format based on mode
        group_format = SPIN_GROUP_EXTENDED if extended else SPIN_GROUP_STANDARD
        format_dict = FORMAT_EXTENDED if extended else FORMAT_STANDARD

        # Format main parameters with proper field widths
        main_parts = [
            format_float(self.mass, width=format_dict["mass"].stop - format_dict["mass"].start),
            format_float(self.abundance, width=format_dict["abundance"].stop - format_dict["abundance"].start),
            format_float(self.uncertainty, width=format_dict["uncertainty"].stop - format_dict["uncertainty"].start),
            format_vary(self.flag).rjust(format_dict["flag"].stop - format_dict["flag"].start),
        ]

        lines = []
        current_line = "".join(main_parts)

        # Add spin groups with continuation lines as needed
        groups_per_line = group_format["per_line"]
        group_width = group_format["width"]

        for i in range(0, len(self.spin_groups), groups_per_line):
            group_chunk = self.spin_groups[i : i + groups_per_line]
            group_str = "".join(str(g).rjust(group_width) for g in group_chunk)

            if i == 0:
                # First line includes main parameters
                lines.append(f"{current_line}{group_str}")
            else:
                # Continuation lines
                needs_continuation = i + groups_per_line < len(self.spin_groups)
                if needs_continuation:
                    # Add continuation marker using proper slice
                    marker_slice = group_format["cont_marker"]
                    padded_line = f"{group_str:<{marker_slice.stop}}"
                    lines.append(f"{padded_line[:-2]}-1")
                else:
                    lines.append(group_str)

        return lines


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

    Example:
        >>> lines = [
        ...     "ISOTOpic abundances and masses",
        ...     "16.000    0.99835   0.00002    0  1  2  3",
        ...     "17.000    0.00165   0.00001    0  4  5  6",
        ...     ""
        ... ]
        >>> card = IsotopeCard.from_lines(lines)
    """

    isotopes: List[IsotopeParameters] = Field(default_factory=list)
    extended: bool = Field(default=False, description="Use extended format for >99 spin groups")

    @model_validator(mode="after")
    def validate_abundances(self) -> "IsotopeCard":
        """Validate that total abundance doesn't exceed 1.0.

        Returns:
            IsotopeCard: Self if validation passes

        Raises:
            ValueError: If total abundance > 1.0
        """
        total = sum(iso.abundance for iso in self.isotopes)
        if total > 1.0:
            raise ValueError(f"Total abundance {total} exceeds 1.0")
        return self

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if line matches any valid header format
        """
        line_upper = line.strip().upper()
        return any(header.upper() in line_upper for header in CARD_10_HEADERS)

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
        if not lines:
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Remove header and trailing blank lines
        content_lines = [line for line in lines[1:] if line.strip()]
        if not content_lines:
            raise ValueError("No parameter lines found")

        # Check if we need extended format
        extended = False
        for line in content_lines:
            # Look for any spin group number > 99 in the data
            numbers = [int(n) for n in line.split() if n.strip().isdigit()]
            if any(abs(n) > 99 for n in numbers):
                extended = True
                break

        # Parse isotopes
        isotopes = []
        current_lines = []

        for line in content_lines:
            # If line starts with a number, it's a new isotope
            if line.strip() and line[0].isdigit():
                if current_lines:
                    isotopes.append(IsotopeParameters.from_lines(current_lines, extended=extended))
                current_lines = []
            current_lines.append(line)

        # Don't forget the last isotope
        if current_lines:
            isotopes.append(IsotopeParameters.from_lines(current_lines, extended=extended))

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
