import json
from pathlib import Path

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

    # Initialize a LptManager object to manage the LPT file
    def __init__(
        self,
        lpt_file_path: Path = None,
        lst_file_path: Path = None,
    ):
        self.run_results = RunResults()

        # Convert to Path if passed as string
        if lpt_file_path is not None and not isinstance(lpt_file_path, Path):
            lpt_file_path = Path(lpt_file_path)
        if lst_file_path is not None and not isinstance(lst_file_path, Path):
            lst_file_path = Path(lst_file_path)

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

    def print_number_of_fit_results(self):
        """Print the number of fit results."""
        num_fit_results = len(self.run_results.fit_results)
        logger.info(f"Number of fit results: {num_fit_results}")

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

    def plot_transmission(self, override_data_type: bool = False):
        """Plot the transmission data from the results."""
        if self.run_results.data:
            # Check if data type is transmission
            if self.run_results.data.data_type == "TRANSMISSION" or override_data_type:
                self.run_results.data.plot_transmission()
            else:
                logger.warning("Data type is not transmission. Cannot plot.")
        else:
            logger.warning("No results data available for plotting.")

    def plot_cross_section(self, override_data_type: bool = False):
        """Plot the cross-section data from the results."""
        if self.run_results.data:
            if self.run_results.data.data_type == "CROSS_SECTION" or override_data_type:
                self.run_results.data.plot_cross_section()
            else:
                logger.warning("Data type is not cross-section. Cannot plot.")
        else:
            logger.warning("No results data available for plotting.")

    def get_data(self):
        """Get the data from the results."""
        if self.run_results.data:
            return self.run_results.data
        else:
            logger.warning("No results data available.")
            return None
