import pytest
import numpy as np
from scipy.constants import h, c, electron_volt, m_n

from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions, TimeUnitOptions, convert_to_cross_section, convert_to_energy, convert_time_units
from pleiades.utils.units import convert_from_wavelength_to_energy_ev, DistanceUnitOptions, convert_array_from_time_to_lambda


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

def test_convert_array_from_time_to_lambda():
    # Test case 1: Simple conversion with no detector offset
    time_array = np.array([1.0, 2.0, 3.0])  # in microseconds
    time_unit = TimeUnitOptions.us
    distance_source_detector = 5.0  # in meters
    distance_source_detector_unit = DistanceUnitOptions.m
    detector_offset = 0.0  # no offset
    detector_offset_unit = TimeUnitOptions.s
    lambda_unit = DistanceUnitOptions.angstrom

    expected_lambda = (h / m_n) * (time_array * 1e-6 + detector_offset) / distance_source_detector * 1e10
    result = convert_array_from_time_to_lambda(
        time_array, time_unit, distance_source_detector, distance_source_detector_unit, detector_offset, detector_offset_unit, lambda_unit
    )
    assert np.allclose(result, expected_lambda)


    time_array = np.array([6319])  # in microseconds
    time_unit = TimeUnitOptions.us
    distance_source_detector = 25.0  # in meters
    distance_source_detector_unit = DistanceUnitOptions.m
    detector_offset = 0.0  # no offset
    detector_offset_unit = TimeUnitOptions.s
    lambda_unit = DistanceUnitOptions.angstrom

    expected_lambda = ((h / m_n) * (time_array * 1e-6) / distance_source_detector ) * 1e10  # convert to angstrom
    result = convert_array_from_time_to_lambda(
        time_array, time_unit, distance_source_detector, distance_source_detector_unit, detector_offset, detector_offset_unit, lambda_unit
    )
    assert np.allclose(result, expected_lambda)


    # Test case 2: Conversion with detector offset
    detector_offset = 0.5  # in microseconds
    detector_offset_unit = TimeUnitOptions.us
    lambda_unit = DistanceUnitOptions.nm

    expected_lambda = (h / m_n) * ((time_array * 1e-6) + (detector_offset * 1e-6)) / distance_source_detector * 1e9  # convert to 
    result = convert_array_from_time_to_lambda(
        time_array, time_unit, distance_source_detector, distance_source_detector_unit, detector_offset, detector_offset_unit, lambda_unit
    )
    assert np.allclose(result, expected_lambda)

    # Test case 3: Different distance and time units
    time_array = np.array([1000.0, 2000.0, 3000.0])  # in nanoseconds
    time_unit = TimeUnitOptions.ns
    distance_source_detector = 500.0  # in centimeters
    distance_source_detector_unit = DistanceUnitOptions.cm
    lambda_unit = DistanceUnitOptions.angstrom

    expected_lambda = (h / m_n) * (time_array * 1e-9 + detector_offset * 1e-6) / (distance_source_detector * 1e-2) * 1e10  # convert to angstrom
    result = convert_array_from_time_to_lambda(
        time_array, time_unit, distance_source_detector, distance_source_detector_unit, detector_offset, detector_offset_unit, lambda_unit
    )
    assert np.allclose(result, expected_lambda)


if __name__ == "__main__":
    pytest.main()
