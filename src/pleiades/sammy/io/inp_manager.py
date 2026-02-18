"""
Module for managing SAMMY input (.inp) files.

This module provides the InpManager class to generate and write SAMMY input files
based on FitOptions configurations. It supports different modes (ENDF, fitting, custom)
through the refactored FitOptions class and its factory methods.
"""

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, get_args, get_origin

from pydantic import BaseModel, Field

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


class InpDatasetMetadata(BaseModel):
    """Optional typed dataset metadata used to seed INP generation.

    These values are dataset-level hints and should only be used when the
    corresponding value is not already provided in ``FitConfig``.
    """

    element: Optional[str] = Field(default=None, description="Element symbol (e.g. Au, Ta)")
    mass_number: Optional[int] = Field(default=None, description="Mass number for isotope name composition")
    atomic_mass_amu: Optional[float] = Field(default=None, description="Atomic mass (amu)")
    min_energy_eV: Optional[float] = Field(default=None, description="Minimum fit energy (eV)")
    max_energy_eV: Optional[float] = Field(default=None, description="Maximum fit energy (eV)")
    temperature_K: Optional[float] = Field(default=None, description="Sample temperature (K)")
    density_g_cm3: Optional[float] = Field(default=None, description="Material density (g/cm^3)")
    thickness_mm: Optional[float] = Field(default=None, description="Sample thickness (mm)")


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
        # Preserve legacy-safe defaults when FitConfig energy bounds are unset.
        min_energy = energy.min_energy if energy.min_energy is not None and energy.min_energy > 0 else 0.001
        max_energy = energy.max_energy if energy.max_energy is not None and energy.max_energy > 0 else 1000.0
        element_info = ElementInfo(
            element=self._element_name_from_fit_config(),
            atomic_weight=self._atomic_mass_from_fit_config(),
            min_energy=min_energy,
            max_energy=max_energy,
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

    def _number_density_from_dataset_metadata(self, dataset_metadata: Optional[InpDatasetMetadata]) -> Optional[float]:
        """Derive number density from typed dataset metadata.

        Number density derivation is all-or-nothing: if any of the required
        inputs are provided, all three must be present to avoid silently
        generating inconsistent values.
        """
        if dataset_metadata is None:
            return None

        density = dataset_metadata.density_g_cm3
        thickness = dataset_metadata.thickness_mm
        atomic_mass = dataset_metadata.atomic_mass_amu

        has_any_density_input = any(value is not None for value in (density, thickness, atomic_mass))
        if not has_any_density_input:
            return None
        if density is None or thickness is None or atomic_mass is None:
            raise ValueError(
                "dataset_metadata must include density_g_cm3, thickness_mm, and atomic_mass_amu to derive THICK"
            )

        from pleiades.utils.units import calculate_number_density

        return calculate_number_density(density, thickness, atomic_mass)

    def generate_physical_constants_section(self, dataset_metadata: Optional[InpDatasetMetadata] = None) -> str:
        """
        Generate Card Set 5 physical constants from FitConfig.

        Args:
            dataset_metadata: Optional typed metadata used only as a fallback
                source for temperature when FitConfig does not define one.

        Returns:
            str: Physical constants line
        """
        broadening = self.fit_config.physics_params.broadening_parameters

        temperature = broadening.temp
        if temperature is None and dataset_metadata is not None:
            temperature = dataset_metadata.temperature_K
        temperature = 293.6 if temperature is None else temperature

        flight_path = broadening.dist
        flight_path = 25.0 if flight_path is None else flight_path

        delta_l = broadening.deltal
        delta_l = 0.0 if delta_l is None else delta_l
        delta_g = broadening.deltag
        delta_g = 0.0 if delta_g is None else delta_g
        delta_e = broadening.deltae
        delta_e = 0.0 if delta_e is None else delta_e

        constants = PhysicalConstants(
            temperature=temperature,
            flight_path_length=flight_path,
            delta_l=delta_l,
            delta_g=delta_g,
            delta_e=delta_e,
        )

        lines = Card05.to_lines(constants)
        return "\n" + lines[0]

    def generate_card_7_section(self, dataset_metadata: Optional[InpDatasetMetadata] = None) -> str:
        """
        Generate Card Set 7 (CRFN, THICK) from FitConfig.

        Args:
            dataset_metadata: Optional typed metadata used to derive THICK when
                broadening.thick is not already defined in FitConfig.

        Returns:
            str: Card Set 7 line or empty string if unavailable
        """
        broadening = self.fit_config.physics_params.broadening_parameters
        crfn = broadening.crfn
        thick = broadening.thick
        if thick is None:
            thick = self._number_density_from_dataset_metadata(dataset_metadata)

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

    def generate_card_set_2_element_info(self, dataset_metadata: Optional[InpDatasetMetadata] = None) -> str:
        """
        Generate Card Set 2 (element information) according to SAMMY documentation.

        This generates the second line with element name, atomic weight, and energy range
        according to SAMMY Card Set 2 specification.

        Args:
            dataset_metadata: Optional typed metadata used to override selected
                Card 2 values after reading defaults from FitConfig.

        Returns:
            str: Properly formatted Card Set 2 element information line
        """
        element_info = self._element_info_from_fit_config()
        if dataset_metadata:
            if dataset_metadata.element:
                if dataset_metadata.mass_number is not None:
                    element_info.element = f"{dataset_metadata.element}{dataset_metadata.mass_number}"
                else:
                    element_info.element = dataset_metadata.element
            if dataset_metadata.atomic_mass_amu is not None:
                element_info.atomic_weight = dataset_metadata.atomic_mass_amu
            if dataset_metadata.min_energy_eV is not None:
                element_info.min_energy = dataset_metadata.min_energy_eV
            if dataset_metadata.max_energy_eV is not None:
                element_info.max_energy = dataset_metadata.max_energy_eV

        lines = Card02.to_lines(element_info)
        return lines[0]

    def generate_broadening_parameters_section(self, dataset_metadata: Optional[InpDatasetMetadata] = None) -> str:
        """
        Generate broadening parameters section from FitConfig.

        Args:
            dataset_metadata: Optional typed metadata used to fill temperature
                and derive THICK when these are not defined in FitConfig.

        Returns:
            str: Broadening parameters section with required blank line before it
        """
        from pleiades.sammy.fitting.config import FitConfig
        from pleiades.sammy.io.card_formats.par04_broadening import Card04
        from pleiades.utils.helper import VaryFlag

        broadening_params = self.fit_config.physics_params.broadening_parameters.model_copy(deep=True)

        if (
            broadening_params.temp is None
            and dataset_metadata is not None
            and dataset_metadata.temperature_K is not None
        ):
            broadening_params.temp = dataset_metadata.temperature_K

        if broadening_params.thick is None:
            derived_thick = self._number_density_from_dataset_metadata(dataset_metadata)
            if derived_thick is not None:
                broadening_params.thick = derived_thick
                broadening_params.flag_thick = VaryFlag.YES

        # Skip Card 4 generation when no primary broadening values exist.
        has_primary_broadening_values = any(
            value is not None
            for value in (
                broadening_params.crfn,
                broadening_params.temp,
                broadening_params.thick,
                broadening_params.deltal,
                broadening_params.deltag,
                broadening_params.deltae,
            )
        )
        if not has_primary_broadening_values:
            return ""

        fit_config = FitConfig()
        fit_config.physics_params.broadening_parameters = broadening_params
        lines = [""] + Card04.to_lines(fit_config)
        return "\n".join(lines)

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
        self,
        dataset_metadata: Optional[InpDatasetMetadata] = None,
        resolution_file_path: Path = None,
    ) -> str:
        """
        Generate complete multi-isotope INP content with parameter sections.

        Args:
            dataset_metadata: Optional typed metadata with dataset-level hints
            resolution_file_path: Optional absolute path to resolution function file

        Returns:
            str: Complete multi-isotope INP file content
        """
        broadening = self.fit_config.physics_params.broadening_parameters
        flight_path_m = broadening.dist if broadening.dist is not None else 25.0

        sections = [
            self.generate_title_section(),
            self.generate_card_set_2_element_info(dataset_metadata),
            "\n".join(self.generate_commands()),
            self.generate_physical_constants_section(dataset_metadata),
            self.generate_card_7_section(dataset_metadata),
            self.generate_reaction_type_section(),
            self.generate_broadening_parameters_section(dataset_metadata),
            self.generate_misc_parameters_section(flight_path_m=flight_path_m),
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
        cls,
        output_path: Path,
        fit_config: FitConfig,
        title: str = None,
        dataset_metadata: Optional[InpDatasetMetadata] = None,
        resolution_file_path: Path = None,
    ) -> Path:
        """
        Create input file for multi-isotope JSON mode fitting.

        This method generates a complete INP file for multi-isotope fitting that includes
        both static alphanumeric commands and calculated parameter sections.

        Args:
            output_path: Path to write the input file
            fit_config: Typed fit configuration used as the source of INP values
            title: Optional title for the inp file
            raise ValueError("fit_config is required and must be an instance of FitConfig")
                values (for example, Card 2 overrides or THICK derivation inputs)
            resolution_file_path: Optional absolute path to resolution function file

        Returns:
            Path: Path to the created file
        """
        if fit_config is None or not isinstance(fit_config, FitConfig):
            raise ValueError("fit_config must be an instance of FitConfig")

        options = FitOptions.from_multi_isotope_config()
        manager = cls(
            options=options,
            fit_config=fit_config,
            title=title or "Multi-isotope JSON mode fitting",
            reaction_type="transmission",
        )

        # Use specialized multi-isotope content generation
        try:
            content = manager.generate_multi_isotope_inp_content(dataset_metadata, resolution_file_path)
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                f.write(content)

            logger.info(f"Successfully wrote multi-isotope SAMMY input file to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to write multi-isotope SAMMY input file: {str(e)}")
            raise
