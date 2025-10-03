#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
from pleiades.nuclear.models import IsotopeParameters, SpinGroups
from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.helper import check_pseudo_scientific
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
    """Validates a list representing spin group numbers according to specific rules.

    The input list is expected to have the following structure:
        - The first element is a flag (vary flag) that must be either 0 or 1.
        - The remaining elements represent spin group numbers.

    Validation criteria:
        1. The list must not be empty.
        2. The first element (flag) must be 0 or 1.
        3. All spin group numbers (elements after the first) must be:
            - Positive integers (> 0)
            - Unique (no duplicates)
            - Strictly increasing (each subsequent number is greater than the previous)

    Parameters
    ----------
    lst : list
        A list where the first element is a flag (0 or 1), followed by spin group numbers.

    Returns
    -------
    bool
        True if the list meets all validation criteria, False otherwise.

    Examples
    --------
    >>> logical_line_two([1, 2, 3, 5])
    True
    >>> logical_line_two([0, 1, 1, 2])
    False
    >>> logical_line_two([2, 1, 2, 3])
    False
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
    """
    Parses a line to extract spin group numbers using either the standard or extended format.

    This function attempts to parse a given line, extracting spin group numbers based on two possible
    formats: standard and extended. The function first strips trailing whitespace from the line, then
    divides the relevant portion of the line into fields according to the widths defined in the
    LINE_TWO_BACK_MATTER_STANDARD and LINE_TWO_BACK_MATTER_EXTENDED dictionaries. It attempts to
    convert each field to an integer, stopping at the first occurrence of "-1" or an invalid value.

    The function then checks which format (standard or extended) yields a logically valid result
    using the logical_line_two function. If a valid format is found, it returns a tuple containing
    the first spin group number and a list of the remaining spin group numbers. If neither format
    is valid, it logs an error and raises a ValueError.

    Args:
        line (str): The input line from which to parse spin group numbers.

    Returns:
        tuple: A tuple (first_group, remaining_groups), where first_group is the first parsed spin group
               number (int), and remaining_groups is a list of the remaining parsed spin group numbers (List[int]).

    Raises:
        ValueError: If neither the standard nor extended format yields a valid set of spin group numbers.

    Logs:
        Error messages if the input line cannot be parsed into a valid format.
    """
    line = line.rstrip()  # Strip the line of any trailing whitespace

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
    """
    Parse a line according to the Card-10 line-3 extended format and return a list of spin groups.

    This function processes a fixed-width formatted line, extracting integer values representing spin groups.
    It iterates over the line in field-width increments, starting from a specified offset, and attempts to
    convert each field to an integer. If a field contains the continuation marker "-1", parsing stops.
    If a field cannot be converted to an integer, -1 is appended as a placeholder.

    Args:
        line (str): The input line to parse, expected to follow the Card-10 line-3 extended format.

    Returns:
        List[int]: A list of integers representing the parsed spin groups. Invalid or empty fields are
        represented by -1. Parsing stops at the first occurrence of the "-1" marker.
    """
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

            mass = check_pseudo_scientific(line_two[LINE_TWO_FRONT_MATTER["mass"]])
            abundance = check_pseudo_scientific(line_two[LINE_TWO_FRONT_MATTER["abundance"]])
            uncertainty = check_pseudo_scientific(line_two[LINE_TWO_FRONT_MATTER["uncertainty"]])
            flag, spin_group_numbers = get_line_two_format_and_parse(line_two)

            # Check the rest of the lines to append to the spin groups
            # These are all the same format (LINE_THREE_MATTER_EXTENDED)
            for line in line_threes:
                spin_group_numbers.extend(parse_line_three(line))

            # Create SpinGroups objects for each spin group number
            spin_groups = [SpinGroups(spin_group_number=sgn) for sgn in spin_group_numbers if sgn > 0]

            # Update or create the isotope in the FitConfig object
            # if isotopes is None, create a new list
            if fit_config.nuclear_params.isotopes is None:
                logger.info(f"Isotope list is empty, creating new isotope with mass {mass}")
                fit_config.nuclear_params.isotopes = [
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
                ]

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
                    logger.info(
                        f"Isotope with mass {mass} not found. "
                        f"Creating new isotope. Total isotopes: {len(fit_config.nuclear_params.isotopes)}. "
                        f"Existing masses: {[iso.isotope_information.mass_data.atomic_mass for iso in fit_config.nuclear_params.isotopes]}"
                    )
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

    @staticmethod
    def to_lines(fit_config: FitConfig) -> List[str]:
        """Convert a fit_config object to a Card 10 list of lines.

           Figures out the number of spin groups and formats the lines accordingly.
        Args:
            fit_config (FitConfig): FitConfig object containing isotope parameters.

        Returns:
            List[str]: List of lines representing the Card10 object.
        """

        lines = []

        # check if fit_config is an instance of FitConfig
        if not isinstance(fit_config, FitConfig):
            message = "fit_config must be an instance of FitConfig"
            logger.error(message)
            raise ValueError(message)

        # Check if there are any isotopes in the fit_config
        if not fit_config.nuclear_params.isotopes:
            logger.warning("No isotopes found in fit_config, returning empty lines.")
            return lines

        # Get the total number of spin groups across all isotopes
        total_spin_groups = sum(len(isotope.spin_groups) for isotope in fit_config.nuclear_params.isotopes)

        # Add the header line
        lines.append("ISOTOpic abundances and masses")
        # Add the isotope lines
        for isotope in fit_config.nuclear_params.isotopes:
            # Create the line_two front matter string
            line_two = (
                f"{isotope.isotope_information.mass_data.atomic_mass:10.5f}"
                f"{isotope.abundance:10.5f}"
                f"{isotope.uncertainty:10.5f}"
            )

            # Add the vary flag
            vary_flag = 1 if isotope.vary_abundance else 0
            line_two += f"{vary_flag:2d}"

            # Determine number of spin groups for this isotope
            spin_groups = [sg.spin_group_number for sg in isotope.spin_groups]
            total_spin_groups_in_isotope = len(spin_groups)

            if total_spin_groups < 99 and total_spin_groups_in_isotope < 25:
                # Use standard format
                line_two += "".join(f"{sg:2d}" for sg in spin_groups)
                lines.append(line_two)

            elif total_spin_groups < 99 and total_spin_groups_in_isotope > 25:
                # Use standard format for line two and extended format for line three
                line_two += "".join(
                    f"{sg:2d}" for sg in spin_groups[: LINE_TWO_BACK_MATTER_STANDARD["fields_per_line"]]
                )
                lines.append(line_two)
                # Add continuation marker
                lines.append("-1")
                # Add remaining spin groups in line three format
                for i in range(
                    LINE_TWO_BACK_MATTER_STANDARD["fields_per_line"],
                    total_spin_groups_in_isotope,
                    LINE_THREE_MATTER_EXTENDED["fields_per_line"],
                ):
                    line_three = "".join(
                        f"{sg:5d}" for sg in spin_groups[i : i + LINE_THREE_MATTER_EXTENDED["fields_per_line"]]
                    )
                    lines.append(line_three)

            else:
                # Use extended format for line two
                line_two_format = LINE_TWO_BACK_MATTER_EXTENDED
                line_three_format = LINE_THREE_MATTER_EXTENDED
                line_two += "".join(f"{sg:5d}" for sg in spin_groups[: line_two_format["fields_per_line"]])
                lines.append(line_two)

                # add continuation marker
                lines.append("-1")

                # continue to add remaining spin groups in line three format
                for i in range(
                    line_two_format["fields_per_line"], len(spin_groups), line_three_format["fields_per_line"]
                ):
                    line_three = "".join(f"{sg:5d}" for sg in spin_groups[i : i + line_three_format["fields_per_line"]])
                    lines.append(line_three)

        # Add a blank line to terminate the card
        lines.append("")

        return lines
