from enum import Enum

import numpy as np
from scipy.constants import electron_volt, h, m_n

""" Small library of units and conversions for use in SAMMY fitting. """


class TimeUnitOptions(str, Enum):
    s = "s"
    ms = "ms"
    us = "us"
    ns = "ns"
    ps = "ps"


class EnergyUnitOptions(str, Enum):
    meV = "meV"
    eV = "eV"
    keV = "keV"
    MeV = "MeV"
    GeV = "GeV"
    J = "J"


class CrossSectionUnitOptions(str, Enum):
    barn = "barn"
    millibarn = "millibarn"
    microbarn = "microbarn"
    cm2 = "cm^2"


class DistanceUnitOptions(str, Enum):
    cm = "cm"
    nm = "nm"
    pm = "pm"
    m = "m"
    angstrom = "angstrom"


def convert_time_units(from_unit, to_unit):
    """Convert time from one unit to another unit
    based on TimeUnitOptions options

    Args:
        from_unit (TimeUnitOptions): Unit to convert from.
        to_unit (TimeUnitOptions): Unit to convert to.

    Returns:
        float: Time in the new unit.
    """

    # Conversion factors
    conversion_factors = {
        TimeUnitOptions.s: 1,
        TimeUnitOptions.ms: 1e-3,
        TimeUnitOptions.us: 1e-6,
        TimeUnitOptions.ns: 1e-9,
        TimeUnitOptions.ps: 1e-12,
    }

    return conversion_factors[from_unit] / conversion_factors[to_unit]


def convert_distance_units(from_unit, to_unit):
    """Convert distance from one unit to another unit
    based on DistanceUnitOptions options

    Args:
        from_unit (DistanceUnitOptions): Unit to convert from.
        to_unit (DistanceUnitOptions): Unit to convert to.

    Returns:
        float: distance in the new unit.
    """

    # Conversion factors
    conversion_factors = {
        DistanceUnitOptions.nm: 1e-9,
        DistanceUnitOptions.cm: 1e-2,
        DistanceUnitOptions.pm: 1e-12,
        DistanceUnitOptions.m: 1,
        DistanceUnitOptions.angstrom: 1e-10,
    }

    return conversion_factors[from_unit] / conversion_factors[to_unit]


def convert_to_energy(from_unit, to_unit):
    """Convert energy from one unit to another unit
    based on EnergyUnitOptions options

    Args:
        from_unit (EnergyUnitOptions): Unit to convert from.
        to_unit (EnergyUnitOptions): Unit to convert to.

    Returns:
        float: Energy in the new unit.
    """

    # Conversion factors
    conversion_factors = {
        EnergyUnitOptions.meV: 1e-3,
        EnergyUnitOptions.eV: 1,
        EnergyUnitOptions.keV: 1e3,
        EnergyUnitOptions.MeV: 1e6,
        EnergyUnitOptions.GeV: 1e9,
        EnergyUnitOptions.J: 1 / electron_volt,
    }

    return conversion_factors[from_unit] / conversion_factors[to_unit]


def convert_to_cross_section(from_unit, to_unit):
    """Convert cross section from one unit to another unit
    based on CrossSectionUnitOptions options

    Args:
        from_unit (CrossSectionUnitOptions): Unit to convert from.
        to_unit (CrossSectionUnitOptions): Unit to convert to.

    Returns:
        float: Cross section in the new unit.
    """

    # Conversion factors
    conversion_factors = {
        CrossSectionUnitOptions.barn: 1,
        CrossSectionUnitOptions.millibarn: 1e-3,
        CrossSectionUnitOptions.microbarn: 1e-6,
        CrossSectionUnitOptions.cm2: 1e-24,
    }

    return conversion_factors[from_unit] / conversion_factors[to_unit]


# def convert_from_wavelength_to_energy_ev(wavelength,
#                                          unit_from=DistanceUnitOptions.angstrom):
#     """Convert wavelength to energy based on the given units.

#     Args:
#         wavelength (float): Wavelength value.
#         unit_from (WavelengthUnitOptions): Unit of the input wavelength.

#     Returns:
#         float: Energy in the new unit.
#     """
#     wavelength_m = wavelength * convert_distance_units(unit_from, DistanceUnitOptions.m)
#     energy = h * c / wavelength_m
#     energy = energy * convert_to_energy(EnergyUnitOptions.J, EnergyUnitOptions.eV)
#     return energy


