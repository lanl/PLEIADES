#!/usr/bin/env python
"""Data class for card 01::resonance."""

from typing import List, Optional

from pydantic import BaseModel, Field

from pleiades.utils.helper import VaryFlag, safe_parse
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


# Define format constants
RESONANCE_FORMAT = {
    "resonance_energy": slice(0, 11),
    "capture_width": slice(11, 22),
    "channel1_width": slice(22, 33),
    "channel2_width": slice(33, 44),
    "channel3_width": slice(44, 55),
    "vary_energy": slice(55, 57),
    "vary_capture_width": slice(57, 59),
    "vary_channel1": slice(59, 61),
    "vary_channel2": slice(61, 63),
    "vary_channel3": slice(63, 65),
    "igroup": slice(65, 67),
    "x_value": slice(67, 80),  # Added to detect special cases
}


class UnsupportedFormatError(ValueError):
    """Error raised when encountering unsupported format features."""

    pass


class ResonanceEntry(BaseModel):
    """This class handles the parameters for a single resonance entry in Card Set 1 of a SAMMY parameter file.

    Single resonance entry for SAMMY parameter file (strict format)

    Attributes:
        resonance_energy: Resonance energy Eλ (eV)
        capture_width: Capture width Γγ (milli-eV)

        channel1_width: Particle width for channel 1 (milli-eV)
        channel2_width: Particle width for channel 2 (milli-eV)
        channel3_width: Particle width for channel 3 (milli-eV)
        NOTE:   If any particle width Γ is negative, SAMMY uses abs(Γ)
                for the width and set the associated amplitude γ to be negative.

        vary_energy:    Flag indicating if resonance energy is varied
        vary_capture_width: Flag indicating if capture width is varied
        vary_channel1: Flag indicating if channel 1 width is varied
        vary_channel2: Flag indicating if channel 2 width is varied
        vary_channel3: Flag indicating if channel 3 width is varied
        NOTE:   0 = no, 1 = yes, 3 = PUP (PUP = Partially Unknown Parameter)

        igroup: Quantum numbers group number (or spin_groups)
        NOTE:   If IGROUP is negative or greater than 50, this resonance will be
                omitted from the calculation.

        x_value: Special value used to detect multi-line entries (unsupported)

    """

    resonance_energy: float = Field(description="Resonance energy Eλ (eV)")
    capture_width: float = Field(description="Capture width Γγ (milli-eV)")
    channel1_width: Optional[float] = Field(None, description="Particle width for channel 1 (milli-eV)")
    channel2_width: Optional[float] = Field(None, description="Particle width for channel 2 (milli-eV)")
    channel3_width: Optional[float] = Field(None, description="Particle width for channel 3 (milli-eV)")
    vary_energy: VaryFlag = Field(default=VaryFlag.NO)
    vary_capture_width: VaryFlag = Field(default=VaryFlag.NO)
    vary_channel1: VaryFlag = Field(default=VaryFlag.NO)
    vary_channel2: VaryFlag = Field(default=VaryFlag.NO)
    vary_channel3: VaryFlag = Field(default=VaryFlag.NO)
    igroup: int = Field(description="Quantum numbers group number")

    @classmethod
    def from_str(cls, line: str) -> "ResonanceEntry":
        """Parse a resonance entry from a fixed-width format line"""
        if not line.strip():
            raise ValueError("Empty line provided")

        # Make sure line is at least 80 characters
        line = f"{line:<80}"

        # Check for special cases we don't support
        x_value = line[RESONANCE_FORMAT["x_value"]].strip()

        if x_value:
            try:
                x_float = float(x_value)
                if x_float < 0:
                    raise UnsupportedFormatError(
                        "SORRY! While SAMMY allows multi-line resonance entries (indicated by negative "
                        "X value in columns 68-80), this implementation does not support this feature yet."
                    )
            except UnsupportedFormatError:
                raise  # Reraise the error
            except ValueError as e:
                logger.error(f"Failed to parse X value: {e}")
                pass

        params = {}

        # Parse each field according to format (excluding x_value)
        for field, slice_obj in RESONANCE_FORMAT.items():
            if field == "x_value":  # Skip X value in parsing
                continue

            value = line[slice_obj].strip()

            if value:  # Only process non-empty fields
                if field.startswith("vary_"):
                    try:
                        params[field] = VaryFlag(int(value))
                    except (ValueError, TypeError):
                        params[field] = VaryFlag.NO
                elif field == "igroup":
                    params[field] = safe_parse(value, as_int=True) or 1
                else:
                    parsed_value = safe_parse(value)
                    if parsed_value is not None:
                        params[field] = parsed_value

        return cls(**params)

    def to_str(self) -> str:
        """Convert the resonance entry to fixed-width format string"""
        line = " " * 80

        def format_float(value: Optional[float]) -> str:
            if value is None:
                return " " * 11
            return f"{value:11.4E}"

        def format_vary(value: VaryFlag) -> str:
            return f"{value.value:2d}"

        updates = {
            "resonance_energy": format_float(self.resonance_energy),
            "capture_width": format_float(self.capture_width),
            "channel1_width": format_float(self.channel1_width),
            "channel2_width": format_float(self.channel2_width),
            "channel3_width": format_float(self.channel3_width),
            "vary_energy": format_vary(self.vary_energy),
            "vary_capture_width": format_vary(self.vary_capture_width),
            "vary_channel1": format_vary(self.vary_channel1),
            "vary_channel2": format_vary(self.vary_channel2),
            "vary_channel3": format_vary(self.vary_channel3),
            "igroup": f"{self.igroup:2d}",
        }

        for field, formatted_value in updates.items():
            slice_obj = RESONANCE_FORMAT[field]
            line = f"{line[: slice_obj.start]}{formatted_value}{line[slice_obj.stop :]}"

        return line.rstrip()


