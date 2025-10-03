"""
SAMMY JSON configuration file management.

This module provides Pydantic models and JsonManager class for generating and parsing
SAMMY JSON configuration files used in multi-isotope fitting workflows. It integrates
with the nuclear data manager to automatically retrieve and stage ENDF files.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pleiades.nuclear.manager import NuclearDataManager
from pleiades.nuclear.models import DataRetrievalMethod, EndfLibrary
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="sammy_json_manager")


class IsotopeEntry(BaseModel):
    """
    Pydantic model for a single isotope entry in SAMMY JSON configuration.

    Based on analysis of sammy_json_example/endfAdd_new_1.js structure.
    """

    model_config = ConfigDict(validate_default=True)

    mat: str = Field(description="MAT number as string (e.g., '7225')")
    abundance: str = Field(description="Isotopic abundance as string (e.g., '0.0016')")
    adjust: str = Field(default="false", description="Whether to adjust abundance during fitting")
    uncertainty: str = Field(default="0.02", description="Uncertainty in abundance")

    @field_validator("mat")
    @classmethod
    def validate_mat_number(cls, v: str) -> str:
        """Validate MAT number is a valid string representation of integer."""
        try:
            int(v)
            return v
        except ValueError:
            raise ValueError(f"MAT number must be a valid integer string, got: {v}")

    @field_validator("abundance")
    @classmethod
    def validate_abundance(cls, v: str) -> str:
        """Validate abundance is a valid string representation of float."""
        try:
            abundance_float = float(v)
            if not (0.0 <= abundance_float <= 1.0):
                raise ValueError(f"Abundance must be between 0.0 and 1.0, got: {abundance_float}")
            return v
        except ValueError as e:
            if "between" in str(e):
                raise e
            raise ValueError(f"Abundance must be a valid float string, got: {v}")


class SammyJsonConfig(BaseModel):
    """
    Pydantic model for complete SAMMY JSON configuration.

    Based on analysis of sammy_json_example/endfAdd_new_1.js structure.
    Contains global settings and isotope entries.
    """

    model_config = ConfigDict(
        validate_default=True,
        extra="allow",  # Allow dynamic isotope entries
        str_strip_whitespace=True,
    )

    # Global settings (based on reference analysis)
    forceRMoore: str = Field(default="yes", description="Force Reich-Moore formalism")
    purgeSpinGroups: str = Field(default="yes", description="Purge spin groups setting")
    fudge: str = Field(default="0.7", description="Fudge factor")

    # Dynamic isotope entries will be added programmatically
    # Format: isotope_name -> List[IsotopeEntry]
    # e.g., "hf174_endf": [IsotopeEntry(...)]

    def add_isotope_entry(self, isotope_name: str, entry: IsotopeEntry) -> None:
        """
        Add an isotope entry to the configuration.

        Args:
            isotope_name: Name/key for the isotope (e.g., "hf174_endf")
            entry: IsotopeEntry containing MAT, abundance, etc.
        """
        # SAMMY expects isotope entries as lists (even for single entries)
        # Use __setattr__ for Pydantic v2 with extra="allow"
        self.__setattr__(isotope_name, [entry])
        logger.debug(f"Added isotope entry: {isotope_name}")

    def get_isotope_entries(self) -> Dict[str, List[IsotopeEntry]]:
        """
        Get all isotope entries from the configuration.

        Returns:
            Dict[str, List[IsotopeEntry]]: Mapping of isotope names to entries
        """
        isotope_entries = {}

        # Use model_dump() to get all fields including extra ones in Pydantic v2
        all_fields = self.model_dump()

        for field_name, value in all_fields.items():
            if (
                field_name not in ["forceRMoore", "purgeSpinGroups", "fudge"]
                and isinstance(value, list)
                and len(value) > 0
            ):
                # Convert back to IsotopeEntry objects if needed
                if isinstance(value[0], dict):
                    isotope_entries[field_name] = [IsotopeEntry(**entry_dict) for entry_dict in value]
                else:
                    isotope_entries[field_name] = value

        return isotope_entries

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary suitable for JSON serialization.

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        result = {"forceRMoore": self.forceRMoore, "purgeSpinGroups": self.purgeSpinGroups, "fudge": self.fudge}

        # Add isotope entries
        for isotope_name, entries in self.get_isotope_entries().items():
            result[isotope_name] = [entry.model_dump() for entry in entries]

        return result


class JsonManager:
    """
    Manager for SAMMY JSON configuration files.

    Handles generation and parsing of JSON configuration files using Pydantic models.
    Integrates with NuclearDataManager to automatically download and stage ENDF files.

    Example:
        >>> json_manager = JsonManager()
        >>> json_path = json_manager.create_json_config(
        ...     isotopes=["Hf-174", "Hf-176", "Hf-177"],
        ...     abundances=[0.0016, 0.0526, 0.186],
        ...     working_dir="./sammy_workspace"
        ... )
        # Creates complete workspace with config.json + ENDF files
    """

    def __init__(self, nuclear_manager: Optional[NuclearDataManager] = None):
        """
        Initialize JsonManager.

        Args:
            nuclear_manager: Optional NuclearDataManager instance. If not provided,
                           a new instance will be created.
        """
        self.nuclear_manager = nuclear_manager or NuclearDataManager()
        logger.info("JsonManager initialized with Pydantic v2 models")

    def create_json_config(
        self,
        isotopes: List[str],
        abundances: List[float],
        working_dir: Union[str, Path],
        json_filename: str = "config.json",
        library: EndfLibrary = EndfLibrary.ENDF_B_VIII_0,
        method: DataRetrievalMethod = DataRetrievalMethod.API,
        custom_global_settings: Optional[Dict[str, str]] = None,
    ) -> Path:
        """
        Create a SAMMY JSON configuration file and stage required ENDF files.

        Creates a complete workspace for SAMMY JSON mode by:
        1. Downloading/staging all required ENDF files to working directory
        2. Generating JSON configuration that references the actual ENDF filenames
        3. Ensuring JSON keys match the staged ENDF file names

        Args:
            isotopes: List of isotope names (e.g., ["Hf-174", "Hf-176"])
            abundances: List of isotopic abundances as fractions (same order as isotopes)
            working_dir: Directory where JSON file and ENDF files will be created
            json_filename: Name for the JSON configuration file
            library: ENDF library to use for isotope data
            method: Data retrieval method (API is faster for multiple files)
            custom_global_settings: Optional custom global settings to override defaults

        Returns:
            Path: Path to the created JSON file

        Raises:
            ValueError: If isotopes and abundances lists have different lengths
        """
        # Validate input parameters
        if len(isotopes) != len(abundances):
            raise ValueError(
                f"Isotopes and abundances lists must have same length: "
                f"got {len(isotopes)} isotopes and {len(abundances)} abundances"
            )

        if not isotopes:
            raise ValueError("At least one isotope must be provided")

        # Convert working directory to Path object and create it
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Creating SAMMY workspace for {len(isotopes)} isotopes: {isotopes}")
        logger.info(f"Working directory: {working_dir}")

        # Step 1: Stage ENDF files first to get actual filenames
        logger.info("Step 1: Staging ENDF files...")
        staged_files = {}

        for isotope_name in isotopes:
            try:
                # Get isotope information
                isotope_info = self.nuclear_manager.isotope_manager.get_isotope_info(isotope_name)

                # Download ENDF file to working directory
                endf_path = self.nuclear_manager.download_endf_resonance_file(
                    isotope=isotope_info, library=library, output_dir=str(working_dir), method=method
                )

                # Store actual filename for JSON reference
                endf_path_obj = Path(endf_path)
                if endf_path_obj.exists():
                    staged_files[isotope_name] = endf_path_obj
                    logger.debug(f"Staged {isotope_name}: {endf_path_obj.name}")
                else:
                    raise FileNotFoundError(f"ENDF file not created for {isotope_name}")

            except Exception as e:
                logger.error(f"Failed to stage ENDF file for {isotope_name}: {e}")
                raise ValueError(f"Failed to stage ENDF file for {isotope_name}: {e}")

        # Step 2: Create JSON config using actual ENDF filenames as keys
        logger.info("Step 2: Creating JSON configuration with actual ENDF filenames...")

        # Create SammyJsonConfig with custom global settings if provided
        global_settings = {}
        if custom_global_settings:
            global_settings.update(custom_global_settings)

        config = SammyJsonConfig(**global_settings)

        # Process each isotope using actual ENDF filenames as JSON keys
        for isotope_name, abundance in zip(isotopes, abundances):
            try:
                # Get isotope information for MAT number
                isotope_info = self.nuclear_manager.isotope_manager.get_isotope_info(isotope_name)

                # Create isotope entry
                entry = IsotopeEntry(
                    mat=str(isotope_info.material_number),
                    abundance=str(abundance),
                    # adjust and uncertainty use defaults ("false", "0.02")
                )

                # Use actual ENDF filename as JSON key (maintains traceability)
                endf_filename = staged_files[isotope_name].name

                # Add to configuration
                config.add_isotope_entry(endf_filename, entry)

                logger.debug(f"Added {isotope_name} (MAT={isotope_info.material_number}) as {endf_filename}")

            except Exception as e:
                logger.error(f"Failed to process isotope {isotope_name}: {e}")
                raise ValueError(f"Failed to process isotope {isotope_name}: {e}")

        # Step 3: Write JSON file to working directory
        json_path = working_dir / json_filename
        json_dict = config.to_dict()

        with open(json_path, "w") as f:
            json.dump(json_dict, f, indent=2)

        logger.info(f"JSON configuration written to: {json_path}")
        logger.info(f"Configuration contains {len(config.get_isotope_entries())} isotope entries")
        logger.info(f"SAMMY workspace complete: {len(staged_files)} ENDF files + 1 JSON file")

        return json_path

    def _generate_isotope_key(self, isotope_name: str) -> str:
        """
        Generate a meaningful but concise JSON key name from isotope name.

        Args:
            isotope_name: Isotope name like "Hf-174"

        Returns:
            str: JSON key like "hf174_endf"
        """
        # Convert "Hf-174" -> "hf174_endf"
        # This is meaningful, shorter than full ENDF filename, but still descriptive
        key = isotope_name.lower().replace("-", "") + "_endf"
        return key

    def stage_endf_files(
        self,
        isotopes: List[str],
        working_dir: Union[str, Path],
        library: EndfLibrary = EndfLibrary.ENDF_B_VIII_0,
        method: DataRetrievalMethod = DataRetrievalMethod.API,
    ) -> Dict[str, Path]:
        """
        Download and stage ENDF files for specified isotopes.

        Args:
            isotopes: List of isotope names (e.g., ["Hf-174", "Hf-176"])
            working_dir: Directory where ENDF files will be staged
            library: ENDF library to use
            method: Data retrieval method (API is faster for multiple files)

        Returns:
            Dict[str, Path]: Mapping of isotope names to staged file paths
        """
        working_dir = Path(working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Staging ENDF files for {len(isotopes)} isotopes in {working_dir}")
        logger.info(f"Using {method.name} method with {library.name}")

        staged_files = {}

        for isotope_name in isotopes:
            try:
                # Get isotope information
                isotope_info = self.nuclear_manager.isotope_manager.get_isotope_info(isotope_name)

                # Download ENDF file to working directory
                endf_path = self.nuclear_manager.download_endf_resonance_file(
                    isotope=isotope_info, library=library, output_dir=str(working_dir), method=method
                )

                # Verify file was created
                endf_path_obj = Path(endf_path)
                if endf_path_obj.exists():
                    staged_files[isotope_name] = endf_path_obj
                    logger.debug(f"Staged {isotope_name}: {endf_path_obj.name}")
                else:
                    logger.error(f"ENDF file not created for {isotope_name}: {endf_path}")
                    raise FileNotFoundError(f"ENDF file not created for {isotope_name}")

            except Exception as e:
                logger.error(f"Failed to stage ENDF file for {isotope_name}: {e}")
                raise ValueError(f"Failed to stage ENDF file for {isotope_name}: {e}")

        logger.info(f"Successfully staged {len(staged_files)} ENDF files")
        return staged_files

    def parse_json_config(self, json_path: Union[str, Path]) -> SammyJsonConfig:
        """
        Parse an existing SAMMY JSON configuration file into Pydantic model.

        Args:
            json_path: Path to the JSON file to parse

        Returns:
            SammyJsonConfig: Parsed and validated JSON configuration

        Raises:
            FileNotFoundError: If JSON file doesn't exist
            json.JSONDecodeError: If JSON file is invalid
            ValidationError: If JSON doesn't match expected structure
        """
        json_path = Path(json_path)

        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")

        logger.info(f"Parsing JSON configuration: {json_path}")

        with open(json_path, "r") as f:
            json_data = json.load(f)

        # Create base config with global settings
        config = SammyJsonConfig(
            forceRMoore=json_data.get("forceRMoore", "yes"),
            purgeSpinGroups=json_data.get("purgeSpinGroups", "yes"),
            fudge=json_data.get("fudge", "0.7"),
        )

        # Add isotope entries
        for key, value in json_data.items():
            if key not in ["forceRMoore", "purgeSpinGroups", "fudge"] and isinstance(value, list):
                # Convert each entry to IsotopeEntry model
                isotope_entries = [IsotopeEntry(**entry_dict) for entry_dict in value]
                setattr(config, key, isotope_entries)

        logger.info(f"Successfully parsed JSON with {len(config.get_isotope_entries())} isotope entries")
        return config
