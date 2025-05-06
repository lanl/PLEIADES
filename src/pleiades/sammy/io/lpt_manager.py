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


def parse_value_and_varied(s):
    """
    Parse a value that may have a parenthesis indicating it was varied.
    Returns (float_value, varied_flag)
    """
    match = re.match(r"([-\d.Ee+]+)(\s*\([^)]+\))?", s)
    if match:
        value = float(match.group(1))
        varied = match.group(2) is not None
        return value, varied
    raise ValueError(f"Could not parse value: {s}")

def split_lpt_values(line):
    """
    Splits a line into values, where each value may be followed by a parenthesis group.
    Example: '2.9660E+02(  4)  1.1592E-01(  5)' -> ['2.9660E+02(  4)', '1.1592E-01(  5)']
    """
    return re.findall(r'[-+]?\d*\.\d+E[+-]?\d+(?:\s*\([^)]+\))?', line)

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
    def __init__(self, file_path: str = None, run_results: RunResults = None):
        if run_results is not None:
            self.run_results = run_results
        else:
            self.run_results = RunResults()
            
        if file_path:
            self.process_lpt_file(file_path, self.run_results)

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
        physics_data.broadening_parameters. Also sets .*_varied attributes if present.
        Handles both cases: with or without RADIUS field.
        """
        logger.debug("Extracting broadening information...")
        paramters_found = False
        for idx, line in enumerate(lines):
            # Look for header line
            if (
                ("TEMPERATURE" in line and "THICKNESS" in line)
                or ("RADIUS" in line and "TEMPERATURE" in line and "THICKNESS" in line)
            ):
                header = line.strip().split()
                next_line = lines[idx + 1].strip()
                parts = split_lpt_values(next_line)
                print(parts)
                # Case with RADIUS
                if "RADIUS" in header and len(parts) >= 3:
                    paramters_found = True
                    radius, radius_varied = parse_value_and_varied(parts[0])
                    temp, temp_varied = parse_value_and_varied(parts[1])
                    thick, thick_varied = parse_value_and_varied(parts[2])
                    physics_data.broadening_parameters.radius = radius
                    physics_data.broadening_parameters.temp = temp
                    physics_data.broadening_parameters.thick = thick
                    if hasattr(physics_data.broadening_parameters, "radius_varied"):
                        physics_data.broadening_parameters.radius_varied = radius_varied
                    if hasattr(physics_data.broadening_parameters, "temp_varied"):
                        physics_data.broadening_parameters.temp_varied = temp_varied
                    if hasattr(physics_data.broadening_parameters, "thick_varied"):
                        physics_data.broadening_parameters.thick_varied = thick_varied
                # Case without RADIUS
                elif "TEMPERATURE" in header and "THICKNESS" in header and len(parts) >= 2:
                    paramters_found = True
                    temp, temp_varied = parse_value_and_varied(parts[0])
                    thick, thick_varied = parse_value_and_varied(parts[1])
                    physics_data.broadening_parameters.temp = temp
                    physics_data.broadening_parameters.thick = thick
                    if hasattr(physics_data.broadening_parameters, "temp_varied"):
                        physics_data.broadening_parameters.temp_varied = temp_varied
                    if hasattr(physics_data.broadening_parameters, "thick_varied"):
                        physics_data.broadening_parameters.thick_varied = thick_varied
                else:
                    continue

                # Find DELTA-L line
                for j in range(idx + 2, min(idx + 6, len(lines))):
                    if "DELTA-L" in lines[j]:
                        delta_line = lines[j + 1].strip()
                        delta_parts = split_lpt_values(delta_line)
                        print(delta_parts)
                        if len(delta_parts) >= 3:
                            deltal, deltal_varied = parse_value_and_varied(delta_parts[0])
                            deltag, deltag_varied = parse_value_and_varied(delta_parts[1])
                            deltae, deltae_varied = parse_value_and_varied(delta_parts[2])
                            physics_data.broadening_parameters.deltal = deltal
                            physics_data.broadening_parameters.deltag = deltag
                            physics_data.broadening_parameters.deltae = deltae
                            if hasattr(physics_data.broadening_parameters, "deltal_varied"):
                                physics_data.broadening_parameters.deltal_varied = deltal_varied
                            if hasattr(physics_data.broadening_parameters, "deltag_varied"):
                                physics_data.broadening_parameters.deltag_varied = deltag_varied
                            if hasattr(physics_data.broadening_parameters, "deltae_varied"):
                                physics_data.broadening_parameters.deltae_varied = deltae_varied
                        break
                break  # Only read the first block

        return bool(paramters_found)

    def extract_normalization_info(self, lines, physics_data):
        """
        Extracts normalization parameters from an LPT file and stores them in
        physics_data.normalization_parameters (NormalizationParameters).
        """
        logger.debug("Extracting normalization information...")

        parameters_found = False

        for idx, line in enumerate(lines):
            # Look for the normalization header
            if "NORMALIZATION" in line and "BCKG" in line:
                next_line = lines[idx + 1].strip()
                parts = next_line.split()
                # There should be 4 values on this line
                if len(parts) >= 4:
                    parameters_found = True
                    anorm, flag_anorm = parse_value_and_varied(parts[0])
                    backa, flag_backa = parse_value_and_varied(parts[1])
                    backb, flag_backb = parse_value_and_varied(parts[2])
                    backc, flag_backc = parse_value_and_varied(parts[3])
                    # Assign to the model
                    norm_params = physics_data.normalization_parameters
                    norm_params.anorm = anorm
                    norm_params.flag_anorm = VaryFlag.YES if flag_anorm else VaryFlag.NO
                    norm_params.backa = backa
                    norm_params.flag_backa = VaryFlag.YES if flag_backa else VaryFlag.NO
                    norm_params.backb = backb
                    norm_params.flag_backb = VaryFlag.YES if flag_backb else VaryFlag.NO
                    norm_params.backc = backc
                    norm_params.flag_backc = VaryFlag.YES if flag_backc else VaryFlag.NO

                # Look for the next background line (for backd, backf)
                for j in range(idx + 2, min(idx + 6, len(lines))):
                    if "BCKG*EXP" in lines[j]:
                        bkg_line = lines[j + 1].strip()
                        bkg_parts = bkg_line.split()
                        if len(bkg_parts) >= 2:
                            backd, flag_backd = parse_value_and_varied(bkg_parts[0])
                            backf, flag_backf = parse_value_and_varied(bkg_parts[1])
                            norm_params.backd = backd
                            norm_params.flag_backd = VaryFlag.YES if flag_backd else VaryFlag.NO
                            norm_params.backf = backf
                            norm_params.flag_backf = VaryFlag.YES if flag_backf else VaryFlag.NO
                        break
                break  # Only read the first normalization block

        return parameters_found
    
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

        normalization_results_found = self.extract_normalization_info(lines, fit_results.physics_data)
        if not normalization_results_found:
            logger.info("Normalization results not found.")

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

    def process_lpt_file(self, file_path: str, run_results: RunResults = None) -> bool:
        """
        Process a SAMMY LPT file into blocks of iteration results and store them in a
        RunResults object. This function reads the .LPT file, extracts the results of each
        fit iteration, stores them in a tempurary FitResults objects, and then appends them to a
        RunResults object which is returned.

        The RunResults object can be used to access the results of all iterations.

        Args:
            file_path (str): Path to the .LPT file.
        """

        if run_results is None:
            raise ValueError("A RunResults object must be provided to process_lpt_file.")

        try:
            with open(file_path, "r") as file:
                lpt_content = file.read()
                # Log that the file was read successfully
                logger.info(f"Successfully read the file: {file_path}")

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return False
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return False

        # Split the content into blocks based on the delimiter
        blocks = self.split_lpt_blocks(lpt_content)
        logger.debug(f"Split LPT content into {len(blocks)} blocks.")

        for block_type, block_text in blocks:
            # Extract results from the block
            fit_results = self.extract_results_from_string(block_text)

            # Append the fit results to the RunResults object
            run_results.add_fit_result(fit_results)

