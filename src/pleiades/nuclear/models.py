#!/usr/bin/env python
"""Core physical quantity models with validation."""

import re
from enum import Enum, auto
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated

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
    material_number: Optional[int] = Field(default=None)

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
