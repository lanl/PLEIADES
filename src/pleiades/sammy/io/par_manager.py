# This file contains the ParManager class, which is responsible for managing the file input/output operations
# around SAMMY parameter files. It handles reading, writing, and updating parameter files, using the FitConfig class.
from enum import Enum
from pathlib import Path

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.inp04_particlepairs import Card04 as InpCard04
from pleiades.sammy.io.card_formats.inp10_spingroups import Card10p2 as InpCard10p2
from pleiades.sammy.io.card_formats.par01_resonances import Card01 as ParCard01
from pleiades.sammy.io.card_formats.par04_broadening import Card04 as ParCard04
from pleiades.sammy.io.card_formats.par06_normalization import Card06 as ParCard06
from pleiades.sammy.io.card_formats.par07_radii import Card07 as ParCard07
from pleiades.sammy.io.card_formats.par07a_radii import Card07a as ParCard07a
from pleiades.sammy.io.card_formats.par10_isotopes import Card10 as ParCard10
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class Cards(Enum):
    PAR_CARD_1 = "Parameter Card 1"  # Resonance data
    PAR_CARD_2 = "Parameter Card 2"  # Fudge Factor
    PAR_CARD_3 = "Parameter Card 3"  # External R-function parameters
    PAR_CARD_3A = "Parameter Card 3a"  # alternative for External R-function parameters
    PAR_CARD_4 = "Parameter Card 4"  # Broadening parameters
    PAR_CARD_5 = "Parameter Card 5"  # Unused but correlated variables
    PAR_CARD_6 = "Parameter Card 6"  # Normalization and background
    PAR_CARD_7 = "Parameter Card 7"  # Radius parameters (default format)
    PAR_CARD_7A = "Parameter Card 7a"  # Radius parameters (“key-word” format)
    PAR_CARD_8 = "Parameter Card 8"  # Data reduction parameters
    PAR_CARD_9 = "Parameter Card 9"  # ORRES
    PAR_CARD_10 = "Parameter Card 10"  # Isotopic abundances and masses
    PAR_CARD_11 = "Parameter Card 11"  # Miscellaneous parameters
    PAR_CARD_12 = "Parameter Card 12"  # Paramagnetic cross section parameters
    PAR_CARD_13 = "Parameter Card 13"  # Background functions
    PAR_CARD_14 = "Parameter Card 14"  # RPI Resolution function
    PAR_CARD_14A = "Parameter Card 14a"  # RPI Transmission resolution function
    PAR_CARD_15 = "Parameter Card 15"  # DETECtor efficiencies
    PAR_CARD_16 = "Parameter Card 16"  # USER-Defined resolution function
    PAR_LAST_B = "Parameter Card Last B"  # EXPLIcit uncertainties and correlations follow
    PAR_LAST_C = "Parameter Card Last C"  # RELATive uncertainties follow
    PAR_LAST_D = "Parameter Card Last D"  # PRIOR uncertainties follow in key-word format

    # If command “QUANTUM NUMBERS ARE inparameter file” is used, then
    # the following input cards will be in the parameter file.
    INP_CARD_4 = "Input Card 4"  # Particle pair definitions
    INP_CARD_10_2 = "Input Card 10.2"  # Spin groups