def convert_array_from_time_to_lambda(
    time_array: np.ndarray,
    time_unit: TimeUnitOptions,
    distance_source_detector: float,
    distance_source_detector_unit: DistanceUnitOptions,
    detector_offset: float,
    detector_offset_unit: DistanceUnitOptions,
    lambda_unit: DistanceUnitOptions,
) -> np.ndarray:
    """Convert an array of time values to wavelength values.

    Args:
        time_array (np.ndarray): Array of time values.
        time_unit (TimeUnitOptions): Unit of the input time.
        distance_source_detector (float): Distance from the source to the detector.
        distance_source_detector_unit (DistanceUnitOptions): Unit of the distance.
        detector_offset (float): Offset of the detector.
        detector_offset_unit (DistanceUnitOptions): Unit of the offset.
        lambda_unit (DistanceUnitOptions): Unit of the output wavelength.

    This is using the formula: lambda_m = h/(m_n * distance_source_detector_m) * (time_array_s + detector_offset_s)

    Returns:
        np.ndarray: Array of wavelength values.
    """
    time_array_s = time_array * convert_time_units(time_unit, TimeUnitOptions.s)
    detector_offset_s = detector_offset * convert_time_units(detector_offset_unit, TimeUnitOptions.s)
    distance_source_detector_m = distance_source_detector * convert_distance_units(
        distance_source_detector_unit, DistanceUnitOptions.m
    )

    h_over_mn = h / m_n
    lambda_m = h_over_mn * (time_array_s + detector_offset_s) / distance_source_detector_m

    lambda_converted = lambda_m * convert_distance_units(DistanceUnitOptions.m, lambda_unit)

    return lambda_converted


def convert_array_from_time_to_energy(
    time_array: np.ndarray,
    time_unit: TimeUnitOptions,
    distance_source_detector: float,
    distance_source_detector_unit: DistanceUnitOptions,
    detector_offset: float,
    detector_offset_unit: DistanceUnitOptions,
    energy_unit: EnergyUnitOptions,
) -> np.ndarray:
    """Convert an array of time values to energy values.

    Args:
        time_array (np.ndarray): Array of time values.
        time_unit (TimeUnitOptions): Unit of the input time.
        distance_source_detector (float): Distance from the source to the detector.
        distance_source_detector_unit (DistanceUnitOptions): Unit of the distance.
        detector_offset (float): Offset of the detector.
        detector_offset_unit (DistanceUnitOptions): Unit of the offset.
        energy_unit (EnergyUnitOptions): Unit of the output energy.

    this is using the formula: E_ev = 1/2 m_n (L/t_tof)^2 / electron_volt

    where
        t_tof = L/ v (L is the distance from the source to the detector in m, v is the velocity of the neutron in m/s).
        E is the kinetic energy of the neutron in eV.

    Returns:
        np.ndarray: Array of energy values.
    """

    time_units_factor = convert_time_units(time_unit, TimeUnitOptions.s)
    time_array_s = time_array * time_units_factor

    detector_units_factor = convert_time_units(detector_offset_unit, TimeUnitOptions.s)
    detector_offset = detector_units_factor * detector_offset

    distance_source_detector_factor = convert_distance_units(distance_source_detector_unit, DistanceUnitOptions.m)
    distance_source_detector_m = distance_source_detector * distance_source_detector_factor

    # Calculate the energy in eV using the formula E_ev = 1/2 m_n (L/t_tof)^2 / electron_volt

    full_time_array_s = time_array_s + detector_offset
    energy_array_ev = 0.5 * m_n * (distance_source_detector_m / full_time_array_s) ** 2 / electron_volt

    energy_array_factor = convert_to_energy(EnergyUnitOptions.eV, energy_unit)
    energy_array = energy_array_ev * energy_array_factor
    energy_array = np.array(energy_array)

    return energy_array


def calculate_number_density(material_density_g_cm3: float, thickness_mm: float, atomic_mass_amu: float) -> float:
    """
    Convert material properties to number density (atoms/barn).

    Migrated from legacy/pleiades_old/simData.py for use in multi-isotope INP generation.

    Args:
        material_density_g_cm3: Material density in g/cm³
        thickness_mm: Sample thickness in mm
        atomic_mass_amu: Atomic mass in amu

    Returns:
        float: Number density in atoms/barn (areal density)

    Example:
        >>> # For Hafnium sample: density=13.31 g/cm³, thickness=5mm, mass=178.49 amu
        >>> density = calculate_number_density(13.31, 5.0, 178.49)
        >>> print(f"Number density: {density:.6e} atoms/barn")

    Note:
        This calculation uses the same formula as the legacy code:
        areal_density = thickness * density * AVOGADRO / atomic_mass / CM2_TO_BARN

        TODO: Future enhancement - auto-retrieve material density from element database
    """
    from pleiades.core.constants import CONSTANTS

    # Convert thickness from mm to cm
    thickness_cm = thickness_mm / 10.0

    # Use PLEIADES physics constants
    AVOGADRO = CONSTANTS.avogadro_number  # 6.02214076e23
    CM2_TO_BARN = 1.0 / CONSTANTS.barn_to_cm2  # 1e24

    # Calculate areal density (same formula as legacy code)
    areal_density = thickness_cm * material_density_g_cm3 * AVOGADRO / atomic_mass_amu / CM2_TO_BARN

    return areal_density