class ResonanceCard(BaseModel):
    """Container for a complete set of resonance entries (Card Set 1).

    Card Set 1 is unique as it has no header, contains multiple resonance entries,
    and is terminated by a blank line.

    Attributes:
        entries: List of resonance parameter entries
    """

    entries: List[ResonanceEntry] = Field(default_factory=list)

    @classmethod
    def from_lines(cls, lines: List[str]) -> "ResonanceCard":
        """Parse resonance entries from lines.

        Args:
            lines: List of resonance entry lines

        Returns:
            ResonanceCard: Container with parsed entries

        Raises:
            ValueError: If any line cannot be parsed as a resonance entry
        """
        entries = []
        for line in lines:
            if line.strip():  # Skip blank lines
                try:
                    entry = ResonanceEntry.from_str(line)
                    entries.append(entry)
                except Exception as e:
                    raise ValueError(f"Failed to parse resonance entry: {str(e)}\nLine: {line}")

        if not entries:
            raise ValueError("No valid resonance entries found")

        return cls(entries=entries)

    def to_lines(self) -> List[str]:
        """Convert entries to fixed-width format lines.

        Returns:
            List[str]: Formatted lines including blank terminator
        """
        lines = []
        for entry in self.entries:
            lines.append(entry.to_str())
        lines.append("")  # Blank line terminator
        return lines


if __name__ == "__main__":
    # Enable logging for debugging
    from pleiades.utils.logger import configure_logger

    configure_logger(console_level="DEBUG")
    # Test with regular cases
    good_examples = [
        "-3.6616E+06 1.5877E+05 3.6985E+09                       0 0 1     1",
        "-8.7373E+05 1.0253E+03 1.0151E+02                       0 0 1     1",
    ]

    logger.debug("**Testing valid formats**")
    for i, line in enumerate(good_examples):
        entry = ResonanceEntry.from_str(line)
        logger.debug(f"Example {i + 1}:")
        logger.debug(f"Original: {line}")
        logger.debug(f"Parsed: {entry}")
        logger.debug(f"Reformatted: {entry.to_str()}")

    # Test with special case (should raise error)
    logger.debug("**Testing unsupported format**")
    try:
        # Make sure the negative value is properly aligned in columns 68-80
        bad_line = "-3.6616E+06 1.5877E+05 3.6985E+09                       0 0 1     1    -1.234"
        logger.debug(f"Testing line: '{bad_line}'")
        logger.debug(f"Length before padding: {len(bad_line)}")
        ResonanceEntry.from_str(bad_line)
    except UnsupportedFormatError as e:
        logger.debug("Caught expected error for unsupported format:")
        logger.debug(str(e))

    # Let's also try with a malformed line to make sure our padding doesn't hide issues
    logger.debug("**Testing malformed format**")
    try:
        malformed_line = "-3.6616E+06 1.5877E+05 3.6985E+09 -1.234"  # Clearly wrong format
        ResonanceEntry.from_str(malformed_line)
        logger.debug("No error raised for malformed format!")
    except ValueError as e:
        logger.debug("Caught expected error for malformed line:", str(e))
