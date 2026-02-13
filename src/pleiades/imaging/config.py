"""
Configuration models for 2D resonance imaging.

This module defines configuration structures for batch SAMMY fitting,
including material properties and imaging parameters.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ImagingConfig(BaseModel):
    """Configuration for 2D resonance imaging workflow.

    Contains all parameters needed for batch SAMMY fitting across pixels,
    including isotopes, material properties, and energy range.

    Attributes:
        isotopes: List of isotope names (e.g., ["Ta-181"], ["Hf-174", "Hf-176", ...])
        element: Chemical symbol (e.g., "Ta", "Hf", "W")
        mass_number: Mass number of primary isotope
        density_g_cm3: Sample density in g/cm³
        thickness_mm: Sample thickness in mm
        atomic_mass_amu: Atomic mass in amu
        abundance: Fractional abundance (0-1)
        min_energy_eV: Minimum energy in eV
        max_energy_eV: Maximum energy in eV
        temperature_K: Sample temperature in Kelvin
        natural_abundances: If True, use natural abundances; if False, use custom abundances
        custom_abundances: Custom abundance values (must match len(isotopes))
    """

    # Isotopes
    isotopes: List[str] = Field(..., min_length=1, description="List of isotope names (e.g., ['Ta-181'])")

    # Material properties
    element: str = Field(..., description="Chemical symbol (e.g., 'Ta', 'Hf')")
    mass_number: int = Field(..., gt=0, description="Mass number")
    density_g_cm3: float = Field(..., gt=0, description="Density in g/cm³")
    thickness_mm: float = Field(..., gt=0, description="Thickness in mm")
    atomic_mass_amu: float = Field(..., gt=0, description="Atomic mass in amu")

    # Abundance
    natural_abundances: bool = Field(True, description="Use natural abundances")
    custom_abundances: Optional[List[float]] = Field(None, description="Custom abundance values (sums to 1)")

    # Energy range
    min_energy_eV: float = Field(1.0, gt=0, description="Minimum energy in eV")
    max_energy_eV: float = Field(100.0, gt=0, description="Maximum energy in eV")

    # Temperature
    temperature_K: float = Field(293.6, gt=0, description="Sample temperature in Kelvin")

    def get_material_properties(self) -> dict:
        """Get material properties dict for InpManager.

        Returns:
            Dictionary compatible with InpManager.create_multi_isotope_inp()
        """
        return {
            "element": self.element,
            "mass_number": self.mass_number,
            "density_g_cm3": self.density_g_cm3,
            "thickness_mm": self.thickness_mm,
            "atomic_mass_amu": self.atomic_mass_amu,
            "abundance": 1.0,  # Total abundance (will be split among isotopes)
            "min_energy": self.min_energy_eV,
            "max_energy_eV": self.max_energy_eV,
            "temperature_K": self.temperature_K,
        }

    def get_abundances(self) -> List[float]:
        """Get abundance list for JsonManager.

        Returns:
            List of abundance values for each isotope
        """
        if self.natural_abundances:
            # Use natural abundances (JsonManager will handle this)
            return [1.0] * len(self.isotopes)
        elif self.custom_abundances is not None:
            if len(self.custom_abundances) != len(self.isotopes):
                raise ValueError(
                    f"custom_abundances length {len(self.custom_abundances)} != isotopes length {len(self.isotopes)}"
                )
            return self.custom_abundances
        else:
            raise ValueError("Must specify custom_abundances if natural_abundances=False")
