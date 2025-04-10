"""Manages access to isotope data files packaged with PLEIADES."""

import functools
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

from pleiades.nuclear.isotopes.models import FileCategory


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
            raise ValueError(f"Invalid file extension for {category}. " f"Allowed extensions: {self._CATEGORY_FILE_EXTENSIONS[category]}")

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
            return path.suffix in self._CATEGORY_FILE_EXTENSIONS[category] and any(
                file.name == filename for file in self._cached_files[category]
            )
        except Exception:
            return False