PAR_HEADER_MAP = {
    "RESONANCES are listed next": Cards.PAR_CARD_1,
    "EXTERnal R-function parameters follow": Cards.PAR_CARD_3,
    "R-EXTernal parameters follow": Cards.PAR_CARD_3A,
    "BROADening parameters may be varied": Cards.PAR_CARD_4,
    "UNUSEd but correlated variables": Cards.PAR_CARD_5,
    "NORMAlization and background": Cards.PAR_CARD_6,
    "RADIUs parameters follow": Cards.PAR_CARD_7,
    "RADII are in KEY-WORD format": Cards.PAR_CARD_7A,
    "CHANNel radius parameters follow": Cards.PAR_CARD_7A,
    "DATA reduction parameters are next": Cards.PAR_CARD_8,
    "ORRES": Cards.PAR_CARD_9,
    "ISOTOpic abundances and masses": Cards.PAR_CARD_10,
    "NUCLIde abundances and masses": Cards.PAR_CARD_10,
    "MISCEllaneous parameters follow": Cards.PAR_CARD_11,
    "PARAMagnetic cross section parameters follow": Cards.PAR_CARD_12,
    "BACKGround functions": Cards.PAR_CARD_13,
    "RPI Resolution function": Cards.PAR_CARD_14,
    "GEEL resolution function": Cards.PAR_CARD_14,
    "GELINa resolution": Cards.PAR_CARD_14,
    "NTOF resolution function": Cards.PAR_CARD_14,
    "RPI Transmission resolution function": Cards.PAR_CARD_14A,
    "RPI Capture resolution function": Cards.PAR_CARD_14A,
    "GEEL DEFAUlts": Cards.PAR_CARD_14A,
    "GELINa DEFAUlts": Cards.PAR_CARD_14A,
    "NTOF DEFAUlts": Cards.PAR_CARD_14A,
    "DETECtor efficiencies": Cards.PAR_CARD_15,
    "USER-Defined resolution function": Cards.PAR_CARD_16,
    "EXPLIcit uncertainties and correlations follow": Cards.PAR_LAST_B,
    "RELATive uncertainties follow": Cards.PAR_LAST_C,
    "PRIOR uncertainties follow in key-word format": Cards.PAR_LAST_D,
    "PARTIcle pair definitions": Cards.INP_CARD_4,
    "SPIN GROUPs": Cards.INP_CARD_10_2,
}


