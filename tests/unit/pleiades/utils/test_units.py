import numpy as np
import pytest
from scipy.constants import electron_volt, h, m_n

from pleiades.utils.units import (
    CrossSectionUnitOptions,
    DistanceUnitOptions,
    EnergyUnitOptions,
    TimeUnitOptions,
    convert_array_from_time_to_energy,
    convert_array_from_time_to_lambda,
    convert_time_units,
    convert_to_cross_section,
    convert_to_energy,
)


def test_convert_to_energy():
    assert convert_to_energy(EnergyUnitOptions.eV, EnergyUnitOptions.keV) == 1e-3
    assert convert_to_energy(EnergyUnitOptions.MeV, EnergyUnitOptions.eV) == 1e6
    #    assert convert_to_energy(EnergyUnitOptions.J, EnergyUnitOptions.eV) == 6.242e12 / 1
    assert convert_to_energy(EnergyUnitOptions.J, EnergyUnitOptions.eV) == 1 / electron_volt


def test_convert_to_cross_section():
    assert convert_to_cross_section(CrossSectionUnitOptions.barn, CrossSectionUnitOptions.millibarn) == 1e3
    assert convert_to_cross_section(CrossSectionUnitOptions.microbarn, CrossSectionUnitOptions.barn) == 1e-6


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
        time_array,
        time_unit,
        distance_source_detector,
        distance_source_detector_unit,
        detector_offset,
        detector_offset_unit,
        lambda_unit,
    )
    assert np.allclose(result, expected_lambda)

    time_array = np.array([6319])  # in microseconds
    time_unit = TimeUnitOptions.us
    distance_source_detector = 25.0  # in meters
    distance_source_detector_unit = DistanceUnitOptions.m
    detector_offset = 0.0  # no offset
    detector_offset_unit = TimeUnitOptions.s
    lambda_unit = DistanceUnitOptions.angstrom

    expected_lambda = ((h / m_n) * (time_array * 1e-6) / distance_source_detector) * 1e10  # convert to angstrom
    result = convert_array_from_time_to_lambda(
        time_array,
        time_unit,
        distance_source_detector,
        distance_source_detector_unit,
        detector_offset,
        detector_offset_unit,
        lambda_unit,
    )
    assert np.allclose(result, expected_lambda)

    # Test case 2: Conversion with detector offset
    detector_offset = 0.5  # in microseconds
    detector_offset_unit = TimeUnitOptions.us
    lambda_unit = DistanceUnitOptions.nm

    expected_lambda = (
        (h / m_n) * ((time_array * 1e-6) + (detector_offset * 1e-6)) / distance_source_detector * 1e9
    )  # convert to
    result = convert_array_from_time_to_lambda(
        time_array,
        time_unit,
        distance_source_detector,
        distance_source_detector_unit,
        detector_offset,
        detector_offset_unit,
        lambda_unit,
    )
    assert np.allclose(result, expected_lambda)

    # Test case 3: Different distance and time units
    time_array = np.array([1000.0, 2000.0, 3000.0])  # in nanoseconds
    time_unit = TimeUnitOptions.ns
    distance_source_detector = 500.0  # in centimeters
    distance_source_detector_unit = DistanceUnitOptions.cm
    lambda_unit = DistanceUnitOptions.angstrom

    expected_lambda = (
        (h / m_n) * (time_array * 1e-9 + detector_offset * 1e-6) / (distance_source_detector * 1e-2) * 1e10
    )  # convert to angstrom
    result = convert_array_from_time_to_lambda(
        time_array,
        time_unit,
        distance_source_detector,
        distance_source_detector_unit,
        detector_offset,
        detector_offset_unit,
        lambda_unit,
    )
    assert np.allclose(result, expected_lambda)


def test_convert_array_from_time_to_energy_basic():
    # Simple test: 1, 2, 3 microseconds, 5 meters, no offset, output in eV
    time_array = np.array([1.0, 2.0, 3.0])
    time_unit = TimeUnitOptions.us
    distance_source_detector = 5.0
    distance_source_detector_unit = DistanceUnitOptions.m
    detector_offset = 0.0
    detector_offset_unit = TimeUnitOptions.us
    energy_unit = EnergyUnitOptions.eV

    # E_ev = 0.5 * m_n * (L / (t + offset))^2 / electron_volt
    t_s = time_array * 1e-6
    L_m = distance_source_detector
    expected = 0.5 * m_n * (L_m / t_s) ** 2 / electron_volt

    result = convert_array_from_time_to_energy(
        time_array,
        time_unit,
        distance_source_detector,
        distance_source_detector_unit,
        detector_offset,
        detector_offset_unit,
        energy_unit,
    )
    assert np.allclose(result, expected)


def test_convert_array_from_time_to_energy_with_offset_and_units():
    # Test with offset and different units
    time_array = np.array([1000.0, 2000.0, 3000.0])  # ns
    time_unit = TimeUnitOptions.ns
    distance_source_detector = 500.0  # cm
    distance_source_detector_unit = DistanceUnitOptions.cm
    detector_offset = 0.5  # us
    detector_offset_unit = TimeUnitOptions.us
    energy_unit = EnergyUnitOptions.eV

    t_s = time_array * 1e-9 + detector_offset * 1e-6
    L_m = distance_source_detector * 1e-2
    expected = 0.5 * m_n * (L_m / t_s) ** 2 / electron_volt

    result = convert_array_from_time_to_energy(
        time_array,
        time_unit,
        distance_source_detector,
        distance_source_detector_unit,
        detector_offset,
        detector_offset_unit,
        energy_unit,
    )
    assert np.allclose(result, expected)


def test_convert_array_from_time_to_energy_to_keV():
    # Test output in keV
    time_array = np.array([5000.0])  # ns
    time_unit = TimeUnitOptions.ns
    distance_source_detector = 2.0  # m
    distance_source_detector_unit = DistanceUnitOptions.m
    detector_offset = 0.0
    detector_offset_unit = TimeUnitOptions.ns
    energy_unit = EnergyUnitOptions.keV

    t_s = time_array * 1e-9
    L_m = distance_source_detector
    expected_eV = 0.5 * m_n * (L_m / t_s) ** 2 / electron_volt
    expected_keV = expected_eV * 1e-3

    result = convert_array_from_time_to_energy(
        time_array,
        time_unit,
        distance_source_detector,
        distance_source_detector_unit,
        detector_offset,
        detector_offset_unit,
        energy_unit,
    )
    assert np.allclose(result, expected_keV)


def test_convert_array_from_time_to_energy_zero_time_raises():
    # Should handle division by zero gracefully (return inf or nan)
    time_array = np.array([0.0])
    time_unit = TimeUnitOptions.s
    distance_source_detector = 1.0
    distance_source_detector_unit = DistanceUnitOptions.m
    detector_offset = 0.0
    detector_offset_unit = TimeUnitOptions.s
    energy_unit = EnergyUnitOptions.eV

    result = convert_array_from_time_to_energy(
        time_array,
        time_unit,
        distance_source_detector,
        distance_source_detector_unit,
        detector_offset,
        detector_offset_unit,
        energy_unit,
    )
    assert np.isinf(result[0]) or np.isnan(result[0])


if __name__ == "__main__":
    pytest.main()
