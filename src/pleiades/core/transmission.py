#!/usr/bin/env python
"""
Neutron transmission calculations.

Migration source: simData.py
Changes:
- Added type hints and validation
- Improved error handling
- Used Pydantic models for data validation
- Added logging
"""

import logging
from typing import List, Tuple

import numpy as np
from scipy.interpolate import interp1d

from pleiades.core.models import Isotope

logger = logging.getLogger(__name__)


class TransmissionError(Exception):
    """Base exception for transmission calculation errors."""

    pass


def calculate_transmission(isotope: Isotope, energies: List[float]) -> List[Tuple[float, float]]:
    """
    Calculate transmission values for given energies.

    Migration source: simData.py create_transmission()
    Changes:
    - Added type hints
    - Improved error handling
    - Used Pydantic models for validation
    - Added logging

    Args:
        isotope: Isotope instance with loaded cross-section data
        energies: List of energy values in eV

    Returns:
        List of (energy, transmission) tuples

    Raises:
        TransmissionError: If calculation fails
    """
    try:
        if not isotope.xs_data:
            raise TransmissionError("No cross-section data loaded")

        # Create interpolation function
        xs_energies = [pt.energy for pt in isotope.xs_data]
        xs_values = [pt.cross_section for pt in isotope.xs_data]

        xs_interp = interp1d(xs_energies, xs_values, kind="linear", fill_value="extrapolate")

        # Calculate transmissions
        transmissions = []
        for energy in energies:
            xs = float(xs_interp(energy))
            trans = min(1.0, np.exp(-xs * isotope.areal_density))
            transmissions.append((energy, trans))

        return transmissions

    except Exception as e:
        raise TransmissionError(f"Transmission calculation failed: {str(e)}") from e
