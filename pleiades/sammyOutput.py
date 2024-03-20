import pathlib
from typing import List, Union, Dict, Union
from itertools import takewhile, dropwhile
import configparser
import re
import pandas


class lptResults:
    def __init__(self,filename: str) -> None:
        """
        Initializes the class with the filename to be parsed and prepares the results structure.

        Args:
            filename (str): Path to the LPT file to be analyzed.
        """
        self._filename = filename
        
        # Initialize the results structure. This has two main sections:
        # 1. General information about the run
        # 2. Results of each SAMMY fit iteration 
        self._results = {
            "General": {
                "Emin": "",                     # minimum energy
                "Emax": "",                     # maximum energy
                "Target Element": "",           # target element
                "Atomic Weight": "",            # atomic weight
                "Number of nuclides": "",       # number of nuclides
                "Data Type": "",                # data type
                "Iteration Block Lines": []     # start and end lines of each iteration block
            },
            "Iteration Results": []             # results of each iteration block
        }
        
        self.preprocess_lpt_file()  # Preprocess the LPT file to extract general info and identify iteration blocks
        self.grab_results_of_fits() # Extracts results from each iteration block
        
    def preprocess_lpt_file(self):
        """
        Preprocess the LPT file to extract general info and identify iteration blocks.
        """
        
        # Flags to identify the start of each iteration block
        iteration_start_flags = [
            "***** INITIAL VALUES FOR PARAMETERS",
            "***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS",
            "***** NEW VALUES FOR RESONANCE PARAMETERS"
        ]
        
        # Store the start and end lines of each iteration block
        iteration_start_lines = [] 
        
        # Read the LPT file and extract general information
        with open(self._filename, "r") as lpt_file:
            lines = lpt_file.readlines()
            
        # Loop through each line and extract general information
        for i, line in enumerate(lines):
            # Extract general information
            if line.startswith(" Emin and Emax ="):
                self._results["General"]["Emin"], self._results["General"]["Emax"] = self._parse_emin_emax(line)
            elif line.startswith(" TARGET ELEMENT IS"):
                self._results["General"]["Target Element"] = line.split("IS")[1].strip()
            elif line.startswith(" ATOMIC WEIGHT IS"):
                self._results["General"]["Atomic Weight"] = line.split("IS")[1].strip()
            elif line.startswith(" Number of nuclides is "):
                self._results["General"]["Number of nuclides"] = int(line.split("is")[1].strip())
            
            # Identify the start of each iteration block
            elif any(flag in line for flag in iteration_start_flags):
                iteration_start_lines.append(i)
        
        # Store iteration block start and end lines
        for i, start_line in enumerate(iteration_start_lines):
            if i < len(iteration_start_lines) - 1:
                end_line = iteration_start_lines[i + 1] - 1
            else:
                end_line = len(lines) - 1
            self._results["General"]["Iteration Block Lines"].append([start_line, end_line])        
    
    
    def grab_results_of_fits(self):
        """ grabs the results of each iteration block and stores them in the results structure
        returns: None
        """
        with open(self._filename, "r") as lpt_file:
            lines = lpt_file.readlines()

        for block in self._results["General"]["Iteration Block Lines"]:
            start_line, end_line = block
            iteration_block = lines[start_line:end_line + 1]
            iteration_result = self._parse_iteration_block(iteration_block)
            self._results["Iteration Results"].append(iteration_result)
    
    def _parse_iteration_block(self, block_lines):
        """
        Parses an iteration block and extracts parameters.
        Args:
            block_lines (list): List of lines in the iteration block
        Returns:
            dict: Dictionary containing the iteration results
        """
        iteration_result = {
            "Temperature": "",
            "Thickness": "",
            "DELTA-L": "",
            "DELTA-T-GAUS": "",
            "DELTA-T-EXP": "",
            "NORMALIZATION": "",
            "Backgrounds": {
                "BCKG(CONST)": "",
                "BCKG/SQRT(E)": "",
                "BCKG*SQRT(E)": ""
            },
            "Nuclides": [],
            "Chi2": "",
            "RedChi2": ""
        }

        # Loop through each line in the block and extract parameters
        for i, line in enumerate(block_lines):
            
            # If the line contains TEMPERATURE and THICKNESS, then their information is to follow (next line)
            if "TEMPERATURE" in line and "THICKNESS" in line:
                # Extract temperature and thickness from the line
                match = re.search(r"(\d+\.\d+E[+-]?\d+)\s+(\d+\.\d+E[+-]?\d+)", block_lines[i+1])
                if match:
                    iteration_result["Temperature"] = float(match.group(1))
                    iteration_result["Thickness"] = float(match.group(2))
            
            # If the line contains DELTA-L, DELTA-T-GAUS, and DELTA-T-EXP, then their information is to follow
            elif "DELTA-L" in line and "DELTA-T-GAUS" in line and "DELTA-T-EXP" in line:
                # Extract all three Deltas
                match = re.search(r"(\d+\.\d+E[+-]?\d+)\s+(\d+\.\d+E[+-]?\d+)\s+(\d+\.\d+E[+-]?\d+)", block_lines[i+1])
                if match:
                    iteration_result["DELTA-L"] = float(match.group(1))
                    iteration_result["DELTA-T-GAUS"] = float(match.group(2))
                    iteration_result["DELTA-T-EXP"] = float(match.group(3))
            
            # If the line contains CUSTOMARY CHI SQUARED, then it also contains the chi squared
            elif " CUSTOMARY CHI SQUARED =" in line:
                match = re.search(r"CUSTOMARY CHI SQUARED =\s*([+-]?[0-9]*\.?[0-9]*(?:[Ee][+-]?[0-9]+)?)",line)
                if match:
                    iteration_result["Chi2"] = float(match.group(1))
            
            # If the line contains CUSTOMARY CHI SQUARED DIVIDED BY NDAT, then it also contains the reduced chi squared
            elif " CUSTOMARY CHI SQUARED DIVIDED BY NDAT =" in line:
                match = re.search(r"CUSTOMARY CHI SQUARED DIVIDED BY NDAT =\s*([+-]?[0-9]*\.?[0-9]*(?:[Ee][+-]?[0-9]+)?)",line)
                if match:
                    iteration_result["RedChi2"] = float(match.group(1))
            
            # If the line contains Nuclide, Abundance, Mass, and Spin groups, then information on the nuclides is to follow
            elif " Nuclide" in line and "Abundance" in line and "Mass" in line and "Spin groups" in line:
                # Extract nuclide information
                for j in range(self._results["General"]["Number of nuclides"]):
                    iteration_result["Nuclides"].append({
                        "Number": block_lines[i+j+1][0:12].strip(),
                        "Abundance": block_lines[i+j+1][12:22].strip(),
                        "Vary Flag": block_lines[i+j+1][22:27].strip(),
                        "Mass": block_lines[i+j+1][33:40].strip(),
                        "SpinGroups": block_lines[i+j+1][40:].strip()
                    })              
        
        return iteration_result
        
    def _parse_emin_emax(self, line):
        """Parses Emin and Emax values from a given line.

        Args:
            line (str): Line containing Emin and Emax values

        Returns:
            tuple: Tuple containing Emin and Emax values
        """
        # Ensure the regex pattern matches scientific notation accurately
        match = re.search(r"Emin and Emax =\s*([+-]?[0-9]*\.?[0-9]*(?:[Ee][+-]?[0-9]+)?)\s+([+-]?[0-9]*\.?[0-9]*(?:[Ee][+-]?[0-9]+)?)", line)
        if match:
            emin = float(match.group(1))
            emax = float(match.group(2))
            return emin, emax
        else:
            return None, None


