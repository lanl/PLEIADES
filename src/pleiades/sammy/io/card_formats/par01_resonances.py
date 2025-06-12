#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.nuclear.isotopes.manager import (
    IsotopeManager,  # Needed to create isotopes if no isotopes are found in fit_config
)
from pleiades.nuclear.models import ResonanceEntry  # Needed to store resonance data
from pleiades.sammy.fitting.config import FitConfig  # FitConfig object to contain list of resonance entries
from pleiades.utils.helper import (  # VaryFlag and check_pseudo_scientific for parameter parsing
    VaryFlag,
    check_pseudo_scientific,
)
from pleiades.utils.logger import loguru_logger  # Logger for debugging

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

        if not lines:
            message = "No lines provided"
            logger.error(message)
            raise ValueError(message)

        # if fit_config is not an instance of FitConfig, raise an error
        if fit_config is not None and not isinstance(fit_config, FitConfig):
            message = "fit_config must be an instance of FitConfig"
            logger.error(message)
            raise ValueError(message)

        elif fit_config is None:
            fit_config = FitConfig()

        # Check to see if the the first line is a header line, if so skip it
        if cls.is_header_line(lines[0]):
            header_line = lines[0]
            logger.info(f"Header line found: {header_line.strip()}")
            # Skip the header line
            lines = lines[1:]
        else:
            # If no header line, log a warning
            logger.warning("No header line found, assuming first line is data")

        if not lines:
            message = "No content lines found after header and blank lines"
            logger.error(message)
            raise ValueError(message)

        multiple_isotopes = False
        # Check if there are multiple isotopes in the fit_config object
        if fit_config.nuclear_params.isotopes:
            for isotope in fit_config.nuclear_params.isotopes:
                if len(isotope.spin_groups) > 1:
                    multiple_isotopes = True
                    break

        # If there are no isotopes in the fit_config, create a "unknown" [UNKN] isotope
        if not fit_config.nuclear_params.isotopes:
            logger.warning("No isotopes found in fit_config, creating a default UNKN isotope")
            fit_config.nuclear_params.isotopes.append(IsotopeManager.create_isotope_from_string("UNKN-01"))

        for line in lines:
            if not line.strip():
                break
            if line.strip().startswith("#") or not any(c.isdigit() for c in line):
                continue

            try:
                resonance_energy = check_pseudo_scientific(line[0:11].strip())
                capture_width = check_pseudo_scientific(line[11:22].strip()) if line[11:22].strip() else None
                channel1_width = check_pseudo_scientific(line[22:33].strip()) if line[22:33].strip() else None
                channel2_width = check_pseudo_scientific(line[33:44].strip()) if line[33:44].strip() else None
                channel3_width = check_pseudo_scientific(line[44:55].strip()) if line[44:55].strip() else None
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

            # If multiple isotopes are present, add the resonance entry to corresponding isotopes by
            # matching spin group in the fit_config with the igroup in the resonance entry
            if multiple_isotopes:
                # Check if igroup is in the spin groups of any isotope
                for isotope in fit_config.nuclear_params.isotopes:
                    if igroup in isotope.spin_groups:
                        # Add the resonance entry to the isotope's resonance list
                        isotope.resonances.append(resonance)
                        break
            else:
                # If only one isotope, add the resonance entry to that isotope's resonance list
                # This assumes that there is only one isotope in the fit_config
                # and that it has a single spin group.
                fit_config.nuclear_params.isotopes[0].resonances.append(resonance)

    @classmethod
    def to_lines(cls, fit_config: FitConfig) -> List[str]:
        """Convert a fit_config object to Card 1 list of lines.

        Returns:
            List[str]: List of lines representing the Card 1 object.
        """
        
        # if fit_config is none or not an instance of FitConfig, raise an error
        if fit_config is None or not isinstance(fit_config, FitConfig):
            message = "fit_config must be an instance of FitConfig"
            logger.error(message)
            raise ValueError(message)
        
        lines = []
        # Header line
        lines.append("RESONANCES")

        # Iterate over isotopes and their resonances
        for isotope in fit_config.nuclear_params.isotopes:
            for resonance in isotope.resonances:
                line = f"{resonance.resonance_energy:11.5E} " \
                       f"{resonance.capture_width:11.5E} " \
                       f"{resonance.channel1_width:11.5E} " \
                       f"{resonance.channel2_width:11.5E} " \
                       f"{resonance.channel3_width:11.5E} " \
                       f"{int(resonance.vary_energy):2d} " \
                       f"{int(resonance.vary_capture_width):2d} " \
                       f"{int(resonance.vary_channel1):2d} " \
                       f"{int(resonance.vary_channel2):2d} " \
                       f"{int(resonance.vary_channel3):2d} " \
                       f"{resonance.igroup:2d}"
                lines.append(line)

        return lines
