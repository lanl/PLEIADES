#!/usr/bin/env python
"""Data class for card 03::external R-function parameters."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from pleiades.utils.helper import VaryFlag, format_float, format_vary, safe_parse
from pleiades.utils.logger import loguru_logger


class ExternalRFormat(Enum):
    FORMAT_3 = "3"  # Standard format
    FORMAT_3A = "3a"  # Alternative compact format


# For Format 3
FORMAT_3 = {
    "spin_group": slice(0, 3),  # Fortran 1-3
    "channel": slice(3, 5),  # Fortran 4-5
    "E_down": slice(5, 16),  # Fortran 6-16
    "E_up": slice(16, 27),  # Fortran 17-27
    "R_con": slice(27, 38),  # Fortran 28-38
    "R_lin": slice(38, 49),  # Fortran 39-49
    "s_alpha": slice(49, 60),  # Fortran 50-60
    "vary_E_down": slice(61, 62),  # Fortran 62
    "vary_E_up": slice(63, 64),  # Fortran 64
    "vary_R_con": slice(65, 66),  # Fortran 66
    "vary_R_lin": slice(67, 68),  # Fortran 68
    "vary_s_alpha": slice(69, 70),  # Fortran 70
}

# For Format 3a (compact format)
FORMAT_3A = {
    "spin_group": slice(0, 2),  # Fortran 1-2
    "channel": slice(2, 3),  # Fortran 3
    "vary_E_down": slice(3, 4),  # Fortran 4
    "vary_E_up": slice(4, 5),  # Fortran 5
    "vary_R_con": slice(5, 6),  # Fortran 6
    "vary_R_lin": slice(6, 7),  # Fortran 7
    "vary_s_con": slice(7, 8),  # Fortran 8
    "vary_s_lin": slice(8, 9),  # Fortran 9
    "vary_R_q": slice(9, 10),  # Fortran 10
    "E_down": slice(10, 20),  # Fortran 11-20
    "E_up": slice(20, 30),  # Fortran 21-30
    "R_con": slice(30, 40),  # Fortran 31-40
    "R_lin": slice(40, 50),  # Fortran 41-50
    "s_con": slice(50, 60),  # Fortran 51-60
    "s_lin": slice(60, 70),  # Fortran 61-70
    "R_q": slice(70, 80),  # Fortran 71-80
}

CARD_3_HEADER = "EXTERnal R-function parameters follow"
CARD_3A_HEADER = "R-EXTernal parameters follow"


class ExternalREntry(BaseModel):
    format_type: ExternalRFormat
    # Common fields
    spin_group: int
    channel: int
    E_down: float = Field(description="Logarithmic singularity below energy range (eV)")
    E_up: float = Field(description="Logarithmic singularity above energy range (eV)")
    R_con: float = Field(description="Constant term")
    R_lin: float = Field(description="Linear term")

    # Format 3 specific
    s_alpha: Optional[float] = Field(None, description="Coefficient of logarithmic term (must be non-negative)", ge=0.0)
    vary_s_alpha: Optional[VaryFlag] = Field(default=VaryFlag.NO)

    # Format 3a specific
    s_con: Optional[float] = Field(None, description="Constant coefficient of logarithmic term", ge=0.0)
    s_lin: Optional[float] = Field(None, description="Linear coefficient of logarithmic term")
    R_q: Optional[float] = Field(None, description="Quadratic term")
    vary_s_con: Optional[VaryFlag] = Field(default=VaryFlag.NO)
    vary_s_lin: Optional[VaryFlag] = Field(default=VaryFlag.NO)
    vary_R_q: Optional[VaryFlag] = Field(default=VaryFlag.NO)

    # Common vary flags
    vary_E_down: VaryFlag = Field(default=VaryFlag.NO)
    vary_E_up: VaryFlag = Field(default=VaryFlag.NO)
    vary_R_con: VaryFlag = Field(default=VaryFlag.NO)
    vary_R_lin: VaryFlag = Field(default=VaryFlag.NO)

    @model_validator(mode="after")
    def validate_format_specific_fields(self) -> "ExternalREntry":
        if self.format_type == ExternalRFormat.FORMAT_3:
            if self.s_alpha is None:
                raise ValueError("s_alpha is required for Format 3")
            if any(v is not None for v in [self.s_con, self.s_lin, self.R_q]):
                raise ValueError("Format 3a specific fields should not be set for Format 3")
        else:  # FORMAT_3A
            if any(v is not None for v in [self.s_alpha]):
                raise ValueError("Format 3 specific fields should not be set for Format 3a")
            if any(v is None for v in [self.s_con, self.s_lin, self.R_q]):
                raise ValueError("s_con, s_lin, and R_q are required for Format 3a")
        return self

    @classmethod
    def from_str(cls, line: str, format_type: ExternalRFormat) -> "ExternalREntry":
        """Parse an external R-function entry from a fixed-width format line.

        Args:
            line: Input line to parse
            format_type: Format type to use

        Returns:
            ExternalREntry: Parsed entry

        Raises:
            ValueError: If line is empty or parsing fails
        """
        if not line.strip():
            raise ValueError("Empty line provided")

        # Make sure line is long enough by padding with spaces
        line = f"{line:<80}"

        # Select format based on type
        format_layout = FORMAT_3 if format_type == ExternalRFormat.FORMAT_3 else FORMAT_3A

        params = {"format_type": format_type}

        # Parse integer fields
        for field in ["spin_group", "channel"]:
            value = safe_parse(line[format_layout[field]], as_int=True)
            if value is not None:
                params[field] = value

        # Parse float fields common to both formats
        for field in ["E_down", "E_up", "R_con", "R_lin"]:
            value = safe_parse(line[format_layout[field]])
            if value is not None:
                params[field] = value

        # Parse format-specific float fields
        if format_type == ExternalRFormat.FORMAT_3:
            value = safe_parse(line[format_layout["s_alpha"]])
            if value is not None:
                params["s_alpha"] = value
        else:  # FORMAT_3A
            for field in ["s_con", "s_lin", "R_q"]:
                value = safe_parse(line[format_layout[field]])
                if value is not None:
                    params[field] = value

        # Parse common vary flags
        for field in ["vary_E_down", "vary_E_up", "vary_R_con", "vary_R_lin"]:
            value = line[format_layout[field]].strip() or "0"
            try:
                params[field] = VaryFlag(int(value))
            except (ValueError, TypeError):
                params[field] = VaryFlag.NO

        # Parse format-specific vary flags
        if format_type == ExternalRFormat.FORMAT_3:
            try:
                value = int(line[format_layout["vary_s_alpha"]].strip() or "0")
                params["vary_s_alpha"] = VaryFlag(value)
            except (ValueError, TypeError):
                params["vary_s_alpha"] = VaryFlag.NO
        else:  # FORMAT_3A
            for field in ["vary_s_con", "vary_s_lin", "vary_R_q"]:
                try:
                    value = int(line[format_layout[field]].strip() or "0")
                    params[field] = VaryFlag(value)
                except (ValueError, TypeError):
                    params[field] = VaryFlag.NO

        return cls(**params)

    def to_str(self) -> str:
        """Convert the external R-function entry to fixed-width format string."""
        if self.format_type == ExternalRFormat.FORMAT_3:
            # Format 3 has specific spacing requirements
            parts = [
                f"{self.spin_group:2d} ",  # 3 digits
                f"{self.channel:1d} ",  # 2 digits
                format_float(self.E_down, width=11),  # 11 chars
                format_float(self.E_up, width=11),  # 11 chars
                format_float(self.R_con, width=11),  # 11 chars
                format_float(self.R_lin, width=11),  # 11 chars
                format_float(self.s_alpha, width=11),  # 11 chars
                " ",  # pad one space to ensure flag section in the right column
                format_vary(self.vary_E_down),
                " ",
                format_vary(self.vary_E_up),
                " ",
                format_vary(self.vary_R_con),
                " ",
                format_vary(self.vary_R_lin),
                " ",
                format_vary(self.vary_s_alpha),
            ]
            return "".join(parts)
        else:  # FORMAT_3A
            # Format 3A has compact spacing
            # NOTE: compact format uses 10 chars for each float field
            #       whereas
            #       regular format uses 11 chars
            parts = [
                f"{self.spin_group:2d}",
                f"{self.channel:1d}",
                format_vary(self.vary_E_down),
                format_vary(self.vary_E_up),
                format_vary(self.vary_R_con),
                format_vary(self.vary_R_lin),
                format_vary(self.vary_s_con),
                format_vary(self.vary_s_lin),
                format_vary(self.vary_R_q),
                format_float(self.E_down, width=10),
                format_float(self.E_up, width=10),
                format_float(self.R_con, width=10),
                format_float(self.R_lin, width=10),
                format_float(self.s_con, width=10),
                format_float(self.s_lin, width=10),
                format_float(self.R_q, width=10),
            ]
            return "".join(parts)


class ExternalRFunction(BaseModel):
    """Container for External R-function entries (Card Set 3/3a).

    This class handles a complete External R-function card set, including:
    - Header line
    - Multiple parameter entries
    - Trailing blank line

    Examples:
        >>> # Create from lines
        >>> lines = [
        ...     "EXTERnal R-function parameters follow",
        ...     " 1 2 1.2340E+00 5.6780E+00 1.2300E-01 4.5600E-01 7.8900E-01 1 0 0 1 0",
        ...     " 2 1 2.3450E+00 6.7890E+00 2.3400E-01 5.6700E-01 8.9000E-01 0 1 0 0 1",
        ...     ""
        ... ]
        >>> r_function = ExternalRFunction.from_lines(lines)
        >>> len(r_function.entries)
        2

        >>> # Convert back to lines
        >>> output_lines = r_function.to_lines()
        >>> len(output_lines)
        4  # Header + 2 entries + blank line
    """

    format_type: ExternalRFormat
    entries: List[ExternalREntry] = Field(default_factory=list)

    @classmethod
    def is_header_line(cls, line: str) -> Optional[ExternalRFormat]:
        """Check if line is a header and return corresponding format type.

        Args:
            line: Input line to check

        Returns:
            ExternalRFormat if line is a header, None otherwise
        """
        line = line.strip()
        if line.startswith("EXTER"):
            return ExternalRFormat.FORMAT_3
        elif line.startswith("R-EXT"):
            return ExternalRFormat.FORMAT_3A
        return None

    @classmethod
    def write_header(cls, format_type: ExternalRFormat) -> str:
        """Generate the appropriate header line for the format.

        Args:
            format_type: Format type to use

        Returns:
            str: Header line
        """
        if format_type == ExternalRFormat.FORMAT_3:
            return CARD_3_HEADER
        else:
            return CARD_3A_HEADER

    @classmethod
    def from_lines(cls, lines: List[str]) -> "ExternalRFunction":
        """Parse a complete External R-function card set from lines.

        Args:
            lines: List of input lines including header and entries

        Returns:
            ExternalRFunction: Parsed card set

        Raises:
            ValueError: If no valid header found or invalid format
        """
        if not lines:
            raise ValueError("No lines provided")

        # Find and validate header
        format_type = cls.is_header_line(lines[0])
        if format_type is None:
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Parse entries (skip header and trailing blank lines)
        entries = []
        for line in lines[1:]:
            if not line.strip():  # Skip blank lines
                continue
            try:
                entry = ExternalREntry.from_str(line, format_type)
                entries.append(entry)
            except ValueError as e:
                raise ValueError(f"Failed to parse entry line: {line}") from e

        return cls(format_type=format_type, entries=entries)

    def to_lines(self) -> List[str]:
        """Convert the card set to a list of lines.

        Returns:
            List[str]: Lines including header, entries, and trailing blank line
        """
        lines = []

        # Add header
        lines.append(self.write_header(self.format_type))

        # Add entries
        for entry in self.entries:
            lines.append(entry.to_str())

        # Add trailing blank line
        lines.append("")

        return lines


if __name__ == "__main__":
    # Enable logging for debugging
    from pleiades.utils.logger import configure_logger

    configure_logger(console_level="DEBUG")
    logger = loguru_logger.bind(name=__name__)

    # Test ExternalREntry with both formats
    logger.debug("**Testing ExternalREntry with Format 3**")
    format3_examples = [
        " 1 2 1.2340E+00 5.6780E+00 1.2300E-01 4.5600E-01 7.8900E-01  1 0 1 0 1",
        " 2 1 2.3450E+00 6.7890E+00 2.3400E-01 5.6700E-01 8.9000E-01  0 1 0 0 1",
        #                                                           ^^ two spaces here
    ]

    for i, line in enumerate(format3_examples):
        entry = ExternalREntry.from_str(line, ExternalRFormat.FORMAT_3)
        logger.debug(f"Format 3 Example {i + 1}:")
        logger.debug(f"Object     : {entry}")
        logger.debug(f"Original   : {line}")
        logger.debug(f"Reformatted: {entry.to_str()}")
        logger.debug("")

    logger.debug("**Testing ExternalREntry with Format 3A**")
    format3a_examples = [
        "12100100001.2340E+005.6780E+001.2300E-014.5600E-017.8900E-018.9000E-019.0000E-01",
        "21201001012.3450E+006.7890E+002.3400E-015.6700E-018.9000E-019.1000E-019.2000E-01",
    ]

    for i, line in enumerate(format3a_examples):
        entry = ExternalREntry.from_str(line, ExternalRFormat.FORMAT_3A)
        logger.debug(f"Format 3A Example {i + 1}:")
        logger.debug(f"Object     : {entry}")
        logger.debug(f"Original   : {line}")
        logger.debug(f"Reformatted: {entry.to_str()}")
        logger.debug("")

    # Test ExternalRFunction with complete card sets
    logger.debug("**Testing ExternalRFunction with Format 3**")
    format3_lines = [
        "EXTERnal R-function parameters follow",
        " 1 2 1.2340E+00 5.6780E+00 1.2300E-01 4.5600E-01 7.8900E-01  1 0 0 1 0",
        " 2 1 2.3450E+00 6.7890E+00 2.3400E-01 5.6700E-01 8.9000E-01  0 1 0 0 1",
        "",
    ]

    try:
        r_function = ExternalRFunction.from_lines(format3_lines)
        logger.debug("Successfully parsed Format 3 card set:")
        logger.debug(f"Number of entries: {len(r_function.entries)}")
        logger.debug("Output lines:")
        for line in r_function.to_lines():
            logger.debug(f"'{line}'")
        logger.debug("")
    except ValueError as e:
        logger.error(f"Failed to parse Format 3 card set: {e}")

    logger.debug("**Testing ExternalRFunction with Format 3A**")
    format3a_lines = [
        "R-EXTernal parameters follow",
        "12100100001.2340E+005.6780E+001.2300E-014.5600E-017.8900E-018.9000E-019.0000E-01",
        "21201001012.3450E+006.7890E+002.3400E-015.6700E-018.9000E-019.1000E-019.2000E-01",
        "",
    ]

    try:
        r_function = ExternalRFunction.from_lines(format3a_lines)
        logger.debug("Successfully parsed Format 3A card set:")
        logger.debug(f"Number of entries: {len(r_function.entries)}")
        logger.debug("Output lines:")
        for line in r_function.to_lines():
            logger.debug(f"'{line}'")
        logger.debug("")
    except ValueError as e:
        logger.error(f"Failed to parse Format 3A card set: {e}")

    # Test error handling
    logger.debug("**Testing Error Handling**")

    # Test invalid s_alpha (negative value)
    try:
        bad_line = " 1 2 1.2340E+00 5.6780E+00 1.2300E-01 4.5600E-01 -7.8900E-01 1 0 0 1 0"
        logger.debug(f"Testing line with negative s_alpha: '{bad_line}'")
        ExternalREntry.from_str(bad_line, ExternalRFormat.FORMAT_3)
    except ValueError as e:
        logger.debug(f"Caught expected error for negative s_alpha: {e}")

    # Test invalid header
    try:
        bad_lines = ["WRONG header line", " 1 2 1.2340E+00 5.6780E+00 1.2300E-01 4.5600E-01 7.8900E-01 1 0 0 1 0", ""]
        logger.debug("Testing invalid header:")
        ExternalRFunction.from_lines(bad_lines)
    except ValueError as e:
        logger.debug(f"Caught expected error for invalid header: {e}")
