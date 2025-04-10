#!/usr/bin/env python
"""Unit tests for core data models."""

import pytest

from pleiades.nuclear.models import IsotopeInfo, IsotopeMassData


def test_isotope_mass_data():
    """Test IsotopeMassData model."""
    data = IsotopeMassData(atomic_mass=238.0289, mass_uncertainty=0.0001, binding_energy=7.6, beta_decay_energy=None)
    assert data.atomic_mass == pytest.approx(238.0289)
    assert data.binding_energy == pytest.approx(7.6)
    assert data.beta_decay_energy is None


def test_isotope_info_from_string():
    """Test IsotopeInfo.from_string method."""
    isotope = IsotopeInfo.from_string("U-235")
    assert isotope.name == "U-235"
    assert isotope.element == "U"
    assert isotope.mass_number == 235

    isotope = IsotopeInfo.from_string("235-U")
    assert isotope.name == "U-235"
    assert isotope.element == "U"
    assert isotope.mass_number == 235

    with pytest.raises(ValueError, match="Invalid isotope format"):
        IsotopeInfo.from_string("InvalidFormat")


def test_isotope_info_str():
    """Test IsotopeInfo.__str__ method."""
    isotope = IsotopeInfo(name="U-235", element="U", mass_number=235)
    assert str(isotope) == "U-235"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
