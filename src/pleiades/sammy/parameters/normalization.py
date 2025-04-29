#!/usr/bin/env python
"""Data class for card 06::normalization and background parameters."""

from typing import List, Optional

from pydantic import BaseModel, Field

from pleiades.utils.helper import VaryFlag, format_float, format_vary, safe_parse
from pleiades.utils.logger import loguru_logger

# Format definitions for fixed-width fields
# Each numeric field follows a 9+1 pattern for readability
FORMAT_MAIN = {
    "anorm": slice(0, 10),  # Normalization
    "backa": slice(10, 20),  # Constant background
    "backb": slice(20, 30),  # Background proportional to 1/E
    "backc": slice(30, 40),  # Background proportional to √E
    "backd": slice(40, 50),  # Exponential background coefficient
    "backf": slice(50, 60),  # Exponential decay constant
    "flag_anorm": slice(60, 62),  # Flag for ANORM
    "flag_backa": slice(62, 64),  # Flag for BACKA
    "flag_backb": slice(64, 66),  # Flag for BACKB
    "flag_backc": slice(66, 68),  # Flag for BACKC
    "flag_backd": slice(68, 70),  # Flag for BACKD
    "flag_backf": slice(70, 72),  # Flag for BACKF
}

FORMAT_UNCERTAINTY = {
    "d_anorm": slice(0, 10),
    "d_backa": slice(10, 20),
    "d_backb": slice(20, 30),
    "d_backc": slice(30, 40),
    "d_backd": slice(40, 50),
    "d_backf": slice(50, 60),
}

CARD_6_HEADER = "NORMAlization and background are next"


class NormalizationParameters(BaseModel):
    """Parameters for normalization and background for one angle.

    Contains:
    - Normalization and background values
    - Their uncertainties (optional)
    - Flags indicating whether each parameter should be varied

    Note on fixed-width format:
    Each numeric field in the file uses a 10-column width with a 9+1 pattern:
    - 9 characters for the actual numeric data (e.g. "1.2340E+00")
    - 1 character for space separator
    """

    # Main parameters
    anorm: float = Field(description="Normalization (dimensionless)")
    backa: float = Field(description="Constant background")
    backb: float = Field(description="Background proportional to 1/E")
    backc: float = Field(description="Background proportional to √E")
    backd: float = Field(description="Exponential background coefficient")
    backf: float = Field(description="Exponential decay constant")

    # Optional uncertainties
    d_anorm: Optional[float] = Field(None, description="Uncertainty on ANORM")
    d_backa: Optional[float] = Field(None, description="Uncertainty on BACKA")
    d_backb: Optional[float] = Field(None, description="Uncertainty on BACKB")
    d_backc: Optional[float] = Field(None, description="Uncertainty on BACKC")
    d_backd: Optional[float] = Field(None, description="Uncertainty on BACKD")
    d_backf: Optional[float] = Field(None, description="Uncertainty on BACKF")

    # Vary flags
    flag_anorm: VaryFlag = Field(default=VaryFlag.NO)
    flag_backa: VaryFlag = Field(default=VaryFlag.NO)
    flag_backb: VaryFlag = Field(default=VaryFlag.NO)
    flag_backc: VaryFlag = Field(default=VaryFlag.NO)
    flag_backd: VaryFlag = Field(default=VaryFlag.NO)
    flag_backf: VaryFlag = Field(default=VaryFlag.NO)

    @classmethod
    def from_lines(cls, lines: List[str]) -> "NormalizationParameters":
        """Parse normalization parameters from a list of fixed-width format lines.

        Args:
            lines: List of input lines

        Returns:
            NormalizationParameters: Parsed parameters

        Raises:
            ValueError: If lines are invalid or required data is missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        # Make sure first line is long enough
        main_line = f"{lines[0]:<72}"

        params = {}

        # Parse main parameters
        for field in ["anorm", "backa", "backb", "backc", "backd", "backf"]:
            value = safe_parse(main_line[FORMAT_MAIN[field]])
            if value is not None:
                params[field] = value

        # Parse vary flags
        for field in ["flag_anorm", "flag_backa", "flag_backb", "flag_backc", "flag_backd", "flag_backf"]:
            value = main_line[FORMAT_MAIN[field]].strip() or "0"
            try:
                params[field] = VaryFlag(int(value))
            except (ValueError, TypeError):
                params[field] = VaryFlag.NO

        # Parse uncertainties if present
        if len(lines) > 1 and lines[1].strip():
            unc_line = f"{lines[1]:<60}"
            for field in ["d_anorm", "d_backa", "d_backb", "d_backc", "d_backd", "d_backf"]:
                value = safe_parse(unc_line[FORMAT_UNCERTAINTY[field]])
                if value is not None:
                    params[field] = value

        return cls(**params)

    def to_lines(self) -> List[str]:
        """Convert the parameters to a list of fixed-width format lines.

        Returns:
            List[str]: Lines representing the parameters
        """
        lines = []

        # Format main parameter line
        main_parts = [
            format_float(self.anorm, width=9),
            format_float(self.backa, width=9),
            format_float(self.backb, width=9),
            format_float(self.backc, width=9),
            format_float(self.backd, width=9),
            format_float(self.backf, width=9),
            format_vary(self.flag_anorm),
            format_vary(self.flag_backa),
            format_vary(self.flag_backb),
            format_vary(self.flag_backc),
            format_vary(self.flag_backd),
            format_vary(self.flag_backf),
        ]
        lines.append(" ".join(main_parts))

        # Add uncertainties line if any uncertainties are present
        if any(
            getattr(self, f"d_{param}") is not None for param in ["anorm", "backa", "backb", "backc", "backd", "backf"]
        ):
            unc_parts = [
                format_float(getattr(self, f"d_{param}", 0.0), width=10)
                for param in ["anorm", "backa", "backb", "backc", "backd", "backf"]
            ]
            lines.append("".join(unc_parts))

        return lines


class NormalizationBackgroundCard(BaseModel):
    """Container for complete normalization/background card set (Card Set 6).

    This class handles a complete card set, including:
    - Header line
    - Parameter entries for each angle
    - Trailing blank line
    """

    angle_sets: List[NormalizationParameters] = Field(min_items=1)

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if line is a valid header
        """
        return line.strip().upper().startswith("NORMA")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "NormalizationBackgroundCard":
        """Parse a complete normalization card set from lines.

        Args:
            lines: List of input lines including header

        Returns:
            NormalizationBackgroundCard: Parsed card set

        Raises:
            ValueError: If no valid header found or invalid format
        """
        if not lines:
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Parse parameters (skip header and trailing blank lines)
        content_lines = [line for line in lines[1:] if line.strip()]
        if not content_lines:
            raise ValueError("No parameter lines found")

        # Parse angle sets (each set can have 1-2 lines)
        angle_sets = []
        i = 0
        while i < len(content_lines):
            # Check if next line exists and is an uncertainty line
            next_lines = [content_lines[i]]
            if i + 1 < len(content_lines):
                # Check if next line looks like uncertainties (contains numeric values)
                # rather than a new parameter set
                if safe_parse(content_lines[i + 1][:10]) is not None:
                    next_lines.append(content_lines[i + 1])
                    i += 2
                else:
                    i += 1
            else:
                i += 1

            angle_sets.append(NormalizationParameters.from_lines(next_lines))

        return cls(angle_sets=angle_sets)

    def to_lines(self) -> List[str]:
        """Convert the card set to a list of lines.

        Returns:
            List[str]: Lines including header and parameters
        """
        lines = [CARD_6_HEADER]
        for angle_set in self.angle_sets:
            lines.extend(angle_set.to_lines())
        lines.append("")  # Trailing blank line
        return lines


