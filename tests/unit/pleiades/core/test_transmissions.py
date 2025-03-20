# Module: pleiades/tests/core/test_transmission.py
"""Unit tests for transmission calculations."""

import numpy as np
import pytest

from pleiades.nuclear.models import CrossSectionPoint, Isotope, IsotopeIdentifier, Mass
from pleiades.core.transmission import TransmissionError, calculate_transmission


@pytest.fixture
def test_energies():
    """Create test energy grid."""
    return np.logspace(0, 6, 10)  # 1 eV to 1 MeV


@pytest.fixture
def sample_xs_data():
    """Create sample cross-section data."""
    return [
        CrossSectionPoint(energy=1.0, cross_section=10.0),
        CrossSectionPoint(energy=10.0, cross_section=5.0),
        CrossSectionPoint(energy=100.0, cross_section=2.0),
        CrossSectionPoint(energy=1000.0, cross_section=1.0),
    ]


@pytest.fixture
def test_isotope(sample_xs_data):
    """Create test isotope with cross-section data."""
    identifier = IsotopeIdentifier(element="U", mass_number=238)
    isotope = Isotope(
        identifier=identifier,
        atomic_mass=Mass(value=238.0289),
        thickness=2.0,
        thickness_unit="cm",
        abundance=0.992745,
        density=19.1,
        density_unit="g/cm3",
    )
    isotope.xs_data = sample_xs_data
    return isotope


def test_transmission_calculation(test_isotope, test_energies):
    """Test basic transmission calculation."""
    results = calculate_transmission(test_isotope, test_energies)

    assert len(results) == len(test_energies)
    for energy, trans in results:
        assert 0.0 <= trans <= 1.0  # Physical bounds


def test_transmission_interpolation(test_isotope):
    """Test interpolation of cross sections."""
    # Test point between known values
    energies = [1.0]  # Between 1.0 and 10.0 in sample data
    results = calculate_transmission(test_isotope, energies)

    assert len(results) == 1
    energy, trans = results[0]
    assert 0.0 <= trans <= 1.0


def test_full_transmission():
    """Test case with zero cross section."""
    identifier = IsotopeIdentifier(element="U", mass_number=238)
    isotope = Isotope(
        identifier=identifier,
        atomic_mass=Mass(value=238.0289),
        thickness=1.0,
        thickness_unit="cm",
        abundance=0.992745,
        density=19.1,
        density_unit="g/cm3",
    )
    isotope.xs_data = [CrossSectionPoint(energy=1.0, cross_section=0.0)]

    results = calculate_transmission(isotope, [1.0])
    assert results[0][1] == pytest.approx(1.0)  # Should be full transmission


def test_no_xs_data(test_isotope):
    """Test error when no cross-section data available."""
    test_isotope.xs_data = []
    with pytest.raises(TransmissionError):
        calculate_transmission(test_isotope, [1.0])


def test_transmission_thickness_scaling(sample_xs_data):
    """Test transmission scales correctly with thickness."""
    identifier = IsotopeIdentifier(element="U", mass_number=238)
    isotope1 = Isotope(
        identifier=identifier,
        atomic_mass=Mass(value=238.0289),
        thickness=1.0,
        thickness_unit="cm",
        abundance=0.992745,
        density=19.1,
        density_unit="g/cm3",
    )
    isotope2 = Isotope(
        identifier=identifier,
        atomic_mass=Mass(value=238.0289),
        thickness=2.0,  # Double thickness
        thickness_unit="cm",
        abundance=0.992745,
        density=19.1,
        density_unit="g/cm3",
    )

    isotope1.xs_data = sample_xs_data
    isotope2.xs_data = sample_xs_data

    trans1 = calculate_transmission(isotope1, [1.0])[0][1]
    trans2 = calculate_transmission(isotope2, [1.0])[0][1]

    # Trans2 should be approximately trans1 squared
    assert trans2 == pytest.approx(trans1 * trans1, rel=1e-5)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
