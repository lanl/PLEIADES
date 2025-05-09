from enum import Enum
from scipy.constants import h, c, electron_volt


""" Small library of units and conversions for use in SAMMY fitting. """


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


class WavelengthUnitOptions(str, Enum):
    nm = "nm"
    pm = "pm"
    m = "m"
    angstrom = "angstrom"


def convert_wavlength_units(from_unit, to_unit):
    """Convert wavelength from one unit to another unit
    based on WavelengthUnitOptions options

    Args:
        from_unit (WavelengthUnitOptions): Unit to convert from.
        to_unit (WavelengthUnitOptions): Unit to convert to.

    Returns:
        float: Wavelength in the new unit.
    """

    # Conversion factors
    conversion_factors = {
        WavelengthUnitOptions.nm: 1e-9,
        WavelengthUnitOptions.pm: 1e-12,
        WavelengthUnitOptions.m: 1,
        WavelengthUnitOptions.angstrom: 1e-10,
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
        # EnergyUnitOptions.J: 6.242e12,
        EnergyUnitOptions.J: 1/electron_volt,
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


def convert_from_wavelength_to_energy(wavelength, 
                                      unit_from=WavelengthUnitOptions.angstrom, 
                                      unit_to=EnergyUnitOptions.eV):
    """Convert wavelength to energy based on the given units.

    Args:
        wavelength (float): Wavelength value.
        unit_from (WavelengthUnitOptions): Unit of the input wavelength.
        unit_to (EnergyUnitOptions): Unit of the output energy.

    Returns:
        float: Energy in the new unit.
    """
    wavelength_m = wavelength * convert_wavlength_units(unit_from, WavelengthUnitOptions.m)
    energy = h * c / wavelength_m
    energy = energy * convert_to_energy(EnergyUnitOptions.J, EnergyUnitOptions.eV)
    return energy