class LptFile:
    # utilities to read and parse an LPT output file

    def __init__(self,filename: str) -> None:
        """Reads a .lpt file

        Args:
            filename (str): SAMMY output file with .lpt extension
        """
        self._filename = filename
        
        LPT_SEARCH_PATTERNS = { 
            "input_file":dict(start_text=" Name of input file", skipped_rows=1,line_format="line.split()[1]"),
            "par_file":dict(start_text=" Name of parameter file", skipped_rows=1, line_format="line.split()[1]"),
            "Emin":dict( start_text=" Emin and Emax", skipped_rows=0, line_format="float(line.split()[4])"),
            "Emax":dict( start_text=" Emin and Emax", skipped_rows=0, line_format="float(line.split()[5])"),
            "thickness":dict( start_text="  TEMPERATURE      THICKNESS",skipped_rows=1, line_format="float(line.split()[1])"),
            "varied_params":dict( start_text=" Number of varied parameters", skipped_rows=0, line_format="int(line.split()[5])"),
            "reduced_chi2":dict( start_text=" CUSTOMARY CHI SQUARED DIVIDED", skipped_rows=0, line_format="float(line.split()[7])"),
            "flight_path_length":dict( start_text="    Flight Path=", skipped_rows=0,line_format="float(line.split()[2])"),
            "time_elapsed":dict( start_text="                              Total time", skipped_rows=0,line_format="float(line.split()[3])"),
        }
        
        
    
        self.LPT_SEARCH_PATTERNS = LPT_SEARCH_PATTERNS

        self.params = ParamsConfig(self)
            

    def stats(self) -> dict:
        """parse and collect statistical data from a SAMMY.LPT file
        
        Returns (dict): formatted statistical data from the run
        """        
        stats = {}
        # loop over all search patterns
        for pattern_key in self.LPT_SEARCH_PATTERNS:
            with open(self._filename,"r") as fid:
                for line in fid:
                    pattern = self.LPT_SEARCH_PATTERNS[pattern_key]    
                    if line.startswith(pattern["start_text"]):
                        # skip requested number of rows
                        [line:=next(fid) for row in range(pattern["skipped_rows"])]
                        # update the stats dictionary
                        try:
                            stats[pattern_key] = eval(pattern["line_format"])
                        except:
                            import warnings
                            warnings.warn(f"pattern key: {pattern_key} has returned wrong parsing result")

        return stats
    

    def register_new_stats(self,keyname: str, start_text: str, skipped_rows: str, line_format: str ) -> None:
        """
        Registers a search pattern for parsing statistical values from the .lpt file.

        Args:
            - keyname (str): The name of the requested parameter.
            - start_text (str): A string used for line.startswith search to identify relevant lines.
            - skipped_rows (int): The number of rows to skip from the 'start_text' during parsing.
            - line_format (str): Python code snippet used to parse the line for the requested value.
                                Typically, this would be a split method on the input `line` variable.

        Example:
        Register a search pattern for temperature values in the .lpt file:
        >>> from pleiades import sammyOutput
        >>> sammyOutput.register_search_pattern(keyname="temperature", start_text="  TEMPERATURE",
                                                skipped_rows=1, line_format="float(line.split()[0])")
        """
        self.LPT_SEARCH_PATTERNS[keyname] = dict(start_text=start_text,
                                                 skipped_rows=skipped_rows,
                                                 line_format=line_format)
        
    def register_normalization_stats(self, register_vary:bool = False) -> None:
        """
        register six normalization params to the `stats` method

        Args:
            - register_vary: (bool) if True register also the vary parameters
        """
        self.register_new_stats("normalization","   NORMALIZATION", 1, "float(line[1:12])")
        self.register_new_stats("constant_bg","   NORMALIZATION", 1, "float(line[18:29])")
        self.register_new_stats("one_over_v_bg","   NORMALIZATION", 1, "float(line[35:46])")
        self.register_new_stats("sqrt_energy_bg","   NORMALIZATION", 1, "float(line[52:63])")
        self.register_new_stats("exponential_bg","    BCKG*EXP(.)", 1, "float(line[1:12])")
        self.register_new_stats("exp_decay_bg","    BCKG*EXP(.)", 1, "float(line[18:29])")

        if register_vary:
            self.register_new_stats("vary_normalization","   NORMALIZATION", 1, "1 if line[13:17].strip() else 0")
            self.register_new_stats("vary_constant_bg","   NORMALIZATION", 1, "1 if line[30:34].strip() else 0")
            self.register_new_stats("vary_one_over_v_bg","   NORMALIZATION", 1, "1 if line[47:51].strip() else 0")
            self.register_new_stats("vary_sqrt_energy_bg","   NORMALIZATION", 1, "1 if line[64:68].strip() else 0")
            self.register_new_stats("vary_exponential_bg","    BCKG*EXP(.)", 1, "1 if line[13:17].strip() else 0")
            self.register_new_stats("vary_exp_decay_bg","    BCKG*EXP(.)", 1, "1 if line[30:34].strip() else 0")

    

    def register_broadening_stats(self, register_vary:bool = False) -> None:
        """
        register five broadening params to the `stats` method

        Args:
            - register_vary: (bool) if True register also the vary parameters
        """
        self.register_new_stats("temperature","  TEMPERATURE      THICKNESS", 1, "float(line[1:12])")
        self.register_new_stats("thickness","  TEMPERATURE      THICKNESS", 1, "float(line[18:29])")
        self.register_new_stats("flight_path_spread","    DELTA-L         DELTA-T-GAUS", 1, "float(line[1:12])")
        self.register_new_stats("deltag_fwhm","    DELTA-L         DELTA-T-GAUS", 1, "float(line[18:29])")
        self.register_new_stats("deltae_us","    DELTA-L         DELTA-T-GAUS", 1, "float(line[35:46])")

        if register_vary:
            self.register_new_stats("vary_temperature","  TEMPERATURE      THICKNESS", 1, "1 if line[12:17].strip() else 0")
            self.register_new_stats("vary_thickness","  TEMPERATURE      THICKNESS", 1, "1 if line[29:34].strip() else 0")
            self.register_new_stats("vary_flight_path_spread","    DELTA-L         DELTA-T-GAUS", 1, "1 if line[12:17].strip() else 0")
            self.register_new_stats("vary_deltag_fwhm","    DELTA-L         DELTA-T-GAUS", 1, "1 if line[29:34].strip() else 0")
            self.register_new_stats("vary_deltae_us","    DELTA-L         DELTA-T-GAUS", 1, "1 if line[46:51].strip() else 0")


    def register_misc_stats(self, register_vary:bool = False) -> None:
        """
        register misc params to the `stats` method

        Args:
            - register_vary: (bool) if True register also the vary parameters
        """
        self.register_new_stats("t0","    t-zero", 0, "float(line[13:24])")
        self.register_new_stats("L0","    t-zero", 0, "float(line[42:53])")
        self.register_new_stats("delta_L1","    Delta-L", 0, "float(line[13:24])")
        self.register_new_stats("delta_L0","    Delta-L", 0, "float(line[50:61])")
        self.register_new_stats("DE","    Delta-E=", 0, "float(line[13:24])")
        self.register_new_stats("D0","    Delta-E=", 0, "float(line[52:63])")
        self.register_new_stats("DlnE","    Delta-E=", 1, "float(line[13:24])")


        if register_vary:
            self.register_new_stats("vary_t0","    t-zero", 0, "1 if line[24:29].strip() else 0")
            self.register_new_stats("vary_L0","    t-zero", 0, "1 if line[53:58].strip() else 0")
            self.register_new_stats("vary_delta_L1","    Delta-L", 0, "1 if line[24:29].strip() else 0")
            self.register_new_stats("vary_delta_L0","    Delta-L", 0, "1 if line[61:66].strip() else 0")
            self.register_new_stats("vary_DE","    Delta-E=", 0, "1 if line[24:29].strip() else 0")
            self.register_new_stats("vary_D0","    Delta-E=", 0, "1 if line[63:68].strip() else 0")
            self.register_new_stats("vary_DlnE","    Delta-E=", 1, "1 if line[24:29].strip() else 0")                            

        
    def register_abundances_stats(self,isotopes:list =[]) -> None:
        """
        register final isotopic abundances

        Args:
            - isotopes (list): A list of isotope names, in the order added to the compound par file
                               in case of empty list, pleiades will try to read the first 5 isotopes and assign them with numbers 
        """
        if isotopes:
            for num,isotope in enumerate(isotopes):
                self.register_new_stats(f"{isotope}"," Nuclide    Abundance", num+1, "float(line[12:18])")
        else:
            for num in range(5):
                self.register_new_stats(f"weight_{num}"," Nuclide    Abundance", num+1, "float(line[12:18])")            


    def param_table(self, only_vary:bool = True,
                    dataframe:bool = True) -> Union[dict,"pandas.DataFrame"]:
        """get a table of parameters and uncertainties

        Args:
            only_vary (bool): if True, return only the varied parameters
            dataframe (bool, default True): if True return a pandas.DataFrame, otherwise return a dictionary
        """
        # get the part of the LPT file that has the final parameters listed
        with open(self._filename,"r") as fid:
            parameter_lines = list(takewhile(lambda line: not line.startswith(' ***** CORRELATION MATRIX FOR OUTPUT PARAMETERS'),
                                            dropwhile(lambda line: not line.startswith(' ***** NEW VALUES FOR RESONANCE PARAMETERS'), fid)))
        
        # get the part of the LPT file that has the correleation matrix listed
        with open(self._filename,"r") as fid:
            uncertainty_lines = list(takewhile(lambda line: not line.startswith(" ***** RATIO OF UNCERTAINTIES ON VARIED PARAMETERS "),
                                            dropwhile(lambda line: not line.startswith(' ***** CORRELATION MATRIX FOR OUTPUT PARAMETERS'), fid)))

        params = {}    
        for line in parameter_lines:
            for match in re.compile(r'([0-9.]+(?:[eE][+-]?\d+)?)\s*\(\s*(\d+)\)').finditer(line):
                if match:
                    params[int(match.group(2))] = float(match.group(1))

        uncertainties = {}    

        for line in uncertainty_lines:
            try:
                uncertainties[len(uncertainties)+1] = float(line[5:15])
            except:
                pass
        
        # get a dictionary of vary parameters
        

        
        initial_params = self.params.get_vary_params(only_vary=True)
        if uncertainties:
            final_params = {vary_key:(params[key], uncertainties[key],"1") for vary_key,key in zip(initial_params,params)}
        else:
            final_params = {vary_key:(params[key], "","1") for vary_key,key in zip(initial_params,params)}
        if only_vary:
            initial_params.update(final_params)
        else:
            all_initial_params = self.params.get_vary_params(only_vary=False)
            initial_params = {key:(all_initial_params[key] if key not in final_params else final_params[key]) for key in all_initial_params }

        self.final_params = initial_params # this is an updated copy of initial_params

        if dataframe:
            return pandas.DataFrame(self.final_params,index=["param","uncertainty","vary"]).T
        else:
            return initial_params

        
        


    def commands(self) -> list:
        """parse and collect the alphanumeric command cards from a SAMMY.LPT file
        
            Returns (list): of alphanumeric commands used in SAMMY run
        """        
        with open(self._filename,"r") as fid:
            for line in fid:
                if line.startswith(" *********** Alphanumeric Control Information"):
                    line = next(fid)
                    cards = []
                    while not line.startswith(" **** end"):
                        if line.strip():
                            cards.append(line.replace("\n","").strip())
                        line = next(fid)
                        
        return cards
    

