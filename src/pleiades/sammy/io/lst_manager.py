from pathlib import Path

from pleiades.sammy.data.options import SammyData
from pleiades.sammy.results.models import RunResults


class LstManager:
    """
    LstManager is a class designed to manage and extract results from SAMMY LST files.
    This class provides methods to parse LST files, extract relevant data, and organize
    it into structured objects for further analysis. When initialized, it is passed a RunResults
    object to store the results.

    Attributes:
        lst_file_path (Path): Path to the SAMMY LST file.
        data (SammyData): An instance of SammyData to hold the extracted data.
    Methods:
        __init__(lst_file_path: Path, run_results: RunResults = None):
            Initializes the LstManager with the path to a SAMMY LST file.
        process_lst_file():
            Parses the SAMMY LST file and extracts relevant data in a SammyData object
    """

    def __init__(self, lst_file_path: Path = None, run_results: RunResults = None):
        """
        Initialize the LstManager with the path to a SAMMY LST file.

        Args:
            lst_file_path (Path): Path to the SAMMY LST file.
            run_results (RunResults, optional): A container for multiple fit results.
                If not provided, a new RunResults object will be created.
        """

        if run_results is not None:
            self.run_results = run_results
        else:
            self.run_results = RunResults()

        # If lst_file_path is not None, and file exists, process the file
        if lst_file_path is not None and isinstance(lst_file_path, Path):
            if not lst_file_path.exists():
                raise FileNotFoundError(f"The file {lst_file_path} does not exist.")
            else:
                self.process_lst_file(lst_file_path, self.run_results)

    def process_lst_file(self, lst_file_path: Path, run_results: RunResults):
        """
        Parse the SAMMY LST file and extract relevant data in a SammyData object.
        The SammyData object is stored in self.run_results.data.
        """
        # Create SammyData and load the file
        lst_data = SammyData(data_file=lst_file_path)
        lst_data.load()  # Explicitly load and validate

        # Store in RunResults
        run_results.data = lst_data
