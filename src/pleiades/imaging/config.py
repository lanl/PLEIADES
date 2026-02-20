"""
Configuration models for 2D resonance imaging.

This module defines configuration structures for batch SAMMY fitting,
including material properties and imaging parameters.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from pleiades.nuclear.isotopes.manager import IsotopeManager
from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.inp_manager import InpDatasetMetadata


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

    # Fitting control
    fit_abundances: bool = Field(
        True,
        description=(
            "If True, SAMMY fits per-isotope abundances via a two-pass strategy "
            "(JSON mode for ENDF extraction, then traditional mode with IFLISO=1). "
            "If False, abundances are held fixed and only global thickness is fitted."
        ),
    )

    @model_validator(mode="after")
    def validate_energy_range(self) -> "ImagingConfig":
        """Ensure min_energy_eV < max_energy_eV."""
        if self.min_energy_eV >= self.max_energy_eV:
            raise ValueError(f"min_energy_eV ({self.min_energy_eV}) must be < max_energy_eV ({self.max_energy_eV})")
        return self

    def get_material_properties(self) -> dict:
        """Get material properties dict (legacy helper).

        Returns:
            Dictionary of material properties.
        """
        return {
            "element": self.element,
            "mass_number": self.mass_number,
            "density_g_cm3": self.density_g_cm3,
            "thickness_mm": self.thickness_mm,
            "atomic_mass_amu": self.atomic_mass_amu,
            "abundance": 1.0,
            "min_energy_eV": self.min_energy_eV,
            "max_energy_eV": self.max_energy_eV,
            "temperature_K": self.temperature_K,
        }

    def to_fit_config(self) -> FitConfig:
        """Build a FitConfig for InpManager.create_multi_isotope_inp().

        Populates the nuclear_params with isotope information looked up
        via IsotopeManager so that InpManager can generate correct Card Set 2.
        """
        fit_config = FitConfig(fit_title="Imaging pixel resonance fitting")
        for isotope_name in self.isotopes:
            fit_config.append_isotope_from_string(isotope_name)
        return fit_config

    def to_dataset_metadata(self) -> InpDatasetMetadata:
        """Build an InpDatasetMetadata with material/energy overrides."""
        return InpDatasetMetadata(
            element=self.element,
            mass_number=self.mass_number,
            atomic_mass_amu=self.atomic_mass_amu,
            min_energy_eV=self.min_energy_eV,
            max_energy_eV=self.max_energy_eV,
            temperature_K=self.temperature_K,
            density_g_cm3=self.density_g_cm3,
            thickness_mm=self.thickness_mm,
        )

    def get_abundances(self) -> List[float]:
        """Get abundance list for JsonManager.

        Returns:
            List of abundance values for each isotope (as fractions, not percentages)
        """
        if self.natural_abundances:
            # Look up actual natural abundances from PLEIADES isotope database
            isotope_manager = IsotopeManager()
            abundances = []
            for isotope_name in self.isotopes:
                isotope_info = isotope_manager.get_isotope_info(isotope_name)
                if isotope_info is None or isotope_info.abundance is None:
                    raise ValueError(
                        f"Natural abundance not found for {isotope_name}. "
                        "Use custom_abundances instead or verify isotope name."
                    )
                # Convert from percent to fraction (isotopes.info stores as percent)
                abundances.append(isotope_info.abundance / 100.0)
            return abundances
        elif self.custom_abundances is not None:
            if len(self.custom_abundances) != len(self.isotopes):
                raise ValueError(
                    f"custom_abundances length {len(self.custom_abundances)} != isotopes length {len(self.isotopes)}"
                )
            # Validate abundance sum (allow slightly > 1.0 for rounding, but flag obvious errors)
            abundance_sum = sum(self.custom_abundances)
            if abundance_sum > 1.01:  # 1% tolerance for rounding errors
                raise ValueError(
                    f"custom_abundances sum to {abundance_sum:.4f} > 1.0 (physically meaningless). "
                    "Abundances represent fractions and must sum to ≤ 1.0."
                )
            if any(a < 0 for a in self.custom_abundances):
                raise ValueError("custom_abundances must be non-negative")
            return self.custom_abundances
        else:
            raise ValueError("Must specify custom_abundances if natural_abundances=False")
