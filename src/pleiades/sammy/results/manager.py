from pleiades.sammy.results.models import RunResults, FitResults
from pleiades.nuclear.models import nuclearParameters
from pleiades.experimental.models import PhysicsParameters
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class ResultsManager:
    """
    A class to manage and extract results from SAMMY calculations.
    
    Attributes:
        run_results (RunResults): A container for multiple fit results.
    """
    
    def __init__(self):
        self.run_results = RunResults()
    
    def add_fit_result(self, fit_result: FitResults):
        """Add a FitResults object to the RunResults."""
        self.run_results.add_fit_result(fit_result)
    
    def get_single_fit_results(self, index: int) -> FitResults:
        """Retrieve a single fit result from the list."""
        if self.fit_results:
            return self.fit_results[index]
        else:
            raise ValueError("No fit results available.")
    
    