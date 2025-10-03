#!/usr/bin/env python
"""Data class for card 05::unused but correlated variables."""

from typing import List

from pydantic import BaseModel, Field, model_validator

from pleiades.utils.helper import safe_parse
from pleiades.utils.logger import loguru_logger

# Format definitions for fixed-width fields
# Name line has 8 possible 5-character fields separated by 5 spaces
FORMAT_NAMES = {f"name{i}": slice(i * 10, i * 10 + 5) for i in range(8)}

# Value line has 8 possible 10-character fields
FORMAT_VALUES = {f"value{i}": slice(i * 10, (i + 1) * 10) for i in range(8)}

CARD_5_HEADER = "UNUSEd but correlated variables come next"


class UnusedVariable(BaseModel):
    """Container for a single unused but correlated variable.

    Contains:
    - name: 5-character name of the variable
    - value: Numerical value of the variable
    """

    name: str = Field(description="Name of the unused variable (5 chars)")
    value: float = Field(description="Value of the unused variable")

    @model_validator(mode="after")
    def validate_name_length(self) -> "UnusedVariable":
        """Validate that name is exactly 5 characters."""
        if len(self.name) != 5:
            self.name = f"{self.name:<5}"  # Pad with spaces if needed
        return self


class UnusedCorrelatedParameters(BaseModel):
    """Container for a set of unused but correlated variables.

    Contains:
    - variables: List of UnusedVariable objects
    """

    variables: List[UnusedVariable] = Field(default_factory=list)

    @classmethod
    def from_lines(cls, lines: List[str]) -> "UnusedCorrelatedParameters":
        """Parse unused correlated parameters from pairs of name/value lines.

        Args:
            lines: List of input lines (excluding header)

        Returns:
            UnusedCorrelatedParameters: Parsed parameters

        Raises:
            ValueError: If lines are invalid or required data is missing
        """
        if not lines or len(lines) < 2:
            raise ValueError("At least one pair of name/value lines required")

        variables = []

        # Process pairs of lines (names followed by values)
        for i in range(0, len(lines), 2):
            if i + 1 >= len(lines):
                break

            name_line = f"{lines[i]:<80}"  # Pad to full width
            value_line = f"{lines[i + 1]:<80}"

            # Extract all non-empty names and corresponding values
            for j in range(8):
                name = name_line[FORMAT_NAMES[f"name{j}"]].strip()
                if name:
                    value_str = value_line[FORMAT_VALUES[f"value{j}"]].strip()
                    value = safe_parse(value_str)
                    if value is not None:
                        variables.append(UnusedVariable(name=name, value=value))

        return cls(variables=variables)

    def to_lines(self) -> List[str]:
        """Convert the parameters to a list of fixed-width format lines.

        Returns:
            List[str]: Lines representing the parameters
        """
        lines = []

        # Process variables in groups of 8
        for i in range(0, len(self.variables), 8):
            group = self.variables[i : i + 8]

            # Format name line
            names = [""] * 8
            for j, var in enumerate(group):
                names[j] = f"{var.name:<5}"
            name_line = "     ".join(names).rstrip()
            lines.append(name_line)

            # Format value line
            values = ["          "] * 8  # 10 spaces each
            for j, var in enumerate(group):
                values[j] = f"{var.value:10.4E}"
            value_line = "".join(values[: len(group)])
            lines.append(value_line)

        return lines


class UnusedCorrelatedCard(BaseModel):
    """Container for a complete unused correlated variable card set (Card Set 5).

    This class handles a complete card set, including:
    - Header line
    - Parameter entries
    - Trailing blank line
    """

    parameters: UnusedCorrelatedParameters

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if line is a valid header
        """
        return line.strip().upper().startswith("UNUSE")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "UnusedCorrelatedCard":
        """Parse a complete card set from lines.

        Args:
            lines: List of input lines including header

        Returns:
            UnusedCorrelatedCard: Parsed card set

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

        parameters = UnusedCorrelatedParameters.from_lines(content_lines)
        return cls(parameters=parameters)

    def to_lines(self) -> List[str]:
        """Convert the card set to a list of lines.

        Returns:
            List[str]: Lines including header and parameters
        """
        lines = [CARD_5_HEADER]
        lines.extend(self.parameters.to_lines())
        lines.append("")  # Trailing blank line
        return lines


if __name__ == "__main__":
    # Enable logging for debugging
    from pleiades.utils.logger import configure_logger

    configure_logger(console_level="DEBUG")
    logger = loguru_logger.bind(name=__name__)

    # Test example with two groups of variables
    logger.debug("**Testing variable parsing**")
    test_lines = [
        (" " * 5).join([f"NVAR{i}" for i in range(1, 4)]),
        "1.2304E+002.9800E+021.5000E-01",
        (" " * 5).join([f"NVAR{i}" for i in range(4, 6)]),
        "2.5000E-021.0000E+00",
    ]

    try:
        params = UnusedCorrelatedParameters.from_lines(test_lines)
        logger.debug("Successfully parsed parameters:")
        for var in params.variables:
            logger.debug(f"{var.name}: {var.value}")
        logger.debug("\nOutput lines:")
        for line in params.to_lines():
            logger.debug(f"'{line}'")
        logger.debug("")
    except ValueError as e:
        logger.error(f"Failed to parse parameters: {e}")

    # Test complete card set
    logger.debug("**Testing complete card set**")
    card_lines = [
        "UNUSEd but correlated variables come next",
        (" " * 5).join([f"NVAR{i}" for i in range(1, 4)]),
        "1.2340E+002.9800E+021.5000E-01 ",
        (" " * 5).join([f"NVAR{i}" for i in range(4, 6)]),
        "2.5000E-021.0000E+00",
        "",
    ]

    try:
        card = UnusedCorrelatedCard.from_lines(card_lines)
        logger.debug("Successfully parsed complete card set")
        logger.debug("Output lines:")
        for line in card.to_lines():
            logger.debug(f"'{line}'")
    except ValueError as e:
        logger.error(f"Failed to parse complete card set: {e}")

    # Test error handling
    logger.debug("\n**Testing Error Handling**")

    # Test invalid header
    try:
        bad_lines = ["WRONG header line", "NVAR1", "1.2340E+00", ""]
        logger.debug("Testing invalid header:")
        UnusedCorrelatedCard.from_lines(bad_lines)
    except ValueError as e:
        logger.debug(f"Caught expected error for invalid header: {e}")

    # Test mismatched name/value lines
    try:
        bad_lines = ["NVAR1     NVAR2", "1.2340E+00"]  # Missing value
        UnusedCorrelatedParameters.from_lines(bad_lines)
    except ValueError as e:
        logger.debug(f"Caught expected error for mismatched lines: {e}")