class ParamsConfig:
    # utilities to parse and read param config files

    def __init__(self, parent: "LptFile") -> None:
        """
        utilities to read and parse param config files
        """
        self.parent = parent
        self._archivepath = pathlib.Path(self.parent._filename).parent.parent
        

        self.load_initial();

    
    def load_initial(self, filename: str="params.ini") -> dict:
        # loads the intial_config file and update internal self.data params
        inifilename = self._archivepath / "params.ini"
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(inifilename)
        self.params = {key:dict(config[key]) for key in config.sections()}
        # make also a flatten_params object, where all dictionaries are normalized to parent
        self.flatten_params = {}
        for key in self.params:
            self.flatten_params.update(self.params[key])

        return self.params
    
    def get_vary_params(self, only_vary: bool=True) -> dict:
        """get a list of all vary params

        Args:
            only_vary (bool): if True, return only params which has are varied, otherwise return both varied and fixed params
        Returns:
            dict of vary_params and vary values
        """
        if only_vary:
            vary_params = {key:value for key,value in self.flatten_params.items() if key.startswith("vary_") and value=="1"}
        else:
            vary_params = {key:value for key,value in self.flatten_params.items() if key.startswith("vary_")}

        # sort according to order of parameters as they appear in the LPT file
        params_order = ["isotopes","temperature","thickness",
                        "flight_path_spread","deltag_fwhm","deltae_us",
                        "delta_L1","delta_L0",
                        "t0","L0",
                        "DE","D0","DlnE",
                        "normalization","constant_bg",
                        "one_over_v_bg","sqrt_energy_bg",
                        "exponential_bg","exp_decay_bg"]
        sorted_params = {}
        # populatet isotopes first:
        for isotope in eval(self.flatten_params["isotopes"]):
            if only_vary:
                if self.flatten_params[f"vary_{isotope}"] == "1":
                    sorted_params[isotope] = (self.flatten_params[isotope],0.,self.flatten_params[f"vary_{isotope}"])
            else:
                sorted_params[isotope] = (self.flatten_params[isotope],0.,self.flatten_params[f"vary_{isotope}"])

        for key in params_order:
            if f"vary_{key}" in vary_params:
                # return param, error, vary
                sorted_params[key] = (self.flatten_params[key],0.,vary_params[f"vary_{key}"])   

        return sorted_params


