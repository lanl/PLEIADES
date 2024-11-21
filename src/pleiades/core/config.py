#!/usr/bin/env python
"""Core configuration module for Pleiades."""

# core/config.py
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union, TypeVar, Type, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Annotated
from rich import print_json
from rich.tree import Tree
from rich.console import Console
import configparser
import json


T = TypeVar("T", bound="PLEIADESConfig")


class UnitSystem(str, Enum):
    """Units used in the system"""

    LENGTH_CM = "cm"
    LENGTH_MM = "mm"
    DENSITY_G_CM3 = "g/cm3"
    DENSITY_ATOMS_CM2 = "atoms/cm2"
    ENERGY_EV = "eV"


class SammyMethod(str, Enum):
    """SAMMY execution methods"""

    COMPILED = "compiled"
    DOCKER = "docker"


class VaryParam(BaseModel):
    """Parameter that can be varied in fitting"""

    value: Annotated[float, Field(description="Parameter value")]
    vary: Annotated[bool, Field(description="Whether to vary in fitting")] = False
    uncertainty: Annotated[
        Optional[float], Field(description="Parameter uncertainty")
    ] = None


class PathConfig(BaseModel):
    """Path configuration with validation"""

    working_dir: Annotated[Path, Field(description="Working directory")] = Path.cwd()

    data_dir: Annotated[Path, Field(description="Data directory")]

    sammy_fit_dir: Annotated[Path, Field(description="SAMMY fit directory")]

    archive_dir: Annotated[Path, Field(description="Archive directory")] = Field(
        default_factory=lambda: Path(".archive")
    )

    endf_dir: Annotated[Path, Field(description="ENDF data directory")] = Field(
        default_factory=lambda: Path("endf")
    )

    results_dir: Annotated[Path, Field(description="Results directory")] = Field(
        default_factory=lambda: Path("results")
    )

    @model_validator(mode="after")
    def create_directories(self) -> "PathConfig":
        """Ensure all directories exist"""
        for field, value in self.__dict__.items():
            if isinstance(value, Path):
                value.mkdir(parents=True, exist_ok=True)
        return self


class FileConfig(BaseModel):
    """File naming configuration"""

    data_file: Annotated[str, Field(description="Data file name")]
    input_file: Annotated[str, Field(description="Input file name")] = "input.inp"
    params_file: Annotated[str, Field(description="Parameter file name")] = "params.par"
    output_file: Annotated[str, Field(description="Output file name")] = "output.out"


class BroadeningConfig(BaseModel):
    """Broadening parameters configuration"""

    thickness: VaryParam
    temperature: VaryParam
    flight_path_spread: VaryParam
    deltag_fwhm: VaryParam
    deltae_us: VaryParam


class NormalizationConfig(BaseModel):
    """Normalization parameters configuration"""

    normalization: VaryParam = Field(default_factory=lambda: VaryParam(value=1.0))
    constant_bg: VaryParam = Field(default_factory=lambda: VaryParam(value=0.0))
    one_over_v_bg: VaryParam = Field(default_factory=lambda: VaryParam(value=0.0))
    sqrt_energy_bg: VaryParam = Field(default_factory=lambda: VaryParam(value=0.0))
    exponential_bg: VaryParam = Field(default_factory=lambda: VaryParam(value=0.0))
    exp_decay_bg: VaryParam = Field(default_factory=lambda: VaryParam(value=0.0))


class EnergyConfig(BaseModel):
    """Energy range configuration"""

    min: Annotated[float, Field(gt=0, description="Minimum energy")]
    max: Annotated[float, Field(gt=0, description="Maximum energy")]

    @model_validator(mode="after")
    def validate_range(self) -> "EnergyConfig":
        if self.min >= self.max:
            raise ValueError("min energy must be less than max energy")
        return self


class IsotopeConfig(BaseModel):
    """Isotope configuration"""

    name: Annotated[str, Field(description="Isotope name (e.g. U-238)")]
    abundance: VaryParam
    atomic_mass: Annotated[Optional[float], Field(description="Atomic mass")] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        import re

        if not re.match(r"^[A-Za-z]{1,2}-\d{1,3}$", v):
            raise ValueError(f"Invalid isotope name: {v}")
        return v


class SammyConfig(BaseModel):
    """SAMMY execution configuration"""

    method: Annotated[SammyMethod, Field(description="SAMMY execution method")] = (
        SammyMethod.COMPILED
    )

    command: Annotated[str, Field(description="SAMMY command")] = "sammy"

    run_name: Annotated[str, Field(description="Name for this run")]

    use_endf: Annotated[bool, Field(description="Use ENDF data")] = False

    fudge_factor: Annotated[
        float, Field(gt=0, description="Uncertainty scale factor")
    ] = 1.0


