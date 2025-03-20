#!/usr/bin/env python
"""Parser for SAMMY's Card Set 16 (User-Defined Resolution Function) parameters.

Format specification from Table VI B.2:
Card Set 16 defines user-defined resolution functions with the following components:

1. Header line ("USER-Defined resolution function")
2. Optional BURST line for burst width parameters
3. Optional CHANN lines for channel-dependent parameters
4. Required FILE= lines specifying data files

Each section has specific fixed-width format requirements.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from pleiades.utils.helper import VaryFlag, format_float, format_vary, safe_parse

# Format definitions - column positions for each parameter type
FORMAT_SPECS = {
    "BURST": {
        "identifier": slice(0, 5),  # "BURST"
        "flag": slice(6, 7),  # IFBRST
        "width": slice(10, 20),  # BURST value
        "uncertainty": slice(20, 30),  # dBURST
    },
    "CHANN": {
        "identifier": slice(0, 5),  # "CHANN"
        "flag": slice(6, 7),  # ICH flag
        "energy": slice(10, 20),  # ECRNCH
        "width": slice(20, 30),  # CH value
        "uncertainty": slice(30, 40),  # dCH
    },
    "FILE": {
        "identifier": slice(0, 5),  # "FILE="
        "name": slice(5, 75),  # Filename
    },
}


class Card16ParameterType(str, Enum):
    """Enumeration of Card 16 parameter types."""

    USER = "USER"  # Header identifier
    BURST = "BURST"
    CHANN = "CHANN"
    FILE = "FILE="


class UserResolutionParameters(BaseModel):
    """Container for User-Defined Resolution Function parameters.

    Attributes:
        type: Parameter type identifier (always "USER")
        burst_width: Square burst width value (ns), optional
        burst_uncertainty: Uncertainty on burst width, optional
        burst_flag: Flag for varying burst width
        channel_energies: List of energies for channel widths
        channel_widths: List of channel width values
        channel_uncertainties: List of uncertainties on channel widths
        channel_flags: List of flags for varying channel widths
        filenames: List of data file names
    """

    type: Card16ParameterType = Card16ParameterType.USER
    burst_width: Optional[float] = Field(None, description="Square burst width (ns)")
    burst_uncertainty: Optional[float] = Field(None, description="Uncertainty on burst width")
    burst_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for burst width")
    channel_energies: List[float] = Field(default_factory=list, description="Energies for channels")
    channel_widths: List[float] = Field(default_factory=list, description="Channel width values")
    channel_uncertainties: List[Optional[float]] = Field(default_factory=list, description="Channel uncertainties")
    channel_flags: List[VaryFlag] = Field(default_factory=list, description="Channel flags")
    filenames: List[str] = Field(default_factory=list, description="Resolution function filenames")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "UserResolutionParameters":
        """Parse user resolution parameters from fixed-width format lines."""
        if not lines:
            raise ValueError("No lines provided")

        # Verify header line
        header = lines[0].strip()
        if not header.startswith("USER-Defined"):
            raise ValueError(f"Invalid header: {header}")

        # Initialize parameters
        params = cls()

        # Process remaining lines
        current_line = 1
        while current_line < len(lines):
            line = f"{lines[current_line]:<80}"  # Pad to full width

            # Skip blank lines
            if not line.strip():
                current_line += 1
                continue

            # Parse BURST line
            if line.startswith("BURST"):
                # Verify identifier
                identifier = line[FORMAT_SPECS["BURST"]["identifier"]].strip()
                if identifier != "BURST":
                    raise ValueError(f"Invalid BURST identifier: {identifier}")

                # Parse flag
                try:
                    burst_flag = VaryFlag(int(line[FORMAT_SPECS["BURST"]["flag"]].strip() or "0"))
                except ValueError as e:
                    raise ValueError(f"Invalid BURST flag value: {e}")

                # Parse width and uncertainty
                burst_width = safe_parse(line[FORMAT_SPECS["BURST"]["width"]])
                if burst_width is None:
                    raise ValueError("Missing required burst width value")

                burst_uncertainty = safe_parse(line[FORMAT_SPECS["BURST"]["uncertainty"]])

                params.burst_width = burst_width
                params.burst_uncertainty = burst_uncertainty
                params.burst_flag = burst_flag

            elif line.startswith("CHANN"):
                # Verify identifier
                identifier = line[FORMAT_SPECS["CHANN"]["identifier"]].strip()
                if identifier != "CHANN":
                    raise ValueError(f"Invalid CHANN identifier: {identifier}")

                # Parse flag
                try:
                    flag = VaryFlag(int(line[FORMAT_SPECS["CHANN"]["flag"]].strip() or "0"))
                except ValueError as e:
                    raise ValueError(f"Invalid CHANN flag value: {e}")

                # Parse required values
                energy = safe_parse(line[FORMAT_SPECS["CHANN"]["energy"]])
                width = safe_parse(line[FORMAT_SPECS["CHANN"]["width"]])
                if energy is None or width is None:
                    raise ValueError("Missing required energy or width value")

                # Parse optional uncertainty
                uncertainty = safe_parse(line[FORMAT_SPECS["CHANN"]["uncertainty"]])

                # Append values to lists
                params.channel_energies.append(energy)
                params.channel_widths.append(width)
                params.channel_uncertainties.append(uncertainty)
                params.channel_flags.append(flag)

            elif line.startswith("FILE="):
                # Verify identifier and format
                identifier = line[FORMAT_SPECS["FILE"]["identifier"]].strip()
                if identifier != "FILE=":
                    raise ValueError(f"Invalid FILE identifier: {identifier}")

                # Get raw filename by removing "FILE=" prefix
                raw_filename = line[5:].strip()  # Everything after FILE=
                if not raw_filename:
                    raise ValueError("Missing filename")

                # Check raw filename length before column slicing
                if len(raw_filename) > 70:
                    raise ValueError(f"Filename length ({len(raw_filename)}) exceeds maximum length (70 characters)")

                # Now we can safely use the column slice knowing it won't truncate valid data
                filename = line[FORMAT_SPECS["FILE"]["name"]].strip()
                params.filenames.append(filename)

            else:
                raise ValueError(f"Invalid line type: {line.strip()}")

            current_line += 1

        return params

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines."""
        lines = ["USER-Defined resolution function"]

        # Add BURST line if parameters present
        if self.burst_width is not None:
            burst_parts = [
                "BURST",  # Identifier
                " ",  # Column 6 spacing
                format_vary(self.burst_flag),  # Col 7
                "   ",  # Columns 8-10 spacing
                format_float(self.burst_width, width=10),
                format_float(self.burst_uncertainty, width=10),
            ]
            lines.append("".join(burst_parts))

        # Add CHANN lines if parameters present
        for i in range(len(self.channel_energies)):
            channel_parts = [
                "CHANN",  # Identifier
                " ",  # Column 6 spacing
                format_vary(self.channel_flags[i]),  # Col 7
                "   ",  # Columns 8-10 spacing
                format_float(self.channel_energies[i], width=10),
                format_float(self.channel_widths[i], width=10),
                format_float(self.channel_uncertainties[i], width=10),
            ]
            lines.append("".join(channel_parts))

        # Add FILE lines if present
        for filename in self.filenames:
            lines.append(f"FILE={filename}")

        # Add required blank line at end per spec
        lines.append("")

        return lines


if __name__ == "__main__":
    print("Refer to unit tests for usage examples.")
