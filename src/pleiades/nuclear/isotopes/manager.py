"""Manages access to isotope data files packaged with PLEIADES."""
import re
import functools
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

from pleiades.nuclear.isotopes.models import FileCategory, IsotopeInfo, IsotopeMassData


class IsotopeManager:
    """
    Manages access to isotope data files packaged with PLEIADES.

    This class provides a centralized interface for accessing isotope data files
    that are distributed with the PLEIADES package. It handles path resolution,
    validates file existence, and caches results for improved performance.
    """

    # Mapping of file categories to their valid file extensions
    _CATEGORY_FILE_EXTENSIONS = {
        FileCategory.ISOTOPES: {".info", ".mas20", ".list"}
    }

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
                    item for item in base_path.iterdir()
                    if item.suffix in self._CATEGORY_FILE_EXTENSIONS[category]
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
            raise ValueError(f"Invalid file extension for {category}. "
                            f"Allowed extensions: {self._CATEGORY_FILE_EXTENSIONS[category]}")

        print(f"Searching for {filename} in cached files for {category}: {self._cached_files[category]}")
        for file in self._cached_files[category]:
            print(f"Checking file: {file.name}")
            if file.name == filename:
                print(f"Found file: {file}")
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
            return path.suffix in self._CATEGORY_FILE_EXTENSIONS[category] and \
                any(file.name == filename for file in self._cached_files[category])
        except Exception:
            return False
        
    def get_isotope_info(self, isotope_str: str) -> Optional[IsotopeInfo]:
        """
        Extract isotope information from the isotopes.info file.

        Args:
            isotope_str: String representation of the isotope (e.g., "U-238")

        Returns:
            IsotopeInfo containing isotope details if found, None otherwise
        """
        
        # Create a IsotopeInfo instance from the isotope string
        isotope = IsotopeInfo.from_string(isotope_str)
        
        # get the mass of the isotope from the mass.mas20 file
        isotope.mass_data = self.check_and_get_mass_data(isotope.element, isotope.mass_number)
        
        # check if the isotope is a stable isotope with known abundance and spin
        self.check_and_set_abundance_and_spins(isotope)
        
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
                    if match and match.expand(r"\2-\3") == str(isotope):
                        return int(line[-5:])
            return None
        except Exception as e:
            logger.error(f"Error getting MAT number for {isotope}: {str(e)}")
            raise

