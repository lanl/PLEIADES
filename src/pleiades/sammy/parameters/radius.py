#!/usr/bin/env python
"""Card Set 7/7a: Radius Parameters.

This module handles both fixed-width (Card Set 7) and keyword-based (Card Set 7a) formats
for radius parameters in SAMMY parameter files.
"""

import logging
import re
from enum import Enum
from typing import List, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from pleiades.sammy.parameters.helper import VaryFlag, format_float, format_vary, safe_parse


class OrbitalMomentum(str, Enum):
    """Valid values for orbital angular momentum specification."""

    ODD = "ODD"
    EVEN = "EVEN"
    ALL = "ALL"


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

    effective_radius: float = Field(description="Radius for potential scattering (Fermi)")
    true_radius: float = Field(description="Radius for penetrabilities and shifts (Fermi)")
    channel_mode: int = Field(
        description="Channel specification mode (0: all channels, 1: specific channels)",
        ge=0,  # Greater than or equal to 0
        le=1,  # Less than or equal to 1
    )
    vary_effective: VaryFlag = Field(default=VaryFlag.NO, description="Flag for varying effective radius")
    vary_true: VaryFlag = Field(default=VaryFlag.NO, description="Flag for varying true radius")
    spin_groups: List[int] = Field(
        description="List of spin group numbers",
        min_length=1,  # Must have at least one spin group
    )
    channels: Optional[List[int]] = Field(default=None, description="List of channel numbers (required when channel_mode=1)")

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
                raise ValueError("When vary_true is USE_FROM_PARFILE (-1), " "true_radius must match effective_radius")

        # Special cases for true_radius
        if self.true_radius == 0:
            if self.vary_true == VaryFlag.USE_FROM_PARFILE:
                raise ValueError("When true_radius=0 (use CRFN value), " "vary_true cannot be USE_FROM_PARFILE (-1)")

        if self.true_radius < 0:
            if self.vary_true == VaryFlag.USE_FROM_PARFILE:
                raise ValueError("When true_radius is negative (AWRI specification), " "vary_true cannot be USE_FROM_PARFILE (-1)")

        return self


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

