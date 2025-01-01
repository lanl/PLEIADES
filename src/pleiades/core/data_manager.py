#!/usr/bin/env python
"""Manages access to nuclear data files packaged with PLEIADES."""

import functools
import logging
import re
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional, Set

from pleiades.core.models import CrossSectionPoint, DataCategory, IsotopeIdentifier, IsotopeInfo, IsotopeMassData

logger = logging.getLogger(__name__)


class NuclearDataManager:
    """
    Manages access to nuclear data files packaged with PLEIADES.

    This class provides a centralized interface for accessing nuclear data files
    that are distributed with the PLEIADES package. It handles path resolution,
    validates file existence, and caches results for improved performance.
    """

    # Mapping of categories to their valid file extensions
    _VALID_EXTENSIONS = {
        DataCategory.ISOTOPES: {".info", ".mas20", ".list"},
        DataCategory.RESONANCES: {".endf"},
        DataCategory.CROSS_SECTIONS: {".tot"},
    }

    def __init__(self):
        """Initialize the NuclearDataManager."""
        self._cached_files: Dict[DataCategory, Set[Path]] = {}
        self._initialize_cache()

    def _initialize_cache(self) -> None:
        """Initialize the cache of available files for each category."""
        for category in DataCategory:
            try:
                category_path = self._get_category_path(category)
                data_path = resources.files("pleiades.data").joinpath(category_path)
                self._cached_files[category] = {
                    item.name for item in data_path.iterdir() if item.suffix in self._VALID_EXTENSIONS[category]
                }
            except Exception as e:
                logger.error(f"Failed to initialize cache for {category}: {str(e)}")
                self._cached_files[category] = set()

    @staticmethod
    def _get_category_path(category: DataCategory) -> str:
        """Get the filesystem path for a category."""
        return DataCategory.to_path(category)

    @functools.lru_cache(maxsize=128)
    def get_file_path(self, category: DataCategory, filename: str) -> Path:
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
        if not isinstance(category, DataCategory):
            raise ValueError(f"Invalid category: {category}")

        file_path = Path(filename)
        if file_path.suffix not in self._VALID_EXTENSIONS[category]:
            raise ValueError(
                f"Invalid file extension for {category}. " f"Allowed extensions: {self._VALID_EXTENSIONS[category]}"
            )

        try:
            with resources.path(f"pleiades.data.{self._get_category_path(category)}", filename) as path:
                if not path.exists():
                    raise FileNotFoundError(f"File {filename} not found in {category}")
                return path
        except Exception as e:
            raise FileNotFoundError(f"Error accessing {filename} in {category}: {str(e)}")

    def list_files(self, category: Optional[DataCategory] = None) -> Dict[DataCategory, List[str]]:
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
            if not isinstance(category, DataCategory):
                raise ValueError(f"Invalid category: {category}")
            return {category: sorted(self._cached_files[category])}

        return {cat: sorted(self._cached_files[cat]) for cat in DataCategory}

    def validate_file(self, category: DataCategory, filename: str) -> bool:
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
            return path.suffix in self._VALID_EXTENSIONS[category] and path in self._cached_files[category]
        except Exception:
            return False

    def get_isotope_info(self, isotope: IsotopeIdentifier) -> Optional[IsotopeInfo]:
        """
        Extract isotope information from the isotopes.info file.

        Args:
            isotope: IsotopeIdentifier instance

        Returns:
            IsotopeInfo containing spin and abundance if found, None otherwise
        """
        try:
            with self.get_file_path(DataCategory.ISOTOPES, "isotopes.info").open() as f:
                for line in f:
                    line = line.strip()
                    if line and line[0].isdigit():
                        data = line.split()
                        if data[3] == isotope.element and int(data[1]) == isotope.mass_number:
                            return IsotopeInfo(spin=float(data[5]), abundance=float(data[7]))
            return None
        except Exception as e:
            logger.error(f"Error reading isotope info for {isotope}: {str(e)}")
            raise

    def get_mass_data(self, isotope: IsotopeIdentifier) -> Optional[IsotopeMassData]:
        """
        Extract mass data for an isotope from the mass.mas20 file.

        Args:
            isotope: IsotopeIdentifier instance

        Returns:
            IsotopeMassData containing atomic mass, mass uncertainty

        Raises:
            ValueError: If data cannot be parsed
        """
        try:
            with self.get_file_path(DataCategory.ISOTOPES, "mass.mas20").open() as f:
                # Skip header lines
                for _ in range(36):
                    next(f)

                for line in f:
                    if (isotope.element in line[:25]) and (str(isotope.mass_number) in line[:25]):
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
                return None
        except Exception as e:
            logger.error(f"Error reading mass data for {isotope}: {str(e)}")
            raise

    def read_cross_section_data(self, filename: str, isotope: IsotopeIdentifier) -> List[CrossSectionPoint]:
        """
        Read cross-section data from a .tot file for a specific isotope.

        Args:
            filename: Name of the cross-section file
            isotope: IsotopeIdentifier instance

        Returns:
            List of CrossSectionPoint containing energy and cross-section values

        Raises:
            ValueError: If isotope data not found or file format is invalid
        """
        try:
            data_points = []
            isotope_found = False
            capture_data = False

            # Convert to string format expected in file (e.g., "U-238")
            isotope_str = str(isotope)

            with self.get_file_path(DataCategory.CROSS_SECTIONS, filename).open() as f:
                for line in f:
                    if isotope_str.upper() in line:
                        isotope_found = True
                    elif isotope_found and "#data..." in line:
                        capture_data = True
                    elif isotope_found and "//" in line:
                        break
                    elif capture_data and not line.startswith("#"):
                        try:
                            energy_MeV, xs = line.split()  # noqa: N806
                            data_points.append(
                                CrossSectionPoint(
                                    energy=float(energy_MeV) * 1e6,  # Convert MeV to eV
                                    cross_section=float(xs),
                                )
                            )
                        except ValueError:
                            logger.warning(f"Skipping malformed line in {filename}: {line.strip()}")
                            continue

            if not isotope_found:
                raise ValueError(f"No data found for isotope {isotope_str} in {filename}")

            return data_points
        except Exception as e:
            logger.error(f"Error reading cross-section data from {filename}: {str(e)}")
            raise

    def get_mat_number(self, isotope: IsotopeIdentifier) -> Optional[int]:
        """
        Get ENDF MAT number for an isotope.

        Args:
            isotope: IsotopeIdentifier instance

        Returns:
            ENDF MAT number if found, None otherwise

        Raises:
            ValueError: If isotope format is invalid
        """
        try:
            with self.get_file_path(DataCategory.ISOTOPES, "neutrons.list").open() as f:
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

    def clear_cache(self) -> None:
        """Clear the file cache and force reinitialization."""
        self._cached_files.clear()
        self._initialize_cache()
