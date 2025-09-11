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

    def generate_physical_constants_section(self, material_properties: Dict = None) -> str:
        """
        Generate the physical constants section for multi-isotope mode.

        Args:
            material_properties: Dict with material properties

        Returns:
            str: Physical constants line
        """
        if material_properties:
            temperature = material_properties.get("temperature_K", 293.6)
            flight_path = material_properties.get("flight_path_m", 25.0)

            # Format: TEMP FLIGHT_PATH DELTAL DELTAG DELTAE
            # Reference: 293.6    25.0    0.0       0.0     0.0
            return f"\n    {temperature:5.1f}    {flight_path:4.1f}    0.0       0.0     0.0"

        # Default for VENUS
        return "\n    293.6    25.0    0.0       0.0     0.0"

    def generate_sample_density_section(self, material_properties: Dict = None) -> str:
        """
        Generate the sample density section.

        Args:
            material_properties: Dict with material properties

        Returns:
            str: Sample density line with density (g/cm3) and number density (atoms/barn)
        """
        if material_properties:
            from pleiades.utils.units import calculate_number_density

            density = material_properties.get("density_g_cm3", 9.0)
            thickness_mm = material_properties.get("thickness_mm", 5.0)
            atomic_mass = material_properties.get("atomic_mass_amu", 28.0)

            # Calculate number density (atoms/barn) - NOT physical thickness
            number_density = calculate_number_density(density, thickness_mm, atomic_mass)

            return f"  {density:8.6f} {number_density:.6e}"

        # Default values (matching reference format)
        return "  9.000000 1.797e-03"

    def generate_reaction_type_section(self) -> str:
        """
        Generate the reaction type section of the inp file.

        Returns:
            str: Reaction type or placeholder comment
        """
        if self.reaction_type:
            return self.reaction_type
        return "# PLACEHOLDER: Replace with reaction type (transmission, capture, fission, etc.)"

    def generate_isotope_section_proper(self, material_properties: Dict = None) -> str:
        """
        Generate isotope section using actual Card10 class.

        Args:
            material_properties: Dict with material properties including element info

        Returns:
            str: Properly formatted isotope line using Card10
        """
        from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
        from pleiades.nuclear.models import IsotopeParameters
        from pleiades.sammy.fitting.config import FitConfig
        from pleiades.sammy.io.card_formats.par10_isotopes import Card10
        from pleiades.utils.helper import VaryFlag

        if material_properties:
            # Create FitConfig and add isotope using Card10
            fit_config = FitConfig()

            # Create IsotopeInfo with proper mass_data
            element = material_properties.get("element", "Hf")
            mass_number = material_properties.get("mass_number", 177)
            atomic_mass = material_properties.get("atomic_mass_amu", 176.9432)

            # Create mass data
            mass_data = IsotopeMassData(
                atomic_mass=atomic_mass,
                mass_uncertainty=0.001,  # Default uncertainty
                binding_energy=0.0,  # Default
                beta_decay_energy=0.0,  # Default
            )

            isotope_info = IsotopeInfo(
                name=f"{element}-{mass_number}", element=element, mass_number=mass_number, mass_data=mass_data
            )

            # Create IsotopeParameters
            isotope_params = IsotopeParameters(
                isotope_information=isotope_info,
                abundance=material_properties.get("abundance", 1.0),
                uncertainty=0.00002,  # Default uncertainty
                vary_abundance=VaryFlag.NO,
            )

            # Add to fit_config
            fit_config.nuclear_params.isotopes.append(isotope_params)

            # Generate lines using Card10
            lines = Card10.to_lines(fit_config)

            # Return all data lines (skip header and empty lines)
            data_lines = [line for line in lines if not Card10.is_header_line(line) and line.strip()]
            if data_lines:
                return "\n".join(data_lines)

        # Fallback
        return "Hf177     176.9432  1.0000E+00 1.7500E+6"

    def generate_broadening_parameters_section(self, material_properties: Dict = None) -> str:
        """
        Generate broadening parameters section for multi-isotope mode.

        Args:
            material_properties: Dict with material properties for calculations

        Returns:
            str: Broadening parameters section
        """
        if material_properties:
            from pleiades.experimental.models import BroadeningParameters
            from pleiades.sammy.fitting.config import FitConfig
            from pleiades.sammy.io.card_formats.par04_broadening import Card04
            from pleiades.utils.helper import VaryFlag
            from pleiades.utils.units import calculate_number_density

            # Extract and validate material properties
            density = material_properties.get("density_g_cm3")
            thickness = material_properties.get("thickness_mm", 5.0)
            atomic_mass = material_properties.get("atomic_mass_amu")
            temperature = material_properties.get("temperature_K", 293.6)

            if density is None or atomic_mass is None:
                raise ValueError("material_properties must contain 'density_g_cm3' and 'atomic_mass_amu'")

            # Calculate number density
            number_density = calculate_number_density(density, thickness, atomic_mass)

            # Create FitConfig with broadening parameters using proper Card04
            fit_config = FitConfig()

            # Create BroadeningParameters object
            broadening_params = BroadeningParameters(
                crfn=8.0,  # Matching radius
                temp=temperature,  # Temperature
                thick=number_density,  # Calculated number density
                deltal=0.0,  # Flight path spread
                deltag=0.0,  # Gaussian resolution
                deltae=0.0,  # Exponential resolution
                flag_thick=VaryFlag.YES,  # Allow SAMMY to vary thickness
            )

            # Add to fit_config
            fit_config.physics_params.broadening_parameters = broadening_params

            # Generate proper Card04 output
            lines = Card04.to_lines(fit_config)
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
        from pleiades.sammy.parameters.misc import TzeroParameters
        from pleiades.utils.helper import VaryFlag

        # Create TzeroParameters with proper values
        # TZERO values (rounded uncertainties required - SAMMY cannot use zero uncertainty)
        tzero_params = TzeroParameters(
            t0_value=0.86000000,  # Time offset t₀ (μs)
            t0_uncertainty=0.00200000,  # Uncertainty on t₀ (μs)
            l0_value=1.0020000,  # L₀ value (dimensionless)
            l0_uncertainty=2.00000e-5,  # Uncertainty on L₀
            flight_path_length=flight_path_m,  # Flight path (m)
            t0_flag=VaryFlag.YES,  # Allow SAMMY to vary t₀
            l0_flag=VaryFlag.YES,  # Allow SAMMY to vary L₀
        )

        # Generate proper TZERO output with header
        lines = [
            "",  # Empty line
            "MISCEllaneous parameters follow",
        ] + tzero_params.to_lines()

        return "\n".join(lines)

    def generate_normalization_parameters_section(self) -> str:
        """
        Generate normalization parameters section.

        Returns:
            str: Normalization parameters section
        """
        from pleiades.experimental.models import NormalizationParameters
        from pleiades.sammy.fitting.config import FitConfig
        from pleiades.sammy.io.card_formats.par06_normalization import Card06
        from pleiades.utils.helper import VaryFlag

        # Create FitConfig with normalization parameters using proper Card06
        fit_config = FitConfig()

        # Create NormalizationParameters object
        # NORM values (non-zero uncertainties required - SAMMY cannot fit parameters with zero uncertainty)
        norm_params = NormalizationParameters(
            anorm=1.0,  # Normalization factor
            backa=0.01000000,  # Constant background
            backb=0.02000000,  # Background ∝ 1/E
            backc=0.00100000,  # Background ∝ √E
            backd=0.0,  # Exponential background coefficient
            backf=0.0,  # Exponential decay constant
            flag_anorm=VaryFlag.YES,  # Allow SAMMY to vary normalization
            flag_backa=VaryFlag.YES,  # Allow SAMMY to vary constant background
            flag_backb=VaryFlag.YES,  # Allow SAMMY to vary 1/E background
            flag_backc=VaryFlag.YES,  # Allow SAMMY to vary √E background
            flag_backd=VaryFlag.NO,  # Don't vary exponential coefficient
            flag_backf=VaryFlag.NO,  # Don't vary exponential constant
        )

        # Add to fit_config
        fit_config.physics_params.normalization_parameters = norm_params

        # Generate proper Card06 output
        lines = Card06.to_lines(fit_config)
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

    def generate_multi_isotope_inp_content(
        self, material_properties: Dict = None, resolution_file_path: Path = None
    ) -> str:
        """
        Generate complete multi-isotope INP content with parameter sections.

        Args:
            material_properties: Dict with material properties for parameter calculations
            resolution_file_path: Optional absolute path to resolution function file

        Returns:
            str: Complete multi-isotope INP file content
        """
        sections = [
            self.generate_title_section(),
            self.generate_isotope_section_proper(material_properties),
            "\n".join(self.generate_commands()),
            self.generate_physical_constants_section(material_properties),
            self.generate_sample_density_section(material_properties),
            self.generate_reaction_type_section(),
            self.generate_broadening_parameters_section(material_properties),
            self.generate_misc_parameters_section(),
            self.generate_normalization_parameters_section(),
            self.generate_resolution_function_section(
                str(resolution_file_path.resolve()) if resolution_file_path else "venus_resolution.dat"
            ),
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
    def create_multi_isotope_inp(
        cls, output_path: Path, title: str = None, material_properties: Dict = None, resolution_file_path: Path = None
    ) -> Path:
        """
        Create input file for multi-isotope JSON mode fitting.

        This method generates a complete INP file for multi-isotope fitting that includes
        both static alphanumeric commands and calculated parameter sections.

        Args:
            output_path: Path to write the input file
            title: Optional title for the inp file
            material_properties: Optional dict with material properties for parameter calculations
            resolution_file_path: Optional absolute path to resolution function file

        Returns:
            Path: Path to the created file
        """
        options = FitOptions.from_multi_isotope_config()
        manager = cls(options, title=title or "Multi-isotope JSON mode fitting", reaction_type="transmission")

        # Use specialized multi-isotope content generation
        try:
            content = manager.generate_multi_isotope_inp_content(material_properties, resolution_file_path)
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                f.write(content)

            logger.info(f"Successfully wrote multi-isotope SAMMY input file to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to write multi-isotope SAMMY input file: {str(e)}")
            raise
