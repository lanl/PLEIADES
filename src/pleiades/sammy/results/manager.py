from pleiades.sammy.results.models import RunResults, FitResults
from pleiades.sammy.io.lpt_manager import LptManager

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class ResultsManager:
    """
    A class to manage and extract results from SAMMY calculations.
    
    Attributes:
        run_results (RunResults): A container for multiple fit results.
    """
        
    # Initialize a LptManager object to manage the LPT file
    def __init__(
        self,
        lpt_file_path: str = None,
        lst_file_path: str = None,
        par_file_path: str = None,
        inp_file_path: str = None,
    ):
        self.lpt_manager = None
        self.lst_manager = None
        self.par_manager = None
        self.inp_manager = None
        self.run_results = RunResults()

        # Initialize the managers based on the provided file paths
        # If a file path is provided, process the file and extract results.
        if lpt_file_path is not None:
            self.lpt_manager = LptManager(lpt_file_path)
        if lst_file_path is not None:
            # self.lst_manager = LstManager(lst_file_path)  # Implement if needed
            pass
        if par_file_path is not None:
            # self.par_manager = ParManager(par_file_path)  # Implement if needed
            pass
        if inp_file_path is not None:
            # self.inp_manager = InpManager(inp_file_path)  # Implement if needed
            pass
    
    def add_fit_result(self, fit_result: FitResults):
        """Add a FitResults object to the RunResults."""
        self.run_results.add_fit_result(fit_result)
    
    def get_single_fit_results(self, index: int) -> FitResults:
        """Retrieve a single fit result from the list."""
        if self.run_results.fit_results:
            return self.run_results.fit_results[index]
        else:
            raise ValueError("No fit results available.")
    
    