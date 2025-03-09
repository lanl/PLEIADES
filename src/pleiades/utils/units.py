from enum import Enum

""" Small library of units and conversions for use in SAMMY fitting. """

class EnergyUnitOptions(str, Enum):
    meV = "meV"
    eV = "eV"
    keV = "keV"
    MeV = "MeV"
    GeV = "GeV"
    J = "J"
    erg = "erg"

class CrossSectionUnitOptions(str, Enum):
    barn = "barn"
    millibarn = "millibarn"
    microbarn = "microbarn"
    cm2 = "cm^2"
    m2 = "m^2"
    
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
        EnergyUnitOptions.J: 6.242e12,
        EnergyUnitOptions.erg: 6.242e11
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
        CrossSectionUnitOptions.m2: 1e-4
    }
    
    return conversion_factors[from_unit] / conversion_factors[to_unit]
