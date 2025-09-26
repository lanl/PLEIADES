import re
from collections import defaultdict

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
from pleiades.nuclear.models import IsotopeParameters, RadiusParameters
from pleiades.sammy.results.models import FitResults, RunResults
from pleiades.utils.helper import VaryFlag
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


def parse_value_and_varied(s: str) -> tuple[float, bool]:
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


def split_lpt_values(line: str) -> list[str]:
    """
    Splits a line into values, where each value may be followed by a parenthesis group.
    Example: '2.9660E+02(  4)  1.1592E-01(  5)' -> ['2.9660E+02(  4)', '1.1592E-01(  5)']
    """
    return re.findall(r"[-+]?\d*\.\d+E[+-]?\d+(?:\s*\([^)]+\))?", line)


class LptManager:
    """
    LptManager is a class designed to manage and extract results from SAMMY LPT files.
    These files typically contain information about nuclear resonance parameters,
    broadening parameters, normalization parameters, and chi-squared results for
    various fit iterations. The class provides methods to parse and process these
    files, extract relevant data, and organize it into structured objects for further analysis.
    Attributes:
        lpt_delimiters (list): A list of delimiters used to split the LPT file content
            into blocks for processing. These delimiters correspond to specific sections
            in the LPT file, such as initial values, intermediate values, and new values
            for resonance parameters.
    Methods:
        __init__(file_path: str = None, run_results: RunResults = None):
            Initializes the LptManager object. If a file path is provided, the LPT file
            is processed immediately. If a RunResults object is provided, it is used to
            store the extracted results.
        extract_isotope_info(lines, nuclear_data):
            Extracts isotope information, including isotopic abundance, mass, and spin
            groups, from the LPT file lines. Updates the nuclear_data.isotopes attribute
            with the extracted data.
        extract_radius_info(lines, nuclear_data):
            Extracts effective and true radii along with spin group numbers from the LPT
            file lines. Groups the extracted data by isotopes and stores it in the
            radius_parameters attribute of each isotope in nuclear_data.isotopes.
        extract_broadening_info(lines, physics_data):
            Extracts broadening parameters, such as temperature, thickness, and radius,
            from the LPT file lines. Updates the physics_data.broadening_parameters
            attribute with the extracted data.
        extract_normalization_info(lines, physics_data):
            Extracts normalization parameters, including background coefficients, from
            the LPT file lines. Updates the physics_data.normalization_parameters
            attribute with the extracted data.
        extract_chi_squared_info(lines, chi_squared_results):
            Extracts chi-squared, reduced chi-squared, and degrees of freedom (dof)
            from the LPT file lines. Updates the chi_squared_results object with the
            extracted data.
        extract_results_from_string(lpt_block_string: str) -> FitResults:
            Processes a block of LPT file content as a string and extracts various
            results, including isotope, radius, broadening, normalization, and
            chi-squared information. Returns a FitResults object containing the
            extracted data.
        split_lpt_blocks(lpt_content: str):
            Splits the LPT file content into blocks based on predefined delimiters.
            Returns a list of tuples, where each tuple contains the block type and
            the corresponding block text.
        process_lpt_file(file_path: str, run_results: RunResults = None) -> bool:
            Processes a SAMMY LPT file by reading its content, splitting it into blocks,
            extracting results from each block, and storing the results in a RunResults
            object. Returns True if the file was processed successfully, otherwise False.
    Usage:
        The LptManager class is typically used to parse SAMMY LPT files and extract
        structured data for further analysis. It can be initialized with a file path
        to process the file immediately or used with its methods to extract specific
        types of data from LPT file content.
    """

    # List of delimiters to split the LPT file content
    lpt_delimiters = [
        "***** INITIAL VALUES FOR PARAMETERS",
        "***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS",
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
                        spin_group_numbers = [int(s) for s in match.group(5).split()]

                        # Set vary_abundance flag
                        vary_abundance = VaryFlag.YES if abundance_paren else VaryFlag.NO

                        # Create SpinGroups objects from integers
                        from pleiades.nuclear.models import SpinGroups

                        spin_groups = [
                            SpinGroups(spin_group_number=sg_num, excluded=False) for sg_num in spin_group_numbers
                        ]

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
            # Extract spin group numbers from SpinGroups objects
            spin_groups_set = set(sg.spin_group_number for sg in isotope.spin_groups)
            # Group spin groups by radius pair
            grouped = defaultdict(list)
            for entry in radii:
                if entry["spin_group"] in spin_groups_set:
                    key = (entry["effective_radius"], entry["true_radius"])
                    grouped[key].append(entry["spin_group"])
            # Create RadiusParameters objects for each group
            isotope.radius_parameters = []
            for (eff_radius, true_radius), spin_groups in grouped.items():
                # Convert integer spin groups to SpinGroupChannels objects
                from pleiades.nuclear.models import SpinGroupChannels

                spin_group_channels = [SpinGroupChannels(group_number=sg_num, channels=[]) for sg_num in spin_groups]

                temp_radius_parameters = RadiusParameters(
                    effective_radius=eff_radius, true_radius=true_radius, spin_groups=spin_group_channels
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
            if ("TEMPERATURE" in line and "THICKNESS" in line) or (
                "RADIUS" in line and "TEMPERATURE" in line and "THICKNESS" in line
            ):
                header = line.strip().split()
                next_line = lines[idx + 1].strip()
                parts = split_lpt_values(next_line)
                # Case with RADIUS
                if "RADIUS" in header and len(parts) >= 3:
                    paramters_found = True
                    radius, radius_varied = parse_value_and_varied(parts[0])
                    temp, temp_varied = parse_value_and_varied(parts[1])
                    thick, thick_varied = parse_value_and_varied(parts[2])
                    physics_data.broadening_parameters.crfn = radius
                    physics_data.broadening_parameters.temp = temp
                    physics_data.broadening_parameters.thick = thick
                    if hasattr(physics_data.broadening_parameters, "radius_varied"):
                        physics_data.broadening_parameters.flag_crfn = radius_varied
                    if hasattr(physics_data.broadening_parameters, "temp_varied"):
                        physics_data.broadening_parameters.flag_temp = temp_varied
                    if hasattr(physics_data.broadening_parameters, "thick_varied"):
                        physics_data.broadening_parameters.flag_thick = thick_varied
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
                parts = split_lpt_values(next_line)
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
                        bkg_parts = split_lpt_values(bkg_line)
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

    def extract_chi_squared_info(self, lines, chi_squared_results):
        """
        Extracts chi-squared, reduced chi-squared, and dof from LPT file lines
        and fills the ChiSquaredResults object.
        """
        logger.debug("Extracting chi-squared information...")

        chi2_found = False

        chi2 = None
        reduced_chi2 = None
        dof = None

        for idx, line in enumerate(lines):
            # Chi-squared value
            match_chi2 = re.search(r"CUSTOMARY CHI SQUARED\s*=\s*([-\d.Ee+]+)", line)
            if match_chi2:
                chi2 = float(match_chi2.group(1))
            # Reduced chi-squared value
            match_red = re.search(r"CUSTOMARY CHI SQUARED DIVIDED BY NDAT\s*=\s*([-\d.Ee+]+)", line)
            if match_red:
                reduced_chi2 = float(match_red.group(1))
            # Number of data points (dof)
            match_dof = re.search(r"Number of experimental data points\s*=\s*(\d+)", line)
            if match_dof:
                dof = int(match_dof.group(1))

        # If all values were found, set boolean flag to true
        if chi2 is not None and reduced_chi2 is not None and dof is not None:
            chi_squared_results.chi_squared = chi2
            chi_squared_results.reduced_chi_squared = reduced_chi2
            chi_squared_results.dof = dof
            chi2_found = True

        return chi2_found

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

        chi_squared_results_found = self.extract_chi_squared_info(lines, fit_results.chi_squared_results)
        if not chi_squared_results_found:
            logger.info("Chi-squared results not found.")

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
