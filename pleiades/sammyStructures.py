import configparser
import os

class SammyFitConfig:
    """Class to store and manage SAMMY fit parameters."""
    
    def __init__(self, config_path=None):
        """ Initialize the SammyFitConfig object.
            config_path (str): Path to a configuration file to load parameters from.
        """
        
        # Default values with sublabels
        self.params = {
            
            # Select method to run SAMMY: 'compiled' or 'docker'
            'sammy_run_method': 'compiled', # options: 'compiled' or 'docker'
            'sammy_command': 'sammy',       # command to run sammy, compiled should be "sammy" & docker should be "sammy-docker"
            'sammy_fit_name': 'sammy_fit',  # name of the sammy fit
            'run_endf_for_par': False,      # flag to run from endf to get parFile
            'use_endf_par_file': False,     # flag to use endf generated parFile for sammy fit
            'fit_energy_min': 0.0,          # min energy for sammy fit
            'fit_energy_max': 1.0,          # max energy for sammy fit
            'flight_path_length': 10.0,     # Flight path length
            'fudge_factor': 1.0,            # Sammy fit uncertainty scale factor
            
            # Directories for data, results, and archive
            'directories': {
                'user_defined': False,      # flag to use user defined directories
                'image_dir': '',            # directory for image files
                'data_dir': '',             # directory for data files
                'working_dir': '',          # working directory, where pleiades is being called
                'sammy_fit_dir': '',        # directory where sammy fit is performed
                'endf_dir': 'endf',         # directory for endf sammy runs
                'iso_results_dir': ''       # directory for isotopic results from fits are stored
            },  
            
            # Sammy fit file names
            'filenames': {
                'data_file_name': 'data.dat',
                'input_file_name': 'input.inp',
                'params_file_name': 'params.par',
                'output_file_name': 'output.out'
            },
            # Isotopes for sammy fit
            'isotopes': {
                'names': [],            # list of isotope names
                'abundances': [],       # list of corresponding abundances
                'vary_abundances': []   # list of booleans indicating if the abundances should be varied
            },

            # Fitting normalization and background
            'normalization': {
                'normalization': 1.0, 'vary_normalization': False,
                'constant_bg': 0.0, 'vary_constant_bg': False,
                'one_over_v_bg': 0.0, 'vary_one_over_v_bg': False,
                'sqrt_energy_bg': 0.0, 'vary_sqrt_energy_bg': False,
                'exponential_bg': 0.0, 'vary_exponential_bg': False,
                'exp_decay_bg': 0.0, 'vary_exp_decay_bg': False,
            },

            # Broadening parameters
            'broadening': {
                'match_radius': 0.0, 'vary_match_radius': False,
                'thickness': 0.0, 'vary_thickness': False,
                'temperature': 295, 'vary_temperature': False,
                'flight_path_spread': 0.0, 'vary_flight_path_spread': False,
                'deltag_fwhm': 0.0, 'vary_deltag_fwhm': False,
                'deltae_us': 0.0, 'vary_deltae_us': False,
            },
            'tzero': {
                't0': 0.0, 'vary_t0': False,
                'L0': 0.0, 'vary_L0': False,
            },
            'delta_L': {
                'delta_L1': 0.0, 'delta_L1_err': '', 'vary_delta_L1': False,
                'delta_L0': 0.0, 'delta_L0_err': '', 'vary_delta_L0': False,
            },
            'delta_E': {
                'DE': 0.0, 'DE_err': '', 'vary_DE': False,
                'D0': 0.0, 'D0_err': '', 'vary_D0': False,
                'DlnE': 0.0, 'DlnE_err': '', 'vary_DlnE': False,
            },
            'resonances': {
                'resonance_energy_min': 0.0,    # min energy for resonances in sammy parFile
                'resonance_energy_max': 1.0,    # max energy for resonances in sammy parFile
            }

        }

        # if a config file is provided, load the parameters from it
        if config_path:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config file {config_path} not found.")
            else:
                config = configparser.ConfigParser()
                config.read(config_path)
                self._load_from_config(config)
            
            # Set sammy_fit_dir to sammy_fit_name if sammy_fit_dir is not provided or is empty
            if not self.params['directories']['sammy_fit_dir']:
                self.params['directories']['sammy_fit_dir'] = self.params['sammy_fit_name']

        # Check and create all needed directories
        self._check_directories()

    def _load_from_config(self, config):
        """ Load parameters from a configuration file.

        Args:
            config (SammyFitConfig): ConfigParser object with the configuration parameters.
        """
        for section in config.sections():
            if section in self.params:
                for key, value in config.items(section):
                    if key in self.params[section]:
                        # Check if the value contains commas (for fields like 'names' and 'abundances')
                        if "," in value:
                            # If the field is "abundances", convert to a list of floats
                            if key == 'abundances':
                                self.params[section][key] = [float(v.strip()) for v in value.split(',')]
                            else:
                                # Otherwise, convert to a list of strings
                                self.params[section][key] = [v.strip() for v in value.split(',')]
                        else:
                            # Handle normal value conversion for non-list fields
                            self.params[section][key] = self._convert_value(self._strip_quotes(value))
            else:
                for key, value in config.items(section):
                    if key in self.params:
                        # Strip quotes and convert value
                        self.params[key] = self._convert_value(self._strip_quotes(value))

    def _convert_value(self, value):
        """ Helper method to convert a string value to the appropriate type.

        Args:
            value (string): The string value to convert.

        Returns:
            float or int: The converted value.
        """
        if value.lower() in ['true', 'false']:
            if value.lower() == 'true':
                return True
            elif value.lower() == 'false':
                return False
            else:
                raise ValueError(f"Invalid boolean value: {value}")
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return value

    def _strip_quotes(self, path):
        """Remove surrounding quotes from a string if they exist.
        """
        return path.strip('"').strip("'")

    def _check_directories(self):
        """ Create working_dir and its subdirectories
            Note: If the flag 'user_defined' is set to True, then the user is responsible for setting all the specific directory paths in the config.ini file.
        """
        # Get the working directory or set it to the current directory if not provided
        working_dir = self.params['directories']['working_dir']
        if not working_dir:
                working_dir = os.getcwd()
                self.params['directories']['working_dir'] = working_dir

        # Check if the working_dir exists, if not create it
        if not os.path.exists(working_dir):
            os.makedirs(working_dir, exist_ok=True)

        # Set the directories for the image and data directories
        # Check to see if they are relative or absolute, and if relative then convert to absolute
        if not os.path.isabs(self.params['directories']['data_dir']):
            data_dir = os.path.abspath(self.params['directories']['data_dir'])
        if not os.path.isabs(self.params['directories']['image_dir']):
            image_dir = os.path.abspath(self.params['directories']['image_dir'])
        
        # Check if the directories exist, if not create them
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        if not os.path.exists(image_dir):
            os.makedirs(image_dir, exist_ok=True)
        
    def print_params(self):
        """Prints the parameters in a nicely formatted way.
        """
        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    print('  ' * indent + str(key) + ':')
                    print_dict(value, indent + 1)
                else:
                    print('  ' * indent + str(key) + ': ' + str(value))

        print_dict(self.params)
        
        
