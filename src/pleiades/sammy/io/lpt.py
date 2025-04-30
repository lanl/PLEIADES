# This module imports a results class from the pleiades.sammy.results module
# to create a new class called LptData. The LptData class is filled by reading
# a .LPT file.

from pleiades.sammy.results.models import FitResults, RunResults
from pleiades.sammy.results.manager import extract_results_from_string
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

# List of delimiters to split the LPT file content
lpt_delimiters = [
    "***** INITIAL VALUES FOR PARAMETERS",
    "***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS",
    "***** NEW VALUES FOR RESONANCE PARAMETERS"
]


def split_lpt_blocks(lpt_content: str):
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



def process_lpt_file(file_path: str) -> RunResults:
    """
    Process a SAMMY LPT file into blocks of interation results and store them in a
    RunResults object. This function reads the .LPT file, extracts the results of each 
    fit iteration, stores them in a tempurary FitResults objects, and then appends them to a
    RunResults object which is returned.
    
    The RunResults object can be used to access the results of all iterations.
    

    Args:
        file_path (str): Path to the .LPT file.
    """
    
    temp_fit_results = FitResults()
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
    
    blocks = split_lpt_blocks(lpt_content)
    logger.debug(f"Split LPT content into {len(blocks)} blocks.")
    
    for block_type, block_text in blocks:
        
        # Extract results from the block
        fit_results = extract_results_from_string(block_text)
        
    
    return run_results


