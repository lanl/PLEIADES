# This module imports a results class from the pleiades.sammy.results module
# to create a new class called LptData. The LptData class is filled by reading
# a .LPT file.

import re
from collections import defaultdict

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
from pleiades.nuclear.models import IsotopeParameters, RadiusParameters
from pleiades.sammy.results.models import FitResults, RunResults
from pleiades.utils.helper import VaryFlag
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class LptManager:
    """
    A class to manage and extract results from SAMMY LPT files.


    Attributes:
        run_results (RunResults): A container for multiple fit results.
    """

    # List of delimiters to split the LPT file content
    lpt_delimiters = [
        "***** INITIAL VALUES FOR PARAMETERS",
        "***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS",
        "***** NEW VALUES FOR RESONANCE PARAMETERS",
        "***** NEW VALUES FOR RESONANCE PARAMETERS",
    ]

    # If initialize with a filepath then start processing the file
    def __init__(self, file_path: str = None):
        if file_path:
            self.run_results = self.process_lpt_file(file_path)

    def extract_isotope_info(self, lines, nuclear_data):
        """Extract isotope info and update nuclear_data.isotopes."""

        logger.debug("Extracting isotope information...")
        for idx, line in enumerate(lines):
            if line.strip().startswith("Isotopic abundance and mass for each nuclide"):
                i = idx + 2  # skip header
                while i < len(lines):
                    line_content = lines[i].strip()
                    if not line_content or not re.match(r"^\d+", line_content):
                        break  # End of isotope block
                    # Match with optional parentheses for varied abundance
                    match = re.match(r"^\s*(\d+)\s+([-\d.Ee]+)(\s*\([^)]+\))?\s+([-\d.Ee]+)\s+(.+)$", line_content)

                    if match:
                        abundance_str = match.group(2)
                        abundance = float(abundance_str)
                        abundance_paren = match.group(3)
                        mass = float(match.group(4))
                        spin_groups = [int(s) for s in match.group(5).split()]

                        # Set vary_abundance flag
                        vary_abundance = VaryFlag.YES if abundance_paren else VaryFlag.NO

                        # Minial IsotopeMassData
                        mass_data_info = IsotopeMassData(atomic_mass=mass)

                        # Minimal IsotopeInfo
                        isotope_info = IsotopeInfo(atomic_number=int(round(mass)), mass_data=mass_data_info)

                        isotope = IsotopeParameters(
                            isotope_infomation=isotope_info,
                            abundance=abundance,
                            spin_groups=spin_groups,
                            vary_abundance=vary_abundance,
                        )

                        nuclear_data.isotopes.append(isotope)
                    i += 1

                break

        # if isotope info was found then return true
        return bool(nuclear_data.isotopes)

    def extract_radius_info(self, lines, nuclear_data):
        """
        Extracts effective and true radii along with spin group numbers from the LPT file lines.
        The extracted data is grouped by isotopes and stored in the radius_parameters attribute
        of each isotope in nuclear_data.isotopes.

        The function processes lines containing radius information, identifies spin groups
        associated with specific radii, and organizes them into RadiusParameters objects.

        Args:
            lines (list): List of strings representing the lines of the LPT file.
            nuclear_data (nuclearParameters): Object containing nuclear data, including isotopes.

        Updates:
            nuclear_data.isotopes: Each isotope's radius_parameters attribute is populated with
            a list of RadiusParameters objects, each containing effective_radius, true_radius,
            and associated spin groups. The spin groups for each radius must be in the isotope
            spin group.

        Returns:
            bool:   True if radius info is found in string block
                    False if not
        """

        logger.debug("Extracting radius information...")
        radii = []
        last_radii = (None, None)
        for idx, line in enumerate(lines):
            if "EFFECTIVE RADIUS" in line and "TRUE" in line and "SPIN GROUP" in line:
                in_block = True
                i = idx + 2  # skip header and blank/label line
                while i < len(lines):
                    line_content = lines[i].strip()
                    if not line_content or "#" not in line_content:
                        break
                    # Try to match full line with radii and spin group
                    match = re.match(r"^([-\d.Ee]+)\s+([-\d.Ee]+)\s+(\d+)\s+#\s+(.+)$", line_content)
                    if match:
                        eff_radius = float(match.group(1))
                        true_radius = float(match.group(2))
                        spin_group = int(match.group(3))
                        channels = [int(x) for x in match.group(4).split()]
                        last_radii = (eff_radius, true_radius)
                    else:
                        # Try to match continuation line (just spin group and channels)
                        match2 = re.match(r"^(\d+)\s+#\s+(.+)$", line_content)
                        if match2 and all(last_radii):
                            spin_group = int(match2.group(1))
                            channels = [int(x) for x in match2.group(2).split()]
                            eff_radius, true_radius = last_radii
                        else:
                            break  # End of block
                    radii.append(
                        {
                            "effective_radius": eff_radius,
                            "true_radius": true_radius,
                            "spin_group": spin_group,
                            "channels": channels,
                        }
                    )
                    i += 1

                break

        # For each isotope, group spin groups by (effective_radius, true_radius)
        for isotope in nuclear_data.isotopes:
            spin_groups_set = set(isotope.spin_groups)
            # Group spin groups by radius pair
            grouped = defaultdict(list)
            for entry in radii:
                if entry["spin_group"] in spin_groups_set:
                    key = (entry["effective_radius"], entry["true_radius"])
                    grouped[key].append(entry["spin_group"])
            # Create RadiusParameters objects for each group
            isotope.radius_parameters = []
            for (eff_radius, true_radius), spin_groups in grouped.items():
                temp_radius_parameters = RadiusParameters(
                    effective_radius=eff_radius, true_radius=true_radius, spin_groups=spin_groups
                )
                isotope.radius_parameters.append(temp_radius_parameters)

        # if radius info was found then return true
        return bool(radii)

    def extract_broadening_info(self, lines, physics_data):
        """
        Extracts the broadening parameters from an LPT file and stores them in
        physics_data.broadening_parameters as a list of BroadeningParameters.
        """
        logger.debug("Extracting broadening information...")
        paramters_found = False
        for idx, line in enumerate(lines):
            if line.strip().startswith("TEMPERATURE") and "THICKNESS" in line:
                # Next line contains the values
                temp_line = lines[idx + 1].strip()
                temp_parts = temp_line.split()
                if len(temp_parts) >= 2:
                    paramters_found = True
                    physics_data.broadening_parameters.temp = float(temp_parts[0])
                    physics_data.broadening_parameters.thick = float(temp_parts[1])
                else:
                    continue

                # Find DELTA-L line
                for j in range(idx + 2, min(idx + 6, len(lines))):
                    if "DELTA-L" in lines[j]:
                        delta_line = lines[j + 1].strip()
                        delta_parts = delta_line.split()
                        if len(delta_parts) >= 3:
                            physics_data.broadening_parameters.deltal = float(delta_parts[0])
                            physics_data.broadening_parameters.deltag = float(delta_parts[1])
                            physics_data.broadening_parameters.deltae = float(delta_parts[2])
                        break
                break  # Only read the first block

        # if broadening parameters were found then return true
        return bool(paramters_found)

    def extract_results_from_string(self, lpt_block_string: str) -> FitResults:
        fit_results = FitResults()
        lines = lpt_block_string.splitlines()

        # Call each extraction function in the order you want
        isotpe_results_found = self.extract_isotope_info(lines, fit_results.nuclear_data)
        if not isotpe_results_found:
            logger.info("Isotope results not found.")
        radius_results_found = self.extract_radius_info(lines, fit_results.nuclear_data)
        if not radius_results_found:
            logger.info("Radius results not found.")
        broadening_results_found = self.extract_broadening_info(lines, fit_results.physics_data)
        if not broadening_results_found:
            logger.info("Broadening results not found.")

        return fit_results

    def split_lpt_blocks(self, lpt_content: str):
        """
        Splits the LPT file content into blocks for each fit iteration.
        Returns a list of (block_type, block_text) tuples.
        """
        # Define the delimiters
        initial = "***** INITIAL VALUES FOR PARAMETERS"
        intermediate = "***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS"
        new = "***** NEW VALUES FOR RESONANCE PARAMETERS"

        pattern = f"({re.escape(initial)}|{re.escape(intermediate)}|{re.escape(new)})"
        matches = list(re.finditer(pattern, lpt_content))

        blocks = []
        for i, match in enumerate(matches):
            start = match.start()
            block_type = match.group(0)
            # Determine end of block
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(lpt_content)
            block_text = lpt_content[start:end]
            blocks.append((block_type, block_text))
        return blocks

    def process_lpt_file(self, file_path: str) -> RunResults:
        """
        Process a SAMMY LPT file into blocks of iteration results and store them in a
        RunResults object. This function reads the .LPT file, extracts the results of each
        fit iteration, stores them in a tempurary FitResults objects, and then appends them to a
        RunResults object which is returned.

        The RunResults object can be used to access the results of all iterations.

        Args:
            file_path (str): Path to the .LPT file.
        """

        # Initialize the RunResults object
        run_results = RunResults()

        try:
            with open(file_path, "r") as file:
                lpt_content = file.read()
                # Log that the file was read successfully
                logger.info(f"Successfully read the file: {file_path}")

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")

        # Split the content into blocks based on the delimiter

        blocks = self.split_lpt_blocks(lpt_content)
        logger.debug(f"Split LPT content into {len(blocks)} blocks.")

        for block_type, block_text in blocks:
            # Extract results from the block
            fit_results = self.extract_results_from_string(block_text)

            # Append the fit results to the RunResults object
            run_results.add_fit_result(fit_results)

            # run_results.add_fit_result(fit_results)

        return run_results
