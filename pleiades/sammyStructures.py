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
            'sammy_command': 'sammy',       # command to run sammy, 
                                            # compiled should "sammy" & docker should be "sammy-docker"

            'sammy_fit_name': 'sammy_fit',  # name of the sammy fit
            'run_with_endf': False,         # flag to run from endf par file 
            'fit_energy_min': 0.0,          # min energy for sammy fit
            'fit_energy_max': 1.0,          # max energy for sammy fit
            'flight_path_length': 10.0,     # Flight path length
            'fudge_factor': 1.0,            # Sammy fit uncertainty scale factor
            
            # Directories for data, results, and archive
            'directories': {
                'user_defined': False,      # flag to use user defined directories
                'working_dir': '',          # working directory, where pleiades is being called
                'image_dir': '',            # directory for image files
                'data_dir': '',             # directory for data files
                'sammy_fit_dir': '',        # directory for compound par files
                'archive_dir': '.archive',  # directory for archive files (hidden by default)
                'endf_dir': 'endf',         # directory for endf sammy runs
                'fit_results_dir': ''       # directory for fit results
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
                'names': [],  # list of isotope names
                'abundances': [],  # list of corresponding abundances
                'vary_abundances': []  # list of booleans indicating if the abundances should be varied
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
        self._check_or_create_directories()

    def _load_from_config(self, config):
        """ Load parameters from a configuration file.

        Args:
            config (SammyFitConfig): ConfigParser object with the configuration parameters.
        """
        for section in config.sections():
            if section in self.params:
                for key, value in config.items(section):
                    if key in self.params[section]:
                        # Strip quotes and convert value
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
            return value.lower() == 'true'
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

    def _check_or_create_directories(self):
        """ Create working_dir and its subdirectories
            Note: If the flag 'user_defined' is set to True, then the user is responsible for setting all the specific directory paths in the config.ini file.
        """
        # Get the working directory or set it to the current directory if not provided
        working_dir = self.params['directories']['working_dir']
        if not working_dir:
                working_dir = os.getcwd()
                self.params['directories']['working_dir'] = working_dir

        os.makedirs(working_dir, exist_ok=True)

        # Set the directories for the image and data directories
        # Check to see if they are relative or absolute, and if relative then convert to absolute
        if not os.path.isabs(self.params['directories']['data_dir']):
            data_dir = os.path.abspath(self.params['directories']['data_dir'])
        if not os.path.isabs(self.params['directories']['image_dir']):
            image_dir = os.path.abspath(self.params['directories']['image_dir'])


        # if the user has set the directories then we will use them
        if self.params["directories"]["user_defined"] == True:
            archive_dir = self.params['directories']['archive_dir']
            image_dir = self.params['directories']['image_dir']
            data_dir = self.params['directories']['data_dir']
            sammy_fit_dir = self.params['directories']['sammy_fit_dir']
            fit_results_dir = self.params['directories']['fit_results_dir']
            endf_dir = self.params['directories']['endf_dir']

        # otherwise create the subdirectories within the working directory
        else:
            archive_dir = os.path.join(working_dir, self.params['directories']['archive_dir'])
            endf_dir = os.path.join(archive_dir, self.params['directories']['endf_dir'])
            sammy_fit_dir = os.path.join(archive_dir, self.params['directories']['sammy_fit_dir'])
            fit_results_dir = os.path.join(sammy_fit_dir, self.params['directories']['fit_results_dir'])

            # now we need to reset all the path variables with the full paths
            self.params['directories']['image_dir'] = image_dir
            self.params['directories']['data_dir'] = data_dir
            self.params['directories']['fit_results_dir'] = fit_results_dir
            self.params['directories']['archive_dir'] = archive_dir
            self.params['directories']['endf_dir'] = endf_dir
            self.params['directories']['sammy_fit_dir'] = sammy_fit_dir

        # Check to see if directories exists, if they do not then create them
        #os.makedirs(image_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(fit_results_dir, exist_ok=True)
        os.makedirs(archive_dir, exist_ok=True)
        os.makedirs(endf_dir, exist_ok=True)
        os.makedirs(sammy_fit_dir, exist_ok=True)


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