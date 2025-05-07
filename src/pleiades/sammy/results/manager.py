import json

from pleiades.sammy.io.lpt_manager import LptManager
from pleiades.sammy.io.lst_manager import LstManager
from pleiades.sammy.results.models import FitResults, RunResults
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class ResultsManager:
    """
    A class to manage and extract results from SAMMY calculations.

    Attributes:
        run_results (RunResults): A container for multiple fit results.
    """

    # initialize the ResultsManager with a fit result class
    def __init__(self):
        self.run_results = RunResults()

    # Initialize a LptManager object to manage the LPT file
    def __init__(
        self,
        lpt_file_path: str = None,
        lst_file_path: str = None,
    ):
        self.run_results = RunResults()

        # Initialize the managers based on the provided file paths
        # If a file path is provided, process the file and extract results.
        if lpt_file_path is not None:
            self.lpt_manager = LptManager(lpt_file_path, self.run_results)
        if lst_file_path is not None:
            self.lst_manager = LstManager(lst_file_path, self.run_results)

    def add_fit_result(self, fit_result: FitResults):
        """Add a FitResults object to the RunResults."""
        self.run_results.add_fit_result(fit_result)

    def get_single_fit_results(self, index: int) -> FitResults:
        """Retrieve a single fit result from the list."""
        if self.run_results.fit_results:
            return self.run_results.fit_results[index]
        else:
            raise ValueError("No fit results available.")

    def print_fit_result(self, index: int):
        """Print a specific fit result in a readable format."""
        fit_result = self.get_single_fit_results(index)
        if fit_result:
            logger.info(f"Fit Result {index}:\n{json.dumps(fit_result.model_dump(), indent=2, default=str)}")
        else:
            logger.warning(f"No fit result found at index {index}.")

    # Print the run results in a readable format
    def print_run_results(self):
        """Print the run results in a readable format."""
        if self.run_results.fit_results:
            for fit_result in self.run_results.fit_results:
                logger.info(f"Fit Result: {fit_result}")
        else:
            logger.warning("No fit results available.")
            
    def print_results_data(self):
        """Print the results data in a readable format."""
        if self.run_results.data:
            logger.info(f"Results Data: {self.run_results.data}")
        else:
            logger.warning("No results data available.")