class sammyRunConfig:
    """Class to store and manage parameters needed to execute a SAMMY fit."""
    
    def __init__(self, config: SammyFitConfig=None):
        """ Initialize the sammyRunConfig object.
            config_path (str): Path to a configuration file to load parameters from.
        """
        
        # Default keys and values for sammyRunConfig parameters
        self.params = {
            'sammy_run_method': 'compiled', # options: 'compiled' or 'docker'
            'sammy_command': 'sammy',        # command to run sammy, compiled should be "sammy" & docker should be "sammy-docker"
            'sammy_fit_name': 'sammy_fit',   # name of the sammy fit
            'run_endf_for_par': False,           # flag to run endf to get parFile
            
            'directories': {
                'sammy_fit_dir': '',        # directory where sammy fit is performed
                'input_dir': '',            # directory for input files
                'data_dir': '',             # directory for data files
                'params_dir': '',           # directory for sammy params files
            },
            
            'filenames': {
                'data_file_name': 'data.twenty',       # data file name
                'input_file_name': 'input.inp',     # input file name
                'params_file_name': 'params.par',   # params file name
                'output_file_name': 'output.out'    # output file name
            }
        }
        # if a config file is provided, load the parameters from it
        if config:
            self._convert_from_sammy_fit_config(config)
    
    def _convert_from_sammy_fit_config(self, sammy_fit_config):
        """ Convert a SammyFitConfig object to a sammyRunConfig object.
        
        Args:
            sammy_fit_config (SammyFitConfig): SammyFitConfig object to convert.
        """
        self.params['sammy_run_method'] = sammy_fit_config.params['sammy_run_method']
        self.params['sammy_command'] = sammy_fit_config.params['sammy_command']
        self.params['sammy_fit_name'] = sammy_fit_config.params['sammy_fit_name']
        self.params['run_endf_for_par'] = sammy_fit_config.params['run_endf_for_par']
        self.params['directories']['data_dir'] = sammy_fit_config.params['directories']['data_dir']
        self.params['directories']['sammy_fit_dir'] = sammy_fit_config.params['directories']['sammy_fit_dir']
        self.params['filenames']['data_file_name'] = sammy_fit_config.params['filenames']['data_file_name']
        self.params['filenames']['input_file_name'] = sammy_fit_config.params['filenames']['input_file_name']
        self.params['filenames']['params_file_name'] = sammy_fit_config.params['filenames']['params_file_name']
        self.params['filenames']['output_file_name'] = sammy_fit_config.params['filenames']['output_file_name']
        
    def print_params(self):
        """Prints the parameters in a nicely formatted way.
        """
        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    print('  ' * indent + str(key) + ':')
                    print_dict(value, indent + 1)
                else:
                    print('  ' * indent + str(key) + ': ' + str(value))

        print_dict(self.params)