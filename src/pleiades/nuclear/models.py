#!/usr/bin/env python
"""Core physical quantity models with validation."""

import math
import re
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator
from typing_extensions import Annotated

from pleiades.core.constants import CONSTANTS

NonNegativeFloat = Annotated[float, Field(ge=0)]
PositiveFloat = Annotated[float, Field(gt=0)]


class DataCategory(Enum):
    """Enumeration of valid data categories."""

    ISOTOPES = auto()
    RESONANCES = auto()
    CROSS_SECTIONS = auto()

    @classmethod
    def to_path(cls, category: "DataCategory") -> str:
        """Convert category enum to path string."""
        return category.name.lower()

class IsotopeMassData(BaseModel):
    model_config = ConfigDict(frozen=True)

    atomic_mass: float = Field(description="Mass in atomic mass units")
    mass_uncertainty: NonNegativeFloat
    binding_energy: Optional[float] = Field(description="Binding energy in MeV")
    beta_decay_energy: Optional[float] = Field(description="Beta decay energy in MeV")

class IsotopeInfo(BaseModel):
    """
    A class to represent information about an isotope.
    Attributes:
    -----------
    name : str
        The name of the isotope.
    atomic_number : int
        The atomic number of the isotope or number of protons (must be greater than 0).
    mass_number : int
        The mass number of the isotope or number of nuclei (must be greater than 0).
    element : str
        The symbol of the element.
    atomic_mass : float
        The atomic mass of the isotope (must be greater than or equal to 0).
    abundance : Optional[float]
        The natural abundance of the isotope (must be greater than or equal to 0, default is None).
    spin : Optional[float]
        The nuclear spin of the isotope (default is None).
    Methods:
    --------
    from_string(isotope_str: str) -> "IsotopeInfo":
        Class method to create an IsotopeInfo instance from a string in the format 'element-mass_number' or 'mass_number-element'.
    __str__() -> str:
        Convert the IsotopeInfo instance to a string in the format 'element-mass_number'.
    """

    name: str = Field(description="Isotope name")
    mass_number: int = Field(gt=0)
    element: str = Field(description="Element symbol")
    atomic_number: Optional[int] = Field(gt=0, default=None)
    mass_data: Optional[IsotopeMassData] = Field(description="Isotope mass data", default=None)
    abundance: Optional[float] = Field(ge=0, default=None)
    spin: Optional[float] = Field(default=None)
    
    @classmethod
    def from_string(cls, isotope_str: str) -> "IsotopeInfo":
        match = re.match(r"([A-Za-z]+)-?(\d+)|(\d+)-?([A-Za-z]+)", isotope_str)
        if not match:
            raise ValueError("Invalid isotope format")
        if match.group(1):
            element = match.group(1).capitalize()
            mass_number = int(match.group(2))
        else:
            element = match.group(4).capitalize()
            mass_number = int(match.group(3))
        name = f"{element}-{mass_number}"
        return cls(name=name, element=element, mass_number=mass_number)
    
    def __str__(self) -> str:
        """Convert to string format 'element-mass_number'."""
        return f"{self.element}-{self.mass_number}" 

class IsotopeIdentifier(BaseModel):
    model_config = ConfigDict(frozen=True)

    element: str = Field(pattern=r"^[A-Z][a-z]?$")
    mass_number: int = Field(gt=0)

    @classmethod
    def from_string(cls, isotope_str: str) -> "IsotopeIdentifier":
        match = re.match(r"([A-Za-z]+)-(\d+)", isotope_str)
        if not match:
            raise ValueError("Invalid isotope format")
        return cls(element=match.group(1).capitalize(), mass_number=int(match.group(2)))

    def __str__(self) -> str:
        """Convert to string format 'element-mass_number'."""
        return f"{self.element}-{self.mass_number}"


class CrossSectionPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    energy: NonNegativeFloat = Field(description="Energy in eV")
    cross_section: NonNegativeFloat = Field(description="Cross section in barns")


class UnitType(str, Enum):
    """Physical unit types with strict validation."""

    ENERGY = "energy"  # eV
    MASS = "mass"  # amu
    LENGTH = "length"  # m
    CROSS_SECTION = "cross"  # barns
    TIME = "time"  # s
    TEMPERATURE = "temp"  # K
    DIMENSIONLESS = "none"  # unitless

    @property
    def unit_symbol(self) -> str:
        """Get standard unit symbol."""
        return {
            "energy": "eV",
            "mass": "amu",
            "length": "m",
            "cross": "b",
            "time": "s",
            "temp": "K",
            "none": "",
        }[self.value]


