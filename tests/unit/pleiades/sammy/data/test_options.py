from pathlib import Path

import pytest

from pleiades.sammy.data.options import DataTypeOptions, SammyData
from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions


def test_sammy_data_defaults():
    """Test the default values of SammyData."""
    params = SammyData()

    assert params.data_file is None
    assert params.data_type == DataTypeOptions.TRANSMISSION
    assert params.energy_units == EnergyUnitOptions.eV
    assert params.cross_section_units == CrossSectionUnitOptions.barn
    assert params.data is None


def test_sammy_data_custom_values():
    """Test custom values of SammyData."""
    params = SammyData(
        data_type=DataTypeOptions.CAPTURE,
        energy_units=EnergyUnitOptions.keV,
        cross_section_units=CrossSectionUnitOptions.millibarn,
    )

    assert params.data_type == DataTypeOptions.CAPTURE
    assert params.energy_units == EnergyUnitOptions.keV
    assert params.cross_section_units == CrossSectionUnitOptions.millibarn


def test_invalid_data_type():
    """Test invalid data type."""
    with pytest.raises(ValueError):
        SammyData(data_file=Path("invalid.dat"), data_type="INVALID_TYPE")


if __name__ == "__main__":
    pytest.main()
