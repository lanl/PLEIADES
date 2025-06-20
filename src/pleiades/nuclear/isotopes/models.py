"""
This module provides models and enumerations for representing isotopic data,
including isotope information, mass data, and associated nuclear data libraries.
It is part of the PLEIADES project and is designed to facilitate the handling
and processing of nuclear isotopic information.
Classes:
1. FileCategory:
    - Enumeration of valid categories for isotopic files.
    - Includes a method to convert category enums to path strings.
2. EndfLibrary:
    - Enumeration of supported nuclear data libraries (e.g., ENDF, JEFF, JENDL).
3. IsotopeMassData:
    - A Pydantic model representing mass-related data for isotopes.
    - Includes attributes for atomic mass, mass uncertainty, binding energy, and beta decay energy.
4. IsotopeInfo:
    - A Pydantic model representing detailed information about an isotope.
    - Includes attributes for name, atomic number, mass number, element symbol, atomic mass, abundance,
      spin, material number, and associated ENDF library.
    - Provides methods for creating an instance from a string and converting an instance to a string.
Usage:
------
This library is intended for use in nuclear isotope data processing for R-matrix applications where
isotopes need to be represented, validated, and processed in a structured manner.
"""

import re
from enum import Enum, auto
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated

NonNegativeFloat = Annotated[float, Field(ge=0)]
PositiveFloat = Annotated[float, Field(gt=0)]


class FileCategory(Enum):
    """Enumeration of valid categories."""

    ISOTOPES = auto()

    @classmethod
    def to_path(cls, category: "FileCategory") -> str:
        """Convert category enum to path string."""
        return category.name.lower()


class IsotopeMassData(BaseModel):
    model_config = ConfigDict(frozen=True)

    atomic_mass: Optional[float] = Field(default=None, description="Mass in atomic mass units")
    mass_uncertainty: Optional[NonNegativeFloat] = Field(default=None)
    binding_energy: Optional[float] = Field(default=None, description="Binding energy in MeV")
    beta_decay_energy: Optional[float] = Field(default=None, description="Beta decay energy in MeV")


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

    name: Optional[str] = Field(default=None, description="Isotope name")
    mass_number: Optional[int] = Field(default=None, ge=0)
    element: Optional[str] = Field(default=None, description="Element symbol")
    atomic_number: Optional[int] = Field(default=None, ge=0)
    mass_data: Optional[IsotopeMassData] = Field(default=None, description="Isotope mass data")
    abundance: Optional[float] = Field(default=None, ge=0)
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
