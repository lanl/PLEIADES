#!/usr/bin/env python
"""Physical constants with validation."""

from pydantic import BaseModel, ConfigDict, Field, computed_field


class PhysicalConstants(BaseModel):
    """Physical constants used in nuclear calculations."""

    model_config = ConfigDict(frozen=True)

    # Particle masses (use floats instead of Mass objects)
    neutron_mass_amu: float = Field(default=1.008664915, description="Neutron mass in amu")
    proton_mass_amu: float = Field(default=1.007276466, description="Proton mass in amu")
    electron_mass_amu: float = Field(default=0.000548579909, description="Electron mass in amu")

    # Fundamental constants
    speed_of_light: float = Field(default=299792458.0, description="Speed of light in m/s")
    planck_constant: float = Field(default=4.135667696e-15, description="Planck constant in eV⋅s")
    boltzmann_constant: float = Field(default=8.617333262e-5, description="Boltzmann constant in eV/K")
    elementary_charge: float = Field(default=1.602176634e-19, description="Elementary charge in Coulombs")
    avogadro_number: float = Field(default=6.02214076e23, description="Avogadro's number in mol^-1")

    # Nuclear physics constants
    barn_to_cm2: float = Field(default=1e-24, description="Conversion factor from barns to cm²")
    amu_to_kg: float = Field(default=1.660539067e-27, description="Conversion factor from amu to kg")

    # Derived constants
    @computed_field
    @property
    def neutron_mass_kg(self) -> float:
        """Neutron mass in kilograms."""
        return self.neutron_mass_amu * self.amu_to_kg

    @computed_field
    @property
    def atomic_mass_unit_eV(self) -> float:  # noqa: N802
        """One atomic mass unit in eV/c²."""
        return 931.494061e6  # MeV/c² to eV/c²


# Create singleton instance
CONSTANTS = PhysicalConstants()
