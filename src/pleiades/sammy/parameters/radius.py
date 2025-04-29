#!/usr/bin/env python
"""Card Set 7/7a: Radius Parameters.

This module handles both fixed-width (Card Set 7) and keyword-based (Card Set 7a) formats
for radius parameters in SAMMY parameter files.
"""

import re
from enum import Enum
from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from pleiades.utils.helper import VaryFlag, format_float, format_vary, parse_keyword_pairs_to_dict, safe_parse
from pleiades.utils.logger import Logger, _log_and_raise_error

# Initialize logger with file logging
logger = Logger(__name__)

####################################################################################################
# Header flags and format definitions
####################################################################################################
CARD_7_HEADER = "RADIUs parameters follow"
CARD_7A_HEADER = "RADII are in KEY-WORD format"
CARD_7_ALT_HEADER = "RADIUs parameters follow"

# Format definitions for fixed-width fields
FORMAT_DEFAULT = {
    "pareff": slice(0, 10),  # Effective radius (Fermi)
    "partru": slice(10, 20),  # True radius (Fermi)
    "ichan": slice(20, 21),  # Channel indicator
    "ifleff": slice(21, 22),  # Flag for PAREFF
    "ifltru": slice(22, 24),  # Flag for PARTRU
    # Spin groups start at col 24, 2 cols each
    # After IX=0 marker, channel numbers use 2 cols each
}

# Format definitions for fixed-width fields
FORMAT_ALTERNATE = {
    "pareff": slice(0, 10),  # Radius for potential scattering
    "partru": slice(10, 20),  # Radius for penetrabilities
    "ichan": slice(20, 25),  # Channel indicator (5 cols)
    "ifleff": slice(25, 30),  # Flag for PAREFF (5 cols)
    "ifltru": slice(30, 35),  # Flag for PARTRU (5 cols)
    # Spin groups start at col 35, 5 cols each
    # After IX=0 marker, channel numbers use 5 cols each
}


class RadiusFormat(Enum):
    """Supported formats for radius parameter cards."""

    DEFAULT = "default"  # Fixed width (<99 spin groups)
    ALTERNATE = "alternate"  # Fixed width (>=99 spin groups)
    KEYWORD = "keyword"  # Keyword based


