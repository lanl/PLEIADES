import pytest
from pathlib import Path

from pleiades.sammy.data.options import DataTypeOptions, sammyData
from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions


def test_sammy_data_defaults():
    """Test the default values of sammyData."""
    params = sammyData()

    assert params.data_file is None
    assert params.data_type == DataTypeOptions.TRANSMISSION
    assert params.energy_units == EnergyUnitOptions.eV
    assert params.cross_section_units == CrossSectionUnitOptions.barn
    assert params.data is None


def test_sammy_data_custom_values():
    """Test custom values of sammyData."""
    params = sammyData(
        data_file=Path("custom.dat"),
        data_type=DataTypeOptions.CAPTURE,
        energy_units=EnergyUnitOptions.keV,
        cross_section_units=CrossSectionUnitOptions.millibarn,
    )

    assert params.data_file == Path("custom.dat")
    assert params.data_type == DataTypeOptions.CAPTURE
    assert params.energy_units == EnergyUnitOptions.keV
    assert params.cross_section_units == CrossSectionUnitOptions.millibarn


def test_invalid_data_type():
    """Test invalid data type."""
    with pytest.raises(ValueError):
        sammyData(data_file=Path("invalid.dat"), data_type="INVALID_TYPE")


if __name__ == "__main__":
    pytest.main()