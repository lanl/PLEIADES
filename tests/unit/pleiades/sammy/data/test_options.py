import pytest

from pleiades.sammy.data.options import DataTypeOptions, dataParameters
from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions


def test_data_parameters_defaults():
    """Test the default values of dataParameters."""
    params = dataParameters()

    assert params.data_file is None
    assert params.data_type == DataTypeOptions.TRANSMISSION
    assert params.energy_units == EnergyUnitOptions.eV
    assert params.cross_section_units == CrossSectionUnitOptions.barn
    assert params.data_title is None
    assert params.data_comment is None


def test_data_parameters_custom_values():
    """Test custom values of dataParameters."""
    params = dataParameters(
        data_file="custom.dat",
        data_type=DataTypeOptions.CAPTURE,
        energy_units=EnergyUnitOptions.keV,
        cross_section_units=CrossSectionUnitOptions.millibarn,
        data_title="Custom Data",
        data_comment="This is a custom data set.",
    )

    assert params.data_file == "custom.dat"
    assert params.data_type == DataTypeOptions.CAPTURE
    assert params.energy_units == EnergyUnitOptions.keV
    assert params.cross_section_units == CrossSectionUnitOptions.millibarn
    assert params.data_title == "Custom Data"
    assert params.data_comment == "This is a custom data set."


def test_invalid_data_type():
    """Test invalid data type."""
    with pytest.raises(ValueError):
        dataParameters(data_file="invalid.dat", data_type="INVALID_TYPE")


if __name__ == "__main__":
    pytest.main()
