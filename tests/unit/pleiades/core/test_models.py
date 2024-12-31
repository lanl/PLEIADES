#!/usr/bin/env python
"""Unit tests for core data models."""

import pytest
from pydantic import ValidationError

from pleiades.core.models import (
    CrossSectionPoint,
    Isotope,
    IsotopeIdentifier,
    IsotopeInfo,
    IsotopeMassData,
    Mass,
)


@pytest.fixture
def u238_identifier():
    """Create a U-238 isotope identifier."""
    return IsotopeIdentifier(element="U", mass_number=238)


@pytest.fixture
def sample_isotope(u238_identifier):
    """Create a sample U-238 isotope instance."""
    return Isotope(
        identifier=u238_identifier,
        atomic_mass=Mass(value=238.0289),
        thickness=1.0,
        thickness_unit="cm",
        abundance=0.992745,
        density=19.1,  # g/cm³
        density_unit="g/cm3",
    )


def test_isotope_identifier_creation():
    """Test IsotopeIdentifier creation and validation."""
    identifier = IsotopeIdentifier(element="U", mass_number=238)
    assert identifier.element == "U"
    assert identifier.mass_number == 238

    # Test string conversion
    assert str(identifier) == "U-238"

    # Test invalid inputs
    with pytest.raises(ValidationError):
        IsotopeIdentifier(element="1U", mass_number=238)
    with pytest.raises(ValidationError):
        IsotopeIdentifier(element="U", mass_number=-1)


def test_isotope_identifier_from_string():
    """Test IsotopeIdentifier creation from string."""
    identifier = IsotopeIdentifier.from_string("U-238")
    assert identifier.element == "U"
    assert identifier.mass_number == 238

    # Test invalid formats
    with pytest.raises(ValueError):
        IsotopeIdentifier.from_string("U238")
    with pytest.raises(ValueError):
        IsotopeIdentifier.from_string("238U")


def test_isotope_creation(sample_isotope):
    """Test Isotope model creation and validation."""
    assert sample_isotope.density == 19.1
    assert sample_isotope.thickness_unit == "cm"

    # Test validation
    with pytest.raises(ValidationError):
        Isotope(
            identifier=sample_isotope.identifier,
            atomic_mass=Mass(value=-1.0),  # Invalid mass
            thickness=1.0,
            thickness_unit="cm",
            abundance=0.5,
            density=1.0,
        )


def test_isotope_areal_density(sample_isotope):
    """Test areal density calculation."""
    # Test with different thickness units
    cm_isotope = sample_isotope
    mm_isotope = Isotope(**{**sample_isotope.model_dump(), "thickness": 10.0, "thickness_unit": "mm"})

    # Should give same result for equivalent thicknesses
    assert pytest.approx(cm_isotope.areal_density) == mm_isotope.areal_density


def test_cross_section_point():
    """Test CrossSectionPoint model."""
    point = CrossSectionPoint(energy=1.0, cross_section=10.0)
    assert point.energy == 1.0
    assert point.cross_section == 10.0

    with pytest.raises(ValidationError):
        CrossSectionPoint(energy=-1.0, cross_section=10.0)
    with pytest.raises(ValidationError):
        CrossSectionPoint(energy=1.0, cross_section=-10.0)


def test_isotope_mass_data():
    """Test IsotopeMassData model."""
    data = IsotopeMassData(atomic_mass=238.0289, mass_uncertainty=0.0001, binding_energy=7.6, beta_decay_energy=None)
    assert data.atomic_mass == pytest.approx(238.0289)
    assert data.binding_energy == pytest.approx(7.6)
    assert data.beta_decay_energy is None


def test_isotope_info():
    """Test IsotopeInfo model."""
    info = IsotopeInfo(spin=0.0, abundance=99.2745)
    assert info.spin == 0.0
    assert info.abundance == pytest.approx(99.2745)

    with pytest.raises(ValidationError):
        IsotopeInfo(spin=-1.0, abundance=50.0)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
