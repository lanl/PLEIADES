import numpy as np
import os
import pathlib
import re

# current file location
PWD = pathlib.Path(__file__).parent

def extract_isotope_info(filename, isotope):
    """This function extracts the spin and abundance of an isotope from the file isotope.info.

    Args:
        filename (string): isotope.info file location
        
        isotope (string): String of the form "element-nucleonNumber" (e.g. "C-13")

    Returns:
        tuple: spin and natural abundance of the isotope
    """
    with open(filename, 'r') as file:
        lines = file.readlines()
        for line in lines:
            line = line.strip()  # Remove leading/trailing whitespaces
            if line and line[0].isdigit():  # Check if the line contains isotope data
                data = line.split()  # Split the line into columns based on spaces
                
                symbol = data[3]  # Extract the element symbol
                numOfNucleons = data[1]  # Extract the number of nucleons
                
                if isotope == f"{symbol}-{numOfNucleons}":  # Check if the isotope matches
                    spin = data[5]
                    abundance = data[7]
                    return spin, abundance
    return None, None

def parse_ame_line(line):
    """ Takes a line from the AME file and parses it into its constituent values.

    Args:
        line (string): line from the AME file
        
    Returns:
        dict: dictionary of the values from the line
    """
    def safe_float(val, default="nan"):
        return float(val if val.strip() else default)

    def safe_int(val, default=0):
        return int(val if val.strip() else default)

    # Extracting values based on their fixed positions
    cc = line[0]
    NZ = safe_int(line[2:5])
    N = safe_int(line[5:9])
    Z = safe_int(line[9:14])
    A = safe_int(line[14:19])
    el = line[20:23].strip()
    o = line[23:27].strip()
    mass = safe_float(line[28:42].replace("*", "nan").replace("#", ".0"))
    mass_unc = safe_float(line[42:54].replace("*", "nan").replace("#", ".0"))
    binding = safe_float(line[55:68].replace("*", "nan").replace("#", ".0"))
    bind_unc = safe_float(line[69:79].replace("*", "nan").replace("#", ".0"))
    B = line[79:81].strip()
    beta = safe_float(line[82:93].replace("*", "nan").replace("#", ".0"))
    beta_unc = safe_float(line[95:106].replace("*", "nan").replace("#", ".0"))

    atomic_mass_coarse = line[106:109].replace("*", "nan").replace("#", ".0")
    atomic_mass_fine = line[110:124].replace("*", "nan").replace("#", ".0")

    # Check if both coarse and fine are not NaN before converting
    if "nan" not in [atomic_mass_coarse, atomic_mass_fine]:
        atomic_mass = float(atomic_mass_coarse + atomic_mass_fine)
    else:
        atomic_mass = float("nan")

    atomic_mass_unc = safe_float(line[124:136].replace("*", "nan").replace("#", ".0"))

    return {
        "cc": cc,
        "NZ": NZ,
        "N": N,
        "Z": Z,
        "A": A,
        "el": el,
        "o": o,
        "mass": mass,
        "mass_unc": mass_unc,
        "binding": binding,
        "bind_unc": bind_unc,
        "B": B,
        "beta": beta,
        "beta_unc": beta_unc,
        "atomic_mass": atomic_mass,
        "atomic_mass_unc": atomic_mass_unc
    }


def get_info(isotopic_str):
    """Takes a string of the form 'element-atomicNumber' and returns the element and atomic number.

    Args:
        isotopic_str (string): string of the form 'element-atomicNumber'

    Returns:
        tuple: element, atomic number
    """
    
    # Extract the element and its atomic number from the isotopic string
    match = re.match(r'([A-Za-z]+)[-_]?(\d+)', isotopic_str)
    if match:
        element_name = match.group(1)
        atomic_number = int(match.group(2))
    else:
        element_name = ""
        atomic_number = None

    return element_name, atomic_number

def get_mass_from_ame(isotopic_str: str='U-238')->float:
    """Returns the atomic mass from AME tables according to the isotope name (E.g. Eu-153)

    Args:
        isotopic_str (str, optional): isotope name. Defaults to 'U-238'.

    Returns:
        float: the atomic mass in amu
    """
    # import re
    # pattern = r"\b([A-Z][a-z]?)-(\d+)\b"
    # if not re.search(pattern,isotopic_str):
    #     # raise ValueError(f"isotopic_str should be in the format of Element-AtomicMass (U-235)")
        
    
    possible_isotopes_data_list = []


    element, atomic_number = get_info(isotopic_str)
    # Load the file into a list of lines
    nucelar_masses_file = PWD.parent / "nucDataLibs/isotopeInfo/mass.mas20"
    
    with open(nucelar_masses_file, "r") as f:
        
        # Skip the first 36 lines of header info
        for _ in range(36):
            next(f)

        # start searching through lines.
        for line in f:
            # If we find the name of the isotope and the atomic number
            if (element in line[:25]) and (str(atomic_number) in line[:25]):
                possible_isotopes_data = parse_ame_line(line)
                possible_isotopes_data_list.append(possible_isotopes_data)

        # If we didn't find any data for the isotope
        if len(possible_isotopes_data_list) == 0:
            # raise ValueError("No data found for {} in {}".format(isotopic_str, nucelar_masses_file))
            return None 
        # If we found more than one isotope, then we need to find the correct one. 
        else:
            for iso in possible_isotopes_data_list:
                if (iso['el'] == element) and (iso['A'] == atomic_number):
                    final_atomic_mass = iso['atomic_mass']
                    return round(final_atomic_mass/1E6,4)     

def get_mat_number(isotopic_str: str='U-238')-> int:
    """Grabs the ENDF mat number of the requested isotope

    Args:
        isotopic_str (string): string of the form 'element-atomicNumber'

    Returns:
        int: mat number 
    """  
    # import re
    # pattern = r"\b([A-Z][a-z]?)-(\d+)\b"
    # if not re.search(pattern,isotopic_str):
    #     raise ValueError(f"isotopic_str should be in the format of Element-AtomicMass (e.g. U-238)")
    element, atomic_number = get_info(isotopic_str)

    # open the file containing the endf summary table
    with open(PWD.parent / "nucDataLibs/isotopeInfo/neutrons.list","r") as fid:
        pattern = r'\b\s*(\d+)\s*-\s*([A-Za-z]+)\s*-\s*(\d+)([A-Za-z]*)\b' # match the isotope name 
        for line in fid:
            # find match for an isotope string in the line
            match = re.search(pattern,line)

            if match and match.expand(r'\2-\3')==f"{element}-{atomic_number}":
                # the mat number is a 4 digits string at the end of each line
                matnumber = int(line[-5:])
                return matnumber
                
    raise ValueError(f"{isotopic_str} not found")                                                        