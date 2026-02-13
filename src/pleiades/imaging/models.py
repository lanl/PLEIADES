"""
Data models for 2D resonance imaging.

This module defines pydantic models for hyperspectral neutron imaging data
and results. Models follow PLEIADES conventions with numpy array support
and comprehensive validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from pleiades.sammy.results.models import FitResults


class PixelSpectrum(BaseModel):
    """Single pixel's transmission spectrum.

    Represents the energy-resolved transmission data for one spatial pixel,
    ready for SAMMY resonance fitting.

    Attributes:
        row: Pixel row coordinate (0-indexed)
        col: Pixel column coordinate (0-indexed)
        energy: 1D array of neutron energies in eV
        transmission: 1D transmission values (0-1 range)
        uncertainty: 1D uncertainties
        metadata: Optional metadata (e.g., spatial coordinates, source file)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    row: int = Field(..., ge=0, description="Pixel row coordinate")
    col: int = Field(..., ge=0, description="Pixel column coordinate")
    energy: np.ndarray = Field(..., description="1D energy array in eV")
    transmission: np.ndarray = Field(..., description="1D transmission values")
    uncertainty: np.ndarray = Field(..., description="1D uncertainties")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")

    @field_validator("energy", "transmission", "uncertainty")
    @classmethod
    def validate_1d_arrays(cls, v: np.ndarray, info) -> np.ndarray:
        """Ensure arrays are 1D."""
        if v.ndim != 1:
            raise ValueError(f"{info.field_name} must be 1D array, got {v.ndim}D")
        return v

    @field_validator("energy")
    @classmethod
    def validate_energy_positive(cls, v: np.ndarray) -> np.ndarray:
        """Ensure energy values are positive."""
        if len(v) == 0:
            raise ValueError("energy array cannot be empty")
        if np.any(v <= 0):
            raise ValueError(f"energy values must be positive, got min={v.min()}")
        if np.any(~np.isfinite(v)):
            raise ValueError("energy array contains NaN or Inf")
        return v

    @field_validator("transmission")
    @classmethod
    def validate_transmission_range(cls, v: np.ndarray) -> np.ndarray:
        """Ensure transmission values are physically reasonable.

        Allows slight overshoot/undershoot (±5%) to accommodate real normalized
        data with imperfect background subtraction or counting statistics.
        """
        if len(v) == 0:
            raise ValueError("transmission array cannot be empty")
        # Allow [-0.05, 1.05] tolerance for real-world normalization artifacts
        if np.any((v < -0.05) | (v > 1.05)):
            raise ValueError(
                f"transmission must be in [-0.05, 1.05] (allowing normalization tolerance), "
                f"got range=[{v.min()}, {v.max()}]"
            )
        if np.any(~np.isfinite(v)):
            raise ValueError("transmission array contains NaN or Inf")
        return v

    @field_validator("uncertainty")
    @classmethod
    def validate_uncertainty_positive(cls, v: np.ndarray) -> np.ndarray:
        """Ensure uncertainty values are positive."""
        if len(v) == 0:
            raise ValueError("uncertainty array cannot be empty")
        if np.any(v <= 0):
            raise ValueError(f"uncertainty values must be positive, got min={v.min()}")
        if np.any(~np.isfinite(v)):
            raise ValueError("uncertainty array contains NaN or Inf")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate array length consistency."""
        n_energy = len(self.energy)
        n_trans = len(self.transmission)
        n_uncert = len(self.uncertainty)
        if not (n_energy == n_trans == n_uncert):
            raise ValueError(
                f"Array length mismatch: energy={n_energy}, transmission={n_trans}, uncertainty={n_uncert}"
            )

    def to_csv(self, filepath: Path, sep: str = "\t") -> None:
        """Export pixel spectrum to CSV for SAMMY conversion.

        Creates tab-separated file compatible with convert_csv_to_sammy_twenty().

        Args:
            filepath: Output CSV file path
            sep: Column separator (default: tab)
        """
        df = pd.DataFrame({"energy": self.energy, "transmission": self.transmission, "uncertainty": self.uncertainty})
        df.to_csv(filepath, sep=sep, index=False)


class HyperspectralData(BaseModel):
    """Container for hyperspectral imaging dataset.

    Represents complete hyperspectral neutron transmission data with shape
    (n_energy, height, width).

    Attributes:
        data: 3D array (n_energy, height, width) of transmission values
        energy: 1D array of neutron energies in eV
        uncertainty: Optional 3D array of uncertainties (same shape as data)
        source_file: Path to original TIFF file
        metadata: Processing parameters, beam info, etc.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: np.ndarray = Field(..., description="3D transmission data (n_energy, height, width)")
    energy: np.ndarray = Field(..., description="1D energy axis in eV")
    uncertainty: Optional[np.ndarray] = Field(None, description="3D uncertainty array")
    source_file: Path = Field(..., description="Path to source TIFF file")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")

    @field_validator("data")
    @classmethod
    def validate_data_shape(cls, v: np.ndarray) -> np.ndarray:
        """Ensure data is 3D."""
        if v.ndim != 3:
            raise ValueError(f"data must be 3D array (n_energy, height, width), got {v.ndim}D")
        return v

    @field_validator("energy")
    @classmethod
    def validate_energy_1d(cls, v: np.ndarray) -> np.ndarray:
        """Ensure energy is 1D."""
        if v.ndim != 1:
            raise ValueError(f"energy must be 1D array, got {v.ndim}D")
        return v

    @field_validator("uncertainty")
    @classmethod
    def validate_uncertainty_shape(cls, v: Optional[np.ndarray], info) -> Optional[np.ndarray]:
        """Ensure uncertainty matches data shape if provided."""
        if v is not None and v.ndim != 3:
            raise ValueError(f"uncertainty must be 3D array, got {v.ndim}D")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate consistency between data, energy, and uncertainty."""
        n_energy, height, width = self.data.shape
        if len(self.energy) != n_energy:
            raise ValueError(f"Energy length {len(self.energy)} != n_energy {n_energy}")
        if self.uncertainty is not None and self.uncertainty.shape != self.data.shape:
            raise ValueError(f"Uncertainty shape {self.uncertainty.shape} != data shape {self.data.shape}")

    @property
    def shape(self) -> Tuple[int, int, int]:
        """Return (n_energy, height, width) shape."""
        return self.data.shape

    @property
    def n_pixels(self) -> int:
        """Return total number of spatial pixels."""
        _, height, width = self.data.shape
        return height * width


class PixelFitResult(BaseModel):
    """Container for a single pixel's SAMMY fit results.

    Attributes:
        row: Pixel row coordinate
        col: Pixel column coordinate
        fit_results: FitResults from SAMMY (contains isotope abundances)
        success: Whether fit succeeded
        error_message: Error message if fit failed
        chi_squared: Chi-squared value from fit
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    row: int = Field(..., ge=0, description="Pixel row")
    col: int = Field(..., ge=0, description="Pixel column")
    fit_results: Optional[FitResults] = Field(None, description="SAMMY FitResults")
    success: bool = Field(..., description="Whether fit succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    chi_squared: Optional[float] = Field(None, description="Chi-squared from fit")

    def model_post_init(self, __context: Any) -> None:
        """Validate consistency between success status and fit_results."""
        if self.success and self.fit_results is None:
            raise ValueError("If success=True, fit_results must be provided (cannot be None)")
        if not self.success and self.fit_results is not None:
            raise ValueError("If success=False, fit_results should be None")

    def get_abundances(self) -> List[float]:
        """Extract isotope abundances from fit results.

        Returns:
            List of abundance values for each isotope
        """
        if not self.success or self.fit_results is None:
            return []
        return [isotope.abundance for isotope in self.fit_results.nuclear_data.isotopes]


class Imaging2DResults(BaseModel):
    """Container for aggregated 2D imaging results.

    Represents spatially-resolved isotope abundance maps and fitting statistics
    from batch SAMMY fitting.

    Attributes:
        abundance_maps: 3D array (n_isotopes, height, width) of fitted abundances
        isotope_names: List of isotope names corresponding to abundance_maps
        fitted_energy_maps: Optional 3D array (n_resonances, height, width) of fitted energies
        chi_squared_map: 2D array (height, width) of chi-squared values
        success_mask: 2D boolean array where True = successful fit
        source_hyperspectral: Original HyperspectralData
        pixel_results: List of PixelFitResult objects (for debugging)
        metadata: Processing parameters
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    abundance_maps: np.ndarray = Field(..., description="3D abundance maps (n_isotopes, height, width)")
    isotope_names: List[str] = Field(..., description="List of isotope names")
    fitted_energy_maps: Optional[np.ndarray] = Field(None, description="3D fitted energy maps")
    chi_squared_map: np.ndarray = Field(..., description="2D chi-squared map")
    success_mask: np.ndarray = Field(..., description="2D success mask")
    source_hyperspectral: HyperspectralData = Field(..., description="Original data")
    pixel_results: List[PixelFitResult] = Field(default_factory=list, description="Per-pixel results")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")

    @field_validator("abundance_maps")
    @classmethod
    def validate_abundance_shape(cls, v: np.ndarray) -> np.ndarray:
        """Ensure abundance_maps is 3D."""
        if v.ndim != 3:
            raise ValueError(f"abundance_maps must be 3D (n_isotopes, height, width), got {v.ndim}D")
        return v

    @field_validator("chi_squared_map", "success_mask")
    @classmethod
    def validate_2d_maps(cls, v: np.ndarray, info) -> np.ndarray:
        """Ensure maps are 2D."""
        if v.ndim != 2:
            raise ValueError(f"{info.field_name} must be 2D (height, width), got {v.ndim}D")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate consistency between isotope_names, abundance_maps, and spatial shapes."""
        # Check isotope count consistency
        n_isotopes_names = len(self.isotope_names)
        n_isotopes_maps = self.abundance_maps.shape[0]
        if n_isotopes_names != n_isotopes_maps:
            raise ValueError(
                f"isotope_names length ({n_isotopes_names}) must match "
                f"abundance_maps first dimension ({n_isotopes_maps})"
            )

        # Check spatial shape consistency across all 2D/3D maps
        _, height_abundance, width_abundance = self.abundance_maps.shape
        height_chi2, width_chi2 = self.chi_squared_map.shape
        height_mask, width_mask = self.success_mask.shape
        _, height_source, width_source = self.source_hyperspectral.shape

        if not (
            height_abundance == height_chi2 == height_mask == height_source
            and width_abundance == width_chi2 == width_mask == width_source
        ):
            raise ValueError(
                f"Spatial shape mismatch: "
                f"abundance_maps={height_abundance}×{width_abundance}, "
                f"chi_squared_map={height_chi2}×{width_chi2}, "
                f"success_mask={height_mask}×{width_mask}, "
                f"source_hyperspectral={height_source}×{width_source}"
            )

    def save_hdf5(self, filepath: Path) -> None:
        """Save results to HDF5 file with comprehensive metadata.

        HDF5 structure:
            /abundance_maps (n_isotopes, height, width) - float32, gzip
            /isotope_names (n_isotopes,) - string dataset
            /fitted_energy_maps (n_resonances, height, width) - optional
            /chi_squared_map (height, width) - float32
            /success_mask (height, width) - bool
            /energy (n_energy,) - from source_hyperspectral
            /metadata - group with attributes

        Args:
            filepath: Output HDF5 file path
        """
        import h5py

        with h5py.File(filepath, "w") as f:
            # Core results
            f.create_dataset("abundance_maps", data=self.abundance_maps, compression="gzip")
            f.create_dataset("isotope_names", data=np.array(self.isotope_names, dtype="S"))
            f.create_dataset("chi_squared_map", data=self.chi_squared_map, compression="gzip")
            f.create_dataset("success_mask", data=self.success_mask, compression="gzip")

            # Optional energy maps
            if self.fitted_energy_maps is not None:
                f.create_dataset("fitted_energy_maps", data=self.fitted_energy_maps, compression="gzip")

            # Source data reference
            f.create_dataset("energy", data=self.source_hyperspectral.energy)
            f.attrs["source_file"] = str(self.source_hyperspectral.source_file)

            # Metadata
            meta_group = f.create_group("metadata")
            for key, value in self.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    meta_group.attrs[key] = value
