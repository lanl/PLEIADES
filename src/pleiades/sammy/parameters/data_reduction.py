#!/usr/bin/env python
"""Data class for card 08::data reduction parameters."""

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from pleiades.utils.helper import VaryFlag, format_float, format_vary, safe_parse

# Format definitions for fixed-width fields
FORMAT_PARAMETER = {
    "name": slice(0, 5),  # Parameter name (alphanumeric)
    "flag": slice(6, 7),  # Vary flag (0=fixed, 1=varied, 3=PUP)
    "value": slice(10, 20),  # Parameter value
    "uncertainty": slice(20, 30),  # Absolute uncertainty
    "derivative": slice(30, 40),  # Value for partial derivatives
}

CARD_8_HEADER = "DATA reduction parameters are next"


class DataReductionParameter(BaseModel):
    """Container for a single data reduction parameter entry.

    Each parameter has:
    - A name (5-char alphanumeric)
    - A value
    - A flag indicating whether it should be varied
    - Optional uncertainty
    - Optional derivative value
    """

    name: str = Field(max_length=5)
    value: float
    flag: VaryFlag = Field(default=VaryFlag.NO)
    uncertainty: Optional[float] = None
    derivative_value: Optional[float] = None

    @model_validator(mode="after")
    def validate_name(self) -> "DataReductionParameter":
        """Validate name field is not empty and fits format."""
        if not self.name or len(self.name) > 5:
            raise ValueError("Name must be 1-5 characters")
        return self

    @classmethod
    def from_line(cls, line: str) -> "DataReductionParameter":
        """Parse parameter from a fixed-width format line.

        Args:
            line: Input line

        Returns:
            DataReductionParameter: Parsed parameter

        Raises:
            ValueError: If line is invalid or required data missing
        """
        if not line.strip():
            raise ValueError("Empty line provided")

        # Parse name (required)
        name = line[FORMAT_PARAMETER["name"]].strip()
        if not name:
            raise ValueError("Parameter name is required")

        # Parse value (required)
        value = safe_parse(line[FORMAT_PARAMETER["value"]])
        if value is None:
            raise ValueError(f"Invalid or missing value for parameter {name}")

        # Parse flag
        flag_str = line[FORMAT_PARAMETER["flag"]].strip() or "0"
        try:
            flag = VaryFlag(int(flag_str))
        except (ValueError, TypeError):
            flag = VaryFlag.NO

        # Parse optional fields
        uncertainty = safe_parse(line[FORMAT_PARAMETER["uncertainty"]])
        derivative = safe_parse(line[FORMAT_PARAMETER["derivative"]])

        return cls(name=name, value=value, flag=flag, uncertainty=uncertainty, derivative_value=derivative)

    def to_line(self) -> str:
        """Convert the parameter to a fixed-width format line.

        Returns:
            str: Formatted line
        """
        parts = [
            f"{self.name:<5}",
            " ",
            format_vary(self.flag),
            "   ",  # 3 spaces padding
            format_float(self.value, width=10),
            format_float(self.uncertainty, width=10),
            format_float(self.derivative_value, width=10),
        ]
        return "".join(parts)


class DataReductionCard(BaseModel):
    """Container for a complete data reduction parameter card set (Card Set 8).

    This class handles:
    - Header line
    - Multiple parameter entries
    - Trailing blank line
    """

    parameters: List[DataReductionParameter]

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line."""
        return line.strip().upper().startswith("DATA")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "DataReductionCard":
        """Parse a complete data reduction card set from lines.

        Args:
            lines: List of input lines including header

        Returns:
            DataReductionCard: Parsed card set

        Raises:
            ValueError: If no valid header found or invalid format
        """
        if not lines:
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Parse parameters (skip header and trailing blank lines)
        parameters = []
        for line in lines[1:]:
            if not line.strip():
                continue
            try:
                param = DataReductionParameter.from_line(line)
                parameters.append(param)
            except ValueError as e:
                raise ValueError(f"Error parsing parameter line: {e}")

        if not parameters:
            raise ValueError("No parameter lines found")

        return cls(parameters=parameters)

    def to_lines(self) -> List[str]:
        """Convert the card set to a list of lines.

        Returns:
            List[str]: Lines including header and parameters
        """
        lines = [CARD_8_HEADER]
        for param in self.parameters:
            lines.append(param.to_line())
        lines.append("")  # Trailing blank line
        return lines


if __name__ == "__main__":
    from pleiades.utils.logger import configure_logger, loguru_logger

    configure_logger(console_level="DEBUG")
    logger = loguru_logger.bind(name=__name__)

    # Test single parameter parsing
    logger.debug("**Testing single parameter parsing**")
    param_line = "PARAM 1   1.234E+00 5.000E-02 1.234E+00"

    for k, v in FORMAT_PARAMETER.items():
        tmp = param_line[v]
        print(f"{k}: {v} -- {tmp}")  # Debugging output

    try:
        param = DataReductionParameter.from_line(param_line)
        logger.debug(f"Successfully parsed parameter: {param.name} = {param.value}")
        logger.debug(f"Output line: '{param.to_line()}'")
    except ValueError as e:
        logger.error(f"Failed to parse parameter: {e}")

    # Test complete card set
    logger.debug("\n**Testing complete card set**")
    card_lines = [
        "DATA reduction parameters are next",
        "PAR1   1   1.234E+00 5.000E-02 1.234E+00",
        "PAR2   0   2.345E+00 1.000E-02",
        "PAR3   3   3.456E+00",
        "",
    ]

    try:
        card = DataReductionCard.from_lines(card_lines)
        logger.debug("Successfully parsed card set")
        logger.debug("Output lines:")
        for line in card.to_lines():
            logger.debug(f"'{line}'")
    except ValueError as e:
        logger.error(f"Failed to parse card set: {e}")

    # Test error handling
    logger.debug("\n**Testing error handling**")

    # Test invalid header
    try:
        bad_lines = ["WRONG header", "PAR1  1 1.234E+00", ""]
        DataReductionCard.from_lines(bad_lines)
    except ValueError as e:
        logger.debug(f"Caught expected error for invalid header: {e}")

    # Test invalid parameter line
    try:
        bad_param = "PAR1  X invalid_value"
        DataReductionParameter.from_line(bad_param)
    except ValueError as e:
        logger.debug(f"Caught expected error for invalid parameter line: {e}")
