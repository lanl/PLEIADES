from pleiades.sammy.results.models import RunResults, FitResults
from pleiades.nuclear.models import nuclearParameters
from pleiades.experimental.models import PhysicsParameters
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)



def extract_results_from_string(lpt_block_string: str) -> FitResults:
    """
    Extracts results from a given LPT string and returns a FitResults object.
    
    Args:
        lpt_block_string (str): The LPT string containing the results from a given iteration.
        
    Returns:
        FitResults: An object containing the extracted results.
    """
    fit_results = FitResults()
    temp_nuclear_data = nuclearParameters()
    temp_physics_data = PhysicsParameters()
    
    lines = lpt_block_string.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # EFFECTIVE RADIUS block
        if line.startswith('EFFECTIVE RADIUS'):
            # Example: parse next N lines for radii
            i += 1
            while i < len(lines) and lines[i].strip():
                # Parse radii here, e.g.:
                # tokens = lines[i].split()
                # nuclear_data.radius_parameters.append(...)
                i += 1
        # Isotopic abundance block
        elif line.startswith('Isotopic abundance and mass for each nuclide'):
            i += 2  # skip header lines
            while i < len(lines) and lines[i].strip():
                print(lines[i])
                i += 1
        # TEMPERATURE/THICKNESS block
        elif line.startswith('TEMPERATURE') and 'THICKNESS' in line:
            i += 1
            if i < len(lines):
                tokens = lines[i].split()
                if len(tokens) >= 2:
                    pass
                    
            i += 1
        # DELTA-L ... block
        elif line.startswith('DELTA-L') and 'DELTA-T-GAUS' in line:
            i += 1
            if i < len(lines):
                tokens = lines[i].split()
                # physics_data.broadening_parameters.delta_l = float(tokens[0])
                # physics_data.broadening_parameters.delta_t_gaus = float(tokens[1])
                # physics_data.broadening_parameters.delta_t_exp = float(tokens[2])
            i += 1
        else:
            i += 1
    
    return fit_results