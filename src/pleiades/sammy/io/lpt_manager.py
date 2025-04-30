# This module imports a results class from the pleiades.sammy.results module
# to create a new class called LptData. The LptData class is filled by reading
# a .LPT file.

from pleiades.nuclear.models import nuclearParameters, IsotopeParameters
from pleiades.experimental.models import PhysicsParameters
from pleiades.sammy.results.models import RunResults, FitResults
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

class LptManager:
    """
    A class to manage and extract results from SAMMY LPT files.
    
    Attributes:
        run_results (RunResults): A container for multiple fit results.
    """
        
    # List of delimiters to split the LPT file content
    lpt_delimiters = [
        "***** INITIAL VALUES FOR PARAMETERS",
        "***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS",
        "***** NEW VALUES FOR RESONANCE PARAMETERS"
    ]

    # If initialize with a filepath then start processing the file
    def __init__(self, file_path: str = None):
        if file_path:
            self.process_lpt_file(file_path)

    def extract_isotope_info(lines, nuclear_data):
        """Extract isotope info and update nuclear_data.isotopes."""
        for idx, line in enumerate(lines):
            if line.strip().startswith('Isotopic abundance and mass for each nuclide'):
                i = idx + 2  # skip header lines
                while i < len(lines) and lines[i].strip():
                    tokens = lines[i].split()
                    if len(tokens) >= 5:
                        nuclide_number = int(tokens[0])
                        abundance = float(tokens[1].split('(')[0])
                        mass = float(tokens[2])
                        spin_groups = [int(s) for s in tokens[4:]]
                        isotope = IsotopeParameters(
                            nuclide_number=nuclide_number,
                            abundance=abundance,
                            mass=mass,
                            spin_groups=spin_groups
                        )
                        print(isotope)
                        #nuclear_data.isotopes.append(isotope)
                    i += 1
                break

    def extract_results_from_string(self,lpt_block_string: str) -> FitResults:
        fit_results = FitResults()
        temp_nuclear_data = nuclearParameters()
        temp_physics_data = PhysicsParameters()
        lines = lpt_block_string.splitlines()

        # Call each extraction function in the order you want
        self.extract_isotope_info(lines, temp_nuclear_data)
        #extract_radius_info(lines, temp_nuclear_data)
        # Add more extraction calls as needed
            
        return fit_results

    def split_lpt_blocks(self, lpt_content: str):
        """
        Splits the LPT file content into blocks for each fit iteration.
        Returns a list of (block_type, block_text) tuples.
        """
        # Define the delimiters
        initial = "***** INITIAL VALUES FOR PARAMETERS"
        intermediate = "***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS"
        new = "***** NEW VALUES FOR RESONANCE PARAMETERS"

        # Find all delimiter positions
        import re
        pattern = f"({re.escape(initial)}|{re.escape(intermediate)}|{re.escape(new)})"
        matches = list(re.finditer(pattern, lpt_content))

        blocks = []
        for i, match in enumerate(matches):
            start = match.start()
            block_type = match.group(0)
            # Determine end of block
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(lpt_content)
            block_text = lpt_content[start:end]
            blocks.append((block_type, block_text))
        return blocks



    def process_lpt_file(self,file_path: str) -> RunResults:
        """
        Process a SAMMY LPT file into blocks of interation results and store them in a
        RunResults object. This function reads the .LPT file, extracts the results of each 
        fit iteration, stores them in a tempurary FitResults objects, and then appends them to a
        RunResults object which is returned.
        
        The RunResults object can be used to access the results of all iterations.
        

        Args:
            file_path (str): Path to the .LPT file.
        """
        
        # Initialize the RunResults object
        run_results = RunResults()

        try:
            with open(file_path, 'r') as file:
                lpt_content = file.read()
                # Log that the file was read successfully
                logger.info(f"Successfully read the file: {file_path}")
                
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")

        # Split the content into blocks based on the delimiter
        
        blocks = self.split_lpt_blocks(lpt_content)
        logger.debug(f"Split LPT content into {len(blocks)} blocks.")
        
        for block_type, block_text in blocks:
            
            print(f"Processing block type: {block_type}")
            # Extract results from the block
            #fit_results = self.extract_results_from_string(block_text)
            
            # Append the fit results to the RunResults object
            #run_results.add_fit_result(fit_results)
        
        return run_results