class PhysicalQuantity(BaseModel):
    """Base model for physical quantities with validation."""

    model_config = ConfigDict(frozen=True)

    value: float = Field(description="Numerical value")
    unit_type: UnitType = Field(description="Physical unit type")

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        """Validate numerical value."""
        if math.isnan(v):
            raise ValueError("Value cannot be NaN")
        if math.isinf(v):
            raise ValueError("Value cannot be infinite")
        return v

    @computed_field
    @property
    def display_str(self) -> str:
        """String representation with units."""
        return f"{self.value} {self.unit_type.unit_symbol}"


class Energy(PhysicalQuantity):
    """Energy quantity with non-negative validation."""

    value: NonNegativeFloat
    unit_type: UnitType = Field(default=UnitType.ENERGY, frozen=True)

    # Class methods are not affected by Pydantic v2 changes
    @classmethod
    def from_MeV(cls, value: float) -> "Energy":  # noqa: N802
        """Convert from MeV to eV."""
        return cls(value=value * 1e6)

    @computed_field
    @property
    def MeV(self) -> float:  # noqa: N802
        """Energy value in MeV."""
        return self.value * 1e-6


class Mass(PhysicalQuantity):
    """Mass quantity with positive validation."""

    value: PositiveFloat
    unit_type: UnitType = Field(default=UnitType.MASS, frozen=True)

    @computed_field
    @property
    def kg(self) -> float:
        """Mass value in kilograms."""
        return self.value * CONSTANTS.amu_to_kg


class Temperature(PhysicalQuantity):
    """Temperature quantity with non-negative validation."""

    value: NonNegativeFloat
    unit_type: UnitType = Field(default=UnitType.TEMPERATURE, frozen=True)


class Isotope(BaseModel):
    """
    Represents an isotope with its physical properties and data.

    Migration source: simData.py Isotope class
    Changes made:
    - Converted from regular class to Pydantic model
    - Added proper type hints and validation
    - Made immutable with ConfigDict(frozen=True)
    - Added computed properties for derived values
    """

    model_config = ConfigDict(frozen=False)

    # Core properties
    identifier: IsotopeIdentifier
    atomic_mass: Mass
    thickness: NonNegativeFloat
    thickness_unit: str = Field(pattern=r"^(cm|mm|atoms/cm2)$")
    abundance: float = Field(ge=0.0)
    density: NonNegativeFloat
    density_unit: str = Field(default="g/cm3", pattern=r"^g/cm3$")

    # Data source tracking
    xs_file_location: Optional[Path] = None
    xs_data: List[CrossSectionPoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_units(self) -> "Isotope":
        """Validate unit compatibility."""
        valid_thickness_units = {"cm", "mm", "atoms/cm2"}
        if self.thickness_unit not in valid_thickness_units:
            raise ValueError(f"Invalid thickness unit. Must be one of: {valid_thickness_units}")
        if self.density_unit != "g/cm3":
            raise ValueError("Density must be in g/cm3")
        return self

    @classmethod
    def from_config(cls, config: dict) -> "Isotope":
        """
        Create an Isotope instance from configuration dictionary.

        Migration note: Replaces load_isotopes_from_config in simData.py
        """
        identifier = IsotopeIdentifier.from_string(config["name"])

        return cls(
            identifier=identifier,
            atomic_mass=Mass(value=config.get("atomic_mass", 0.0)),
            thickness=float(config.get("thickness", 0.0)),
            thickness_unit=config.get("thickness_unit", "cm"),
            abundance=float(config.get("abundance", 0.0)),
            density=float(config.get("density", 0.0)),
            density_unit=config.get("density_unit", "g/cm3"),
            xs_file_location=Path(config.get("xs_file_location", "")) if config.get("xs_file_location") else None,
        )

    @computed_field
    @property
    def areal_density(self) -> float:
        """
        Calculate areal density in atoms/barn.

        Migration note: Moved from simData.py create_transmission function
        """
        if self.thickness_unit == "atoms/cm2":
            return self.thickness * 1e-24  # Convert to atoms/barn

        thickness_cm = self.thickness
        if self.thickness_unit == "mm":
            thickness_cm /= 10.0

        return thickness_cm * self.density * CONSTANTS.avogadro_number / self.atomic_mass.value / 1e24  # Convert to atoms/barn


# Unit conversion functions
def eV_to_MeV(energy: Energy) -> float:  # noqa: N802
    """Convert energy from eV to MeV."""
    return energy.value * 1e-6


def MeV_to_eV(energy: float) -> Energy:  # noqa: N802
    """Convert energy from MeV to eV."""
    return Energy(value=energy * 1e6)


def barns_to_cm2(cross_section: float) -> float:
    """Convert cross section from barns to cm²."""
    return cross_section * CONSTANTS.barn_to_cm2


def cm2_to_barns(cross_section: float) -> float:
    """Convert cross section from cm² to barns."""
    return cross_section / CONSTANTS.barn_to_cm2
