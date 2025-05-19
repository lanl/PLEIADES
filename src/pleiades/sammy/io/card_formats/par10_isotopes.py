#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
from pleiades.nuclear.models import IsotopeParameters
from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

# Class for Card Set 10 (Isotope Parameters)


# Format definitions for Mass, Abundance, Uncertainty (This does not change with formats)
# Each numeric field has specific width requirements
LINE_TWO_FRONT_MATTER = {
    "mass": slice(0, 10),  # AMUISO: Atomic mass (amu), columns 0-9 (10 chars)
    "abundance": slice(10, 20),  # PARISO: Fractional abundance, columns 10-19 (10 chars)
    "uncertainty": slice(20, 30),  # DELISO: Uncertainty on abundance, columns 20-29 (10 chars)
    "stop": 30,  # Stop reading at column 30
}

# Spin group number positions
# Standard format: 2 columns per group starting at col 33
LINE_TWO_BACK_MATTER_STANDARD = {
    "width": 2,  # Character width of each field
    "start": 30,  # Starts after the first 30 characters
    "fields_per_line": 25,  # Max groups per line
    "cont_marker": slice(78, 80),  # "-1" indicates continuation
}

LINE_TWO_BACK_MATTER_EXTENDED = {
    "width": 5,  # Character width of each field
    "start": 30,  # Starts after the first 30 characters
    "fields_per_line": 10,  # Max fields per line
    "cont_marker": slice(79, 80),  # "-1" indicates continuation
}

LINE_THREE_MATTER_EXTENDED = {
    "width": 5,  # Character width of each field
    "start": 0,  # Starts at the beginning of the line
    "fields_per_line": 16,  # Max fields per line
    "cont_marker": slice(79, 80),  # "-1" indicates continuation
}

# Valid header strings
CARD_10_HEADERS = ["ISOTOpic abundances and masses", "NUCLIde abundances and masses"]


def logical_line_two(lst) -> bool:
    """Validate a list of spin group numbers. The first entry (flag) must be 0 or 1.
    Remaining entries must be unique, positive, and strictly increasing.
    """

    # Check if the list is empty or if the first element, the vary flag, is not 0 or 1
    if not lst or lst[0] not in (0, 1):
        return False

    # Check if the spin groups are unique, positive, and strictly increasing
    spin_groups = lst[1:]
    if (
        len(spin_groups) != len(set(spin_groups))
        or any(x <= 0 for x in spin_groups)
        or any(a >= b for a, b in zip(spin_groups, spin_groups[1:]))
    ):
        return False

    return True


def get_line_two_format_and_parse(line):
    """Try to parse spin groups from a line using the given back_format.
    Returns a list of parsed spin group numbers."""
    line = line.rstrip()  # Strip the line of any trailing whitespace

    # Set both formats to False
    extended_format = False
    standard_format = False

    # Create empty lists to hold the spin groups
    temp_standard_groups = []
    temp_extended_groups = []

    # Get the number of characters in the line
    line_length = len(line[LINE_TWO_FRONT_MATTER["stop"] :])
    number_of_standard_fields = line_length // LINE_TWO_BACK_MATTER_STANDARD["width"]
    number_of_extended_fields = line_length // LINE_TWO_BACK_MATTER_EXTENDED["width"]

    for i in range(number_of_standard_fields):
        col_start = LINE_TWO_BACK_MATTER_STANDARD["start"] + i * LINE_TWO_BACK_MATTER_STANDARD["width"]
        col_end = col_start + LINE_TWO_BACK_MATTER_STANDARD["width"]

        val = line[col_start:col_end]
        if val.strip() == "-1":
            break
        else:
            try:
                temp_standard_groups.append(int(val))
            except ValueError:
                temp_standard_groups.append(-1)

    for i in range(number_of_extended_fields):
        col_start = LINE_TWO_BACK_MATTER_EXTENDED["start"] + i * LINE_TWO_BACK_MATTER_EXTENDED["width"]
        col_end = col_start + LINE_TWO_BACK_MATTER_EXTENDED["width"]

        val = line[col_start:col_end]
        if val.strip() == "-1":
            break
        else:
            try:
                temp_extended_groups.append(int(val))
            except ValueError:
                temp_extended_groups.append(-1)

    # If the standard format is valid, use it
    if logical_line_two(temp_standard_groups):
        return temp_standard_groups[0], temp_standard_groups[1:]

    # If the extended format is valid, use it
    elif logical_line_two(temp_extended_groups):
        return temp_extended_groups[0], temp_extended_groups[1:]

    else:
        # If neither format is valid, return None
        logger.error(f"Invalid format for line: {line}")
        logger.error(f"Standard groups: {temp_standard_groups}")
        logger.error(f"Extended groups: {temp_extended_groups}")
        raise ValueError(f"Invalid format for line: {line}")


