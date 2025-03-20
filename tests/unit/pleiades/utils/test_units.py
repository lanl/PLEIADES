import pytest

from pleiades.utils.units import (
    EnergyUnitOptions,
    CrossSectionUnitOptions,
    convert_to_energy,
    convert_to_cross_section
)

def test_convert_to_energy():
    assert convert_to_energy(EnergyUnitOptions.eV, EnergyUnitOptions.keV) == 1e-3
    assert convert_to_energy(EnergyUnitOptions.MeV, EnergyUnitOptions.eV) == 1e6
    assert convert_to_energy(EnergyUnitOptions.J, EnergyUnitOptions.eV) == 6.242e12 / 1

def test_convert_to_cross_section():
    assert convert_to_cross_section(CrossSectionUnitOptions.barn, CrossSectionUnitOptions.millibarn) == 1e3
    assert convert_to_cross_section(CrossSectionUnitOptions.microbarn, CrossSectionUnitOptions.barn) == 1e-6

if __name__ == "__main__":
    pytest.main()
