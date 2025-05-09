import pytest
from scipy.constants import h, c, electron_volt

from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions, convert_to_cross_section, convert_to_energy
from pleiades.utils.units import convert_from_wavelength_to_energy_ev, WavelengthUnitOptions


def test_convert_to_energy():
    assert convert_to_energy(EnergyUnitOptions.eV, EnergyUnitOptions.keV) == 1e-3
    assert convert_to_energy(EnergyUnitOptions.MeV, EnergyUnitOptions.eV) == 1e6
#    assert convert_to_energy(EnergyUnitOptions.J, EnergyUnitOptions.eV) == 6.242e12 / 1
    assert convert_to_energy(EnergyUnitOptions.J, EnergyUnitOptions.eV) == 1 / electron_volt


def test_convert_to_cross_section():
    assert convert_to_cross_section(CrossSectionUnitOptions.barn, CrossSectionUnitOptions.millibarn) == 1e3
    assert convert_to_cross_section(CrossSectionUnitOptions.microbarn, CrossSectionUnitOptions.barn) == 1e-6

def test_convert_from_wavelength_to_energy():
    # Test conversion from angstrom to eV
    wavelength_angstrom = 3.5  # 3.5 angstrom
    wavelength_m = 3.5e-10
    expected_energy_eV = (h * c) / (wavelength_m * electron_volt)
    assert convert_from_wavelength_to_energy_ev(wavelength_angstrom, 
                                               unit_from=WavelengthUnitOptions.angstrom) == pytest.approx(expected_energy_eV)

    # Test conversion from nm to eV
    wavelength_nm = 1.0  # 1 nm
    expected_energy_eV = h * c / (wavelength_nm * 1e-9 * electron_volt)
    assert convert_from_wavelength_to_energy_ev(wavelength_nm, WavelengthUnitOptions.nm) == pytest.approx(expected_energy_eV)

if __name__ == "__main__":
    pytest.main()