def parse_line_three(line):
    """Parse a line based on the Card-10 line-3 format (extended) and return a list of spin groups."""
    line = line.rstrip()  # Strip the line of any trailing whitespace

    # Create an empty list to hold the spin groups
    temp_extra_spin_groups = []

    # Get the number of characters in the line
    line_length = len(line[LINE_THREE_MATTER_EXTENDED["start"] :])
    number_of_extended_fields = line_length // LINE_THREE_MATTER_EXTENDED["width"]

    # Loop over each possible spin group field in the line
    for i in range(number_of_extended_fields):
        # Calculate the start and end column indices for this field
        col_start = LINE_THREE_MATTER_EXTENDED["start"] + i * LINE_THREE_MATTER_EXTENDED["width"]
        col_end = col_start + LINE_THREE_MATTER_EXTENDED["width"]

        # Extract the substring representing the field value
        val = line[col_start:col_end]

        # If the field contains the continuation marker "-1", this is the end of the line
        if val.strip() == "-1":
            break
        else:
            try:
                # Try to convert the field value to an integer and append to the list
                temp_extra_spin_groups.append(int(val))
            except ValueError:
                # If conversion fails (e.g., empty or invalid), append -1 as a placeholder
                temp_extra_spin_groups.append(-1)

    # Check if the list of spin groups is valid
    return temp_extra_spin_groups


class Card10(BaseModel):
    """Container for a complete isotope parameter card set (Card Set 10).

    This class handles a complete Card Set 10, including:
    - Header line validation
    - Multiple isotope entries
    - Total abundance validation
    - Format selection (standard vs extended)

    NOTE:   Fixed formats for both standard and extended are defined in the
            IsotopeParameters class. But only using the standard format for now.
    """

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if the first 5 characters of the line are 'ISOTO'
        """

        return line.strip().upper().startswith("ISOTO") or line.rstrip().upper().startswith("NUCLI")

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

        # Validate header
        if not cls.is_header_line(lines[0]):
            message = f"Invalid header line: {lines[0]}"
            logger.error(message)
            raise ValueError(message)

        # if fit_config is not an instance of FitConfig, raise an error
        if fit_config is not None and not isinstance(fit_config, FitConfig):
            message = "fit_config must be an instance of FitConfig"
            logger.error(message)
            raise ValueError(message)

        # if fit_config is not an instance of FitConfig, raise an error
        if fit_config is not None and not isinstance(fit_config, FitConfig):
            message = "fit_config must be an instance of FitConfig"
            logger.error(message)
            raise ValueError(message)

        elif fit_config is None:
            fit_config = FitConfig()

        # Remove header and trailing blank spaces in lines
        content_lines = [line for line in lines[1:] if line.rstrip()]
        if not content_lines:
            message = "No content lines found after header and blank lines"
            logger.error(message)
            raise ValueError(message)

        # Parse the lines into groups based on isotopes
        isotope_lines = []  # list to hold groups of isotope lines
        current_isotope = []  # temporary list to hold the current isotope lines

        # Iterate through the lines and group them by isotope
        for line in content_lines:
            # Check if the line has a continuation marker ("-1") at the end
            # If it does, append the line to the current isotope group
            if line.endswith("-1"):
                current_isotope.append(line)

            # If it doesn't, append the line to the current isotope group and add it to the list of isotope lines
            else:
                current_isotope.append(line)
                isotope_lines.append(current_isotope)

                # Reset the current isotope group for the next iteration
                current_isotope = []

        # Process each group of isotope lines
        for group in isotope_lines:
            # Get the isotope mass, abundance, and uncertainty from the first line (line_two in card10)
            line_two = group[0]
            line_threes = group[1:] if len(group) > 1 else []

            mass = float(line_two[LINE_TWO_FRONT_MATTER["mass"]])
            abundance = float(line_two[LINE_TWO_FRONT_MATTER["abundance"]])
            uncertainty = float(line_two[LINE_TWO_FRONT_MATTER["uncertainty"]])
            flag, spin_groups = get_line_two_format_and_parse(line_two)

            # Check the rest of the lines to append to the spin groups
            # These are all the same format (LINE_THREE_MATTER_EXTENDED)
            for line in line_threes:
                spin_groups.extend(parse_line_three(line))

            # Update or create the isotope in the FitConfig object
            # if isotopes is None, create a new list
            if fit_config.nuclear_params.isotopes is None:
                logger.info(f"Isotpe list is empty, creating new isotope with mass {mass}")
                fit_config.nuclear_params.isotopes = {
                    IsotopeParameters(
                        isotope_information=IsotopeInfo(
                            name=f"Isotope-{mass}",
                            mass_data=IsotopeMassData(atomic_mass=mass),
                        ),
                        abundance=abundance,
                        uncertainty=uncertainty,
                        vary_abundance=flag,
                        spin_groups=spin_groups,
                    )
                }

            else:
                found = False
                for isotope in fit_config.nuclear_params.isotopes:
                    if abs(isotope.isotope_information.mass_data.atomic_mass - mass) < 1e-2:
                        logger.info(
                            f"Updating isotope parameters for {isotope.isotope_information.name} from parameter file"
                        )
                        isotope.abundance = abundance
                        isotope.uncertainty = uncertainty
                        isotope.vary_abundance = flag
                        isotope.spin_groups = spin_groups
                        found = True
                        break

                if not found:
                    logger.info(f"Isotope with mass {mass} not found, creating new isotope")
                    fit_config.nuclear_params.isotopes.append(
                        IsotopeParameters(
                            isotope_information=IsotopeInfo(
                                name=f"??-{mass}",
                                mass_data=IsotopeMassData(atomic_mass=mass),
                            ),
                            abundance=abundance,
                            uncertainty=uncertainty,
                            vary_abundance=flag,
                            spin_groups=spin_groups,
                        )
                    )
