"""
Module for managing SAMMY input (.inp) files.

This module provides the InpManager class to generate and write SAMMY input files
based on FitOptions configurations. It supports different modes (ENDF, fitting, custom)
through the refactored FitOptions class and its factory methods.
"""

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, get_args, get_origin

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
from pleiades.nuclear.models import IsotopeParameters
from pleiades.sammy.data.options import DataTypeOptions
from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.fitting.options import FitOptions
from pleiades.sammy.io.card_formats.inp02_element import Card02, ElementInfo
from pleiades.sammy.io.card_formats.inp04_particlepairs import Card04
from pleiades.sammy.io.card_formats.inp05_broadening import Card05, PhysicalConstants
from pleiades.sammy.io.card_formats.inp07_density import Card07, Card07Parameters
from pleiades.sammy.io.card_formats.inp10_spingroups import Card10p2
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

# Default constants for SAMMY parameters
DEFAULT_DENSITY = 9.000000  # Default material density (g/cm³)
DEFAULT_NUMBER_DENSITY = 1.797e-03  # Default number density (atoms/barn-cm)

# TZERO default parameters
DEFAULT_T0_VALUE = 0.86000000  # Time offset t₀ (μs)
DEFAULT_T0_UNCERTAINTY = 0.00200000  # Uncertainty on t₀ (μs)
DEFAULT_L0_VALUE = 1.0020000  # L₀ value (dimensionless)
DEFAULT_L0_UNCERTAINTY = 2.00000e-5  # Uncertainty on L₀


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
        fit_config: FitConfig = None,
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
        self.fit_config = fit_config if fit_config else FitConfig()
        self._fit_config_provided = fit_config is not None

        self.options = options or (self.fit_config.options_and_routines if self._fit_config_provided else FitOptions())
        if self._fit_config_provided and options is not None:
            self.fit_config.options_and_routines = options

        if title is None and self._fit_config_provided:
            title = self.fit_config.fit_title
        self.title = title

        self.isotope_info = isotope_info
        self.physical_constants = physical_constants

        if reaction_type is None and self._fit_config_provided:
            reaction_type = self.fit_config.data_params.data_type.value
        self.reaction_type = reaction_type

    def set_options(self, options: FitOptions) -> None:
        """
        Set FitOptions after initialization.

        Args:
            options: FitOptions instance to use
        """
        self.options = options
        if self._fit_config_provided:
            self.fit_config.options_and_routines = options

    @staticmethod
    def _normalize_command(command: str) -> str:
        return " ".join(command.upper().split())

    @staticmethod
    def _option_class_for_field(field_info) -> Optional[type]:
        annotation = field_info.annotation
        origin = get_origin(annotation)
        if origin is Union:
            args = [arg for arg in get_args(annotation) if arg is not type(None)]  # noqa: E721
            return args[0] if args else None
        return annotation

    @classmethod
    @lru_cache
    def _alphanumeric_command_map(cls) -> Dict[str, Tuple[str, str]]:
        mapping: Dict[str, Tuple[str, str]] = {}

        for section_name, field_info in FitOptions.model_fields.items():
            option_class = cls._option_class_for_field(field_info)
            if option_class is None or not hasattr(option_class, "get_alphanumeric_commands"):
                continue

            bool_fields = {name: field for name, field in option_class.model_fields.items() if field.annotation is bool}

            for field_name in bool_fields:
                data = {name: False for name in bool_fields}
                data[field_name] = True
                try:
                    instance = option_class(**data)
                except Exception:
                    continue
                for command in instance.get_alphanumeric_commands():
                    normalized = cls._normalize_command(command)
                    mapping[normalized] = (section_name, field_name)

        return mapping

    def _apply_alphanumeric_commands(self, commands: List[str]) -> None:
        if not commands:
            return

        command_map = self._alphanumeric_command_map()
        aliases = {
            "CSISRS": "USE CSISRS FORMAT FOR DATA",
            "TWENTY": "USE TWENTY SIGNIFICANT DIGITS",
            "GENERATE ODF FILE AUTOMATICALLY": "GENERATE PLOT FILE AUTOMATICALLY",
            "DO NOT SUPPRESS ANY INTERMEDIATE RESULTS": "DO NOT SUPPRESS ANY INTERMEDIATE PRINTOUT",
        }
        sections: Dict[str, Dict[str, bool]] = {}
        unknown = []

        for command in commands:
            normalized = self._normalize_command(command)
            if normalized in aliases:
                normalized = self._normalize_command(aliases[normalized])
            if normalized in command_map:
                section_name, field_name = command_map[normalized]
                sections.setdefault(section_name, {})[field_name] = True
            else:
                unknown.append(command)

        if unknown:
            logger.warning(f"Unmapped alphanumeric commands: {unknown}")

        options = FitOptions()
        for section_name, fields in sections.items():
            field_info = FitOptions.model_fields[section_name]
            option_class = self._option_class_for_field(field_info)
            if option_class is None:
                continue
            try:
                section_instance = option_class(**fields)
            except Exception as exc:
                logger.warning(f"Failed to parse commands for {section_name}: {exc}")
                continue
            setattr(options, section_name, section_instance)

        self.fit_config.options_and_routines = options
        self.options = options

    def _element_name_from_fit_config(self) -> str:
        isotopes = self.fit_config.nuclear_params.isotopes
        if not isotopes:
            return "Sample"

        isotope = isotopes[0]
        info = isotope.isotope_information
        if info and info.element and info.mass_number:
            return f"{info.element}{info.mass_number}"
        if info and info.name:
            return info.name.replace("-", "")
        return "Sample"

    def _atomic_mass_from_fit_config(self) -> float:
        isotopes = self.fit_config.nuclear_params.isotopes
        if not isotopes:
            return 1.0

        info = isotopes[0].isotope_information
        if info and info.mass_data and info.mass_data.atomic_mass:
            return info.mass_data.atomic_mass
        if info and info.mass_number:
            return float(info.mass_number)
        return 1.0

    @staticmethod
    def _isotope_info_from_element(element_info: ElementInfo) -> IsotopeInfo:
        raw = element_info.element.strip()
        letters = "".join(ch for ch in raw if ch.isalpha())
        digits = "".join(ch for ch in raw if ch.isdigit())
        info = None

        if letters and digits:
            try:
                info = IsotopeInfo.from_string(f"{letters}-{digits}")
            except ValueError:
                info = None

        if info is None and letters:
            info = IsotopeInfo(name=raw or letters, element=letters)
            if digits:
                info.mass_number = int(digits)

        if info is None:
            info = IsotopeInfo(name=raw or "UNK", element=letters or None)
            if digits:
                info.mass_number = int(digits)

        if element_info.atomic_weight is not None:
            info.mass_data = IsotopeMassData(atomic_mass=element_info.atomic_weight)

        return info

    def _element_info_from_fit_config(self) -> ElementInfo:
        energy = self.fit_config.physics_params.energy_parameters
        element_info = ElementInfo(
            element=self._element_name_from_fit_config(),
            atomic_weight=self._atomic_mass_from_fit_config(),
            min_energy=energy.min_energy,
            max_energy=energy.max_energy,
            nepnts=energy.number_of_energy_points,
            itmax=self.fit_config.max_iterations,
            icorr=self.fit_config.i_correlation,
            nxtra=energy.number_of_extra_points,
            iptdop=self.fit_config.iptdop,
            iptwid=self.fit_config.iptwid,
            ixxchn=self.fit_config.ixxchn,
            ndigit=self.fit_config.ndigit,
            idropp=self.fit_config.idropp,
            matnum=self.fit_config.matnum,
        )
        return element_info

    def _element_info_from_dict(self, isotope_info: Dict) -> ElementInfo:
        element = isotope_info.get("element", "Sample")
        atomic_mass = isotope_info.get("atomic_mass_amu", 1.0)
        min_energy = isotope_info.get("min_energy_eV", 0.001)
        max_energy = isotope_info.get("max_energy_eV", 1000.0)

        return ElementInfo(
            element=element,
            atomic_weight=atomic_mass,
            min_energy=min_energy,
            max_energy=max_energy,
            nepnts=isotope_info.get("nepnts", isotope_info.get("number_of_energy_points")),
            itmax=isotope_info.get("itmax", isotope_info.get("max_iterations")),
            icorr=isotope_info.get("icorr", isotope_info.get("i_correlation")),
            nxtra=isotope_info.get("nxtra", isotope_info.get("number_of_extra_points")),
            iptdop=isotope_info.get("iptdop"),
            iptwid=isotope_info.get("iptwid"),
            ixxchn=isotope_info.get("ixxchn"),
            ndigit=isotope_info.get("ndigit"),
            idropp=isotope_info.get("idropp"),
            matnum=isotope_info.get("matnum"),
        )

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
            str: Title line (defaults to "SAMMY analysis" if not provided)
        """
        if self.title:
            return self.title
        return "SAMMY analysis"

    def generate_isotope_section(self) -> str:
        """
        Generate the isotope information section of the inp file using Card Set 2 format.

        Returns:
            str: Properly formatted Card Set 2 element information line
        """
        if self.isotope_info:
            element_info = self._element_info_from_dict(self.isotope_info)
        elif self._fit_config_provided:
            element_info = self._element_info_from_fit_config()
        else:
            element_info = ElementInfo(
                element="Sample",
                atomic_weight=1.0,
                min_energy=0.001,
                max_energy=1000.0,
            )

        lines = Card02.to_lines(element_info)
        return lines[0]

    def generate_physical_constants_section(self, material_properties: Dict = None) -> str:
        """
        Generate the physical constants section for multi-isotope mode.

        Args:
            material_properties: Dict with material properties

        Returns:
            str: Physical constants line
        """
        if material_properties is None and self.physical_constants:
            material_properties = self.physical_constants

        if material_properties is None and self._fit_config_provided:
            broadening = self.fit_config.physics_params.broadening_parameters
            material_properties = {
                "temperature_K": broadening.temp,
                "flight_path_m": broadening.dist,
                "delta_l": broadening.deltal,
                "delta_g": broadening.deltag,
                "delta_e": broadening.deltae,
            }
            material_properties = {key: value for key, value in material_properties.items() if value is not None}

        if material_properties:
            temperature = material_properties.get("temperature_K")
            if temperature is None:
                temperature = material_properties.get("temperature")
            if temperature is None:
                temperature = 293.6

            flight_path = material_properties.get("flight_path_m")
            if flight_path is None:
                flight_path = material_properties.get("flight_path")
            if flight_path is None:
                flight_path = 25.0

            delta_l = material_properties.get("delta_l", 0.0)
            delta_g = material_properties.get("delta_g", 0.0)
            delta_e = material_properties.get("delta_e", 0.0)

            constants = PhysicalConstants(
                temperature=temperature,
                flight_path_length=flight_path,
                delta_l=delta_l,
                delta_g=delta_g,
                delta_e=delta_e,
            )
        else:
            constants = PhysicalConstants(
                temperature=293.6,
                flight_path_length=25.0,
                delta_l=0.0,
                delta_g=0.0,
                delta_e=0.0,
            )

        lines = Card05.to_lines(constants)
        return "\n" + lines[0]

    def generate_card_7_section(self, material_properties: Dict = None) -> str:
        """
        Generate the Card Set 7 section (CRFN, THICK).

        Args:
            material_properties: Dict with material properties

        Returns:
            str: Card Set 7 line or empty string if unavailable
        """
        crfn = None
        thick = None

        if material_properties:
            crfn = material_properties.get("crfn")
            thick = material_properties.get("thick")

            if thick is None:
                density = material_properties.get("density_g_cm3")
                thickness_mm = material_properties.get("thickness_mm")
                atomic_mass = material_properties.get("atomic_mass_amu")
                if density is not None and thickness_mm is not None and atomic_mass is not None:
                    from pleiades.utils.units import calculate_number_density

                    thick = calculate_number_density(density, thickness_mm, atomic_mass)

        if crfn is None or thick is None:
            broadening = self.fit_config.physics_params.broadening_parameters
            crfn = broadening.crfn if crfn is None else crfn
            thick = broadening.thick if thick is None else thick

        if crfn is None or thick is None:
            return ""

        params = Card07Parameters(crfn=crfn, thick=thick)
        lines = Card07.to_lines(params)
        return lines[0]

    def generate_reaction_type_section(self) -> str:
        """
        Generate the reaction type section of the inp file.

        Returns:
            str: Reaction type (defaults to "transmission" if not provided)
        """
        if self.reaction_type:
            return self.reaction_type
        return "transmission"

    def generate_card_set_2_element_info(self, material_properties: Dict = None) -> str:
        """
        Generate Card Set 2 (element information) according to SAMMY documentation.

        This generates the second line with element name, atomic weight, and energy range
        according to SAMMY Card Set 2 specification.

        Args:
            material_properties: Dict with material properties including element info

        Returns:
            str: Properly formatted Card Set 2 element information line
        """
        if material_properties:
            element = material_properties.get("element", "Au")
            mass_number = material_properties.get("mass_number")
            atomic_mass = material_properties.get("atomic_mass_amu", 196.966569)
            min_energy = material_properties.get("min_energy_eV", 0.001)
            max_energy = material_properties.get("max_energy_eV", 1000.0)

            if mass_number is not None:
                element_name = f"{element}{mass_number}"
            else:
                element_name = element

            element_info = ElementInfo(
                element=element_name,
                atomic_weight=atomic_mass,
                min_energy=min_energy,
                max_energy=max_energy,
                nepnts=material_properties.get("nepnts", material_properties.get("number_of_energy_points")),
                itmax=material_properties.get("itmax", material_properties.get("max_iterations")),
                icorr=material_properties.get("icorr", material_properties.get("i_correlation")),
                nxtra=material_properties.get("nxtra", material_properties.get("number_of_extra_points")),
                iptdop=material_properties.get("iptdop", self.fit_config.iptdop if self._fit_config_provided else None),
                iptwid=material_properties.get("iptwid", self.fit_config.iptwid if self._fit_config_provided else None),
                ixxchn=material_properties.get("ixxchn", self.fit_config.ixxchn if self._fit_config_provided else None),
                ndigit=material_properties.get("ndigit", self.fit_config.ndigit if self._fit_config_provided else None),
                idropp=material_properties.get("idropp", self.fit_config.idropp if self._fit_config_provided else None),
                matnum=material_properties.get("matnum", self.fit_config.matnum if self._fit_config_provided else None),
            )
        elif self._fit_config_provided:
            element_info = self._element_info_from_fit_config()
        else:
            element_info = ElementInfo(
                element="Au197",
                atomic_weight=196.96657,
                min_energy=0.001,
                max_energy=1000.0,
            )

        lines = Card02.to_lines(element_info)
        return lines[0]

    def generate_broadening_parameters_section(self, material_properties: Dict = None) -> str:
        """
        Generate broadening parameters section for multi-isotope mode.

        Args:
            material_properties: Dict with material properties for calculations

        Returns:
            str: Broadening parameters section with required blank line before it
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

            # Generate proper Card04 output with required blank line before it
            lines = [""] + Card04.to_lines(fit_config)  # Add blank line before broadening section
            return "\n".join(lines)

        return ""  # Return empty string when no broadening parameters

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
            t0_value=DEFAULT_T0_VALUE,  # Time offset t₀ (μs)
            t0_uncertainty=DEFAULT_T0_UNCERTAINTY,  # Uncertainty on t₀ (μs)
            l0_value=DEFAULT_L0_VALUE,  # L₀ value (dimensionless)
            l0_uncertainty=DEFAULT_L0_UNCERTAINTY,  # Uncertainty on L₀
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
            str: Normalization parameters section with required blank line before it
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

        # Generate proper Card06 output with required blank line before it
        lines = [""] + Card06.to_lines(fit_config)  # Add blank line before normalization section
        return "\n".join(lines)

    def generate_resolution_function_section(self, resolution_file: str = "venus_resolution.dat") -> str:
        """
        Generate user-defined resolution function section.

        Args:
            resolution_file: Name of resolution function file, or None to disable

        Returns:
            str: Resolution function section or empty string if disabled
        """
        if resolution_file is None:
            return ""

        from pleiades.sammy.parameters.user_resolution import UserResolutionParameters

        user_res = UserResolutionParameters(filenames=[resolution_file])
        lines = user_res.to_lines()

        return "\n" + "\n".join(lines)

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
            self.generate_card_set_2_element_info(material_properties),  # Use Card Set 2 for element info
            "\n".join(self.generate_commands()),
            self.generate_physical_constants_section(material_properties),
            self.generate_card_7_section(material_properties),
            self.generate_reaction_type_section(),
            self.generate_broadening_parameters_section(material_properties),
            self.generate_misc_parameters_section(),
            self.generate_normalization_parameters_section(),
            self.generate_resolution_function_section(
                str(resolution_file_path.resolve()) if resolution_file_path else None
            ),
        ]
        return "\n".join(sections)

    def generate_inp_content(self) -> str:
        """
        Generate full content for SAMMY input file.

        Returns:
            str: Complete content for SAMMY input file
        """
        card_7 = self.generate_card_7_section()
        sections = [
            self.generate_title_section(),
            self.generate_isotope_section(),
            "\n".join(self.generate_commands()),
            "",  # Empty line for readability
            self.generate_physical_constants_section(),
        ]
        if card_7:
            sections.append(card_7)
        sections.append(self.generate_reaction_type_section())
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

    def read_inp_file(self, file_path: Path, fit_config: FitConfig = None) -> FitConfig:
        """
        Read a SAMMY input file and populate a FitConfig instance.

        Args:
            file_path: Path to the input file
            fit_config: Optional FitConfig to populate

        Returns:
            FitConfig: Populated FitConfig instance
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        target_config = fit_config if fit_config else self.fit_config
        if target_config is None or not isinstance(target_config, FitConfig):
            raise ValueError("fit_config must be an instance of FitConfig")

        self.fit_config = target_config
        self._fit_config_provided = True

        lines = [line.rstrip("\n") for line in file_path.read_text().splitlines()]
        idx = 0

        def next_nonempty(start: int) -> int:
            while start < len(lines) and not lines[start].strip():
                start += 1
            return start

        def is_numeric_line(line: str) -> bool:
            parts = line.split()
            if not parts:
                return False
            for part in parts:
                try:
                    float(part)
                except ValueError:
                    return False
            return True

        def parse_reaction_type(line: str) -> Optional[DataTypeOptions]:
            candidate = line.strip().upper()
            for option in DataTypeOptions:
                if candidate == option.value.upper():
                    return option
            return None

        # Title line
        idx = next_nonempty(idx)
        if idx >= len(lines):
            raise ValueError("Input file is empty")
        self.fit_config.fit_title = lines[idx].strip()
        idx += 1

        # Card Set 2 element line
        idx = next_nonempty(idx)
        if idx >= len(lines):
            raise ValueError("Missing Card Set 2 element line")
        element_info = Card02.from_lines([lines[idx]])
        idx += 1

        if not self.fit_config.nuclear_params.isotopes:
            isotope_info = self._isotope_info_from_element(element_info)
            self.fit_config.nuclear_params.isotopes.append(IsotopeParameters(isotope_information=isotope_info))

        energy = self.fit_config.physics_params.energy_parameters
        energy.min_energy = element_info.min_energy
        energy.max_energy = element_info.max_energy
        if element_info.nepnts is not None:
            energy.number_of_energy_points = element_info.nepnts
        if element_info.nxtra is not None:
            energy.number_of_extra_points = element_info.nxtra
        if element_info.itmax is not None:
            self.fit_config.max_iterations = element_info.itmax
        if element_info.icorr is not None:
            self.fit_config.i_correlation = element_info.icorr

        self.fit_config.iptdop = element_info.iptdop
        self.fit_config.iptwid = element_info.iptwid
        self.fit_config.ixxchn = element_info.ixxchn
        self.fit_config.ndigit = element_info.ndigit
        self.fit_config.idropp = element_info.idropp
        self.fit_config.matnum = element_info.matnum

        # Alphanumeric command lines
        commands = []
        while idx < len(lines):
            line = lines[idx].strip()
            if not line:
                idx += 1
                continue
            if line.startswith("#") or set(line) == {"-"}:
                idx += 1
                continue
            if is_numeric_line(line):
                break
            commands.append(lines[idx])
            idx += 1
        self._apply_alphanumeric_commands(commands)

        # Physical constants line
        if idx < len(lines) and is_numeric_line(lines[idx]):
            try:
                constants = Card05.from_lines([lines[idx]])
                broadening = self.fit_config.physics_params.broadening_parameters
                broadening.temp = constants.temperature
                broadening.dist = constants.flight_path_length
                broadening.deltal = constants.delta_l
                broadening.deltag = constants.delta_g
                broadening.deltae = constants.delta_e
            except ValueError:
                logger.warning("Failed to parse Card Set 5 constants line")
            idx += 1

        # Card Set 7 line (CRFN, THICK)
        idx = next_nonempty(idx)
        if idx < len(lines) and is_numeric_line(lines[idx]):
            try:
                card_7 = Card07.from_lines([lines[idx]])
                broadening = self.fit_config.physics_params.broadening_parameters
                broadening.crfn = card_7.crfn
                broadening.thick = card_7.thick
            except ValueError:
                logger.warning("Failed to parse Card Set 7 line")
            idx += 1

        # Reaction type line
        idx = next_nonempty(idx)
        if idx < len(lines):
            reaction_type = parse_reaction_type(lines[idx])
            if reaction_type:
                self.fit_config.data_params.data_type = reaction_type
                idx += 1

        # Particle pair definitions (Card 4)
        remaining_lines = lines[idx:]
        skip_indices = set()
        for line_idx, line in enumerate(remaining_lines):
            if Card04.is_header_line(line):
                block_indices = [line_idx]
                cursor = line_idx + 1
                while cursor < len(remaining_lines) and remaining_lines[cursor].strip():
                    block_indices.append(cursor)
                    cursor += 1
                skip_indices.update(block_indices)
                block = [remaining_lines[i] for i in block_indices]
                try:
                    Card04.from_lines(block, self.fit_config)
                except ValueError:
                    logger.warning("Failed to parse particle pair definitions from input file")

        # Spin group lines
        spin_group_lines = [line for i, line in enumerate(remaining_lines) if line.strip() and i not in skip_indices]
        if spin_group_lines:
            try:
                Card10p2.from_lines(spin_group_lines, self.fit_config)
            except ValueError:
                logger.warning("Failed to parse spin group lines from input file")

        return self.fit_config

    @classmethod
    def from_fit_config(
        cls,
        fit_config: FitConfig,
        isotope_info: Optional[Dict] = None,
        physical_constants: Optional[Dict] = None,
        reaction_type: Optional[str] = None,
        options: Optional[FitOptions] = None,
        title: Optional[str] = None,
    ) -> "InpManager":
        """
        Create an InpManager instance backed by a FitConfig.

        Args:
            fit_config: FitConfig object to read defaults from
            isotope_info: Optional dict to override Card Set 2 element info
            physical_constants: Optional dict to override Card Set 5 constants
            reaction_type: Optional reaction type override
            options: Optional FitOptions override
            title: Optional title override
        """
        if fit_config is None or not isinstance(fit_config, FitConfig):
            raise ValueError("fit_config must be an instance of FitConfig")

        return cls(
            fit_config=fit_config,
            isotope_info=isotope_info,
            physical_constants=physical_constants,
            reaction_type=reaction_type,
            options=options,
            title=title,
        )

    @classmethod
    def parse_inp_file(cls, file_path: Path, fit_config: FitConfig = None) -> FitConfig:
        """
        Parse an input file into a FitConfig instance.

        Args:
            file_path: Path to the input file
            fit_config: Optional FitConfig to populate

        Returns:
            FitConfig: Populated FitConfig
        """
        manager = cls(fit_config=fit_config if fit_config else FitConfig())
        return manager.read_inp_file(file_path, manager.fit_config)

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