####################################################################################################
# RadiusParameters class and its corresponding Container class
####################################################################################################
class RadiusParameters(BaseModel):
    """Container for nuclear radius parameters used in SAMMY calculations.

    This class represents a set of radius parameters that define both the potential
    scattering radius and the radius used for penetrabilities and shift calculations.
    These parameters can be applied globally or to specific spin groups and channels.

    Attributes:
        effective_radius (float):
            The radius (in Fermi) used for potential scattering calculations.

        true_radius (float):
            The radius (in Fermi) used for penetrabilities and shift calculations.
            Special values:
            - If 0: Uses the CRFN value from input file/card set 4
            - If negative: Absolute value represents mass ratio to neutron (AWRI),
              radius calculated as 1.23(AWRI)^1/3 + 0.8 (ENDF formula)

        channel_mode (int):
            Determines how channels are specified:
            - 0: Parameters apply to all channels
            - 1: Parameters apply only to specified channels in channels list

        vary_effective (VaryFlag):
            Flag indicating how effective radius should be treated:
            - NO (0): Parameter is held fixed
            - YES (1): Parameter is varied in fitting
            - PUP (3): Parameter is treated as a propagated uncertainty parameter

        vary_true (VaryFlag):
            Flag indicating how true radius should be treated:
            - USE_FROM_EFFECTIVE (-1): Treated as identical to effective_radius
            - NO (0): Parameter is held fixed
            - YES (1): Parameter is varied independently
            - PUP (3): Parameter is treated as a propagated uncertainty parameter

        spin_groups (List[int]):
            List of spin group numbers that use these radius parameters.
            Values > 500 indicate omitted resonances.

        channels (Optional[List[int]]):
            List of channel numbers when channel_mode=1.
            When channel_mode=0, this should be None.

    Note:
        This class supports the three different input formats specified in SAMMY:
        - Default format (card set 7) for <99 spin groups
        - Alternate format for >99 spin groups
        - Keyword-based format
        However, internally it maintains a consistent representation regardless
        of input format.
    """

    effective_radius: float = Field(description="Radius for potential scattering (Fermi)", ge=0)
    true_radius: float = Field(description="Radius for penetrabilities and shifts (Fermi)")
    channel_mode: int = Field(
        description="Channel specification mode (0: all channels, 1: specific channels)",
        ge=0,  # Greater than or equal to 0
        le=1,  # Less than or equal to 1
    )
    vary_effective: VaryFlag = Field(default=VaryFlag.NO, description="Flag for varying effective radius")
    vary_true: VaryFlag = Field(default=VaryFlag.NO, description="Flag for varying true radius")
    spin_groups: Optional[List[int]] = Field(
        description="List of spin group numbers",
    )
    channels: Optional[List[int]] = Field(
        default=None, description="List of channel numbers (required when channel_mode=1)"
    )

    @field_validator("spin_groups")
    def validate_spin_groups(cls, v: List[int]) -> List[int]:
        """Validate spin group numbers.

        Args:
            v: List of spin group numbers

        Returns:
            List[int]: Validated spin group numbers

        Raises:
            ValueError: If any spin group number is invalid
        """
        for group in v:
            if group <= 0:
                raise ValueError(f"Spin group numbers must be positive, got {group}")

            # Values > 500 are valid but indicate omitted resonances
            # We allow them but might want to warn the user
            if group > 500:
                print(f"Warning: Spin group {group} > 500 indicates omitted resonances")

        return v

    @field_validator("vary_true")
    def validate_vary_true(cls, v: VaryFlag) -> VaryFlag:
        """Validate vary_true flag has valid values.

        For true radius, we allow an additional special value -1 (USE_FROM_PARFILE)

        Args:
            v: Vary flag value

        Returns:
            VaryFlag: Validated flag value

        Raises:
            ValueError: If flag value is invalid
        """
        allowed_values = [
            VaryFlag.USE_FROM_PARFILE,  # -1
            VaryFlag.NO,  # 0
            VaryFlag.YES,  # 1
            VaryFlag.PUP,  # 3
        ]
        if v not in allowed_values:
            raise ValueError(f"vary_true must be one of {allowed_values}, got {v}")
        return v

    @model_validator(mode="after")
    def validate_channels(self) -> "RadiusParameters":
        """Validate channel specifications.

        Ensures that:
        1. If channel_mode=1, channels must be provided
        2. If channel_mode=0, channels should be None

        Returns:
            RadiusParameters: Self if validation passes

        Raises:
            ValueError: If channel specifications are invalid
        """
        if self.channel_mode == 1 and not self.channels:
            raise ValueError("When channel_mode=1, channels must be provided")
        if self.channel_mode == 0 and self.channels is not None:
            raise ValueError("When channel_mode=0, channels must be None")
        return self

    @model_validator(mode="after")
    def validate_true_radius_consistency(self) -> "RadiusParameters":
        """Validate consistency between true_radius and vary_true.

        Ensures that:
        1. If vary_true is USE_FROM_PARFILE, true_radius matches effective_radius
        2. If true_radius is 0, vary_true cannot be USE_FROM_PARFILE
        3. If true_radius is negative, it represents AWRI and vary_true cannot be USE_FROM_PARFILE

        Returns:
            RadiusParameters: Self if validation passes

        Raises:
            ValueError: If radius specifications are inconsistent
        """
        if self.vary_true == VaryFlag.USE_FROM_PARFILE:
            if self.true_radius != self.effective_radius:
                raise ValueError("When vary_true is USE_FROM_PARFILE (-1), true_radius must match effective_radius")

        # Special cases for true_radius
        if self.true_radius == 0:
            if self.vary_true == VaryFlag.USE_FROM_PARFILE:
                raise ValueError("When true_radius=0 (use CRFN value), vary_true cannot be USE_FROM_PARFILE (-1)")

        if self.true_radius < 0:
            if self.vary_true == VaryFlag.USE_FROM_PARFILE:
                raise ValueError(
                    "When true_radius is negative (AWRI specification), vary_true cannot be USE_FROM_PARFILE (-1)"
                )

        return self

    def __repr__(self) -> str:
        """Return a string representation of the radius parameters."""
        return (
            f"RadiusParameters("
            f"effective_radius={self.effective_radius}, "
            f"true_radius={self.true_radius}, "
            f"channel_mode={self.channel_mode}, "
            f"vary_effective={self.vary_effective}, "
            f"vary_true={self.vary_true}, "
            f"spin_groups={self.spin_groups}, "
            f"channels={self.channels})"
        )


