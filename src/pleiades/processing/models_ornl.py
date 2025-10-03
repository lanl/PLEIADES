"""
ORNL-specific data models for neutron imaging normalization at VENUS.

This module defines data structures for the ORNL/VENUS neutron imaging
processing pipeline. These models represent raw measurement data and
calculated transmission spectra used in the normalization process.

The models use Pydantic v2 for validation and serialization while
efficiently handling numpy arrays for numerical data.
"""

from typing import Any, Dict, Optional, Tuple

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from pleiades.processing import Roi


class Run(BaseModel):
    """Container for a single measurement run (sample or open beam).

    This represents data from a single run at the VENUS beamline,
    containing detector counts, beam monitoring data, and metadata.

    Attributes:
        counts: 3D array of detector counts with shape (tof, y, x)
        proton_charge: Total integrated proton charge in microCoulombs
        shutter_counts: Optional 1D array of shutter monitor counts per TOF bin
        dead_pixel_mask: Optional 2D boolean mask where True indicates dead pixels
        metadata: Dictionary containing run_number, folder, timestamp, etc.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    counts: np.ndarray = Field(..., description="(tof, y, x) detector counts")
    proton_charge: float = Field(..., gt=0, description="Total proton charge in μC")
    shutter_counts: Optional[np.ndarray] = Field(
        None, description="(tof,) per-energy shutter values, ignored for resonance"
    )
    dead_pixel_mask: Optional[np.ndarray] = Field(None, description="(y, x) boolean dead pixel mask")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="folder, run_number, timestamp, etc.")

    @field_validator("counts")
    @classmethod
    def validate_counts_shape(cls, v: np.ndarray) -> np.ndarray:
        """Ensure counts is a 3D array."""
        if v.ndim != 3:
            raise ValueError(f"counts must be 3D array (tof, y, x), got {v.ndim}D")
        return v

    @field_validator("shutter_counts")
    @classmethod
    def validate_shutter_shape(cls, v: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Ensure shutter_counts is 1D if provided."""
        if v is not None and v.ndim != 1:
            raise ValueError(f"shutter_counts must be 1D array (tof,), got {v.ndim}D")
        return v

    @field_validator("dead_pixel_mask")
    @classmethod
    def validate_dead_mask_shape(cls, v: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """Ensure dead_pixel_mask is 2D boolean if provided."""
        if v is not None:
            if v.ndim != 2:
                raise ValueError(f"dead_pixel_mask must be 2D array (y, x), got {v.ndim}D")
            if v.dtype != bool:
                raise ValueError(f"dead_pixel_mask must be boolean, got {v.dtype}")
        return v

    def get_tof_range(self) -> Tuple[int, int, int]:
        """Return (n_tof, n_y, n_x) shape of the counts array."""
        return self.counts.shape


class Transmission(BaseModel):
    """Container for calculated transmission spectrum.

    This represents the normalized transmission data ready for SAMMY fitting,
    containing the transmission spectrum, uncertainties, and processing metadata.

    Attributes:
        energy: 1D array of neutron energies in eV
        transmission: 1D array of transmission values (typically 0-1)
        uncertainty: 1D array of transmission uncertainties
        roi: Optional ROI used for spatial selection
        roi_center: (x, y) coordinates of the ROI center
        metadata: Processing parameters, source runs, etc.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    energy: np.ndarray = Field(..., description="1D array of neutron energies in eV")
    transmission: np.ndarray = Field(..., description="1D transmission values, typically 0-1 range")
    uncertainty: np.ndarray = Field(..., description="1D uncertainties (Poisson + systematic)")
    roi: Optional[Roi] = Field(None, description="ROI used (None = full FOV)")
    roi_center: Tuple[float, float] = Field(..., description="(x, y) center of ROI")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="source runs, proton charges, processing params")

    @field_validator("energy", "transmission", "uncertainty")
    @classmethod
    def validate_1d_arrays(cls, v: np.ndarray, info) -> np.ndarray:
        """Ensure arrays are 1D."""
        if v.ndim != 1:
            raise ValueError(f"{info.field_name} must be 1D array, got {v.ndim}D")
        return v

    @field_validator("transmission")
    @classmethod
    def validate_transmission_range(cls, v: np.ndarray) -> np.ndarray:
        """Warn if transmission values are outside typical range."""
        if np.any(v < 0) or np.any(v > 1.5):
            # Not an error, but worth noting
            import warnings

            warnings.warn(f"Transmission values outside typical range [0, 1.5]: [{v.min()}, {v.max()}]")
        return v

    @field_validator("uncertainty")
    @classmethod
    def validate_positive_uncertainty(cls, v: np.ndarray) -> np.ndarray:
        """Ensure uncertainties are non-negative."""
        if np.any(v < 0):
            raise ValueError(f"Uncertainties must be non-negative, got min={v.min()}")
        return v

    def model_post_init(self, __context) -> None:
        """Validate array length consistency after initialization."""
        n_energy = len(self.energy)
        n_trans = len(self.transmission)
        n_uncert = len(self.uncertainty)

        if not (n_energy == n_trans == n_uncert):
            raise ValueError(
                f"Array length mismatch: energy={n_energy}, transmission={n_trans}, uncertainty={n_uncert}"
            )

    def to_dat_format(self) -> np.ndarray:
        """Export as 3-column array for SAMMY .dat file.

        Energy values are sorted in increasing order as required by SAMMY.

        Returns:
            Array with shape (n_points, 3) containing:
            - Column 0: Energy in eV (increasing order)
            - Column 1: Transmission (0-1)
            - Column 2: Uncertainty (0-1)
        """
        # Sort by increasing energy (SAMMY requirement)
        sort_indices = np.argsort(self.energy)
        return np.column_stack(
            [self.energy[sort_indices], self.transmission[sort_indices], self.uncertainty[sort_indices]]
        )

    def save_dat(self, filepath: str) -> None:
        """Save transmission data in SAMMY .dat format.

        Data is automatically sorted by increasing energy as required by SAMMY.

        Args:
            filepath: Path to output .dat file
        """
        data = self.to_dat_format()  # Already sorted by energy
        header = "Energy(eV)  Transmission  Uncertainty"  # np.savetxt adds the # automatically
        np.savetxt(filepath, data, header=header, fmt="%.6e")
