#!/usr/bin/env python
"""Manages access to nuclear data files packaged with PLEIADES."""

import io
import logging
import zipfile
from pathlib import Path
from typing import Optional, Tuple

import requests

from pleiades.nuclear.isotopes.manager import IsotopeManager
from pleiades.nuclear.isotopes.models import IsotopeInfo
from pleiades.nuclear.models import DataSource, EndfLibrary, IsotopeParameters
from pleiades.utils.config import get_config

logger = logging.getLogger(__name__)


class NuclearDataManager:
    """Manager for nuclear data files and caching."""

    def __init__(self, isotope_manager: Optional[IsotopeManager] = None):
        """
        Initialize the NuclearDataManager.

        Args:
            isotope_manager: Optional instance of IsotopeManager. If not provided, a new instance will be created.
        """
        self.isotope_manager = isotope_manager or IsotopeManager()
        # Initialize cache directory
        self._initialize_cache()
        # Default ENDF library - pinned to VIII.0
        self.default_library = EndfLibrary.ENDF_B_VIII_0

    def _initialize_cache(self) -> None:
        """Initialize the cache directory structure."""
        config = get_config()
        # Ensure cache directories exist for each data source and library
        for source in DataSource:
            for library in EndfLibrary:
                cache_dir = self._get_cache_dir(source, library)
                cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_dir(self, source: DataSource, library: EndfLibrary) -> Path:
        """
        Get the cache directory for a specific data source and library.

        Args:
            source: The data source (IAEA, NNDC)
            library: The ENDF library version

        Returns:
            Path to the cache directory
        """
        config = get_config()
        return config.nuclear_data_cache_dir / source / library

    def _get_cache_file_path(self, source: DataSource, library: EndfLibrary, isotope: IsotopeInfo, mat: int) -> Path:
        """
        Get the path to the cached data file.

        Args:
            source: The data source (IAEA, NNDC)
            library: The ENDF library version
            isotope: IsotopeInfo instance
            mat: Material number

        Returns:
            Path to the cached file
        """
        z = f"{isotope.atomic_number:03d}"
        element = isotope.element.capitalize()
        a = isotope.mass_number
        filename = f"n_{z}-{element}-{a}_{mat}.dat"
        return self._get_cache_dir(source, library) / filename

    def create_isotope_parameters_from_string(self, isotope_str: str) -> IsotopeParameters:
        """
        Create an IsotopeParameters instance with the isotope set.

        Args:
            isotope_str: String representation of the isotope (e.g., "U-238").

        Returns:
            IsotopeParameters instance with the isotope set.

        Raises:
            ValueError: If the isotope string is invalid or not found.
        """
        # Retrieve IsotopeInfo using IsotopeManager
        isotope_info = self.isotope_manager.get_isotope_info(isotope_str)
        if not isotope_info:
            raise ValueError(f"Isotope information for '{isotope_str}' not found.")

        # Create and return an IsotopeParameters instance with default library
        return IsotopeParameters(isotope_infomation=isotope_info, endf_library=self.default_library)

    def clear_cache(self, source: Optional[DataSource] = None, library: Optional[EndfLibrary] = None) -> None:
        """
        Clear the specified cache directories.

        Args:
            source: Optional data source to clear. If None, clears all sources.
            library: Optional library to clear. If None, clears all libraries.
        """
        config = get_config()

        # Determine directories to clear
        if source is None:
            # Clear all sources
            dirs_to_clear = [config.nuclear_data_cache_dir / s.value for s in DataSource]
        elif library is None:
            # Clear specific source, all libraries
            dirs_to_clear = [config.nuclear_data_cache_dir / source.value]
        else:
            # Clear specific source and library
            dirs_to_clear = [config.nuclear_data_cache_dir / source.value / library.value]

        # Delete files in each directory
        for directory in dirs_to_clear:
            if directory.exists():
                for file in directory.glob("*.dat"):
                    try:
                        # Call unlink directly on the file path
                        file.unlink()
                        logger.info(f"Deleted cached file: {file}")
                    except Exception as e:
                        logger.error(f"Failed to delete {file}: {str(e)}")

    def _get_data_from_iaea(
        self, isotope: IsotopeInfo, library: EndfLibrary, cache_file_path: Path
    ) -> Tuple[bytes, str]:
        """
        Download ENDF data from IAEA.

        Args:
            isotope: IsotopeInfo instance
            library: ENDF library version
            cache_file_path: Path to save cached file

        Returns:
            Tuple of (file content bytes, original filename)

        Raises:
            ValueError: If the MAT number cannot be determined
            requests.RequestException: If download fails
        """
        z = f"{isotope.atomic_number:03d}"
        element = isotope.element.capitalize()
        a = isotope.mass_number
        mat = isotope.material_number

        if mat is None:
            mat = self.isotope_manager.get_mat_number(isotope)
            if mat is None:
                raise ValueError(f"Cannot determine MAT number for {isotope}")

        # Construct filename and URL
        filename = f"n_{z}-{element}-{a}_{mat}.zip"
        config = get_config()
        base_url = config.nuclear_data_sources[DataSource.IAEA.value]
        url = f"{base_url}/{library}/n/{filename}"

        logger.info(f"Downloading ENDF data from {url}")
        response = requests.get(url)
        response.raise_for_status()

        # Save the zip content to cache
        cache_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract data file from zip
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith((".endf", ".txt", ".dat")):
                    with zip_ref.open(file) as f:
                        content = f.read()

                    # Write the entire file to cache
                    with open(cache_file_path, "wb") as f:
                        f.write(content)

                    return content, file

        raise FileNotFoundError("No suitable ENDF file found inside the ZIP.")

    def _get_data_from_nndc(
        self, isotope: IsotopeInfo, library: EndfLibrary, cache_file_path: Path
    ) -> Tuple[bytes, str]:
        """
        Download ENDF data from NNDC.

        Args:
            isotope: IsotopeInfo instance
            library: ENDF library version
            cache_file_path: Path to save cached file

        Returns:
            Tuple of (file content bytes, original filename)

        Raises:
            NotImplementedError: NNDC download not yet implemented
        """
        raise NotImplementedError("NNDC data source is not yet implemented")

    def download_endf_resonance_file(
        self,
        isotope: IsotopeInfo,
        library: str,
        output_dir: str = ".",
        source: DataSource = DataSource.IAEA,
        use_cache: bool = True,
    ) -> Path:
        """
        Download and extract resonance parameter section from ENDF library.

        This function first checks if the file is available in cache. If not, it downloads
        the complete file to cache and then extracts the resonance parameters.

        Args:
            isotope: IsotopeInfo instance with atomic_number, element, mass_number, material_number
            library: ENDF library version string (e.g., "ENDF-B-VIII.0")
            output_dir: Directory to write the .par output file
            source: Data source to use (IAEA or NNDC)
            use_cache: Whether to check cache before downloading

        Returns:
            Path to the saved resonance parameter file
        """
        # Convert string to EndfLibrary enum if needed
        if isinstance(library, str):
            try:
                library = next(lib for lib in EndfLibrary if lib.value == library)
            except StopIteration:
                raise ValueError(f"Invalid library: {library}. Valid options: {[lib.value for lib in EndfLibrary]}")

        # Ensure we have a material number
        if isotope.material_number is None:
            isotope.material_number = self.isotope_manager.get_mat_number(isotope)
            if isotope.material_number is None:
                raise ValueError(f"Cannot determine MAT number for {isotope}")

        # Determine cache file path
        cache_file_path = self._get_cache_file_path(source, library, isotope, isotope.material_number)

        # Check if file exists in cache
        content = None
        if use_cache and cache_file_path.exists():
            logger.info(f"Using cached ENDF data from {cache_file_path}")
            with open(cache_file_path, "rb") as f:
                content = f.read()
        else:
            # Download from appropriate source
            if source == DataSource.IAEA:
                content, _ = self._get_data_from_iaea(isotope, library, cache_file_path)
            elif source == DataSource.NNDC:
                content, _ = self._get_data_from_nndc(isotope, library, cache_file_path)
            else:
                raise ValueError(f"Invalid data source: {source}")

        # Extract resonance parameters and write to output file
        z = f"{isotope.atomic_number:03d}"
        element = isotope.element.capitalize()
        a = isotope.mass_number

        output_name = f"{z}-{element}-{a}.{library.value.replace('ENDF-', '')}.par"
        output_path = Path(output_dir) / output_name

        # Extract resonance parameters
        content_text = content.decode("utf-8")
        resonance_lines = [line for line in content_text.splitlines() if line[70:72].strip() in {"2", "32", "34"}]

        output_path.write_text("\n".join(resonance_lines))
        logger.info(f"Resonance parameters written to {output_path}")
        return output_path
