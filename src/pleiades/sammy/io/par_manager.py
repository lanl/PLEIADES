# This file contains the ParManager class, which is responsible for managing the file input/output operations
# around SAMMY parameter files. It handles reading, writing, and updating parameter files, using the FitConfig class.
from pathlib import Path

from pleiades.nuclear.models import ResonanceEntry
from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.helper import VaryFlag
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class ParManager:
    def __init__(self, fit_config: FitConfig = None, par_file: Path = None):
        """
        Initialize the ParManager class. This may or may not be passes a FitConfig object.
        If a FitConfig object is none, then a new one is created with default values.
        Args:
            fit_config (FitConfig): The FitConfig object containing the configuration for the SAMMY fitting process. default=None
            par_file (Path): The path to the SAMMY parameter file. default=None
        """

        self.fit_config = fit_config if fit_config else FitConfig()
        self.par_file = par_file

        # if a par_file is provided, read it
        if par_file:
            self.read_par_file(par_file)

    def extract_resonance_entries(self, lines, fit_config: FitConfig) -> bool:
        """
        Extract resonance information from the lines of the SAMMY parameter file (Card 1).
        Process the resonance data and update the FitConfig object.
        Args:
            lines (list): The lines of the SAMMY parameter file.
            fit_config (FitConfig): The FitConfig object containing the configuration for the SAMMY fitting process.
        Returns:
            bool: True if resonance data was successfully found and processed, False otherwise.
        """

        # Create a list of ResonanceEntry objects
        resonance_entries = []
        found_resonance_data = False

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
            found_resonance_data = True

        return found_resonance_data

    def read_par_file(self, par_file: Path):
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

        # First check on if the par_file is a multi-isotope file

        # Extract resonance information from Card 1
        found_resonance_data = self.extract_resonance_entriess(lines, self.fit_config)