####################################################################################################
# Card variant classes for different formats (default, alternate, keyword)
####################################################################################################
class RadiusCardDefault(BaseModel):
    """Handler for default format radius parameter cards (Card Set 7).

    This class handles parsing and writing radius parameters in the default
    fixed-width format used for systems with fewer than 99 spin groups.

    The format includes:
    - Fixed width fields for radii and flags
    - Support for multiple lines of spin groups with -1 continuation
    - Optional channel numbers after IX=0 marker when channel_mode=1

    Note:
        This format should only be used when the number of spin groups < 99.
        For larger systems, use RadiusCardAlternate.
    """

    parameters: List[RadiusParameters]

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if line is a valid header
        """
        where_am_i = "RadiusCardDefault.is_header_line()"
        logger.info(f"{where_am_i}: Checking if header line - {line}")
        return line.strip().upper().startswith("RADIU")

    @staticmethod
    def _parse_numbers_from_line(line: str, start_pos: int, width: int) -> List[int]:
        """Parse fixed-width integer values from a line.

        Args:
            line: Input line
            start_pos: Starting position
            width: Width of each field

        Returns:
            List[int]: List of parsed integers, stopping at first invalid value
        """
        where_am_i = "RadiusCardDefault._parse_numbers_from_line()"
        logger.info(f"{where_am_i}: Parsing fixed-width integers from line")
        numbers = []
        pos = start_pos
        while pos + width <= len(line):
            value = safe_parse(line[pos : pos + width], as_int=True)
            if value is None:
                break
            numbers.append(value)
            pos += width
        return numbers

    @classmethod
    def _parse_spin_groups_and_channels(cls, line: str) -> Tuple[List[int], Optional[List[int]]]:
        """Parse spin groups and optional channels from a line.

        Args:
            line: Input line containing spin groups/channels

        Returns:
            Tuple containing:
            - List[int]: Spin group numbers
            - Optional[List[int]]: Channel numbers if present

        Note:
            Handles continuation lines (-1 marker) and IX=0 marker for channels
        """
        where_am_i = "RadiusCardDefault._parse_spin_groups_and_channels()"
        logger.info(f"{where_am_i}: Parsing spin groups and channels from line: {line}")

        spin_groups = []
        channels = None

        # Parse numbers 2 columns each starting at position 24
        numbers = cls._parse_numbers_from_line(line, 24, 2)
        logger.info(f"{where_am_i}: Parsed numbers: {numbers}")

        if not numbers:
            return spin_groups, channels

        # Check for continuation marker (-1)
        if numbers[-1] == -1:
            spin_groups.extend(numbers[:-1])
        else:
            # Check for IX=0 marker (indicates channels follow)
            if 0 in numbers:
                zero_index = numbers.index(0)
                spin_groups.extend(numbers[:zero_index])
                channels = numbers[zero_index + 1 :]
            else:
                spin_groups.extend(numbers)

        return spin_groups, channels

    @classmethod
    def from_lines(cls, lines: List[str]) -> "RadiusCardDefault":
        """Parse radius parameters from fixed-width format lines.

        Args:
            lines: List of input lines including header

        Returns:
            RadiusCardDefault: Parsed card

        Raises:
            ValueError: If lines are invalid or required data is missing
        """
        where_am_i = "RadiusCardDefault.from_lines()"

        logger.info(f"{where_am_i}: Parsing radius parameters from lines")
        if not lines:
            logger.error(f"{where_am_i}: No lines provided")
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            logger.error(f"{where_am_i}: Invalid header line: {lines[0]}")
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Get content lines (skip header and trailing blank)
        content_lines = [line for line in lines[1:] if line.strip()]
        if not content_lines:
            logger.error(f"{where_am_i}: No parameter lines found")
            raise ValueError("No parameter lines found")

        # Initialize list to hold RadiusParameters objects
        radius_parameters_list = []

        # Parse each line for main parameters and spin groups
        for line in content_lines:
            # Ensure line is long enough
            if len(line) < 24:  # Minimum length for main parameters
                logger.error(f"{where_am_i}: Parameter line too short")
                raise ValueError("Parameter line too short")

            # Parse main parameters
            params = {
                "effective_radius": safe_parse(line[FORMAT_DEFAULT["pareff"]]),
                "true_radius": safe_parse(line[FORMAT_DEFAULT["partru"]]),
                "channel_mode": safe_parse(line[FORMAT_DEFAULT["ichan"]], as_int=True) or 0,
            }

            # Parse flags
            try:
                params["vary_effective"] = VaryFlag(int(line[FORMAT_DEFAULT["ifleff"]].strip() or "0"))
                params["vary_true"] = VaryFlag(int(line[FORMAT_DEFAULT["ifltru"]].strip() or "0"))
                logger.info(f"{where_am_i}: Successfully parsed flags")
            except ValueError:
                logger.error(f"{where_am_i}: Invalid vary flags")
                raise ValueError("Invalid vary flags")

            # Parse spin groups and channels
            spin_groups, channels = cls._parse_spin_groups_and_channels(line)

            if not spin_groups:
                logger.error(f"{where_am_i}: No spin groups found")
                raise ValueError("No spin groups found")

            params["spin_groups"] = spin_groups
            params["channels"] = channels

            # Create parameters object
            try:
                parameters = RadiusParameters(**params)
                logger.info(f"{where_am_i}: Successfully created radius parameters")
                radius_parameters_list.append(parameters)
            except ValueError as e:
                logger.error(f"{where_am_i}: Invalid parameter values: {e}")
                raise ValueError(f"Invalid parameter values: {e}")

        logger.info(f"{where_am_i}: Successfully parsed radius parameters")

        return cls(parameters=radius_parameters_list)

    def to_lines(self) -> List[str]:
        """Convert the card to fixed-width format lines.

        Returns:
            List[str]: Lines including header
        """
        where_am_i = "RadiusCardDefault.to_lines()"

        logger.info(f"{where_am_i}: Converting radius parameters to lines")
        lines = []

        for params in self.parameters:
            # Format main parameters
            main_parts = [
                format_float(params.effective_radius, width=10),
                format_float(params.true_radius, width=10),
                str(params.channel_mode),
                format_vary(params.vary_effective),
                format_vary(params.vary_true),
            ]

            # Add spin groups (up to 28 per line)
            spin_groups = params.spin_groups
            spin_group_lines = []

            current_line = []
            for group in spin_groups:
                current_line.append(f"{group:2d}")
                if len(current_line) == 28:  # Max groups per line
                    spin_group_lines.append("".join(current_line))
                    current_line = []

            # Add any remaining groups
            if current_line:
                spin_group_lines.append("".join(current_line))

            # Combine main parameters with first line of spin groups
            if spin_group_lines:
                first_line = "".join(main_parts)
                if len(spin_group_lines[0]) > 0:
                    first_line += spin_group_lines[0]
                lines.append(first_line)

                # Add remaining spin group lines
                lines.extend(spin_group_lines[1:])

            # Add channels if present
            if params.channels:
                channel_line = "0"  # IX=0 marker
                for channel in params.channels:
                    channel_line += f"{channel:2d}"
                lines.append(channel_line)

        logger.info(f"{where_am_i}: Successfully converted radius parameters to lines")
        return lines


class RadiusCardAlternate(BaseModel):
    """Handler for alternate format radius parameter cards (Card Set 7 alternate).

    This class handles parsing and writing radius parameters in the alternate
    fixed-width format used for systems with more than 99 spin groups.

    The format includes:
    - Fixed width fields for radii and flags (same positions as default)
    - 5-column width for integer values (instead of 2)
    - Support for continuation lines with -1 marker
    - Optional channel numbers after IX=0 marker when channel_mode=1

    Note:
        This format should be used when the number of spin groups >= 99.
        For smaller systems, use RadiusCardDefault.
    """

    parameters: RadiusParameters

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if line is a valid header
        """
        where_am_i = "RadiusCardAlternate.is_header_line()"
        logger.info(f"{where_am_i}: Checking if header line - {line}")
        return line.strip().upper().startswith("RADIU")

    @staticmethod
    def _parse_numbers_from_line(line: str, start_pos: int, width: int) -> List[int]:
        """Parse fixed-width integer values from a line.

        Args:
            line: Input line
            start_pos: Starting position
            width: Width of each field

        Returns:
            List[int]: List of parsed integers, stopping at first invalid value
        """
        where_am_i = "RadiusCardAlternate._parse_numbers_from_line()"
        logger.info(f"{where_am_i}: Parsing fixed-width integers from line")

        numbers = []
        pos = start_pos
        while pos + width <= len(line):
            value = safe_parse(line[pos : pos + width], as_int=True)
            if value is None:
                break
            numbers.append(value)
            pos += width
        return numbers

    @classmethod
    def _parse_spin_groups_and_channels(cls, lines: List[str]) -> Tuple[List[int], Optional[List[int]]]:
        """Parse spin groups and optional channels from lines.

        Args:
            lines: List of input lines containing spin groups/channels

        Returns:
            Tuple containing:
            - List[int]: Spin group numbers
            - Optional[List[int]]: Channel numbers if present

        Note:
            Handles continuation lines (-1 marker) and IX=0 marker for channels
        """
        where_am_i = "RadiusCardAlternate._parse_spin_groups_and_channels()"
        logger.info(f"{where_am_i}: Parsing spin groups and channels from lines")

        spin_groups = []
        channels = None
        logger.info(f"{where_am_i}: parsing spin groups and channels")

        for line in lines:
            # Parse numbers 5 columns each starting at position 35
            numbers = cls._parse_numbers_from_line(line, 35, 5)

            if not numbers:
                continue

            # Check for continuation marker (-1)
            if numbers[-1] == -1:
                spin_groups.extend(numbers[:-1])
                continue

            # Check for IX=0 marker (indicates channels follow)
            if 0 in numbers:
                zero_index = numbers.index(0)
                spin_groups.extend(numbers[:zero_index])
                channels = numbers[zero_index + 1 :]
                break

            spin_groups.extend(numbers)

        return spin_groups, channels

    @classmethod
    def from_lines(cls, lines: List[str]) -> "RadiusCardAlternate":
        """Parse radius parameters from fixed-width format lines.

        Args:
            lines: List of input lines including header

        Returns:
            RadiusCardAlternate: Parsed card

        Raises:
            ValueError: If lines are invalid or required data is missing
        """
        where_am_i = "RadiusCardAlternate.from_lines()"
        logger.info(f"{where_am_i}: Parsing radius parameters from lines")

        if not lines:
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            logger.error(f"{where_am_i}: Invalid header line: {lines[0]}")
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Get content lines (skip header and trailing blank)
        content_lines = [line for line in lines[1:] if line.strip()]
        if not content_lines:
            logger.error(f"{where_am_i}: No parameter lines found")
            raise ValueError("No parameter lines found")

        # Parse first line for main parameters
        main_line = content_lines[0]

        # Ensure line is long enough
        if len(main_line) < 35:  # Minimum length for main parameters
            logger.error(f"{where_am_i}: Parameter line too short")
            raise ValueError("Parameter line too short")

        # Parse main parameters
        params = {
            "effective_radius": safe_parse(main_line[FORMAT_ALTERNATE["pareff"]]),
            "true_radius": safe_parse(main_line[FORMAT_ALTERNATE["partru"]]),
            "channel_mode": safe_parse(main_line[FORMAT_ALTERNATE["ichan"]], as_int=True) or 0,
        }

        # Parse flags (5-column format)
        try:
            params["vary_effective"] = VaryFlag(int(main_line[FORMAT_ALTERNATE["ifleff"]].strip() or "0"))
            params["vary_true"] = VaryFlag(int(main_line[FORMAT_ALTERNATE["ifltru"]].strip() or "0"))
        except ValueError:
            logger.error(f"{where_am_i}: Invalid vary flags")
            raise ValueError("Invalid vary flags")

        # Parse spin groups and channels
        spin_groups, channels = cls._parse_spin_groups_and_channels(content_lines)

        if not spin_groups:
            logger.error(f"{where_am_i}: No spin groups found")
            raise ValueError("No spin groups found")

        params["spin_groups"] = spin_groups
        params["channels"] = channels

        # Create parameters object
        try:
            parameters = RadiusParameters(**params)
        except ValueError as e:
            logger.error(f"{where_am_i}: Invalid parameter values: {e}")
            raise ValueError(f"Invalid parameter values: {e}")

        logger.info(f"{where_am_i}: Successfully parsed radius parameters")
        return cls(parameters=parameters)

    def to_lines(self) -> List[str]:
        """Convert the card to fixed-width format lines.

        Returns:
            List[str]: Lines including header
        """

        lines = []

        # Format main parameters
        main_parts = [
            format_float(self.parameters.effective_radius, width=10),
            format_float(self.parameters.true_radius, width=10),
            f"{self.parameters.channel_mode:>5}",  # 5-column format
            f"{self.parameters.vary_effective.value:>5}",  # 5-column format
            f"{self.parameters.vary_true.value:>5}",  # 5-column format
        ]

        # Add spin groups (up to 9 per line due to 5-column width)
        spin_groups = self.parameters.spin_groups
        spin_group_lines = []

        current_line = []
        for group in spin_groups:
            current_line.append(f"{group:>5}")  # Right-align in 5 columns
            if len(current_line) == 9:  # Max groups per line
                spin_group_lines.append("".join(current_line))
                current_line = []

        # Add any remaining groups
        if current_line:
            spin_group_lines.append("".join(current_line))

        # Combine main parameters with first line of spin groups
        if spin_group_lines:
            first_line = "".join(main_parts)
            if len(spin_group_lines[0]) > 0:
                first_line += spin_group_lines[0]
            lines.append(first_line)

            # Add remaining spin group lines
            lines.extend(spin_group_lines[1:])

        # Add channels if present (using 5-column format)
        if self.parameters.channels:
            channel_line = f"{0:>5}"  # IX=0 marker
            for channel in self.parameters.channels:
                channel_line += f"{channel:>5}"
            lines.append(channel_line)

        # Add trailing blank line
        lines.append("")

        return lines


