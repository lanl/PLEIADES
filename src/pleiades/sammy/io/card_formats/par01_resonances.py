#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.nuclear.models import ResonanceEntry  # Needed to store resonance data
from pleiades.sammy.fitting.config import FitConfig  # FitConfig object to contain list of resonance enerties
from pleiades.utils.helper import VaryFlag
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class Card01(BaseModel):
    """
    Class representing the Card 1 format in the SAMMY parameter file.
    This class is used to extract resonance information from the SAMMY parameter file.
    """

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        NOTE:   This is the one class that may not have a header line. If there is no header line,
                this card should be the first card in the file.
        Args:
            line: Input line to check

        Returns:
            bool: True if the first 5 characters of the line are 'ISOTO'
        """

        return line.strip().upper().startswith("RESONANCES")

    @classmethod
    def from_lines(cls, lines: List[str], fit_config: FitConfig = None) -> None:
        """Parse a complete isotope parameter card set from lines.

        Args:
            lines: List of input lines including header and blank terminator
            FitConfig: FitConfig object to read isotopes into.

        Raises:
            ValueError: If no valid header found or invalid format
        """
        resonance_entries = []

        for line in lines:
            if not line.strip():
                break
            if line.strip().startswith("#") or not any(c.isdigit() for c in line):
                continue

            try:
                resonance_energy = float(line[0:11].strip())
                capture_width = float(line[11:22].strip()) if line[11:22].strip() else None
                channel1_width = float(line[22:33].strip()) if line[22:33].strip() else None
                channel2_width = float(line[33:44].strip()) if line[33:44].strip() else None
                channel3_width = float(line[44:55].strip()) if line[44:55].strip() else None
                vary_energy = VaryFlag(int(line[55:57].strip())) if line[55:57].strip() else VaryFlag.NO
                vary_capture_width = VaryFlag(int(line[57:59].strip())) if line[57:59].strip() else VaryFlag.NO
                vary_channel1 = VaryFlag(int(line[59:61].strip())) if line[59:61].strip() else VaryFlag.NO
                vary_channel2 = VaryFlag(int(line[61:63].strip())) if line[61:63].strip() else VaryFlag.NO
                vary_channel3 = VaryFlag(int(line[63:65].strip())) if line[63:65].strip() else VaryFlag.NO
                igroup = int(line[65:67].strip()) if line[65:67].strip() else 0
            except Exception as e:
                logger.warning(f"Failed to parse resonance line: {line.strip()} ({e})")
                print(line)
                continue

            resonance = ResonanceEntry(
                resonance_energy=resonance_energy,
                capture_width=capture_width,
                channel1_width=channel1_width,
                channel2_width=channel2_width,
                channel3_width=channel3_width,
                vary_energy=vary_energy,
                vary_capture_width=vary_capture_width,
                vary_channel1=vary_channel1,
                vary_channel2=vary_channel2,
                vary_channel3=vary_channel3,
                igroup=igroup,
            )

            resonance_entries.append(resonance)

        print(f"Found {len(resonance_entries)} resonance entries.")
