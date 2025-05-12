import pytest
from scipy.constants import h, c, electron_volt

from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions, TimeUnitOptions, convert_to_cross_section, convert_to_energy, convert_time_units
from pleiades.utils.units import convert_from_wavelength_to_energy_ev, DistanceUnitOptions


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
                                               unit_from=DistanceUnitOptions.angstrom) == pytest.approx(expected_energy_eV)

    # Test conversion from nm to eV
    wavelength_nm = 1.0  # 1 nm
    expected_energy_eV = h * c / (wavelength_nm * 1e-9 * electron_volt)
    assert convert_from_wavelength_to_energy_ev(wavelength_nm, DistanceUnitOptions.nm) == pytest.approx(expected_energy_eV)

def test_convert_time_units():
    # Test conversion from seconds to milliseconds
    assert convert_time_units(TimeUnitOptions.s, TimeUnitOptions.ms) == 1e3

    # Test conversion from nanoseconds to seconds
    assert convert_time_units(TimeUnitOptions.ns, TimeUnitOptions.s) == 1e-9

    # Test conversion from microseconds to milliseconds
    assert convert_time_units(TimeUnitOptions.us, TimeUnitOptions.ms) == 1e-3

    # Test conversion from picoseconds to nanoseconds
    assert convert_time_units(TimeUnitOptions.ps, TimeUnitOptions.ns) == 1e-3

    # Test conversion from milliseconds to seconds
    assert convert_time_units(TimeUnitOptions.ms, TimeUnitOptions.s) == 1e-3



if __name__ == "__main__":
    pytest.main()