CARD_7_HEADER = "RADIUs parameters follow"


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

    parameters: RadiusParameters

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if line is a valid header
        """
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
        spin_groups = []
        channels = None

        for line in lines:
            # Parse numbers 2 columns each starting at position 24
            numbers = cls._parse_numbers_from_line(line, 24, 2)

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
    def from_lines(cls, lines: List[str]) -> "RadiusCardDefault":
        """Parse radius parameters from fixed-width format lines.

        Args:
            lines: List of input lines including header

        Returns:
            RadiusCardDefault: Parsed card

        Raises:
            ValueError: If lines are invalid or required data is missing
        """
        if not lines:
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Get content lines (skip header and trailing blank)
        content_lines = [line for line in lines[1:] if line.strip()]
        if not content_lines:
            raise ValueError("No parameter lines found")

        # Parse first line for main parameters
        main_line = content_lines[0]

        # Ensure line is long enough
        if len(main_line) < 24:  # Minimum length for main parameters
            raise ValueError("Parameter line too short")

        # Parse main parameters
        params = {
            "effective_radius": safe_parse(main_line[FORMAT_DEFAULT["pareff"]]),
            "true_radius": safe_parse(main_line[FORMAT_DEFAULT["partru"]]),
            "channel_mode": safe_parse(main_line[FORMAT_DEFAULT["ichan"]], as_int=True) or 0,
        }

        # Parse flags
        try:
            params["vary_effective"] = VaryFlag(int(main_line[FORMAT_DEFAULT["ifleff"]].strip() or "0"))
            params["vary_true"] = VaryFlag(int(main_line[FORMAT_DEFAULT["ifltru"]].strip() or "0"))
        except ValueError:
            raise ValueError("Invalid vary flags")

        # Parse spin groups and channels
        spin_groups, channels = cls._parse_spin_groups_and_channels(content_lines)

        if not spin_groups:
            raise ValueError("No spin groups found")

        params["spin_groups"] = spin_groups
        params["channels"] = channels

        # Create parameters object
        try:
            parameters = RadiusParameters(**params)
        except ValueError as e:
            raise ValueError(f"Invalid parameter values: {e}")

        return cls(parameters=parameters)

    def to_lines(self) -> List[str]:
        """Convert the card to fixed-width format lines.

        Returns:
            List[str]: Lines including header
        """
        lines = [CARD_7_HEADER]

        # Format main parameters
        main_parts = [
            format_float(self.parameters.effective_radius, width=10),
            format_float(self.parameters.true_radius, width=10),
            str(self.parameters.channel_mode),
            format_vary(self.parameters.vary_effective),
            format_vary(self.parameters.vary_true),
        ]

        # Add spin groups (up to 28 per line)
        spin_groups = self.parameters.spin_groups
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
        if self.parameters.channels:
            channel_line = "0"  # IX=0 marker
            for channel in self.parameters.channels:
                channel_line += f"{channel:2d}"
            lines.append(channel_line)

        # Add trailing blank line
        lines.append("")

        return lines


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

CARD_7_ALT_HEADER = "RADIUs parameters follow"


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
        spin_groups = []
        channels = None

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
        if not lines:
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Get content lines (skip header and trailing blank)
        content_lines = [line for line in lines[1:] if line.strip()]
        if not content_lines:
            raise ValueError("No parameter lines found")

        # Parse first line for main parameters
        main_line = content_lines[0]

        # Ensure line is long enough
        if len(main_line) < 35:  # Minimum length for main parameters
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
            raise ValueError("Invalid vary flags")

        # Parse spin groups and channels
        spin_groups, channels = cls._parse_spin_groups_and_channels(content_lines)

        if not spin_groups:
            raise ValueError("No spin groups found")

        params["spin_groups"] = spin_groups
        params["channels"] = channels

        # Create parameters object
        try:
            parameters = RadiusParameters(**params)
        except ValueError as e:
            raise ValueError(f"Invalid parameter values: {e}")

        return cls(parameters=parameters)

    def to_lines(self) -> List[str]:
        """Convert the card to fixed-width format lines.

        Returns:
            List[str]: Lines including header
        """
        lines = [CARD_7_ALT_HEADER]

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


CARD_7A_HEADER = "RADII are in KEY-WORD format"


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
    particle_pair: Optional[str] = None
    orbital_momentum: Optional[List[Union[int, str]]] = None
    relative_uncertainty: Optional[float] = None
    absolute_uncertainty: Optional[float] = None

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line."""
        return "RADII" in line.upper() and "KEY-WORD" in line.upper()

    @staticmethod
    def _parse_values(value_str: str) -> List[str]:
        """Parse space/comma separated values."""
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
        if not lines or not cls.is_header_line(lines[0]):
            raise ValueError("Invalid or missing header line")

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
        extras = {"particle_pair": None, "orbital_momentum": None, "relative_uncertainty": None, "absolute_uncertainty": None}

        for line in (l.strip() for l in lines[1:] if l.strip()):  # noqa: E741
            if "=" not in line:
                continue

            key, value = [x.strip().lower() for x in line.split("=", 1)]
            values = cls._parse_values(value)

            if not values:
                continue

            if key == "radius":
                params["effective_radius"] = float(values[0])
                params["true_radius"] = float(values[1] if len(values) > 1 else values[0])

            elif key == "flags":
                params["vary_effective"] = VaryFlag(int(values[0]))
                params["vary_true"] = VaryFlag(int(values[1] if len(values) > 1 else values[0]))

            elif key in ["relative", "absolute"]:
                value = float(values[0])
                if key == "relative":
                    extras["relative_uncertainty"] = value
                else:
                    extras["absolute_uncertainty"] = value

            elif key in ["particle-pair", "pp"]:
                extras["particle_pair"] = value

            elif key in ["orbital", "l"]:
                extras["orbital_momentum"] = []
                for v in values:
                    if v.lower() in ["odd", "even", "all"]:
                        extras["orbital_momentum"].append(v.lower())
                    else:
                        extras["orbital_momentum"].append(int(v))

            elif key == "group":
                if "channels" in value.lower():
                    # Group with channels format: "Group= 1 Channels= 1 2 3"
                    group_part, channel_part = value.lower().split("channels")
                    params["spin_groups"].append(int(cls._parse_values(group_part)[0]))
                    params["channels"] = [int(x) for x in cls._parse_values(channel_part)]
                    params["channel_mode"] = 1
                else:
                    # Simple group format: "Group= 1"
                    params["spin_groups"].extend(int(x) for x in values)

        if not params["effective_radius"]:
            raise ValueError("No radius values specified")

        if not params["spin_groups"]:
            # Check if we have both PP and L specified
            if not (extras["particle_pair"] and extras["orbital_momentum"]):
                raise ValueError("Must specify either spin groups or both particle pair (PP) and orbital momentum (L)")

        # Create RadiusParameters instance first
        parameters = RadiusParameters(**params)

        return cls(parameters=parameters, **extras)

    def to_lines(self) -> List[str]:
        """Convert the card to keyword format lines.

        Returns:
            List[str]: Lines in keyword format
        """
        lines = [CARD_7A_HEADER]

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


class RadiusFormat(Enum):
    """Supported formats for radius parameter cards."""

    DEFAULT = "default"  # Fixed width (<99 spin groups)
    ALTERNATE = "alternate"  # Fixed width (>=99 spin groups)
    KEYWORD = "keyword"  # Keyword based