class ParManager:
    def __init__(self, fit_config: FitConfig = None, par_file: Path = None):
        """
        Initialize the ParManager class. This may or may not be passed a FitConfig object.
        If a FitConfig object is None, then a new one is created with default values.
        Args:
            fit_config (FitConfig): The FitConfig object containing the configuration for the SAMMY fitting process. default=None
            par_file (Path): The path to the SAMMY parameter file. default=None
        """

        self.fit_config = fit_config if fit_config else FitConfig()
        self.par_file = par_file

        # if a par_file is provided, read it
        if par_file:
            self.read_par_file(par_file)

    def extract_particle_pairs(self, lines) -> bool:
        """
        Extract particle pair definitions from the lines of the SAMMY parameter file (Card 4).
        Process the particle pair data and update the FitConfig object.
        Args:
            lines (list): The lines of the SAMMY parameter file.
        Returns:
            bool: True if particle pair data was successfully found and processed, False otherwise.
        """

        block = []
        in_block = False

        for line in lines:
            if not in_block and line.upper().startswith("PARTI"):
                in_block = True
                block.append(line.rstrip())
                continue
            if in_block:
                # Stop at blank line or next section header
                if not line.strip():
                    break
                block.append(line.rstrip())

        if block:
            InpCard04.from_lines(block, self.fit_config)
            return True
        return False

    def extract_broadening_parameters(self, lines) -> bool:
        """
        Extract broadening parameters from the lines of the SAMMY parameter file (Card 4).
        Process the broadening data and update the FitConfig object.
        Args:
            lines (list): The lines of the SAMMY parameter file.
        Returns:
            bool: True if broadening data was successfully found and processed, False otherwise.
        """

        block = []
        in_block = False

        for line in lines:
            if not in_block and line.upper().startswith("BROAD"):
                in_block = True
                block.append(line.rstrip())
                continue
            if in_block:
                # Stop at blank line or next section header
                if not line.strip():
                    break
                block.append(line.rstrip())

        if block:
            ParCard04.from_lines(block, self.fit_config)
            return True
        return False

    def extract_normalization_parameters(self, lines) -> bool:
        """
        Extract normalization parameters from the lines of the SAMMY parameter file (Card 6).
        Process the normalization data and update the FitConfig object.
        Args:
            lines (list): The lines of the SAMMY parameter file.
        Returns:
            bool: True if normalization data was successfully found and processed, False otherwise.
        """

        block = []
        in_block = False

        for line in lines:
            if not in_block and line.upper().startswith("NORMA"):
                in_block = True
                block.append(line.rstrip())
                continue
            if in_block:
                # Stop at blank line or next section header
                if not line.strip():
                    break
                block.append(line.rstrip())

        if block:
            ParCard06.from_lines(block, self.fit_config)
            return True
        return False

    def extract_radii_parameters(self, lines) -> bool:
        """
        Extract radius parameters from the lines of the SAMMY parameter file (Card 7).
        Process the radius data and update the FitConfig object.
        NOTE: There are two formats for the radius parameters. The first is the default format
              and the second is the key-word format. In total, there are 3 different headers
              - “RADIUs parameters follow”
              - “RADIIs are in KEY-WORD format”
              - “CHANNel radius parameters follow”

        Args:
            lines (list): The lines of the SAMMY parameter file.
        Returns:
            bool: True if radius data was successfully found and processed, False otherwise.
        """

        block = []
        in_block = False
        header_line = None

        for line in lines:
            first5 = line[:5].upper().strip()
            # Start block if first 5 chars match or KEY-WORD in line
            if not in_block and (first5 in ("RADIU", "RADII", "CHANN") or "KEY-WORD" in line):
                in_block = True
                header_line = line.rstrip()
                block.append(line.rstrip())
                continue
            if in_block:
                if not line.strip():
                    break
                block.append(line.rstrip())

        # Decide which parser to use
        if block:
            header = block[0].upper()
            if header.startswith("RADIU"):
                ParCard07.from_lines(block, self.fit_config)
                return True
            elif header.startswith("RADII") or header.startswith("CHANN") or "KEY-WORD" in header:
                ParCard07a.from_lines(block, self.fit_config)
                return True
        return False

    def extract_isotopes_and_abundances(self, lines) -> bool:
        """
        Search for isotopes in the lines of the SAMMY parameter file. If found, update the FitConfig object with the isotope information.
        Args:
            lines (list): The lines of the SAMMY parameter file.
        Returns:
            bool: True if isotope data was found and processed, False otherwise.
        """

        block = []
        in_block = False

        for line in lines:
            if not in_block and (line.upper().startswith("ISOTO") or line.upper().startswith("NUCLI")):
                in_block = True
                block.append(line.rstrip())
                continue
            if in_block:
                # Stop at blank line or next section header
                if not line.strip():
                    break
                block.append(line.rstrip())

        if block:
            ParCard10.from_lines(block, self.fit_config)
            return True
        return False

    def extract_resonance_entries(self, lines) -> bool:
        """
        Extract resonance information from the lines of the SAMMY parameter file (Card 1).
        Process the resonance data and update the FitConfig object.

        NOTE:   This card will either be the first card in the file (without a header)
                or be listed later in the file with a header.

        Args:
            lines (list): The lines of the SAMMY parameter file.
        Returns:
            bool: True if resonance data was successfully found and processed, False otherwise.
        """

        # Create a block to hold the lines of the resonance data
        # and a flag to indicate if we are in the resonance block
        block = []
        in_block = False
        header_found = False

        # Check if the header is present
        header_found = any(line.strip().upper().startswith("RESONANCES") for line in lines)

        if header_found:
            # If the header is present, we will read until the next blank line or the next section header.
            # We will also skip the header line.
            for line in lines:
                if not in_block and line.strip().upper().startswith("RESONANCES"):
                    in_block = True
                    block.append(line.rstrip())
                    continue
                if in_block:
                    # Stop at blank line or next section header
                    if not line.strip():
                        break
                    block.append(line.rstrip())

        # If the header is not present, we will just read the first lines of
        # the card until we reach a blank line or the next section header.
        else:
            logger.debug("No header line found, assuming first line is data")
            for line in lines:
                if not in_block:
                    in_block = True
                    block.append(line.rstrip())
                    continue
                if in_block:
                    # Stop at blank line or next section header
                    if not line.strip():
                        break
                    block.append(line.rstrip())

        if block:
            ParCard01.from_lines(block, self.fit_config)
            return True

        return False

    def extract_spin_groups(self, lines) -> bool:
        """
        Extract spin group definitions from the lines of the SAMMY parameter file (Input Card 10.2).
        Process the spin group data and update the FitConfig object.
        Args:
            lines (list): The lines of the SAMMY parameter file.
        Returns:
            bool: True if spin group data was successfully found and processed, False otherwise.
        """

        block = []
        in_block = False

        for line in lines:
            if not in_block and line.upper().startswith("SPIN GROUPS"):
                in_block = True
                block.append(line.rstrip())
                continue
            if in_block:
                # Stop at blank line or next section header
                if not line.strip():
                    break
                block.append(line.rstrip())

        if block:
            InpCard10p2.from_lines(block, self.fit_config)
            return True
        return False

    def detect_par_cards(self, lines):
        """
        Scans a list of lines from a SAMMY parameter file to identify and collect parameter card headers.
        This method iterates through each line in the provided list, checking for the presence of known
        parameter card headers as defined in the `PAR_HEADER_MAP`. When a header is detected at the start
        of a line (after stripping whitespace), the corresponding card enumeration is added to a set to
        ensure uniqueness. The set is then sorted and returned as a list.
        NOTE:   By default, there should always be a Card 1 in the file, but there may not be a header line
                for Card 1. Therefore, Card 1 will always be included in the detected cards.

        Args:
            lines (list): The lines of the SAMMY parameter file.

        Returns:
            list: A sorted list of detected parameter cards.
        """

        found_cards = set()
        for line in lines:
            line_key = line.strip()[:5].upper()
            for header, card_enum in PAR_HEADER_MAP.items():
                header_key = header.strip()[:5].upper()
                if line_key == header_key:
                    found_cards.add(card_enum)

        # If no Card 1 is found, add it to the list
        if Cards.PAR_CARD_1 not in found_cards:
            found_cards.add(Cards.PAR_CARD_1)

        return sorted(found_cards, key=lambda x: x.name)

    def read_par_file(self, par_file: Path) -> None:
        """
        Read the SAMMY parameter file and update the FitConfig object.
        Args:
            par_file (Path): The path to the SAMMY parameter file.
        """

        # Check if the file exists
        if not par_file.exists():
            raise FileNotFoundError(f"Parameter file {par_file} does not exist.")

        # Read the parameter file and update the FitConfig object
        with open(par_file, "r") as f:
            logger.info(f"Reading parameter file {par_file}")
            lines = f.readlines()

        detected = self.detect_par_cards(lines)
        logger.info(f"Detected cards in parFile: {detected}")

        # Always process Card 10 first if present as this
        # contains the spin groups for each isotope
        if Cards.PAR_CARD_10 in detected:
            found_isotope_data = self.extract_isotopes_and_abundances(lines)
            if not found_isotope_data:
                logger.error(f"Could not find isotope data in {par_file}.")
            else:
                logger.info(f"Updated isotope and abundance data from {par_file}.")

        for cards in detected:
            # If Input Card 4 is present, it will be processed
            if cards == Cards.INP_CARD_4:
                found_particle_pairs = self.extract_particle_pairs(lines)
                if not found_particle_pairs:
                    logger.error(f"Could not find particle pair data in {par_file}.")
                else:
                    logger.info(f"Updated particle pair data from {par_file}.")

            # Already processed Card 10 so skip it here.
            if cards == Cards.INP_CARD_10_2:
                found_spin_groups = self.extract_spin_groups(lines)
                if not found_spin_groups:
                    logger.error(f"Could not find spin group data in {par_file}.")
                else:
                    logger.info(f"Updated spin group data from {par_file}.")

            # Read Card 1 to get resonance data
            if cards == Cards.PAR_CARD_1:
                found_resonance_data = self.extract_resonance_entries(lines)
                if not found_resonance_data:
                    logger.error(f"Could not find resonance data in {par_file}.")
                else:
                    logger.info(f"Updated resonance data from {par_file}.")

            # Read Card 7 to get radius data
            elif cards == Cards.PAR_CARD_7 or cards == Cards.PAR_CARD_7A:
                found_radius_data = self.extract_radii_parameters(lines)
                if not found_radius_data:
                    logger.error(f"Could not find radius data in {par_file}.")
                else:
                    logger.info(f"Updated radius data from {par_file}.")

            # Read Card 6 to get normalization data
            elif cards == Cards.PAR_CARD_6:
                found_normalization_data = self.extract_normalization_parameters(lines)
                if not found_normalization_data:
                    logger.error(f"Could not find normalization data in {par_file}.")
                else:
                    logger.info(f"Updated normalization data from {par_file}.")

            # Read Card 4 to get broadening data
            elif cards == Cards.PAR_CARD_4:
                found_broadening_data = self.extract_broadening_parameters(lines)
                if not found_broadening_data:
                    logger.error(f"Could not find broadening data in {par_file}.")
                else:
                    logger.info(f"Updated broadening data from {par_file}.")

    # Generation of parameter file sections
    def generate_par_card1_section(self) -> str:
        """
        Generate Card 1 (resonance data) section for the parameter file.
        Returns:
            str: Card 1 section as a string.
        """
        # Example: Use FitConfig or a Card01 class to format resonance data
        # Replace with actual formatting logic

        return "\n".join(ParCard01.to_lines(self.fit_config))

    def generate_par_card4_section(self) -> str:
        """
        Generate Card 4 (broadening parameters) section.
        Returns:
            str: Card 4 section as a string.
        """

        return "\n".join(ParCard04.to_lines(self.fit_config))

    def generate_par_card6_section(self) -> str:
        """
        Generate Card 6 (normalization and background) section.
        Returns:
            str: Card 6 section as a string.
        """

        return "\n".join(ParCard06.to_lines(self.fit_config))

    def generate_par_card7_section(self) -> str:
        """
        Generate Card 7 (radius parameters) section.
        Returns:
            str: Card 7 section as a string.
        """

        return "\n".join(ParCard07.to_lines(self.fit_config))

    def generate_par_card7a_section(self) -> str:
        """
        Generate Card 7a (radius parameters in key-word format) section.
        Returns:
            str: Card 7a section as a string.
        """

        return "\n".join(ParCard07a.to_lines(self.fit_config))

    def generate_par_card10_section(self) -> str:
        """
        Generate Card 10 (isotopic abundances and masses) section.
        Returns:
            str: Card 10 section as a string.
        """

        return "\n".join(ParCard10.to_lines(self.fit_config))

    def generate_inp_card4_section(self) -> str:
        """
        Generate Input Card 4 (particle pair definitions) section.
        Returns:
            str: Input Card 4 section as a string.
        """

        return "\n".join(InpCard04.to_lines(self.fit_config))

    def generate_inp_card10_section(self) -> str:
        """
        Generate Input Card 10.2 (spin groups) section.
        Returns:
            str: Input Card 10.2 section as a string.
        """

        return "\n".join(InpCard10p2.to_lines(self.fit_config))

    def generate_par_content(self) -> str:
        """
        Generate the full content for the SAMMY parameter file.
        Returns:
            str: Complete parameter file content.
        """
        sections = [
            self.generate_inp_card4_section(),
            self.generate_inp_card10_section(),
            self.generate_par_card1_section(),
            self.generate_par_card10_section(),
            self.generate_par_card7a_section(),
            self.generate_par_card6_section(),
            # self.generate_par_card4_section(),
            # Need to add other cards as they are implemented
        ]

        # Filter out empty sections
        return "\n".join([s for s in sections if s])

    def write_par_file(self, file_path: Path) -> Path:
        """
        Write the SAMMY parameter file to disk.
        Args:
            file_path (Path): Path to write the parameter file.
        Returns:
            Path: Path to the created file.
        """
        try:
            content = self.generate_par_content()
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
            logger.info(f"Successfully wrote SAMMY parameter file to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to write SAMMY parameter file: {str(e)}")
            raise IOError(f"Failed to write SAMMY parameter file: {str(e)}")
