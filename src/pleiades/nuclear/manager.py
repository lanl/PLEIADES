#!/usr/bin/env python
"""Manages access to nuclear data files packaged with PLEIADES."""

import io
import zipfile
from pathlib import Path
from typing import Optional, Tuple

import requests

from pleiades.nuclear.isotopes.manager import IsotopeManager
from pleiades.nuclear.isotopes.models import IsotopeInfo
from pleiades.nuclear.models import (
    LIBRARY_FILENAME_PATTERNS,
    DataRetrievalMethod,
    EndfFilenamePattern,
    EndfLibrary,
    IsotopeParameters,
)
from pleiades.utils.config import get_config
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


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
        # Ensure cache directories exist for each retrieval method and library
        for method in DataRetrievalMethod:
            for library in EndfLibrary:
                cache_dir = self._get_cache_dir(method, library)
                cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_dir(self, method: DataRetrievalMethod, library: EndfLibrary) -> Path:
        """
        Get the cache directory for a specific retrieval method and library.

        Args:
            method: The data retrieval method (DIRECT, API)
            library: The ENDF library version

        Returns:
            Path to the cache directory
        """
        config = get_config()
        return config.nuclear_data_cache_dir / method / library

    def _get_cache_file_path(
        self, method: DataRetrievalMethod, library: EndfLibrary, isotope: IsotopeInfo, mat: int
    ) -> Path:
        """
        Get the path to the cached data file.

        Args:
            method: The data retrieval method (DIRECT, API)
            library: The ENDF library version
            isotope: IsotopeInfo instance
            mat: Material number

        Returns:
            Path to the cached file
        """
        z = f"{isotope.atomic_number:03d}"  # Zero-padded to 3 digits
        z_nozero = f"{isotope.atomic_number}"  # Non-zero-padded version
        element = isotope.element.capitalize()
        a = isotope.mass_number

        if method == DataRetrievalMethod.DIRECT:
            # For direct downloads, use the same pattern as the source files, but with .dat extension
            pattern = LIBRARY_FILENAME_PATTERNS.get(library, EndfFilenamePattern.ELEMENT_FIRST)
            format_vars = {"z": z, "z_nozero": z_nozero, "element": element, "a": a, "mat": mat}
            filename = pattern.value.format(**format_vars).replace(".zip", ".dat")
        else:  # API method
            # For API downloads, use a more descriptive filename indicating it contains only resonance data
            library_short = library.value.replace("ENDF-B-", "B").replace(".", "")
            filename = f"n_{z}-{element}-{a}_{mat}_resonance.dat"

        return self._get_cache_dir(method, library) / filename

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
        return IsotopeParameters(isotope_information=isotope_info, endf_library=self.default_library)

    def clear_cache(self, method: Optional[DataRetrievalMethod] = None, library: Optional[EndfLibrary] = None) -> None:
        """
        Clear the specified cache directories.

        Args:
            method: Optional data retrieval method to clear. If None, clears all methods.
            library: Optional library to clear. If None, clears all libraries.
        """
        config = get_config()

        # Determine directories to clear
        if method is None:
            # Clear all methods
            dirs_to_clear = [config.nuclear_data_cache_dir / m.value for m in DataRetrievalMethod]
        elif library is None:
            # Clear specific method, all libraries
            dirs_to_clear = [config.nuclear_data_cache_dir / method.value]
        else:
            # Clear specific method and library
            dirs_to_clear = [config.nuclear_data_cache_dir / method.value / library.value]

        # Delete files in each directory
        for directory in dirs_to_clear:
            if directory.exists():
                for file in directory.glob("*.dat"):
                    try:
                        # Call unlink directly on the file path
                        file.unlink()
                        logger.info(f"Deleted cached file: {file}")
                    except (OSError, PermissionError) as e:
                        logger.error(f"Failed to delete {file}: {str(e)}")

    def _get_data_from_direct(
        self, isotope: IsotopeInfo, library: EndfLibrary, cache_file_path: Path
    ) -> Tuple[bytes, str]:
        """
        Download complete ENDF data file directly from IAEA.

        This method downloads the complete ENDF file for an isotope directly from the IAEA FTP server.
        The file contains all ENDF sections (not just resonance data).

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
        z = f"{isotope.atomic_number:03d}"  # Zero-padded to 3 digits
        z_nozero = f"{isotope.atomic_number}"  # Non-zero-padded version
        element = isotope.element.capitalize()
        a = isotope.mass_number
        mat = isotope.material_number

        if mat is None:
            mat = self.isotope_manager.get_mat_number(isotope)
            if mat is None:
                raise ValueError(f"Cannot determine MAT number for {isotope}")

        # Get the pattern for this library or default to ELEMENT_FIRST
        pattern = LIBRARY_FILENAME_PATTERNS.get(library, EndfFilenamePattern.ELEMENT_FIRST)

        # Format the filename using the pattern and format specification
        format_vars = {"z": z, "z_nozero": z_nozero, "element": element, "a": a, "mat": mat}
        filename = pattern.value.format(**format_vars)

        config = get_config()
        base_url = config.nuclear_data_sources[DataRetrievalMethod.DIRECT.value]

        # Make sure to use the string value of the library enum, not the enum itself
        library_str = library.value if isinstance(library, EndfLibrary) else str(library)
        url = f"{base_url}/{library_str}/n/{filename}"

        logger.info(f"Downloading complete ENDF data from {url}")
        logger.info("This will download and cache the entire ENDF file (all sections)")
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

    def _get_data_from_api(
        self, isotope: IsotopeInfo, library: EndfLibrary, cache_file_path: Path
    ) -> Tuple[bytes, str]:
        """
        Download only the neutron resonance data section from IAEA via the EXFOR API.

        This method uses the IAEA EXFOR API (also used by NNDC website) to selectively
        download only the neutron resonance section of the ENDF file rather than the
        complete file. This is more efficient but contains only partial data.

        Args:
            isotope: IsotopeInfo instance
            library: ENDF library version
            cache_file_path: Path to save cached file

        Returns:
            Tuple of (file content bytes, original filename)

        Raises:
            ValueError: If no suitable data is found
            requests.RequestException: If the download fails
        """
        # Format target string for search
        element = isotope.element.capitalize()
        a = isotope.mass_number
        target = f"{element}-{a}"

        # Convert EndfLibrary enum to API library format
        library_str = library.value
        # API uses ENDF/B-VIII.0 format (with / instead of -)
        library_str = library_str.replace("ENDF-B-", "ENDF/B-")

        logger.info(f"Searching for neutron resonance data for {target} in {library_str} via IAEA EXFOR API")
        logger.info("Note: This will download ONLY the resonance section, not the complete ENDF file")

        # Get the API base URL from configuration
        config = get_config()
        base_url = config.nuclear_data_sources[DataRetrievalMethod.API.value]
        headers = {"User-Agent": "pleiades-endf-client/0.1"}

        try:
            # Query parameters
            params = {
                "Target": target,
                "Reaction": "n,*",  # All neutron reactions
                "Quantity": "res",  # Resonance data
                "Library": library_str,  # Specific library
                "json": "",  # Return JSON format
            }

            # Make the search request
            response = requests.get(f"{base_url}/E4sSearch2", params=params, headers=headers, timeout=30)
            response.raise_for_status()
            search_results = response.json().get("sections", [])

            if not search_results:
                raise ValueError(f"No resonance data found for {target} in {library_str}")

            # Pick the first matching section (most relevant)
            first_match = search_results[0]
            sect_id = first_match["SectID"]
            library_name = first_match.get("LibName", library_str)

            logger.info(f"Found neutron resonance data (SectID: {sect_id}) for {target} in {library_name}")

            # Download the specific section
            download_params = {"SectID": sect_id, "download": ""}

            # Get the section data
            download_response = requests.get(
                f"{base_url}/E4sGetSect", params=download_params, headers=headers, timeout=60
            )
            download_response.raise_for_status()

            # Save to cache
            cache_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file_path, "wb") as f:
                f.write(download_response.content)

            logger.info(f"Downloaded neutron resonance data section for {target}")
            logger.info(f"Cached as: {cache_file_path}")

            return download_response.content, f"{target}_resonance.dat"

        except requests.RequestException as e:
            logger.error(f"Failed to download data from IAEA EXFOR API: {str(e)}")
            raise

    def download_endf_resonance_file(
        self,
        isotope: IsotopeInfo,
        library: str,
        output_dir: str = ".",
        method: DataRetrievalMethod = DataRetrievalMethod.DIRECT,
        use_cache: bool = True,
    ) -> Path:
        """
        Download and extract resonance parameter section from ENDF library.

        This function first checks if the file is available in cache. If not, it downloads
        the data using the specified method and then processes as needed:
        - DIRECT: Downloads complete ENDF file and extracts resonance parameters
        - API: Downloads only resonance data section (more efficient, no extraction needed)

        Args:
            isotope: IsotopeInfo instance with atomic_number, element, mass_number, material_number
            library: ENDF library version string (e.g., "ENDF-B-VIII.0")
            output_dir: Directory to write the .par output file
            method: Data retrieval method to use:
                   - DIRECT: Downloads complete ENDF file (all sections)
                   - API: Downloads only resonance data section (more efficient)
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
        cache_file_path = self._get_cache_file_path(method, library, isotope, isotope.material_number)

        # Prepare output file path
        z = f"{isotope.atomic_number:03d}"
        element = isotope.element.capitalize()
        a = isotope.mass_number
        output_name = f"{z}-{element}-{a}.{library.value.replace('ENDF-', '')}.par"
        output_path = Path(output_dir) / output_name

        # Check if file exists in cache
        content = None
        if use_cache and cache_file_path.exists():
            logger.info(f"Using cached ENDF data from {cache_file_path}")
            with open(cache_file_path, "rb") as f:
                content = f.read()
        else:
            # Download using appropriate method
            if method == DataRetrievalMethod.DIRECT:
                content, _ = self._get_data_from_direct(isotope, library, cache_file_path)
            elif method == DataRetrievalMethod.API:
                content, _ = self._get_data_from_api(isotope, library, cache_file_path)
            else:
                raise ValueError(f"Invalid data retrieval method: {method}")

        # Process the data based on retrieval method
        if method == DataRetrievalMethod.DIRECT:
            # For DIRECT method, extract only the resonance parameter lines
            logger.info("Extracting resonance parameters from complete ENDF file")
            content_text = content.decode("utf-8")
            resonance_lines = [line for line in content_text.splitlines() if line[70:72].strip() in {"2", "32", "34"}]

            if not resonance_lines:
                logger.warning("No resonance parameters found in the downloaded ENDF file")

            # Write the extracted resonance parameters to output file
            output_path.write_text("\n".join(resonance_lines))
            logger.info(f"Resonance parameters extracted and written to {output_path}")

        elif method == DataRetrievalMethod.API:
            # For API method, the content already contains only resonance data
            # Just write it directly to the output file
            logger.info("API method returned resonance data directly, no extraction needed")
            output_path.write_bytes(content)
            logger.info(f"Resonance parameters written to {output_path}")

        # Log information about the method used
        if method == DataRetrievalMethod.API:
            logger.info("Note: Only resonance data was downloaded (API method)")
        else:
            logger.info("Note: Complete ENDF file was downloaded and resonance data was extracted (DIRECT method)")

        return output_path
