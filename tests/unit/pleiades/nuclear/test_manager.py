#!/usr/bin/env python
"""Unit tests for the NuclearDataManager class."""

# tests/unit/pleiades/core/test_data_manager.py
import pytest

from pleiades.nuclear.manager import NuclearDataManager


@pytest.fixture
def data_manager():
    """Create a NuclearDataManager instance using actual package data."""
    return NuclearDataManager()


def test_create_isotope_parameters_from_string_valid(data_manager):
    """
    Test creating IsotopeParameters with a valid isotope string using actual data.
    """
    # Call the method under test with a valid isotope string
    isotope_params = data_manager.create_isotope_parameters_from_string("U-238")

    # Assert that the returned IsotopeParameters instance is correct
    assert isotope_params.isotope_infomation.name == "U-238"
    assert isotope_params.isotope_infomation.mass_number == 238
    assert isotope_params.isotope_infomation.element == "U"
    assert isotope_params.isotope_infomation.material_number == 9237
    assert isotope_params.abundance is None  # Default value
    assert isotope_params.spin_groups == []  # Default empty list


if __name__ == "__main__":
    pytest.main(["-v", __file__])
