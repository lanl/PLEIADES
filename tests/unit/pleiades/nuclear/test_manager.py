#!/usr/bin/env python
"""Unit tests for the NuclearDataManager class."""

# tests/unit/pleiades/core/test_data_manager.py
import pytest

from pleiades.nuclear.manager import NuclearDataManager
from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData


@pytest.fixture
def data_manager():
    """Create a NuclearDataManager instance using actual package data."""
    return NuclearDataManager()



def test_get_isotope_info_u238(data_manager):
    """Test U-238 isotope information retrieval."""
    info = data_manager.get_isotope_info("U-238")

    assert isinstance(info, IsotopeInfo)
    
    # Test against known U-238 values
    assert info.spin == 0.0
    assert abs(info.abundance - 0.992745 * 100) < 1e-6


def test_get_mass_data_u238(data_manager):
    """Test U-238 mass data retrieval."""
    mass_data = data_manager.check_and_get_mass_data(element="U", mass_number=238)
    assert isinstance(mass_data, IsotopeMassData)
    # Test against known U-238 values from mass.mas20
    expected_mass = 238.050786936
    assert abs(mass_data.atomic_mass - expected_mass) < 1e-6


def test_get_mat_number_u238(data_manager):
    """Test U-238 MAT number retrieval."""
    mat = data_manager.get_mat_number(IsotopeInfo.from_string("U-238"))
    assert mat == 9237  # Verify this is the correct MAT number


# Error cases
def test_get_mass_data_nonexistent(data_manager):
    """Test handling of nonexistent isotope."""
    with pytest.raises(ValueError) as excinfo:
        data_manager.check_and_get_mass_data(element="X", mass_number=999)
    assert str(excinfo.value) == "Mass data for X-999 not found"




def test_file_not_found(data_manager):
    """Test handling of nonexistent file."""
    with pytest.raises(FileNotFoundError):
        data_manager.get_file_path(DataCategory.ISOTOPES, "nonexistent.info")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