class RadiusCardKeyword(BaseModel):
    """Handler for keyword-based radius parameter cards (Card Set 7a).

    This class handles parsing and writing radius parameters in the keyword format.
    The format offers a more readable alternative to fixed-width formats while
    maintaining compatibility with RadiusParameters.

    Attributes:
        parameters: The core radius parameters
        particle_pair: Optional particle pair specification
        orbital_momentum: Optional orbital angular momentum values
        relative_uncertainty: Optional relative uncertainty for radii
        absolute_uncertainty: Optional absolute uncertainty for radii
    """

    parameters: RadiusParameters

    # Optional keyword format extras
    particle_pair: Optional[str] = None
    orbital_momentum: Optional[List[Union[int, str]]] = None
    relative_uncertainty: Optional[float] = None
    absolute_uncertainty: Optional[float] = None

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line."""
        where_am_i = "RadiusCardKeyword.is_header_line()"
        logger.info(f"{where_am_i}: Checking if header line - {line}")
        return "RADII" in line.upper() and "KEY-WORD" in line.upper()

    @staticmethod
    def _parse_values(value_str: str) -> List[str]:
        """Parse space/comma separated values."""
        where_am_i = "RadiusCardKeyword._parse_values()"
        logger.info(f"{where_am_i}: Parsing values from string: {value_str}")
        return [v for v in re.split(r"[,\s]+", value_str.strip()) if v]

    @classmethod
    def from_lines(cls, lines: List[str]) -> "RadiusCardKeyword":
        """Parse radius parameters from keyword format lines.

        Args:
            lines: List of input lines including header

        Returns:
            RadiusCardKeyword: Parsed card

        Raises:
            ValueError: If lines are invalid or required data is missing
        """
        where_am_i = "RadiusCardKeyword.from_lines()"
        if not lines:
            logger.error(f"{where_am_i}: No lines provided")
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            logger.error(f"{where_am_i}: Invalid header line: {lines[0]}")
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Parse parameters for RadiusParameters
        params = {
            "effective_radius": None,
            "true_radius": None,
            "channel_mode": 0,
            "vary_effective": VaryFlag.NO,
            "vary_true": VaryFlag.NO,
            "spin_groups": [],
            "channels": None,
        }

        # Parse keyword format extras
        extras = {
            "particle_pair": None,
            "orbital_momentum": None,
            "relative_uncertainty": None,
            "absolute_uncertainty": None,
        }

        # Combine all non-empty lines into single string for parsing
        text = "\n".join(line for line in lines[1:] if line.strip())

        # Use the new parser
        data = parse_keyword_pairs_to_dict(text)

        for key, value in data.items():
            key = key.lower()

            if key == "radius":
                if isinstance(value, list):
                    params["effective_radius"] = value[0]
                    params["true_radius"] = value[1]
                else:
                    params["effective_radius"] = value
                    params["true_radius"] = value

            elif key == "flags":
                if isinstance(value, list):
                    params["vary_effective"] = VaryFlag(int(value[0]))
                    params["vary_true"] = VaryFlag(int(value[1]))
                else:
                    params["vary_effective"] = VaryFlag(value)
                    params["vary_true"] = VaryFlag(value)

            elif key in ["pp", "particle-pair"]:
                extras["particle_pair"] = value

            elif key in ["l", "orbital"]:
                if isinstance(value, list):
                    extras["orbital_momentum"] = [str(v).lower() if isinstance(v, str) else v for v in value]
                else:
                    extras["orbital_momentum"] = [str(value).lower()]

            elif key == "relative":
                extras["relative_uncertainty"] = value[0] if isinstance(value, list) else value

            elif key == "absolute":
                extras["absolute_uncertainty"] = value[0] if isinstance(value, list) else value

            elif key == "channels":
                params["channels"] = [int(x) for x in value]
                params["channel_mode"] = 1

            elif key == "group":
                if isinstance(value, list):
                    params["spin_groups"] = [int(x) for x in value]
                elif isinstance(value, int):
                    params["spin_groups"] = [value]
                else:
                    raise ValueError("Invalid group value")

        # Validate required parameters
        if not params["spin_groups"] and not (extras["particle_pair"] and extras["orbital_momentum"]):
            raise ValueError("Must specify either spin groups or both particle pair (PP) and orbital momentum (L)")

        # Create RadiusParameters instance
        try:
            parameters = RadiusParameters(**params)
        except ValueError as e:
            raise ValueError(f"Invalid parameter values: {e}")

        return cls(parameters=parameters, **extras)

    def to_lines(self) -> List[str]:
        """Convert the card to keyword format lines.

        Returns:
            List[str]: Lines in keyword format
        """
        where_am_i = "RadiusCardKeyword.to_lines()"
        logger.info(f"{where_am_i}: Converting radius parameters to lines")
        lines = []

        # Add radius values
        if self.parameters.true_radius == self.parameters.effective_radius:
            lines.append(f"Radius= {self.parameters.effective_radius}")
        else:
            lines.append(f"Radius= {self.parameters.effective_radius} {self.parameters.true_radius}")

        # Add flags
        if self.parameters.vary_true == self.parameters.vary_effective:
            lines.append(f"Flags= {self.parameters.vary_effective.value}")
        else:
            lines.append(f"Flags= {self.parameters.vary_effective.value} {self.parameters.vary_true.value}")

        # Add uncertainties if present
        if self.relative_uncertainty is not None:
            lines.append(f"Relative= {self.relative_uncertainty}")
        if self.absolute_uncertainty is not None:
            lines.append(f"Absolute= {self.absolute_uncertainty}")

        # Add particle pair and orbital momentum if present
        if self.particle_pair:
            lines.append(f"PP= {self.particle_pair}")
        if self.orbital_momentum:
            lines.append(f"L= {' '.join(str(x) for x in self.orbital_momentum)}")

        # Add group and channel specifications
        if self.parameters.channel_mode == 1 and self.parameters.channels:
            for group in self.parameters.spin_groups:
                lines.append(f"Group= {group} Channels= {' '.join(str(x) for x in self.parameters.channels)}")
        else:
            lines.append(f"Group= {' '.join(str(x) for x in self.parameters.spin_groups)}")

        lines.append("")  # Trailing blank line
        return lines


####################################################################################################
# RadiusCard Class (what is called in parfile.py)
####################################################################################################
class RadiusCard(BaseModel):
    """Main handler for SAMMY radius parameter cards.

    This class provides a simple interface for working with radius parameters
    regardless of format. Users can create parameters directly or read from
    template files, then write in any supported format.

    Example:
        # Create new parameters
        card = RadiusCard(
            parameters=[
                RadiusParameters(
                    effective_radius=3.2,
                    true_radius=3.2,
                    spin_groups=[1, 2, 3]
                )
            ]
        )

        # Write in desired format
        lines = card.to_lines(format=RadiusFormat.KEYWORD)

        # Or read from template and modify
        card = RadiusCard.from_lines(template_lines)
        card.parameters[0].effective_radius = 3.5
        lines = card.to_lines(format=RadiusFormat.DEFAULT)
    """

    parameters: List[RadiusParameters]

    # Optional keyword format extras
    particle_pair: Optional[str] = None
    orbital_momentum: Optional[List[Union[int, str]]] = None
    relative_uncertainty: Optional[float] = None
    absolute_uncertainty: Optional[float] = None

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid radius parameter header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if line matches any valid radius header format
        """
        # set location for logger
        where_am_i = "RadiusCard.is_header_line()"

        line_upper = line.strip().upper()

        logger.info(f"{where_am_i}: {line_upper}")

        # Check all valid header formats
        valid_headers = [
            "RADIUS PARAMETERS FOLLOW",  # Standard/Alternate fixed width
            "RADII ARE IN KEY-WORD FORMAT",  # Keyword format
            "CHANNEL RADIUS PARAMETERS FOLLOW",  # Alternative keyword format
        ]

        return any(header in line_upper for header in valid_headers)

    @classmethod
    def detect_format(cls, lines: List[str]) -> RadiusFormat:
        """Detect format from input lines."""
        where_am_i = "RadiusCard.detect_format()"

        if not lines:
            _log_and_raise_error(logger, "No lines provided", ValueError)

        # Grab header from lines (suppose to be the first line)
        header = lines[0].strip().upper()
        logger.info(f"{where_am_i}: Header line: {header}")

        # Check for valid header formats
        # If KEY-WORD is in the header, it is a keyword format
        if "KEY-WORD" in header:
            logger.info(f"{where_am_i}: Detected keyword format!")
            return RadiusFormat.KEYWORD

        # If DEFAULT or ALTERNATE card formats then "RADIUS" should be in the header
        elif "RADIU" in header:
            # Check format by examining spin group columns
            content_line = next((l for l in lines[1:] if l.strip()), "")  # noqa: E741

            # Check for alternate format (5-column integer values)
            if len(content_line) >= 35 and content_line[25:30].strip():  # 5-col format
                logger.info(f"{where_am_i}: Detected ALTERNATE format based on {content_line}")
                return RadiusFormat.ALTERNATE

            logger.info(f"{where_am_i}: Detected DEFAULT format based on {content_line}")
            return RadiusFormat.DEFAULT

        _log_and_raise_error(logger, "Invalid header format...", ValueError)

    @classmethod
    def from_lines(cls, lines: List[str]) -> "RadiusCard":
        """Parse radius card from lines in any format."""
        where_am_i = "RadiusCard.from_lines()"

        logger.info(f"{where_am_i}: Attempting to parse radius card from lines")
        format_type = cls.detect_format(lines)

        # Try reading in the radius card based on the determined format
        try:
            if format_type == RadiusFormat.KEYWORD:
                keyword_card = RadiusCardKeyword.from_lines(lines)
                logger.info(f"{where_am_i}: Successfully parsed radius card in keyword format")
                return cls(
                    parameters=[keyword_card.parameters],
                    particle_pair=keyword_card.particle_pair,
                    orbital_momentum=keyword_card.orbital_momentum,
                    relative_uncertainty=keyword_card.relative_uncertainty,
                    absolute_uncertainty=keyword_card.absolute_uncertainty,
                )
            elif format_type == RadiusFormat.ALTERNATE:
                radius_card = cls(parameters=[RadiusCardAlternate.from_lines(lines).parameters])
                logger.info(f"{where_am_i}: Successfully parsed radius card from lines in alternate format")
                return radius_card
            else:
                radius_card = cls(parameters=RadiusCardDefault.from_lines(lines).parameters)
                logger.info(f"{where_am_i}: Successfully parsed radius card from lines in default format")
                return radius_card

        except Exception as e:
            logger.error(f"{where_am_i}Failed to parse radius card: {str(e)}\nLines: {lines}")
            raise ValueError(f"Failed to parse radius card: {str(e)}\nLines: {lines}")

    def to_lines(self, radius_format: RadiusFormat = RadiusFormat.DEFAULT) -> List[str]:
        """Write radius card in specified format."""
        where_am_i = "RadiusCard.to_lines()"
        logger.info(f"{where_am_i}: Writing radius card in format: {radius_format}")

        try:
            if radius_format == RadiusFormat.KEYWORD:
                lines = [CARD_7A_HEADER]
                for param in self.parameters:
                    lines.extend(
                        RadiusCardKeyword(
                            parameters=param,
                            particle_pair=self.particle_pair,
                            orbital_momentum=self.orbital_momentum,
                            relative_uncertainty=self.relative_uncertainty,
                            absolute_uncertainty=self.absolute_uncertainty,
                        ).to_lines()
                    )
            elif radius_format == RadiusFormat.ALTERNATE:
                lines = [CARD_7_ALT_HEADER]
                for param in self.parameters:
                    lines.extend(RadiusCardAlternate(parameters=param).to_lines())
            else:
                lines = [CARD_7_HEADER]
                for param in self.parameters:
                    lines.extend(RadiusCardDefault(parameters=[param]).to_lines())

            # Add trailing blank line
            lines.append("")

            logger.info(f"{where_am_i}: Successfully wrote radius card")
            return lines

        except Exception as e:
            logger.error(f"{where_am_i}: Failed to write radius card: {str(e)}")
            raise ValueError(f"Failed to write radius card: {str(e)}")

    @classmethod
    def from_values(
        cls,
        effective_radius: float,
        true_radius: Optional[float] = None,
        spin_groups: List[int] = None,
        channels: Optional[List[int]] = None,
        particle_pair: Optional[str] = None,
        orbital_momentum: Optional[List[Union[int, str]]] = None,
        relative_uncertainty: Optional[float] = None,
        absolute_uncertainty: Optional[float] = None,
        **kwargs,
    ) -> "RadiusCard":
        """Create a new radius card from parameter values.

        Args:
            effective_radius: Radius for potential scattering
            true_radius: Radius for penetrabilities and shifts (defaults to effective_radius)
            spin_groups: List of spin group numbers
            channels: Optional list of channel numbers
            particle_pair: Optional particle pair specification
            orbital_momentum: Optional orbital angular momentum values
            relative_uncertainty: Optional relative uncertainty for radii
            absolute_uncertainty: Optional absolute uncertainty for radii
            **kwargs: Additional parameters to pass to RadiusParameters

        Returns:
            RadiusCard: Created card instance
        """
        where_am_i = "RadiusCard.from_values()"

        # Separate parameters and extras
        params = {
            "effective_radius": effective_radius,
            "true_radius": true_radius or effective_radius,
            "spin_groups": spin_groups or [],
            "channel_mode": 1 if channels else 0,
            "channels": channels,
        }
        params.update(kwargs)  # Only parameter-specific kwargs

        # Create card with both parameters and extras
        card = cls(
            parameters=[RadiusParameters(**params)],
            particle_pair=particle_pair,
            orbital_momentum=orbital_momentum,
            relative_uncertainty=relative_uncertainty,
            absolute_uncertainty=absolute_uncertainty,
        )

        logger.info(f"{where_am_i}: Successfully created RadiusCard")
        return card


####################################################################################################
# IDK what this is for!
####################################################################################################
class OrbitalMomentum(str, Enum):
    """Valid values for orbital angular momentum specification."""

    ODD = "ODD"
    EVEN = "EVEN"
    ALL = "ALL"


####################################################################################################
# main function
####################################################################################################
if __name__ == "__main__":
    # Example usage
    card = RadiusCard.from_values(effective_radius=3.2, true_radius=3.2, spin_groups=[1, 2, 3])
    lines = card.to_lines(radius_format=RadiusFormat.KEYWORD)
    print("\n".join(lines))
    print("Format:", RadiusCard.detect_format(lines))
    print("Parsed card:", RadiusCard.from_lines(lines))