class RadiusCard(BaseModel):
    """Main handler for SAMMY radius parameter cards.

    This class provides a simple interface for working with radius parameters
    regardless of format. Users can create parameters directly or read from
    template files, then write in any supported format.

    Example:
        # Create new parameters
        card = RadiusCard(
            effective_radius=3.2,
            true_radius=3.2,
            spin_groups=[1, 2, 3]
        )

        # Write in desired format
        lines = card.to_lines(format=RadiusFormat.KEYWORD)

        # Or read from template and modify
        card = RadiusCard.from_lines(template_lines)
        card.parameters.effective_radius = 3.5
        lines = card.to_lines(format=RadiusFormat.DEFAULT)
    """

    parameters: RadiusParameters
    # Optional keyword format extras
    particle_pair: Optional[str] = None
    orbital_momentum: Optional[List[Union[int, str]]] = None
    relative_uncertainty: Optional[float] = None
    absolute_uncertainty: Optional[float] = None

    @classmethod
    def detect_format(cls, lines: List[str]) -> RadiusFormat:
        """Detect format from input lines."""
        if not lines:
            raise ValueError("No lines provided")

        header = lines[0].strip().upper()
        if "KEY-WORD" in header:
            return RadiusFormat.KEYWORD
        elif "RADIU" in header:
            # Check format by examining spin group columns
            content_line = next((l for l in lines[1:] if l.strip()), "")  # noqa: E741
            if len(content_line) >= 35 and content_line[25:30].strip():  # 5-col format
                return RadiusFormat.ALTERNATE
            return RadiusFormat.DEFAULT

        raise ValueError("Invalid header format")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "RadiusCard":
        """Parse radius card from lines in any format."""
        format_type = cls.detect_format(lines)

        if format_type == RadiusFormat.KEYWORD:
            keyword_card = RadiusCardKeyword.from_lines(lines)
            return cls(
                parameters=keyword_card.parameters,
                particle_pair=keyword_card.particle_pair,
                orbital_momentum=keyword_card.orbital_momentum,
                relative_uncertainty=keyword_card.relative_uncertainty,
                absolute_uncertainty=keyword_card.absolute_uncertainty,
            )
        elif format_type == RadiusFormat.ALTERNATE:
            return cls(parameters=RadiusCardAlternate.from_lines(lines).parameters)
        else:
            return cls(parameters=RadiusCardDefault.from_lines(lines).parameters)

    def to_lines(self, radius_format: RadiusFormat = RadiusFormat.DEFAULT) -> List[str]:
        """Write radius card in specified format."""
        if radius_format == RadiusFormat.KEYWORD:
            return RadiusCardKeyword(
                parameters=self.parameters,
                particle_pair=self.particle_pair,
                orbital_momentum=self.orbital_momentum,
                relative_uncertainty=self.relative_uncertainty,
                absolute_uncertainty=self.absolute_uncertainty,
            ).to_lines()
        elif radius_format == RadiusFormat.ALTERNATE:
            return RadiusCardAlternate(parameters=self.parameters).to_lines()
        else:
            return RadiusCardDefault(parameters=self.parameters).to_lines()

    @classmethod
    def from_values(
        cls,
        effective_radius: float,
        true_radius: Optional[float] = None,
        spin_groups: List[int] = None,
        channels: Optional[List[int]] = None,
        **kwargs,
    ) -> "RadiusCard":
        """Create a new radius card from parameter values.

        A convenience method for creating cards directly from values.
        """
        params = {
            "effective_radius": effective_radius,
            "true_radius": true_radius or effective_radius,
            "spin_groups": spin_groups or [],
            "channel_mode": 1 if channels else 0,
            "channels": channels,
        }
        params.update(kwargs)  # Allow setting other parameters

        return cls(parameters=RadiusParameters(**params))


if __name__ == "__main__":
    # Enable logging for debugging
    logging.basicConfig(level=logging.DEBUG)

    # Test Targets:
    # 1. Fixed-Width Format Tests (Default Format)
    # - Basic single line (effective_radius, true_radius, single spin group)
    # - Multiple spin groups on one line
    # - Spin groups with continuation (-1 marker)
    # - Channel specification with IX=0 marker
    # - Error case: Invalid format/missing required fields

# 2. Alternate Format Tests (>99 spin groups)
# - Basic alternate format parsing (5-column integers)
# - Multiple spin groups in alternate format
# - Channel specification in alternate format
# - Error case: Invalid alternate format

# 3. Keyword Format Tests
# - Basic radius specification (single value)
# - Separate effective/true radius values
# - Uncertainty specifications (relative and absolute)
# - Particle pair and orbital momentum
# - Groups with channel specifications
# - Error case: Invalid keyword format

# 4. Format Detection and Conversion
# - Detect and parse default format
# - Detect and parse alternate format
# - Detect and parse keyword format
# - Convert between formats
# - Error case: Invalid/ambiguous format

# 5. Direct Parameter Creation
# - Create from minimal values
# - Create with full parameter set
# - Create with keyword format extras
# - Error case: Invalid parameter combinations
