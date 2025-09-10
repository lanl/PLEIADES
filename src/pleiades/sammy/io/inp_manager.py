"""
Module for managing SAMMY input (.inp) files.

This module provides the InpManager class to generate and write SAMMY input files
based on FitOptions configurations. It supports different modes (ENDF, fitting, custom)
through the refactored FitOptions class and its factory methods.
"""

from pathlib import Path
from typing import Dict, List, Optional

from pleiades.sammy.fitting.options import FitOptions
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class InpManager:
    """
    Manages creation and writing of SAMMY input (.inp) files.

    This class takes a FitOptions object and generates a SAMMY input file
    with the appropriate commands based on the selected options.

    Attributes:
        options (FitOptions): Configuration options for SAMMY
        title (str, optional): Title line for the inp file
        isotope_info (Dict, optional): Dictionary with isotope information
        physical_constants (Dict, optional): Dictionary with physical constants
        reaction_type (str, optional): Reaction type (transmission, capture, etc.)
    """

    def __init__(
        self,
        options: FitOptions = None,
        title: str = None,
        isotope_info: Optional[Dict] = None,
        physical_constants: Optional[Dict] = None,
        reaction_type: str = None,
    ):
        """
        Initialize with optional FitOptions and section information.

        Args:
            options: FitOptions instance containing SAMMY configuration
            title: Title/description for the inp file
            isotope_info: Isotope information (name, mass, energy range)
            physical_constants: Physical constants (temperature, flight path, etc.)
            reaction_type: Reaction type (transmission, capture, etc.)
        """
        self.options = options or FitOptions()
        self.title = title
        self.isotope_info = isotope_info
        self.physical_constants = physical_constants
        self.reaction_type = reaction_type

    def set_options(self, options: FitOptions) -> None:
        """
        Set FitOptions after initialization.

        Args:
            options: FitOptions instance to use
        """
        self.options = options

    def generate_commands(self) -> List[str]:
        """
        Generate SAMMY input commands from options.

        Returns:
            List[str]: List of SAMMY alphanumeric commands
        """
        return self.options.get_alphanumeric_commands()

    def generate_title_section(self) -> str:
        """
        Generate the title section of the inp file.

        Returns:
            str: Title line or placeholder comment
        """
        if self.title:
            return self.title
        return "# PLACEHOLDER: Replace with actual title/description"

    def generate_isotope_section(self) -> str:
        """
        Generate the isotope information section of the inp file.

        Returns:
            str: Isotope information line or placeholder comment
        """
        if self.isotope_info:
            # Format isotope information according to SAMMY specifications
            # This would be expanded based on requirements
            return "# Actual isotope information would be formatted here"
        return "# PLACEHOLDER: Replace with isotope information (name, mass, energy range)"

    def generate_physical_constants_section(self) -> str:
        """
        Generate the physical constants section of the inp file.

        Returns:
            str: Physical constants or placeholder comment
        """
        if self.physical_constants:
            # Format physical constants according to SAMMY specifications
            # This would be expanded based on requirements
            return "# PLACEHOLDER: Replace with physical constants (temperature, flight path, etc.)"
        return "# PLACEHOLDER: Replace with physical constants (temperature, flight path, etc.)"

    def generate_reaction_type_section(self) -> str:
        """
        Generate the reaction type section of the inp file.

        Returns:
            str: Reaction type or placeholder comment
        """
        if self.reaction_type:
            return self.reaction_type
        return "# PLACEHOLDER: Replace with reaction type (transmission, capture, fission, etc.)"

    def generate_broadening_parameters_section(self, material_properties: Dict = None) -> str:
        """
        Generate broadening parameters section for multi-isotope mode.

        Args:
            material_properties: Dict with material properties for calculations

        Returns:
            str: Broadening parameters section
        """
        if material_properties:
            from pleiades.utils.units import calculate_number_density

            # Extract material properties with defaults
            density = material_properties.get("density_g_cm3")  # Required
            thickness = material_properties.get("thickness_mm", 5.0)  # Default 5mm
            atomic_mass = material_properties.get("atomic_mass_amu")  # Required
            temperature = material_properties.get("temperature_K", 293.6)  # Default room temp

            if density is None or atomic_mass is None:
                raise ValueError("material_properties must contain 'density_g_cm3' and 'atomic_mass_amu'")

            # Calculate number density
            number_density = calculate_number_density(density, thickness, atomic_mass)

            # Generate broadening parameters section
            # Format: CRFN TEMP THICK DELTAL DELTAG DELTAE FLAGS
            # Reference: 8.0  293.60000 1.797e-04 0.0  0.0  0.0  0 0 1 0 0 0
            lines = [
                "",  # Empty line
                "BROADENING PARAMETERS FOLLOW",
                f"8.0        {temperature:9.5f} {number_density:.3e} 0.0       0.0       0.0       0 0 1 0 0 0",
            ]
            return "\n".join(lines)

        return "\n# PLACEHOLDER: Broadening parameters (provide material_properties to generate)"

    def generate_misc_parameters_section(self, flight_path_m: float = 25.0) -> str:
        """
        Generate miscellaneous parameters (TZERO) section.

        Args:
            flight_path_m: Flight path length in meters (default 25.0 for VENUS)

        Returns:
            str: Miscellaneous parameters section
        """
        # Default TZERO values per your specification:
        # t₀=0.0, t₀_unc=0.0, L₀=1.0, L₀_unc=0.0, flight_path=25.0m, flags=1,1
        lines = [
            "",  # Empty line
            "MISCEllaneous parameters follow",
            f"TZERO 1 1  0.0000000 0.0000000 1.0000000 0.0000000 {flight_path_m:9.6f}",
        ]
        return "\n".join(lines)

    def generate_normalization_parameters_section(self) -> str:
        """
        Generate normalization parameters section.

        Returns:
            str: Normalization parameters section
        """
        # Default NORM values per your specification: 1.0, 0.0, 0.0, 0.0, 0.0, 0.0
        # Flags: let SAMMY fit the first few parameters (1 1 1 1 0 0)
        lines = [
            "",  # Empty line
            'NORMAlization and "constant" background follow',
            "1.00000000 0.00000000 0.00000000 0.00000000 0.        0.        1 1 1 1 0 0",
        ]
        return "\n".join(lines)

    def generate_resolution_function_section(self, resolution_file: str = "venus_resolution.dat") -> str:
        """
        Generate user-defined resolution function section.

        Args:
            resolution_file: Name of resolution function file

        Returns:
            str: Resolution function section
        """
        lines = [
            "",  # Empty line
            "USER-DEFINED RESOLUTION FUNCTION",
            f"FILE={resolution_file}",
        ]
        return "\n".join(lines)

    def generate_multi_isotope_inp_content(self, material_properties: Dict = None) -> str:
        """
        Generate complete multi-isotope INP content with parameter sections.

        Args:
            material_properties: Dict with material properties for parameter calculations

        Returns:
            str: Complete multi-isotope INP file content
        """
        sections = [
            self.generate_title_section(),
            self.generate_isotope_section(),
            "\n".join(self.generate_commands()),
            self.generate_physical_constants_section(),
            self.generate_reaction_type_section(),
            self.generate_broadening_parameters_section(material_properties),
            self.generate_misc_parameters_section(),
            self.generate_normalization_parameters_section(),
            self.generate_resolution_function_section(),
        ]
        return "\n".join(sections)

    def generate_inp_content(self) -> str:
        """
        Generate full content for SAMMY input file.

        Returns:
            str: Complete content for SAMMY input file with placeholders for sections
                 that are not yet implemented
        """
        sections = [
            self.generate_title_section(),
            self.generate_isotope_section(),
            "\n".join(self.generate_commands()),
            "",  # Empty line for readability
            self.generate_physical_constants_section(),
            self.generate_reaction_type_section(),
            "# PLACEHOLDER: Replace with spin group and channel specifications if needed",
        ]
        return "\n".join(sections)

    def write_inp_file(self, file_path: Path) -> Path:
        """
        Write a SAMMY input file to disk.

        Args:
            file_path: Path where the input file should be written

        Returns:
            Path: Path to the created file

        Raises:
            IOError: If file cannot be written
        """
        try:
            content = self.generate_inp_content()
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                f.write(content)

            logger.info(f"Successfully wrote SAMMY input file to {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to write SAMMY input file: {str(e)}")
            raise IOError(f"Failed to write SAMMY input file: {str(e)}")

    @classmethod
    def create_endf_inp(cls, output_path: Path, title: str = None) -> Path:
        """
        Create input file for ENDF mode.

        Args:
            output_path: Path to write the input file
            title: Optional title for the inp file

        Returns:
            Path: Path to the created file
        """
        options = FitOptions.from_endf_config()
        manager = cls(options, title=title or "ENDF extraction mode")
        return manager.write_inp_file(output_path)

    @classmethod
    def create_fitting_inp(cls, output_path: Path, title: str = None) -> Path:
        """
        Create input file for fitting mode.

        Args:
            output_path: Path to write the input file
            title: Optional title for the inp file

        Returns:
            Path: Path to the created file
        """
        options = FitOptions.from_fitting_config()
        manager = cls(options, title=title or "Bayesian fitting mode")
        return manager.write_inp_file(output_path)

    @classmethod
    def create_multi_isotope_inp(cls, output_path: Path, title: str = None, material_properties: Dict = None) -> Path:
        """
        Create input file for multi-isotope JSON mode fitting.

        This method generates a complete INP file for multi-isotope fitting that includes
        both static alphanumeric commands and calculated parameter sections.

        Args:
            output_path: Path to write the input file
            title: Optional title for the inp file
            material_properties: Optional dict with material properties for parameter calculations

        Returns:
            Path: Path to the created file
        """
        options = FitOptions.from_multi_isotope_config()
        manager = cls(options, title=title or "Multi-isotope JSON mode fitting", reaction_type="transmission")

        # Use specialized multi-isotope content generation
        try:
            content = manager.generate_multi_isotope_inp_content(material_properties)
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                f.write(content)

            logger.info(f"Successfully wrote multi-isotope SAMMY input file to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to write multi-isotope SAMMY input file: {str(e)}")
            raise