if __name__ == "__main__":
    # Enable logging for debugging
    from pleiades.utils.logger import configure_logger

    configure_logger(console_level="DEBUG")
    logger = loguru_logger.bind(name=__name__)

    # Test example with main parameters only
    logger.debug("**Testing main parameters only**")
    main_only_lines = ["1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0"]

    try:
        params = NormalizationParameters.from_lines(main_only_lines)
        logger.debug("Successfully parsed main parameters:")
        logger.debug(f"ANORM: {params.anorm}")
        logger.debug(f"BACKA: {params.backa}")
        logger.debug("Output lines:")
        for line in params.to_lines():
            logger.debug(f"'{line}'")
        logger.debug("")
    except ValueError as e:
        logger.error(f"Failed to parse main parameters: {e}")

    # Test example with uncertainties
    logger.debug("**Testing with uncertainties**")
    with_unc_lines = [
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0",
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02",
    ]

    try:
        params = NormalizationParameters.from_lines(with_unc_lines)
        logger.debug("Successfully parsed parameters with uncertainties:")
        logger.debug(f"ANORM: {params.anorm} ± {params.d_anorm}")
        logger.debug(f"BACKA: {params.backa} ± {params.d_backa}")
        logger.debug("Output lines:")
        for line in params.to_lines():
            logger.debug(f"'{line}'")
        logger.debug("")
    except ValueError as e:
        logger.error(f"Failed to parse parameters with uncertainties: {e}")

    # Test complete card set with multiple angles
    logger.debug("**Testing complete card set with multiple angles**")
    card_lines = [
        "NORMAlization and background are next",
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0",
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02",
        "1.300E+00 3.000E+02 1.600E-01 2.600E-02 1.100E+00 5.100E-01  1 0 1 0 1 0",
        "",
    ]

    try:
        card = NormalizationBackgroundCard.from_lines(card_lines)
        logger.debug("Successfully parsed complete card set")
        logger.debug(f"Number of angle sets: {len(card.angle_sets)}")
        logger.debug("Output lines:")
        for line in card.to_lines():
            logger.debug(f"'{line}'")
    except ValueError as e:
        logger.error(f"Failed to parse complete card set: {e}")

    # Test error handling
    logger.debug("\n**Testing Error Handling**")

    # Test invalid header
    try:
        bad_lines = [
            "WRONG header line",
            "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0",
            "",
        ]
        logger.debug("Testing invalid header:")
        NormalizationBackgroundCard.from_lines(bad_lines)
    except ValueError as e:
        logger.debug(f"Caught expected error for invalid header: {e}")

    # Test empty parameter set
    try:
        bad_lines = ["NORMAlization and background are next", ""]
        logger.debug("Testing empty parameter set:")
        NormalizationBackgroundCard.from_lines(bad_lines)
    except ValueError as e:
        logger.debug(f"Caught expected error for empty parameter set: {e}")
