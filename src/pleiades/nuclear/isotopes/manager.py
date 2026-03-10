"""Manages access to isotope data files packaged with PLEIADES."""

import functools
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from pleiades.nuclear.isotopes.models import FileCategory, IsotopeInfo, IsotopeMassData
from pleiades.nuclear.models import IsotopeParameters
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class IsotopeManager:
    """
    Manages access to isotope data files packaged with PLEIADES.

    This class provides a centralized interface for accessing isotope data files
    that are distributed with the PLEIADES package. It handles path resolution,
    validates file existence, and caches results for improved performance.
    """

    # Mapping of file categories to their valid file extensions
    _CATEGORY_FILE_EXTENSIONS = {FileCategory.ISOTOPES: {".info", ".mas20", ".list"}}

    def __init__(self):
        """Initialize the IsotopeManager."""
        self._cached_files: Dict[FileCategory, Set[Path]] = {}
        self._initialize_cache()

    def _initialize_cache(self) -> None:
        """Initialize the cache of available files for each category."""
        base_path = Path(__file__).parent / "files"  # Reference the 'files' directory
        for category in FileCategory:
            try:
                self._cached_files[category] = {
                    item for item in base_path.iterdir() if item.suffix in self._CATEGORY_FILE_EXTENSIONS[category]
                }
            except Exception as e:
                logger.error(f"Failed to initialize cache for {category}: {str(e)}")
                self._cached_files[category] = set()

    @staticmethod
    def _get_category_path(category: FileCategory) -> str:
        """Get the filesystem path for a category."""
        return FileCategory.to_path(category)

    @functools.lru_cache(maxsize=128)
    def get_file_path(self, category: FileCategory, filename: str) -> Path:
        """
        Get the path to a specific data file.

        Args:
            category: The category of the data file
            filename: The name of the file to retrieve

        Returns:
            Path to the requested file

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the category is invalid or file extension is not allowed
        """
        if not isinstance(category, FileCategory):
            raise ValueError(f"Invalid category: {category}")

        file_path = Path(filename)
        if file_path.suffix not in self._CATEGORY_FILE_EXTENSIONS[category]:
            raise ValueError(
                f"Invalid file extension for {category}. Allowed extensions: {self._CATEGORY_FILE_EXTENSIONS[category]}"
            )

        logger.info(f"Searching for {filename} in cached files for {category}: {self._cached_files[category]}")
        for file in self._cached_files[category]:
            logger.info(f"Checking file: {file.name}")
            if file.name == filename:
                logger.info(f"Found file: {file}")
                return file

        raise FileNotFoundError(f"File {filename} not found in {category}")

    def list_files(self, category: Optional[FileCategory] = None) -> Dict[FileCategory, List[str]]:
        """
        List available data files.

        Args:
            category: Optional specific category to list files for

        Returns:
            Dictionary mapping categories to lists of available filenames

        Raises:
            ValueError: If specified category is invalid
        """
        if category is not None:
            if not isinstance(category, FileCategory):
                raise ValueError(f"Invalid category: {category}")
            return {category: sorted(self._cached_files[category])}

        return {cat: sorted(self._cached_files[cat]) for cat in FileCategory}

    def validate_file(self, category: FileCategory, filename: str) -> bool:
        """
        Validate that a file exists and has the correct extension.

        Args:
            category: The category of the file
            filename: The name of the file to validate

        Returns:
            True if the file is valid, False otherwise
        """
        try:
            path = Path(filename)
            return path.suffix in self._CATEGORY_FILE_EXTENSIONS[category] and any(
                file.name == filename for file in self._cached_files[category]
            )
        except Exception:
            return False

    def get_istotpe_info_from_mass(self, mass: float) -> Optional[IsotopeInfo]:
        """
        Extract isotope information from the mass.mas20 file based on the given mass
        and return the corresponding IsotopeInfo object.

        NOTE: This function is not used in the current implementation but is provided
        for future use or testing purposes. We will need to figure out how to use masses
        provided by SAMMY to look up the exact isotope in the mass.mas20 file.

        Args:
            mass: The mass of the isotope
        Returns:
            IsotopeInfo object containing isotope details if found, None otherwise
        """

        # Iterate through the mass.mas20 file to find the isotope with the given mass
        try:
            with self.get_file_path(FileCategory.ISOTOPES, "mass.mas20").open() as f:
                # Skip header lines
                for _ in range(36):
                    next(f)

                for line in f:
                    if str(mass) in line:
                        # Parse the line according to mass.mas20 format
                        element = line[0:2].strip()
                        mass_number = int(line[3:6].strip())
                        return self.get_isotope_info(f"{element}-{mass_number}")
            return None
        except Exception as e:
            logger.error(f"Error reading mass data for mass {mass}: {str(e)}")
            raise

    def get_isotope_info(self, isotope_str: str) -> Optional[IsotopeInfo]:
        """
        Extract isotope information from the isotopes.info file.

        Args:
            isotope_str: String representation of the isotope (e.g., "U-238")

        Returns:
            IsotopeInfo containing isotope details if found, None otherwise
        """

        logger.info(f"Getting isotope parameters for {isotope_str}")

        # Create a IsotopeInfo instance from the isotope string
        isotope = IsotopeInfo.from_string(isotope_str)

        # get the mass of the isotope from the mass.mas20 file
        isotope.mass_data = self.check_and_get_mass_data(isotope.element, isotope.mass_number)

        # check if the isotope is a stable isotope with known abundance and spin
        self.check_and_set_abundance_and_spins(isotope)

        # get the material number
        isotope.material_number = self.get_mat_number(isotope)

        return isotope

    def check_and_get_mass_data(self, element: str, mass_number: int) -> Optional[IsotopeMassData]:
        """
        Extract mass data for an isotope from the mass.mas20 file.

        Args:
            element (str): Element symbol
            mass_number (int): Mass number

        Returns:
            IsotopeMassData containing atomic mass, mass uncertainty

        Raises:
            ValueError: If data cannot be parsed
        """
        try:
            with self.get_file_path(FileCategory.ISOTOPES, "mass.mas20").open() as f:
                # Skip header lines
                for _ in range(36):
                    next(f)

                for line in f:
                    if (element in line[:25]) and (str(mass_number) in line[:25]):
                        # Parse the line according to mass.mas20 format
                        atomic_mass_coarse = line[106:109].replace("*", "nan").replace("#", ".0")
                        atomic_mass_fine = line[110:124].replace("*", "nan").replace("#", ".0")

                        if "nan" not in [atomic_mass_coarse, atomic_mass_fine]:
                            atomic_mass = float(atomic_mass_coarse + atomic_mass_fine) / 1e6
                        else:
                            atomic_mass = float("nan")

                        return IsotopeMassData(
                            atomic_mass=atomic_mass,
                            mass_uncertainty=float(line[124:136].replace("*", "nan").replace("#", ".0")),
                            binding_energy=float(line[54:66].replace("*", "nan").replace("#", ".0")),
                            beta_decay_energy=float(line[81:93].replace("*", "nan").replace("#", ".0")),
                        )
            raise ValueError(f"Mass data for {element}-{mass_number} not found")
        except Exception as e:
            logger.error(f"Error reading mass data for {element}-{mass_number}: {str(e)}")
            raise

    def check_and_set_abundance_and_spins(self, isotope_info: IsotopeInfo) -> None:
        """
        Set the abundance and spin of an isotope from the isotopes.info file.

        Args:
            isotope_info: IsotopeInfo object to modify
        """
        element = isotope_info.element
        mass_number = isotope_info.mass_number

        # Check if isotope is a stable isotope with a known abundance and spin
        with self.get_file_path(FileCategory.ISOTOPES, "isotopes.info").open() as f:
            for line in f:
                line = line.strip()
                if line and line[0].isdigit():
                    data = line.split()

                    # if the isotope (Element-MassNum) is found in the isotopes.info file then set abundance and spin
                    if data[3] == element and int(data[1]) == mass_number:
                        isotope_info.atomic_number = int(data[0])
                        isotope_info.abundance = float(data[7])
                        isotope_info.spin = float(data[5])
                        return

    def get_mat_number(self, isotope: IsotopeInfo) -> Optional[int]:
        """
        Get ENDF MAT number for an isotope.

        Args:
            isotope: IsotopeInfo instance

        Returns:
            ENDF MAT number if found, None otherwise

        Raises:
            ValueError: If isotope format is invalid
        """

        # Setting isotope string to search file.
        isotope_string = str(isotope.element) + "-" + str(isotope.mass_number)
        try:
            with self.get_file_path(FileCategory.ISOTOPES, "neutrons.list").open() as f:
                # Line matching breakdown:
                # "496)  92-U -238 IAEA       EVAL-DEC14 IAEA Consortium                  9237"
                # When line matches pattern
                # We get groups:
                #   match.group(1) = "92"
                #   match.group(2) = "U"
                #   match.group(3) = "238"
                # Check if constructed string matches input:
                #   match.expand(r"\2-\3") = "U-238"
                # If match found, get MAT number:
                # Take last 5 characters of line "  9237" -> 9237
                pattern = r"\b\s*(\d+)\s*-\s*([A-Za-z]+)\s*-\s*(\d+)([A-Za-z]*)\b"

                for line in f:
                    match = re.search(pattern, line)
                    if match and match.expand(r"\2-\3").lower() == str(isotope_string).lower():
                        return int(line[-5:])
            return None
        except Exception as e:
            logger.error(f"Error getting MAT number for {isotope}: {str(e)}")
            raise

    def get_isotope_parameters_from_isotope_string(self, isotope_str: str) -> Optional[IsotopeParameters]:
        """
        Get isotope parameters from an isotope string.

        Args:
            isotope_str: String representation of the isotope (e.g., "U-238")

        Returns:
            IsotopeParameters containing nuclear data if found, None otherwise
        """

        try:
            return IsotopeParameters(isotope_information=self.get_isotope_info(isotope_str))

        except Exception as e:
            logger.error(f"Error getting isotope parameters for {isotope_str}: {str(e)}")
            raise

    def get_isotopes_by_element(self, element: str) -> List[str]:
        """
        Get all naturally occurring isotopes for a given element.

        Reads isotopes.info to find all isotopes of the specified element
        that have non-zero natural abundance.

        Args:
            element: Element symbol (e.g., "Hf", "U", "Au"). Case-insensitive.

        Returns:
            List of isotope strings sorted by mass number (e.g., ["Hf-174", "Hf-176", ...]).
            Returns empty list if element not found or has no natural isotopes.
        """
        # Normalize element symbol for comparison (first letter upper, rest lower)
        element_normalized = element.capitalize()

        isotopes: List[str] = []

        try:
            with self.get_file_path(FileCategory.ISOTOPES, "isotopes.info").open() as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("%"):
                        continue
                    # Data lines start with a digit (atomic number)
                    if line[0].isdigit():
                        data = line.split()
                        # Format: atomic_num mass_num stable/radio element name spin g_factor abundance quadrupole
                        # Index:     0          1        2         3      4     5      6         7         8
                        if len(data) >= 8:
                            file_element = data[3]
                            mass_number = int(data[1])
                            abundance = float(data[7])

                            # Match element and check for non-zero natural abundance
                            if file_element == element_normalized and abundance > 0:
                                isotopes.append(f"{file_element}-{mass_number}")
        except Exception as e:
            logger.warning(f"Error reading isotopes for element {element}: {e}")
            return []

        # Sort by mass number
        isotopes.sort(key=lambda iso: int(iso.split("-")[1]))

        return isotopes

    def get_natural_composition(self, element: str) -> Dict[str, float]:
        """
        Get natural isotopic composition for a given element.

        Reads isotopes.info to get all naturally occurring isotopes and their
        abundances, returned as fractions (0-1) rather than percentages.

        Note: The isotopes.info file stores abundances as PERCENTAGES (0-100).
        This method converts them to fractions (0-1) and validates that
        the sum is approximately 1.0 (within 1% tolerance).

        Args:
            element: Element symbol (e.g., "Hf", "U", "Au"). Case-insensitive.

        Returns:
            Dict mapping isotope strings to abundance fractions.
            E.g., {"Hf-174": 0.0016, "Hf-176": 0.0526, ...}
            Returns empty dict if element not found or has no natural isotopes.
        """
        # Normalize element symbol for comparison (first letter upper, rest lower)
        element_normalized = element.capitalize()

        composition: Dict[str, float] = {}

        try:
            with self.get_file_path(FileCategory.ISOTOPES, "isotopes.info").open() as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("%"):
                        continue
                    # Data lines start with a digit (atomic number)
                    if line[0].isdigit():
                        data = line.split()
                        # Format: atomic_num mass_num stable/radio element name spin g_factor abundance quadrupole
                        # Index:     0          1        2         3      4     5      6         7         8
                        if len(data) >= 8:
                            file_element = data[3]
                            mass_number = int(data[1])
                            abundance_percent = float(data[7])

                            # Match element and check for non-zero natural abundance
                            # Use tolerance for floating point comparison
                            if file_element == element_normalized and abundance_percent > 1e-10:
                                isotope_str = f"{file_element}-{mass_number}"
                                # Convert percentage to fraction
                                abundance_fraction = abundance_percent / 100.0

                                # Validate converted value is in valid range
                                if abundance_fraction > 1.0:
                                    logger.error(
                                        f"Abundance {abundance_percent}% for {isotope_str} exceeds 100%. "
                                        f"Check isotopes.info file format."
                                    )
                                    # Still include but cap at 1.0
                                    abundance_fraction = min(abundance_fraction, 1.0)

                                composition[isotope_str] = abundance_fraction

        except (IOError, FileNotFoundError, PermissionError) as e:
            logger.error(f"Failed to read isotopes.info for element {element}: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Error reading composition for element {element}: {e}")
            return {}

        # Validate that abundances sum to approximately 1.0 (within 1% tolerance)
        if composition:
            total = sum(composition.values())
            if abs(total - 1.0) > 0.01:
                logger.warning(
                    f"Natural abundances for {element} sum to {total:.4f}, expected ~1.0. "
                    f"This may indicate data quality issues in isotopes.info."
                )

        return composition
