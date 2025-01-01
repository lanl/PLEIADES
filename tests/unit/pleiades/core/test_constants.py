#!/usr/bin/env python
"""
Test suite for physical constants and unit conversions.

Reasoning:
- Verify accuracy of physical constants
- Test unit conversion functions
- Ensure immutability of constants
- Validate computed properties
"""

import pytest
from pydantic import ValidationError

from pleiades.core.constants import CONSTANTS
from pleiades.core.models import Mass, UnitType


def test_constants_immutability():
    """Test that constants cannot be modified."""
    with pytest.raises(ValidationError):
        CONSTANTS.speed_of_light = 0

    with pytest.raises(ValidationError):
        CONSTANTS.neutron_mass = Mass(value=0, unit_type=UnitType.MASS)


def test_mass_constants():
    """Test mass constants values and units."""
    assert CONSTANTS.neutron_mass_amu == pytest.approx(1.008664915)
    assert CONSTANTS.proton_mass_amu == pytest.approx(1.007276466)
    assert CONSTANTS.electron_mass_amu == pytest.approx(0.000548579909)


def test_computed_masses():
    """Test computed mass conversions."""
    expected_neutron_kg = 1.674927471e-27  # kg
    assert CONSTANTS.neutron_mass_kg == pytest.approx(expected_neutron_kg, rel=1e-8)


def test_constant_precisions():
    """Test that constants have correct significant figures."""
    assert len(str(CONSTANTS.avogadro_number)) >= 8  # At least 8 significant figures
    assert len(str(CONSTANTS.planck_constant)) >= 8


def test_fundamental_constants():
    """Test fundamental constants against known values."""
    assert CONSTANTS.speed_of_light == 299792458.0
    assert CONSTANTS.elementary_charge == pytest.approx(1.602176634e-19)
    assert CONSTANTS.boltzmann_constant == pytest.approx(8.617333262e-5)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
