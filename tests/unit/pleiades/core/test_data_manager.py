#!/usr/bin/env python
"""Unit tests for the NuclearDataManager class."""

# tests/unit/pleiades/core/test_data_manager.py
import pytest

from pleiades.core.data_manager import NuclearDataManager
from pleiades.core.models import CrossSectionPoint, DataCategory, IsotopeIdentifier, IsotopeInfo, IsotopeMassData


@pytest.fixture
def data_manager():
    """Create a NuclearDataManager instance using actual package data."""
    return NuclearDataManager()


def test_list_files(data_manager):
    """Test listing available files."""
    files = data_manager.list_files()
    assert DataCategory.ISOTOPES in files
    # Test for known files that should exist
    isotope_files = files[DataCategory.ISOTOPES]
    assert "isotopes.info" in isotope_files
    assert "mass.mas20" in isotope_files
    assert "neutrons.list" in isotope_files


def test_get_isotope_info_u238(data_manager):
    """Test U-238 isotope information retrieval."""
    info = data_manager.get_isotope_info(IsotopeIdentifier.from_string("U-238"))
    assert isinstance(info, IsotopeInfo)
    # Test against known U-238 values
    assert info.spin == 0.0
    assert abs(info.abundance - 0.992745 * 100) < 1e-6


def test_get_mass_data_u238(data_manager):
    """Test U-238 mass data retrieval."""
    mass_data = data_manager.get_mass_data(IsotopeIdentifier(element="U", mass_number=238))
    assert isinstance(mass_data, IsotopeMassData)
    # Test against known U-238 values from mass.mas20
    expected_mass = 238.050786936
    assert abs(mass_data.atomic_mass - expected_mass) < 1e-6


def test_read_cross_section_data_u238(data_manager):
    """Test U-238 cross-section data reading."""
    xs_data = data_manager.read_cross_section_data("u-n.tot", "U-238")
    assert len(xs_data) > 0
    assert all(isinstance(point, CrossSectionPoint) for point in xs_data)


def test_get_mat_number_u238(data_manager):
    """Test U-238 MAT number retrieval."""
    mat = data_manager.get_mat_number("U-238")
    assert mat == 9237  # Verify this is the correct MAT number


# Error cases
def test_get_isotope_info_nonexistent(data_manager):
    """Test handling of nonexistent isotope."""
    assert data_manager.get_isotope_info(IsotopeIdentifier(element="X", mass_number=999)) is None


def test_file_not_found(data_manager):
    """Test handling of nonexistent file."""
    with pytest.raises(FileNotFoundError):
        data_manager.get_file_path(DataCategory.ISOTOPES, "nonexistent.info")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
