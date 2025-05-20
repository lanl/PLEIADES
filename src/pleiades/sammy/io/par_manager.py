# This file contains the ParManager class, which is responsible for managing the file input/output operations
# around SAMMY parameter files. It handles reading, writing, and updating parameter files, using the FitConfig class.
from enum import Enum
from pathlib import Path

from pleiades.sammy.fitting.config import FitConfig
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
    PAR_CARD_7A = "Parameter Card 7a"  # Radius parameters (alternative format)
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

    def extract_isotopes_and_abundances(self, lines) -> bool:
        """
        Search for isotopes in the lines of the SAMMY parameter file. If found, update the FitConfig object with the isotope information.
        Args:
            lines (list): The lines of the SAMMY parameter file.
        Returns:
            bool: True if isotope data was found and processed, False otherwise.
        """
        from pleiades.sammy.io.card_formats.par10_isotopes import Card10

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
            Card10.from_lines(block, self.fit_config)
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
        from pleiades.sammy.io.card_formats.par01_resonances import Card01

        # Create a block to hold the lines of the resonance data
        # and a flag to indicate if we are in the resonance block
        block = []
        in_block = False
        header_found = False

        # Check if the header is present
        header_found = any(line.strip().upper().startswith("RESONANCES") for line in lines)

        if header_found:
            logger.error("Header line found: RESONANCES are listed next-------------------")
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
            logger.error("No header line found, assuming first line is data")
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
            print(block)
            Card01.from_lines(block, self.fit_config)
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
            # Already processed Card 10 so skip it here.
            if cards == Cards.PAR_CARD_10:
                continue

            # Read Card 1 to get resonance data
            if cards == Cards.PAR_CARD_1:
                found_resonance_data = self.extract_resonance_entries(lines)
                if not found_resonance_data:
                    logger.error(f"Could not find resonance data in {par_file}.")
                else:
                    logger.info(f"Updated resonance data from {par_file}.")

            # Add more card processing as needed
