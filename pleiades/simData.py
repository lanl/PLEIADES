import re, os
import configparser
import numpy as np
from scipy.interpolate import interp1d
import pleiades.nucData as pnd

AVOGADRO = 6.02214076E23    # Avogadro's number
CM2_TO_BARN = 1E24          # Conversion factor from cm2 to barns

def create_transmission(energy_grid, isotope):
    """Create the transmission data for the given material based on interpolation of the cross-section data and the energy grid for a given material thickness and density. This uses the the attenuation formula: T = e^(-sigma * A) where sigma is the cross-section, and A is the areal density, which is in units of atoms/barn.

    Args:
        xs_data (tuple array): list of tuples containing the energy and cross-section data
        thickness (float): thickness of the material
        thickness_unit (string): unit of the thickness for the given material
        density (float): density of the material
        density_unit (string): unit of the density for the given material
    
    Returns:
        transmission (tuple array): list of tuples containing the energy and transmission data
    """
    
    # Extract information from the isotope object
    thickness = isotope.thickness
    atomic_mass = isotope.atomic_mass
    thickness_unit = isotope.thickness_unit
    density = isotope.density
    density_unit = isotope.density_unit
    xs_data = isotope.xs_data
    
    if thickness_unit != "cm":
        if thickness_unit == "mm":
            thickness /= 10.0
        else:
            raise ValueError("Unsupported thickness unit: {thickness_unit} for {isotope_name}")
    if density_unit != "g/cm3":
        raise ValueError("Unsupported density unit:{density_unit} for {isotope_name}")

    # Calculate the areal density
    areal_density = thickness * density * AVOGADRO / atomic_mass / CM2_TO_BARN 
    
    # Create interpolation function for cross-section data
    energies_eV, cross_sections = zip(*xs_data)
    interpolate_xs_data = interp1d(energies_eV, cross_sections, kind='linear', fill_value="extrapolate")

    # create a list of tuples containing the energy and transmission data
    transmission = []
    interploated_cross_section = []
    
    for energy in energy_grid:
        # Get the cross-section at the given energy
        xs = interpolate_xs_data(energy)
        interploated_cross_section.append((energy, xs))
        
        # Calculate the transmission
        transmission.append((energy, np.exp(-xs * areal_density)))    

    return transmission


def parse_xs_file(file_location, isotope_name):
    """ Parse the cross-section file and return the data for the isotope.

    Args:
        file_location (string): File location of the cross-section data
        isotope_name (string): Name of the isotope to find in the file

    Raises:
        ValueError: If the isotope is not found in the file

    Returns:
        xs_data: List of tuples containing the energy and cross-section data
    """
    
    xs_data = []
    isotope_xs_found = False
    capture_data = False
    
    
    with open(file_location, 'r') as f:
        for line in f:
            # If we find the name of the isotope
            if isotope_name.upper() in line:
                isotope_xs_found = True
            # If we have found the isotope, then look for the "#data..." marker
            if isotope_xs_found:
                if "#data..." in line:
                    capture_data = True
                # If we find the "//" line, stop capturing data
                elif '//' in line:
                    capture_data = False
                    break
                # If capture_data is True and the line doesn't start with a '#', then it's the data
                elif capture_data and not line.startswith("#"):
                    energy_eV, xs = line.split()
                    xs_data.append((float(energy_eV)*1E6, float(xs))) # Convert energy from MeV to eV
                
                
    # If the loop completes and the isotope was not found
    if not isotope_xs_found:
        raise ValueError("Cross-section data for {isotope_name} not found in {file_location}".format(isotope_name=isotope_name, file_location=file_location))

    return xs_data



class Isotope:
    """Class to hold information about an isotope from a config file.
    """
    def __init__(self, name="Unknown", atomic_mass=0.0, thickness=0.0, thickness_unit="atoms/cm2", abundance=0.0, xs_file_location="Unknown", density=0.0, density_unit="g/cm3"):
        self.name = name
        self.atomic_mass = atomic_mass
        self.thickness = thickness
        self.thickness_unit = thickness_unit
        self.abundance = abundance
        self.xs_file_location = xs_file_location
        self.density = density
        self.density_unit = density_unit
        self.xs_data = []  # Array to hold xs data
    
    def load_xs_data(self):
        """Load cross-section data from file."""
        self.xs_data = parse_xs_file(self.xs_file_location, self.name)
        if not self.xs_data:
            raise ValueError(f"No data loaded for {self.name} from {self.xs_file_location}")
    
    def __repr__(self):
        xs_status = "XS data loaded successfully" if len(self.xs_data) != 0 else "XS data not loaded"
        return f"Isotope({self.name},{self.atomic_mass},{self.thickness} {self.thickness_unit}, {self.abundance}, {self.xs_file_location}, {self.density} {self.density_unit}, {xs_status})"

def load_isotopes_from_config(config_file, verbose=False):
    """Load isotopes from a config file.

    Args:
        config_file (string): Path to the config file
        verbose (bool, optional): Print verbose output. Defaults to False.

    Returns:
        array: List of Isotope objects
    """
    isotopes = []
    
    # Create a ConfigParser object and read the config file
    config = configparser.ConfigParser()
    config.read(config_file)
    
    # Create a dummy Isotope instance to get the default values
    default_isotope = Isotope()

    # Loop over each section in the config file
    for section in config.sections():
        # Check if the ignore flag is set for this isotope
        ignore = config.getboolean(section, 'ignore', fallback=False)
        if ignore:
            continue

        # Fetch each attribute with the default value from the dummy Isotope instance
        name = config.get(section, 'name', fallback=default_isotope.name)
        atomic_mass = pnd.get_mass_from_ame(name)
        if atomic_mass == None:
            raise ValueError(f"Could not find atomic mass for {name}")
        thickness = config.getfloat(section, 'thickness', fallback=default_isotope.thickness)
        thickness_unit = config.get(section, 'thickness_unit', fallback=default_isotope.thickness_unit)
        abundance = config.getfloat(section, 'abundance', fallback=default_isotope.abundance)
        xs_file_location = config.get(section, 'xs_file_location', fallback=default_isotope.xs_file_location)
        density = config.getfloat(section, 'density', fallback=default_isotope.density)
        density_unit = config.get(section, 'density_unit', fallback=default_isotope.density_unit)

        # Create an Isotope instance and load the xs data
        isotope = Isotope(name, atomic_mass, thickness, thickness_unit, abundance, xs_file_location, density, density_unit)
        isotope.load_xs_data()
        
        # Append the Isotope instance to the list
        isotopes.append(isotope)

    return isotopes

  
def write_transmission_data(energy_data, transmission_data, output_file, include_error=False, verbose=False):
    """Write the transmission data to a file in the format: energy (eV), transmission (0-1) with SAMMY's twenty character format.

    Args:
        transmission_data (array): List of tuples containing the energy and transmission data
        output_file (string): Path to the output file
        include_error (bool, optional): Include an error column. Defaults to False.
        verbose (bool, optional): Print verbose output. Defaults to False.
    """
    with open(output_file, 'w') as f:
        if verbose:
            print(f"Writing transmission data to {output_file}")
            
        for energy, transmission in zip(energy_data,transmission_data):
            energy_str = f"{energy:>20}"                    # Right-justified, 20 characters
            transmission_str = f"{transmission:>20}"        # Right-justified, 20 characters
            transmission_error_str = f"{0.1:>20}"           # Right-justified, 20 characters
            
            if include_error:
                f.write(f"{energy_str}{transmission_str}{transmission_error_str}\n")
            else:
                f.write(f"{energy_str}{transmission_str}\n")    # Write the data to the file