class TzeroConfig(BaseModel):
    """Time-zero configuration"""

    t0: VaryParam
    L0: VaryParam


class DeltaLConfig(BaseModel):
    """Delta-L configuration"""

    delta_L1: VaryParam
    delta_L0: VaryParam


class DeltaEConfig(BaseModel):
    """Delta-E configuration"""

    DE: VaryParam
    D0: VaryParam
    DlnE: VaryParam


class PLEIADESConfig(BaseModel):
    """Main PLEIADES configuration"""

    paths: PathConfig
    files: FileConfig
    sammy: SammyConfig
    isotopes: List[IsotopeConfig]
    energy: EnergyConfig
    resonances: Optional[EnergyConfig] = None
    broadening: BroadeningConfig
    normalization: NormalizationConfig
    flight_path_length: Annotated[float, Field(gt=0)]
    tzero: Optional[TzeroConfig] = None
    delta_L: Optional[DeltaLConfig] = None
    delta_E: Optional[DeltaEConfig] = None

    @classmethod
    def from_file(cls: Type[T], config_file: Union[str, Path]) -> T:
        """Load configuration from an INI file.

        Args:
            config_file: Path to configuration file

        Returns:
            PLEIADESConfig: Loaded configuration

        Raises:
            ValueError: If required sections are missing or invalid
        """
        config_file = Path(config_file)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        parser = configparser.ConfigParser()
        parser.read(config_file)

        # Convert configparser sections to dictionary
        config_dict = cls._parse_config_sections(parser)

        try:
            return cls(**config_dict)
        except Exception as e:
            raise ValueError(f"Failed to parse configuration file: {e}")

    @staticmethod
    def _parse_config_sections(parser: configparser.ConfigParser) -> Dict[str, Any]:
        """Parse configuration sections into a dictionary structure."""

        def safe_getfloat(
            section: str, option: str, fallback: Any = None
        ) -> Optional[float]:
            """Safely get float value, returning None for empty strings"""
            try:
                value = parser.get(section, option, fallback="")
                return float(value) if value else fallback
            except ValueError:
                return fallback

        config_dict = {
            "paths": {},
            "files": {},
            "sammy": {},
            "isotopes": [],
            "energy": {},
            "broadening": {},
            "normalization": {},
        }

        # Parse main/sammy section
        if "main" in parser:
            config_dict["sammy"].update(
                {
                    "method": parser.get("main", "sammy_run_method"),
                    "command": parser.get("main", "sammy_command", fallback="sammy"),
                    "run_name": parser.get(
                        "main", "sammy_fit_name", fallback="sammy_fit"
                    ),
                    "use_endf": parser.getboolean(
                        "main", "run_with_endf", fallback=False
                    ),
                    "fudge_factor": safe_getfloat("main", "fudge_factor", fallback=1.0),
                }
            )
            config_dict["flight_path_length"] = safe_getfloat(
                "main", "flight_path_length"
            )
            config_dict["energy"] = {
                "min": safe_getfloat("main", "fit_energy_min"),
                "max": safe_getfloat("main", "fit_energy_max"),
            }

        # Parse directories section
        if "directories" in parser:
            config_dict["paths"].update(
                {
                    "working_dir": parser.get(
                        "directories", "working_dir", fallback=str(Path.cwd())
                    ),
                    "data_dir": parser.get("directories", "data_dir"),
                    "sammy_fit_dir": parser.get("directories", "sammy_fit_dir"),
                    "archive_dir": parser.get(
                        "directories", "archive_dir", fallback=".archive"
                    ),
                    "endf_dir": parser.get("directories", "endf_dir", fallback="endf"),
                    "results_dir": parser.get(
                        "directories", "fit_results_dir", fallback="results"
                    ),
                }
            )

        # Parse filenames section
        if "filenames" in parser:
            config_dict["files"].update(
                {
                    "data_file": parser.get("filenames", "data_file_name"),
                    "input_file": parser.get(
                        "filenames", "input_file_name", fallback="input.inp"
                    ),
                    "params_file": parser.get(
                        "filenames", "params_file_name", fallback="params.par"
                    ),
                    "output_file": parser.get(
                        "filenames", "output_file_name", fallback="output.out"
                    ),
                }
            )

        # Parse isotopes section
        if "isotopes" in parser:
            names = parser.get("isotopes", "names").split(",")
            abundances = parser.get("isotopes", "abundances").split(",")
            vary_abundances = parser.get(
                "isotopes", "vary_abundances", fallback=""
            ).split(",")

            for name, abund, vary in zip(names, abundances, vary_abundances):
                config_dict["isotopes"].append(
                    {
                        "name": name.strip(),
                        "abundance": {
                            "value": float(abund.strip()),
                            "vary": vary.strip().lower() == "true",
                        },
                    }
                )

        # Parse broadening section
        if "broadening" in parser:
            config_dict["broadening"] = {
                param: {
                    "value": safe_getfloat("broadening", param),
                    "vary": parser.getboolean(
                        "broadening", f"vary_{param}", fallback=False
                    ),
                }
                for param in [
                    "thickness",
                    "temperature",
                    "flight_path_spread",
                    "deltag_fwhm",
                    "deltae_us",
                ]
            }

        # Parse normalization section
        if "normalization" in parser:
            config_dict["normalization"] = {
                param: {
                    "value": safe_getfloat("normalization", param),
                    "vary": parser.getboolean(
                        "normalization", f"vary_{param}", fallback=False
                    ),
                }
                for param in [
                    "normalization",
                    "constant_bg",
                    "one_over_v_bg",
                    "sqrt_energy_bg",
                    "exponential_bg",
                    "exp_decay_bg",
                ]
            }

        # Parse tzero section
        if "tzero" in parser:
            config_dict["tzero"] = {
                "t0": {
                    "value": safe_getfloat("tzero", "t0"),
                    "vary": parser.getboolean("tzero", "vary_t0", fallback=False),
                },
                "L0": {
                    "value": safe_getfloat("tzero", "L0"),
                    "vary": parser.getboolean("tzero", "vary_L0", fallback=False),
                },
            }

        # Parse delta_L section
        if "delta_L" in parser:
            config_dict["delta_L"] = {
                "delta_L1": {
                    "value": safe_getfloat("delta_L", "delta_L1"),
                    "vary": parser.getboolean(
                        "delta_L", "vary_delta_L1", fallback=False
                    ),
                    "uncertainty": safe_getfloat(
                        "delta_L", "delta_L1_err", fallback=None
                    ),
                },
                "delta_L0": {
                    "value": safe_getfloat("delta_L", "delta_L0"),
                    "vary": parser.getboolean(
                        "delta_L", "vary_delta_L0", fallback=False
                    ),
                    "uncertainty": safe_getfloat(
                        "delta_L", "delta_L0_err", fallback=None
                    ),
                },
            }

        # Parse delta_E section
        if "delta_E" in parser:
            config_dict["delta_E"] = {
                "DE": {
                    "value": safe_getfloat("delta_E", "DE"),
                    "vary": parser.getboolean("delta_E", "vary_DE", fallback=False),
                    "uncertainty": safe_getfloat("delta_E", "DE_err", fallback=None),
                },
                "D0": {
                    "value": safe_getfloat("delta_E", "D0"),
                    "vary": parser.getboolean("delta_E", "vary_D0", fallback=False),
                    "uncertainty": safe_getfloat("delta_E", "D0_err", fallback=None),
                },
                "DlnE": {
                    "value": safe_getfloat("delta_E", "DlnE"),
                    "vary": parser.getboolean("delta_E", "vary_DlnE", fallback=False),
                    "uncertainty": safe_getfloat("delta_E", "DlnE_err", fallback=None),
                },
            }

        # Parse resonances section
        if "resonances" in parser:
            config_dict["resonances"] = {
                "min": safe_getfloat("resonances", "resonance_energy_min"),
                "max": safe_getfloat("resonances", "resonance_energy_max"),
            }

        return config_dict

    def to_file(self, config_file: Union[str, Path]) -> None:
        """Save configuration to an INI file.

        Args:
            config_file: Path to save configuration file
        """
        config_file = Path(config_file)
        parser = configparser.ConfigParser()

        # Main section
        parser["main"] = {
            "sammy_run_method": self.sammy.method,
            "sammy_command": self.sammy.command,
            "sammy_fit_name": self.sammy.run_name,
            "run_with_endf": str(self.sammy.use_endf),
            "fudge_factor": str(self.sammy.fudge_factor),
            "flight_path_length": str(self.flight_path_length),
            "fit_energy_min": str(self.energy.min),
            "fit_energy_max": str(self.energy.max),
        }

        # Directories section
        parser["directories"] = {
            "working_dir": str(self.paths.working_dir),
            "data_dir": str(self.paths.data_dir),
            "sammy_fit_dir": str(self.paths.sammy_fit_dir),
            "archive_dir": str(self.paths.archive_dir),
            "endf_dir": str(self.paths.endf_dir),
            "fit_results_dir": str(self.paths.results_dir),
        }

        # Filenames section
        parser["filenames"] = {
            "data_file_name": self.files.data_file,
            "input_file_name": self.files.input_file,
            "params_file_name": self.files.params_file,
            "output_file_name": self.files.output_file,
        }

        # Isotopes section
        parser["isotopes"] = {
            "names": ",".join(iso.name for iso in self.isotopes),
            "abundances": ",".join(str(iso.abundance.value) for iso in self.isotopes),
            "vary_abundances": ",".join(
                str(iso.abundance.vary) for iso in self.isotopes
            ),
        }

        # Broadening section
        parser["broadening"] = {
            **{
                param: str(getattr(self.broadening, param).value)
                for param in [
                    "thickness",
                    "temperature",
                    "flight_path_spread",
                    "deltag_fwhm",
                    "deltae_us",
                ]
            },
            **{
                f"vary_{param}": str(getattr(self.broadening, param).vary)
                for param in [
                    "thickness",
                    "temperature",
                    "flight_path_spread",
                    "deltag_fwhm",
                    "deltae_us",
                ]
            },
        }

        # Normalization section
        parser["normalization"] = {
            **{
                param: str(getattr(self.normalization, param).value)
                for param in [
                    "normalization",
                    "constant_bg",
                    "one_over_v_bg",
                    "sqrt_energy_bg",
                    "exponential_bg",
                    "exp_decay_bg",
                ]
            },
            **{
                f"vary_{param}": str(getattr(self.normalization, param).vary)
                for param in [
                    "normalization",
                    "constant_bg",
                    "one_over_v_bg",
                    "sqrt_energy_bg",
                    "exponential_bg",
                    "exp_decay_bg",
                ]
            },
        }

        # Write to file
        with config_file.open("w") as f:
            parser.write(f)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return self.model_dump()

    @classmethod
    def from_json(cls: Type[T], json_file: Union[str, Path]) -> T:
        """Load configuration from a JSON file.

        Args:
            json_file: Path to JSON configuration file

        Returns:
            PLEIADESConfig: Loaded configuration

        Raises:
            FileNotFoundError: If JSON file doesn't exist
            ValueError: If JSON file is invalid or doesn't match schema
        """
        json_file = Path(json_file)
        if not json_file.exists():
            raise FileNotFoundError(f"JSON configuration file not found: {json_file}")

        try:
            with open(json_file) as f:
                data = json.load(f)

            # Convert any string paths back to Path objects
            if "paths" in data:
                for key, value in data["paths"].items():
                    if isinstance(value, str):
                        data["paths"][key] = Path(value)

            return cls.model_validate(data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse JSON configuration: {e}")

    def to_json(self, json_file: Union[str, Path]) -> None:
        """Save configuration to JSON file."""
        with open(json_file, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    def model_dump_json(self, **kwargs) -> str:
        """
        Get a JSON string representation of the model.
        Inherent to Pydantic, pretty printed by default.
        """
        return self.model_dump_json(indent=2, **kwargs)

    def print_tree(self) -> None:
        """
        Print the config as a tree structure using rich.
        """
        console = Console()
        tree = Tree("PLEIADESConfig")

        def add_to_tree(tree: Tree, data: Dict[str, Any]) -> None:
            for key, value in data.items():
                if isinstance(value, dict):
                    branch = tree.add(key)
                    add_to_tree(branch, value)
                elif isinstance(value, list):
                    branch = tree.add(key)
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            sub_branch = branch.add(f"[{i}]")
                            add_to_tree(sub_branch, item)
                        else:
                            branch.add(f"[{i}] {item}")
                else:
                    tree.add(f"{key}: {value}")

        add_to_tree(tree, self.model_dump())
        console.print(tree)

    def print_json(self) -> None:
        """
        Print the config as colored JSON using rich.
        """
        print_json(data=self.model_dump_json())

    def print_config(self, format: str = "tree") -> None:
        """
        Print the config in the specified format.

        Args:
            format: One of "tree", "json", or "plain"
        """
        if format == "tree":
            self.print_tree()
        elif format == "json":
            self.print_json()
        elif format == "plain":
            print(self.model_dump_json())
        else:
            raise ValueError(f"Unknown format: {format}")
