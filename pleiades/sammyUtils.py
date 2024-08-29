# High level utility functions to use Pleiades functionality to run SAMMY

import matplotlib.pyplot as plt
import numpy as np

import pathlib
from pathlib import Path

import pandas
import pathlib
import re
import configparser
import os

from pleiades import sammyParFile, sammyInput, sammyRunner, nucData

PWD = pathlib.Path(__file__).parent

class SammyFitConfig:
    """Class to store and manage SAMMY fit parameters."""
    def __init__(self, config_path=None):
        # Default values with sublabels
        self.params = {
            
            # Select method to run SAMMY: 'compiled' or 'docker'
            'sammy_run_method': 'compiled', # options: 'compiled' or 'docker'
            'sammy_command': 'sammy',       # command to run sammy, 
                                            # compiled should "sammy" & docker should be "sammy-docker"

            'run_with_endf': False,         # flag to run from endf par file 
            'fit_energy_min': 0.0,          # min energy for sammy fit
            'fit_energy_max': 1.0,          # max energy for sammy fit
            'flight_path_length': 10.0,     # Flight path length
            'fudge_factor': 1.0,            # Sammy fit incrementation
            
            # Directories for data, results, and archive
            'directories': {
                'user_defined': False,      # flag to use user defined directories
                'working_dir': '',          # working directory, where pleiades is being called
                'image_dir': '',            # directory for image files
                'data_dir': 'data',         # directory for data files
                'sammy_fit_dir': '',        # directory for compound par files
                'archive_dir': '.archive',  # directory for archive files (hidden by default)
                'endf_dir': 'endf',         # directory for endf sammy runs
                'fit_results_dir': ''       # directory for fit results
            },  
            
            # Sammy fit file names
            'filenames': {
                'data_file_name': 'data.dat',
                'input_file_name': 'input.inp',
                'params_file_name': 'params.par'
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

        if config_path:
            config = configparser.ConfigParser()
            config.read(config_path)
            self._load_from_config(config)

        self._check_or_create_directories()

    def _load_from_config(self, config):
        """ Load parameters from a configuration file.

        Args:
            config (SammyFitConfig): ConfigParser object with the configuration parameters.
        """
        for section in config.sections():

            # If the section is 'isotopes' then process the potential arrays for names, abundances, and vary_abundances.
            if section == 'isotopes':
                self.params['isotopes']['names'] = [x for x in config.get('isotopes', 'names').split(',')]
                self.params['isotopes']['abundances'] = [float(x) for x in config.get('isotopes', 'abundances').split(',')]
                self.params['isotopes']['vary_abundances'] = [self._convert_value(x) for x in config.get('isotopes', 'vary_abundances').split(',')]
            
            # If the section is 'directories' 
            elif section == 'directories':
                for key, value in config.items(section):
                    if key in self.params['directories']:
                        self.params['directories'][key] = self._strip_quotes(value)
            
            # If the section is 'filenames' 
            elif section == 'filenames':
                for key, value in config.items(section):
                    if key in self.params['filenames']:
                        self.params['filenames'][key] = self._strip_quotes(value)
            
            elif section == 'main':
                self.params['sammy_run_method'] = self._strip_quotes(config.get('main', 'sammy_run_method'))
                self.params['sammy_command'] = self._strip_quotes(config.get('main', 'sammy_command'))
                self.params['run_with_endf'] = self._convert_value(config.get('main', 'run_with_endf'))
                self.params['fit_energy_min'] = float(config.get('main', 'fit_energy_min'))
                self.params['fit_energy_max'] = float(config.get('main', 'fit_energy_max'))
                self.params['flight_path_length'] = float(config.get('main', 'flight_path_length'))
                self.params['fudge_factor'] = float(config.get('main', 'fudge_factor'))
            
            elif section == 'resonances':
                self.params['resonances']['resonance_energy_min'] = float(config.get('resonances', 'resonance_energy_min'))
                self.params['resonances']['resonance_energy_max'] = float(config.get('resonances', 'resonance_energy_max'))
                    
            else:
                for key, value in config.items(section):
                    if key in self.params[section]:
                        self.params[section][key] = self._convert_value(value)

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
            fit_results_dir = os.path.join(working_dir, self.params['directories']['fit_results_dir'])
            archive_dir = os.path.join(working_dir, self.params['directories']['archive_dir'])
            endf_dir = os.path.join(archive_dir, self.params['directories']['endf_dir'])
            sammy_fit_dir = os.path.join(archive_dir, self.params['directories']['sammy_fit_dir'])

            # now we need to reset all the path variables with the full paths
            self.params['directories']['image_dir'] = image_dir
            self.params['directories']['data_dir'] = data_dir
            self.params['directories']['fit_results_dir'] = fit_results_dir
            self.params['directories']['archive_dir'] = archive_dir
            self.params['directories']['endf_dir'] = endf_dir
            self.params['directories']['sammy_fit_dir'] = sammy_fit_dir

        # Check to see if directories exists, if they do not then create them
        os.makedirs(image_dir, exist_ok=True)
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


def create_parFile_from_endf(config: SammyFitConfig, archive: bool = True, verbose_level: int = 0) -> None:
    """
    Generates a SAMMY input file and runs SAMMY with ENDF data to produce a `.par` file
    for the specified isotope. 

    This function creates a SAMMY input file based on a configuration file, modifies relevant
    cards for the target isotope, saves the input file, and then runs SAMMY with ENDF data
    to generate the corresponding `.par` file.

    Args:
        config (SammyFitConfig): SammyFitConfig object containing the configuration parameters.
        archive (bool, optional): Flag for storing sammy files. Defaults to False.
        verbose_level (int, optional): 0: no printing, 1: prints general info, 2: prints data. Defaults to 0.
    """
    
    isotopes = config.params['isotopes']['names']
    flight_path_length = config.params['flight_path_length']
    endf_dir = config.params['directories']['endf_dir']
    archive_dir = config.params['directories']['archive_dir']
    
    for isotope in isotopes:
        
        # Create a SAMMY input file data structure
        inp = sammyInput.InputFile()

        # Update input data with isotope-specific information
        inp.data["Card2"]["elmnt"] = isotope
        inp.data["Card2"]["aw"] = "auto"
        inp.data["Card5"]["dist"] = flight_path_length
        inp.data["Card5"]["deltag"] = 0.001
        inp.data["Card5"]["deltae"] = 0.001
        inp.data["Card7"]["crfn"] = 0.001
        #TODO: Need a way to figure out the resonance emin and emax of the ENDF res file and set them here. 

    
        #TODO: Need to figure out a better way to deal with commands in card3.
        # Resetting the commands for running SAMMY to generate output par files based on ENDF.
        inp.data["Card3"]['commands'] = 'TWENTY,DO NOT SOLVE BAYES EQUATIONS,INPUT IS ENDF/B FILE'
    
        # Print the input data structure if desired
        if verbose_level > 1: print(inp.data)
    
        # Create a run name or handle based on the isotope name
        sammy_run_handle = isotope.replace("-", "").replace("_", "")
        sammy_input_file_name = sammy_run_handle + ".inp"
    
        # Check if archive is True and create the .archive directory if it doesn't exist
        if archive:
            endf_dir_path = pathlib.Path(endf_dir)
            endf_dir_path.mkdir(parents=True, exist_ok=True)
            if verbose_level > 0:
                print(f"ENDF directory created at {endf_dir_path}")
            
            # Create a directory in the endf_dir_path that corresponds to the sammy_run_handle
            output_dir = endf_dir_path / Path(sammy_run_handle)
            
            # add new output directory to the archive_path
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a SAMMY input file in the output directory
            sammy_input_file = output_dir / (sammy_input_file_name)
            
            if verbose_level > 0: print(f"SAMMY input file created at {sammy_input_file}")
            
        else:
            # determine the current working directory
            output_dir = Path.cwd()
            sammy_input_file = output_dir / (sammy_input_file_name)

        # Write the SAMMY input file to the specified location. 
        inp.process().write(sammy_input_file)
    
        # Run SAMMY with ENDF data to generate .par file
        sammyRunner.run_endf(run_handle = sammy_run_handle, 
                            endf_dir=output_dir,
                            input_file=sammy_input_file_name,
                            verbose_level=verbose_level)
                    
        #TODO: Need to add a check to see if the .par file was created successfully and print a message if not.        




def configure_sammy_run(config: SammyFitConfig, verbose_level: int = 0):
    """
    Configures SAMMY based on a SammyFitConfig object.

    This function takes a SammyFitConfig object and uses the parameters to
    configure the files needed to run SAMMY. It creates a SAMMY input file, modifies the
    relevant cards based on the configuration, saves the input file. It then creates a SAMMY
    parameter file by summing the par files for the isotopes specified in the configuration.
    Finally, it creates a symlink for the data file into the sammy_fit_dir.

    Args:
        config (SammyFitConfig): SammyFitConfig object containing the configuration parameters.
    """
    isotopeParFiles = []
    
    # setting up the directories that we will need to use
    archive_dir = config.params['directories']['archive_dir']
    endf_dir = config.params['directories']['endf_dir']
    sammy_fit_dir = config.params['directories']['sammy_fit_dir']
    data_dir = config.params['directories']['data_dir']
    
    # Grabbing the isotopes, abundances, and fudge factor from the config file
    isotopes = config.params['isotopes']['names']
    abundances = config.params['isotopes']['abundances']
    fudge_factor = config.params['fudge_factor']
    
    # setting the resonance energy min and max, this will clip the resonances in the parFile to the specified energy range
    res_emin = config.params['resonances']['resonance_energy_min']
    res_emax = config.params['resonances']['resonance_energy_max']
    
    # Create a SAMMY parFile for each isotope 
    if verbose_level > 0: print(f"Creating SAMMY parFile files for isotopes: {isotopes} with abundances: {abundances}")

    for isotope, abundance in zip(isotopes, abundances):
        # Get rid of any dashes or underscores in the isotope name
        isotope = isotope.replace("-", "").replace("_", "")
        # Append sammy parFiles using sammyParFile in the ParFile class
        isotopeParFiles.append(sammyParFile.ParFile(filename=f"{endf_dir}/{isotope}/results/SAMNDF.PAR", name = isotope, weight=abundance, emin=res_emin, emax=res_emax).read())

    # Create a output parFile by summing the isotope parFiles
    outputParFile = isotopeParFiles[0] # set the first isotope as the output
    
    # loop through the rest of the isotopes and add them to the output
    for isotopeParFile in isotopeParFiles[1:]:
        outputParFile = outputParFile +  isotopeParFile

    # we want to fit abundances in this case
    # TODO: Need to implement a method to toggle the vary flag for all abundances
    outputParFile.update.toggle_vary_abundances(vary=True)
    
    # change the fudge-factor that essentially responsible for the fit step-size
    # it only has a minor effect on results
    outputParFile.data["info"]["fudge_factor"] = fudge_factor

    # Set broadening parameters based on the configuration
    broadening_args = {
        'match_radius': config.params['broadening']['match_radius'],
        'temperature': config.params['broadening']['temperature'],
        'thickness': config.params['broadening']['thickness'],
        'flight_path_spread': config.params['broadening']['flight_path_spread'],
        'deltag_fwhm': config.params['broadening']['deltag_fwhm'],
        'deltae_us': config.params['broadening']['deltae_us'],
        'vary_match_radius': int(config.params['broadening']['vary_match_radius'] == True),
        'vary_thickness': int(config.params['broadening']['vary_thickness'] == True),
        'vary_temperature': int(config.params['broadening']['vary_temperature'] == True),
        'vary_flight_path_spread': int(config.params['broadening']['vary_flight_path_spread'] == True),
        'vary_deltag_fwhm': int(config.params['broadening']['vary_deltag_fwhm'] == True),
        'vary_deltae_us': int(config.params['broadening']['vary_deltae_us'] == True)
        }
    outputParFile.update.broadening(**broadening_args)

    # Set normalization parameters based on the configuration
    normalization_args = {
        'normalization': float(config.params['normalization']['normalization']),
        'constant_bg': float(config.params['normalization']['constant_bg']),
        'one_over_v_bg': float(config.params['normalization']['one_over_v_bg']),
        'sqrt_energy_bg': float(config.params['normalization']['sqrt_energy_bg']),
        'exponential_bg': float(config.params['normalization']['exponential_bg']),
        'exp_decay_bg': float(config.params['normalization']['exp_decay_bg']),
        'vary_normalization': int(config.params['normalization']['vary_normalization'] == True),
        'vary_constant_bg': int(config.params['normalization']['vary_constant_bg'] == True),
        'vary_one_over_v_bg': int(config.params['normalization']['vary_one_over_v_bg'] == True),
        'vary_sqrt_energy_bg': int(config.params['normalization']['vary_sqrt_energy_bg'] == True),
        'vary_exponential_bg': int(config.params['normalization']['vary_exponential_bg'] == True),
        'vary_exp_decay_bg': int(config.params['normalization']['vary_exp_decay_bg'] == True)
    }
    outputParFile.update.normalization(**normalization_args)

    # write out the output par file
    #TODO: fix hard coding of parFile name
    output_par_file = Path(archive_dir) / Path(sammy_fit_dir) / Path('params').with_suffix(".par")
    if verbose_level > 0: print(f"Writing output parFile: {output_par_file}")
    outputParFile.write(output_par_file)

    # Now create a SAMMY input file
    if verbose_level > 0: print(f"Creating SAMMY inpFile files for isotopes: {isotopes} with abundances: {abundances}")
    
    # Create an inpFile from 
    inp = sammyInput.InputFile(verbose_level=verbose_level)

    # find the lowest atomic number isotope and set it as the element
    lowest_atomic_isotope = min(isotopes, key=lambda isotope: nucData.get_mass_from_ame(isotope))
    
    # Update input data with isotope-specific information
    inp.data["Card2"]["elmnt"] = lowest_atomic_isotope 
    inp.data["Card2"]["aw"] = "auto"
    inp.data["Card2"]["emin"] = config.params['fit_energy_min']
    inp.data["Card2"]["emax"] = config.params['fit_energy_max']
    inp.data["Card5"]["dist"] = config.params['flight_path_length']
    inp.data["Card5"]["deltag"] = 0.001
    inp.data["Card5"]["deltae"] = 0.001
    inp.data["Card7"]["crfn"] = 0.001

    #TODO: Need to figure out a better way to deal with commands in card3.
    # Resetting the commands for running SAMMY to generate output par files based on ENDF.
    inp.data["Card3"]['commands'] = 'CHI_SQUARED,TWENTY,SOLVE_BAYES,QUANTUM_NUMBERS,REICH-MOORE FORMALISm is wanted,GENERATE ODF FILE AUTOMATICALLY,USE I4 FORMAT TO READ SPIN GROUP NUMBER'

    # Print the input data structure if desired
    if verbose_level > 1: print(inp.data)
    
    # Create a run name or handle for the compound inpFile
    #TODO: fix hard coding of inpFile name
    output_inp_file = Path(sammy_fit_dir) / Path('input').with_suffix(".inp")

    # Write the SAMMY input file to the specified location. 
    inp.process().write(output_inp_file)
    if verbose_level > 0: print(f"Created compound input file: {output_inp_file}")

    # Create a symbolic link inside the sammy_fit_dir that points to the data file 
    data_file = os.path.join(data_dir, config.params['filenames']['data_file_name'])
    data_file_name = pathlib.Path(data_file).name

    if verbose_level > 0: print(f"Symlinking data file: {data_file} into {sammy_fit_dir}")

    # Check if the symbolic link already exists
    symlink_path = pathlib.Path(sammy_fit_dir) / data_file_name
    if os.path.islink(symlink_path):
        os.unlink(symlink_path)  # unlink old symlink

    os.symlink(data_file, pathlib.Path(sammy_fit_dir) / data_file_name)   # create new symlink

'''
def run_sammy(config: SammyFitConfig, verbose_level: int = 0):
    """
    Runs SAMMY based on a SammyFitConfig object.

    This function takes a SammyFitConfig object and uses it to run sammy. 

    Args:
        config (SammyFitConfig): SammyFitConfig object containing the configuration parameters.
    """
    sammy_call_method = config.params['sammy_run_method']
    sammy_fit_dir = config.params['directories']['sammy_fit_dir']
    data_dir = config.params['directories']['data_dir']
    input_file = config.params['filenames']['input_file_name']
    parameter_file = config.params['filenames']['params_file_name']
    data_file = data_dir +"/"+ config.params['filenames']['data_file_name']

    sammyRunner.run_sammy_fit(sammy_call_method, sammy_fit_dir, input_file, parameter_file, data_file, verbose_level=verbose_level)

    # Check the output file in the sammy_fit_dir to see if SAMMY executed successfully. 
    output_file = config.params['directories']['sammy_fit_dir']+"/output.out"
    
    # Open the output_file and check for the line " Normal finish to SAMMY"
    with open(output_file, 'r') as file:
        data = file.read()
        if "Normal finish to SAMMY" in data:
            sammy_success = True
            if verbose_level > 0: print("SAMMY executed successfully.")
        else:
            sammy_success = False
            print("SAMMY failed to execute a fit.")
            print("Check the output file for more information: ", output_file)

    return sammy_success

#-------------------------------------------------------------------------    

def sammy_background(energy: np.ndarray, normalization: float = 1.0,
                     constant_bg: float = 0.0, one_over_v_bg: float = 0.0,
                     sqrt_energy_bg: float = 0.0, exponential_bg: float = 0.0,
                     exp_decay_bg: float = 0.0) -> np.ndarray:
    """Calculates the Sammy background function for a given energy array.

    This function implements the background parametrization used by the
    SAMMY code for neutron spectroscopy.

    Args:
        energy (np.ndarray): Array of energy bins in eV.
        normalization (float, optional): Overall normalization factor for the background (default: 1.0).
        constant_bg (float, optional): Constant background term (default: 0.0).
        one_over_v_bg (float, optional): Coefficient for the 1/v term (default: 0.0).
        sqrt_energy_bg (float, optional): Coefficient for the sqrt(E) term (default: 0.0).
        exponential_bg (float, optional): Pre-exponential factor for the exponential term (default: 0.0).
        exp_decay_bg (float, optional): Decay constant for the exponential term (default: 0.0).

    Returns:
        np.ndarray: The calculated background array with the same shape as the input energy array.
    """

    bg = constant_bg + one_over_v_bg / np.sqrt(energy) + sqrt_energy_bg * np.sqrt(energy) + exponential_bg * np.exp(-exp_decay_bg / np.sqrt(energy))
    return bg * normalization


def save_transmission_spectrum(
    archivename: str = "UMo",
    signal: np.ndarray = np.array([]),
    openbeam: np.ndarray = np.array([]),
    flight_path_length: float = 10.7,
    Δt: float = 1.0,
    t_zero: float = 0.0,
    uncertainty_rank: float = 0.0,
    k: float = 1.0,
    ϵ: float = 1.0,
    plot_label: str = "",
    N: np.ndarray = np.array([1.0]),
    scale_bg: float = 1.0,
    bg_type: str = "",
    bg_params: dict = {},
    data_threshold: float = -999,
    resolution_file: str = "FP5_resolution.udp",
) -> None:
    """
    Calculates and saves transmission data from signal and open-beam spectra.

    This function processes signal and open-beam spectra (assumed to be numpy arrays)
    to generate a transmission spectrum with uncertainties. It can then save the
    transmission data to a `.dat` file and optionally create a plot.

    Args:
        archivename (str, optional): Name or path for the output `.dat` file
            (default: "UMo").
        signal (np.ndarray): Array containing the signal spectrum.
        openbeam (np.ndarray): Array containing the open-beam spectrum.
        flight_path_length (float, optional): Flight path length in meters (default: 10.7).
        Δt (float, optional): Time step between data points in microseconds (default: 1.0).
        t_zero (float, optional): Time delay to apply to the data (default: 0.0).
        uncertainty_rank (float, optional): Exponent for uncertainty correction (default: 0.0).
        k (float, optional): Ratio of sample and open-beam background (default: 1.0).
        ϵ (float, optional): Factor for systematic background uncertainty (default: 1.0).
        plot_label (str, optional): Label for the plot (default: "").
        N (np.ndarray, optional): Transmission normalization factor (default: 1.0).
        scale_bg (float, optional): Background scaling factor (default: 1.0).
        bg_type (str, optional): Background function type ("trinidi", "sammy", etc.)
            (default: "sammy").
        bg_params (dict, optional): Parameters for the background function (default: {}).
        data_threshold (float, optional): Minimum value for data points (default: -999). Useful to exclude saturation resonances below threshold
        resolution_file (str, optional): Name of the resolution file (default: "FP5_resolution.udp").
    """
    # Create output filename with proper extension
    output_filename = Path("archive") / Path(archivename) / Path(archivename).with_suffix(".dat")

    # Calculate time of flight (TOF) with center bins
    tof = t_zero * Δt + np.arange(len(signal)) * Δt + 0.5 * Δt

    # Convert TOF to energy
    energy = time2energy(tof*1e-6, flight_path_length)

    # Calculate background based on type
    if bg_type == "sammy":
        background = scale_bg * sammy_background(energy, **bg_params)
    else:
        background = scale_bg * np.ones_like(energy)  # Assume zero background for other types

    # Calculate transmission
    transmission = N * (signal - k * background) / (openbeam - background)

    # Calculate transmission uncertainty
    uncertainty = transmission / (openbeam - background) * np.sqrt(
        np.abs(signal) / transmission**2
        + np.abs(openbeam + (1.0 - k / transmission) ** 2 * ϵ**2 * background)
    )

    # Apply uncertainty rank if specified
    if uncertainty_rank:
        uncertainty /= transmission**uncertainty_rank

    # Ensure positive uncertainty values
    uncertainty = np.abs(uncertainty)

    # Create pandas DataFrame with filtered and formatted data
    data = pandas.DataFrame(
        {"data": transmission[::-1], "err": uncertainty[::-1], "tof": tof[::-1]},
        index=energy[::-1],
    )
    filtered_data = data.query("tof > 0 and data > @data_threshold")[["data", "err"]]

    # Create directory for output file (if needed)
    output_filename.parent.mkdir(parents=True, exist_ok=True)

    # Save filtered data to .dat file
    np.savetxt(
        output_filename,
        filtered_data.reset_index().values,
        fmt="%19.12f",
        newline="\n ",
        header="W data (twenty format)",
    )

    # Remove the first line (header) using system call (consider alternative)
    os.system(f"sed -i '1d' {output_filename}")

    if resolution_file:
        # Create symbolic link to resolution file (consider alternative)
        resolution_file_path = Path.cwd() / "sammy_files" / resolution_file
        resolution_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(resolution_file_path, output_filename.with_name("FP5.udp"))
        except FileNotFoundError:
            print(f"Put the .udp resolution file in this directory {resolution_file_path.parent}")
        except:
            pass
    
    # Plot data if label provided
    if plot_label:
        filtered_data.plot(
            y="data",
            xlim=(0, 50),
            lw=1,
            xlabel="energy [eV]",
            ylabel="average transmission",
            title=output_filename.stem,
            label=plot_label,
        )
        plt.show()  # Explicitly show the plot

'''

def sammy_par_from_endf(isotope: str = "U-239", 
                        flight_path_length: float = 10.72, 
                        emin: float = 0.001,
                        emax: float = 98,
                        archive: bool = True, 
                        archive_dir: str = ".archive/", 
                        verbose_level: int = 0) -> None:
    """
    Generates a SAMMY input file and runs SAMMY with ENDF data to produce a `.par` file
    for the specified isotope. 

    This function creates a SAMMY input file based on a configuration file, modifies relevant
    cards for the target isotope, saves the input file, and then runs SAMMY with ENDF data
    to generate the corresponding `.par` file.

    Args:
        isotope (str, optional): string of isotope name. Defaults to "U-238".
        flight_path_length (float, optional): Flight path lenght in meters. Defaults to 10.72.
        emin (float, optional): minimum energy in eV (default to 0.001 eV)
        emax (float, optional): maximum energy in eV (default to 98 eV)
        archive (bool, optional): Flag for storing sammy files. Defaults to False.
        archive_dir (str, optional): string of path for archiving SAMMY files. Defaults to hidden dir ".archive/".
        verbose_level (int, optional): 0: no printing, 1: prints general info, 2: prints data. Defaults to 0.
    """
    # Create a SAMMY input file data structure
    inp = sammyInput.InputFile()

    # Update input data with isotope-specific information
    inp.data["Card2"]["elmnt"] = isotope
    inp.data["Card2"]["aw"] = "auto"
    inp.data["Card2"]["emin"] = emin
    inp.data["Card2"]["emax"] = emax
    inp.data["Card5"]["dist"] = flight_path_length
    inp.data["Card5"]["deltag"] = 0.001
    inp.data["Card5"]["deltae"] = 0.001
    inp.data["Card7"]["crfn"] = 0.001
    
    #TODO: Need to figure out a better way to deal with commands in card3.
    # Resetting the commands for running SAMMY to generate output par files based on ENDF.
    inp.data["Card3"]['commands'] = 'TWENTY,DO NOT SOLVE BAYES EQUATIONS,INPUT IS ENDF/B FILE'
    
    # Print the input data structure if desired
    if verbose_level > 1: print(inp.data)
    
    # Create a run name or handle based on the isotope name
    sammy_run_handle = isotope.replace("-", "").replace("_", "")
    sammy_input_file_name = sammy_run_handle + ".inp"
    
    # Check if archive is True and create the .archive directory if it doesn't exist
    if archive:
        archive_path = pathlib.Path(archive_dir)
        archive_path.mkdir(parents=True, exist_ok=True)
        if verbose_level > 0:
            print(f"\nArchive directory created at {archive_path}")
        
        # Create a directory in the archive_path that corresponds to the sammy_run_handle
        output_dir = archive_path / Path(sammy_run_handle)
        
        # add new output directory to the archive_path
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a SAMMY input file in the output directory
        sammy_input_file = output_dir / (sammy_input_file_name)
        
        if verbose_level > 0: print(f"SAMMY input file created at {sammy_input_file}")
        
    else:
        # determine the current working directory
        output_dir = Path.cwd()
        sammy_input_file = output_dir / (sammy_input_file_name)
        print(sammy_input_file)

    # Write the SAMMY input file to the specified location. 
    inp.process().write(sammy_input_file)

    # Run SAMMY with ENDF data to generate .par file
    sammyRunner.run_endf(run_handle = sammy_run_handle, 
                         endf_dir=output_dir,
                         input_file=sammy_input_file_name,
                         verbose_level=verbose_level)
    
def run_sammy_fit(archivename: str="UMo",
                  abundances: dict={"U238":0.7,"U235":0.3},
                  emin: float=1.,
                  emax: float=50.,
                  res_emin: float=None,
                  res_emax: float=None,
                  vary_abundances: bool=False,
                  vary_normalization: bool=None,
                  vary_broadening: bool=None,
                  vary_misc: bool=None,
                  vary_resonance_energies: bool=None,
                  vary_gamma_widths: bool=None,
                  vary_neutron_widths: bool=None,
                  vary_resonances_emin: float=None,
                  vary_resonances_emax: float=None,
                  params:dict={},
                  fudge_factor: float=0.5,
                  flight_path_length: float=10.7,
                  atomic_weight:float=None,
                  commands: set=set(),
                  ) -> dict:
    """automatically runs sammy

    Args:
        archivename (str, optional): the directory name to run. Defaults to "UMo".
        abundances (_type_, optional): dictionary of isotope name keys and guess abundences. Defaults to {"U238":0.7,"U235":0.3}.
        emin (float, optional): minimal energy. Defaults to 1.
        emax (float, optional): maximal energy. Defaults to 50.
        res_emin (float, optional): minimal energy for resonance parameters. Defaults to 1.
        res_emax (float, optional): maximal energy for resonance parameters. Defaults to 1.
        vary_abundances (bool, optional): True will vary all abundances parameters. Defaults to False.
        vary_normalization (bool, optional): True will vary all normalization parameters. Defaults to False.
        vary_broadening (bool, optional): True will vary all broadening parameters. Defaults to False.
        vary_misc (bool, optional): True will vary all misc parameters. Defaults to False.
        vary_resonances_emin (float): the lower energy of resonances to toggle vary flag
        vary_resonances_emax (float): the upper energy of resonances to toggle vary flag
        params (dict, optional): dictionary of all normalization and broadening params. Defaults to {}.
        fudge_factor (float, optional): fudge factor, controls the uncertainty of the fit params search. Defaults to 0.5.
        atomic_weight (float, optional): supply the compound atomic weight, if None the atomic weight is guessed from the abundances input. Defaults to None.
        commands (set, optional): update the default commands with additional commands. Use the '~SOLVE_BAYES` notation to remove default commands. Defaults to set().

    Returns:
        dict: samyOutput.LptFile.stats outout
    """
    # runs a UMo fit and returns the simulation stats
    from pathlib import Path

    archivename = Path(archivename)

    if res_emin is None:
        res_emin = emin

    if res_emax is None:
        res_emax = emax
    
    # make the par file for each isotope
    isotopes = []
    for isotope, abundance in abundances.items():
        isotopes.append(sammyParFile.ParFile(f".archive/{isotope}/results/{isotope}.par",
                                             weight=abundance,emin=res_emin,emax=res_emax).read())
    
    # create compound
     
    compound = isotopes[0]
    for isotope in isotopes[1:]:
        compound = compound +  isotope

    
    #I use the W fit results as guess to background params
    # UMo.update.normalization(**output.stats())

    # we want to fit abundances in this case
    compound.update.toggle_vary_abundances(vary=vary_abundances)
    
    # By uncommenting the next lines, at the next step I will try to vary the background parameters
    compound.update.normalization(**params)
    if vary_normalization is not None:
        compound.update.vary_all(vary_normalization,data_key="normalization")
    
    # fix the thickness to 2mm, time-spread of the beam is a free parameter
    compound.update.broadening(**params)
    if vary_broadening is not None:
        compound.update.vary_all(vary_broadening,data_key="broadening")

    # fix the thickness to 2mm, time-spread of the beam is a free parameter
    compound.update.misc(**params)
    if vary_misc is not None:
        compound.update.vary_all(vary_misc,data_key="misc_delta")
        compound.update.vary_all(vary_misc,data_key="misc_tzero")
        compound.update.vary_all(vary_misc,data_key="misc_deltE")

    compound.update.resolution(**params)

    # vary resonance parameters
    if vary_resonance_energies is not None or vary_gamma_widths is not None or vary_neutron_widths is not None:
        compound.update.vary_resonances_in_energy_range(vary_energies=vary_resonance_energies,
                                                        vary_gamma_widths=vary_gamma_widths,
                                                        vary_neutron_widths=vary_neutron_widths,
                                                        emin=vary_resonances_emin,
                                                        emax=vary_resonances_emax)
    
    # change the fudge-factor that essentially responsible for the fit step-size
    # it only has a minor effect on results
    compound.data["info"]["fudge_factor"] = fudge_factor

    
    # write the par file
    compound.write("archive" / archivename / archivename.with_suffix(".par"))
    
    
    # prepare an input file for the compound run
    # I'm being lazy to write a config file, so I'm just using the previous one, and updating a bunch of stuff
    inp = sammyInput.InputFile(PWD / "config_Eu_151.ini")

    # update a title
    inp.data["Card1"]["title"] = "Run SAMMY to find abundence of UMo isotopes"
    
    # update compound name and assumed atomic weight
    inp.data["Card2"]["elmnt"] = str(archivename)
    if not atomic_weight:
        atomic_weight =  np.sum([int(re.search(r'\d+', isotope).group())*abundance for isotope, abundance in abundances.items()])

    inp.data["Card2"]["aw"] = f"{atomic_weight:<.4f}" # estimation of the atomic weight
    inp.data["Card2"]["emin"] = emin
    inp.data["Card2"]["emax"] = emax
    # number of iterations
    inp.data["Card2"]["itmax"] = 15
    inp.data["Card5"]["dist"] = params["flight_path_length"] if "flight_path_length" in params and params["flight_path_length"] else flight_path_length
    inp.data["Card5"]["temp"] = 296.
    
    # update commands. We need to preform the REICH_MOORE and SOLVE_BAYES for this case

    default_commands = set(['CHI_SQUARED', 
                    'TWENTY', 
                    'SOLVE_BAYES',
                    'QUANTUM_NUMBERS', 
                    'REICH_MOORE_FORM', 
                    'GENERATE ODF FILE AUTOMATICALLY', 
                    'USE I4 FORMAT TO READ SPIN GROUP NUMBER'])

    commands = default_commands.union(commands)

    # remove commands flaged with ~
    for command in commands:
        if command.startswith("~") or command.endswith("~"):
            commands.discard(command)
            commands.discard(command.strip("~"))

    inp.data["Card3"]["commands"] = ",".join(commands)
    
    # inp.data["Card7"]["thick"] = 4.8e-2*0.2 # atoms/barn
    
    # write the inp file
    inp.process(auto_update=False).write("archive" / archivename / archivename.with_suffix(".inp"))
    
    # run sammy, it saves the results inside the "./archive/W/results" directory
    sammyRunner.run(archivename=archivename.stem,
                    inpfile=archivename.with_suffix(".inp"),
                    parfile=archivename.with_suffix(".par"),
                    datafile=archivename.with_suffix(".dat"))

    from pleiades import sammyOutput
    output = sammyOutput.LptFile("archive" / Path(archivename.stem) / "results" / Path(archivename.stem).with_suffix(".lpt"))
    
    output.register_abundances_stats(isotopes=list(abundances.keys()))
    output.register_broadening_stats(register_vary=True)
    output.register_normalization_stats(register_vary=True)
    output.register_misc_stats(register_vary=True)
    
    stats = output.stats()
    
    # save to shelve
    import shelve
    with shelve.open("params.store") as fid:
        fid[f"{archivename}/latest"] = stats
    
    return stats
    


def plot_transmission(archivename: str="W", stats: dict ={},
                        plot_bg: bool=True,
                        plot_initial: bool=True,
                        color:str ="#227C9D") -> "pandas.DataFrame":
    """plot transmission spectrum and residuals from an archive

    Args:
        archivename (str, optional): directory name where the fit results are stored. Defaults to "W".
        stats (dict, optional): dictionary containing the fit params (e.g. output of `sammyOutput.stats()`). Defaults to {}.
        plot_bg (bool) if True the background component is calculated and plotted
        plot_initial (bool) if True the initial guess is calculated and plotted
        color (string): the data color

    Returns:
        pandas.DataFrame: returns a table woth transmission spectrum
    """

    archivepath = pathlib.Path(f"archive/{archivename}")
    results = pandas.read_csv((archivepath / "results" / archivename).with_suffix(".lst"),
                              delim_whitespace=True,header=None,
                names=["energy","xs_data",
                       "xs_data_err","xs_initial",
                       "xs_final","trans_data",
                       "trans_data_err","trans_initial",
                       "trans_final","trans_err",
                       "trans_err2","initial_energy","final_energy"]).dropna(axis=1,how="all").dropna()
    results["residual"] = (results["trans_data"] - results["trans_final"])#/results["trans_data_err"]
    if plot_bg:
        # bg
        constant_bg = stats["constant_bg"]
        normalization = stats["normalization"]
        one_over_v_bg =  stats["one_over_v_bg"]/np.sqrt(results["energy"])
        sqrt_energy_bg =  stats["sqrt_energy_bg"]*np.sqrt(results["energy"])
        exp_term_bg = stats["exponential_bg"]*np.exp(-stats["exp_decay_bg"]/np.sqrt(results["energy"]))

        results["total_bg"] = constant_bg + one_over_v_bg + sqrt_energy_bg + exp_term_bg
        results["theoretical_trans"] = (results["trans_final"] - results["total_bg"])/normalization
        results["theoretical_data"] = (results["trans_data"] - results["total_bg"])/normalization
        results["bg"] = results["total_bg"]*normalization


    fig, ax = plt.subplots(2,1,sharex=True,gridspec_kw={"height_ratios":[3,1],"hspace":0.05})
    plt.sca(ax[0])
    if "final_energy" in results.columns:
        results.plot(x="final_energy",y="theoretical_data",yerr="trans_data_err",ls="none",ax=plt.gca(),alpha=0.9,zorder=-1,marker=".",ms=3,lw=1,ecolor="0.8",color=color)
        if plot_initial:
            results.plot(x="final_energy",y="trans_initial",ls="--",lw=1,ax=plt.gca(),alpha=0.9)
        results.plot(x="final_energy",y="theoretical_trans",ls="-",lw=1,ax=plt.gca(),color="#433E3F")
        if plot_bg: results.plot(x="final_energy",y="bg",lw=1,ax=plt.gca(),color="0.5",zorder=-1,ls="--")
    else:
        results.plot(x="energy",y="theoretical_data",yerr="trans_data_err",ls="none",ax=plt.gca(),alpha=0.9,zorder=-1,marker=".",ms=3,lw=1,ecolor="0.8",color=color)
        if plot_initial:
            results.plot(x="energy",y="trans_initial",ls="--",lw=1,ax=plt.gca(),alpha=0.9)
        results.plot(x="energy",y="theoretical_trans",ls="-",lw=1,ax=plt.gca(),color="#433E3F")   
        if plot_bg: results.plot(x="energy",y="bg",lw=1,ax=plt.gca(),color="0.5",zorder=-1,ls="--")     
    plt.ylim(0,1); plt.ylabel("Average transmission");plt.title(archivename)
    if stats:
        plt.legend(title=r"$\chi^2$" + f": {stats['reduced_chi2']:.3f}")
    else:
        plt.legend()
    plt.sca(ax[1])
    if "final_energy" in results.columns:
        results.plot(x="final_energy",y="residual",ls="-",lw=1,ax=plt.gca(),color=color,legend=False)
        plt.xlabel("Energy [eV]"); plt.ylabel(r"Residuals");
    else:
        results.plot(x="energy",y="residual",ls="-",lw=1,ax=plt.gca(),color=color,legend=False)
        plt.xlabel("energy [eV]"); plt.ylabel(r"Residuals");
    plt.sca(ax[0])
    plt.legend([],frameon=False)

    return results


def print_stats_dict(stats: dict) -> str:
    """pretty print the stats dict so it's easy to modify

    Args:
        stats (dict): the stats dict. 

    Returns:
        pprint dictionary string
    """
    from collections import defaultdict
    # find isotope keywords:
    isotopes = ",\t".join([f"{key}:\t{stats[key]}" for key in stats if nucData.get_mass_from_ame(key)])
    isotopes = isotopes + ',' if isotopes else ""
    
    tmp = defaultdict(lambda:"''")
    tmp.update(stats)
    stats = tmp
    template = f"""
{{
'input_file': \'{stats['input_file']:>10}\',  'par_file': \'{stats['par_file']:>10}\',
 'Emin': {stats['Emin']:>10},   'Emax': {stats['Emax']:>10}, 'reduced_chi2': {stats['reduced_chi2']:>10},

# isotopes
 {isotopes}
      
# thickness and temperature
 'thickness':\t{stats['thickness']:>10},\t'vary_thickness':\t{stats['vary_thickness']:>1},
 'temperature':\t{stats['temperature']:>10},\t'vary_temperature':\t{stats['vary_temperature']:>1},
      
# normalization
 'normalization':\t{stats['normalization']:>10},\t'vary_normalization':\t{stats['vary_normalization']:>10}, 
 'constant_bg':\t\t{stats['constant_bg']:>10},\t'vary_constant_bg':\t{stats['vary_constant_bg']:>10},   
 'one_over_v_bg':\t{stats['one_over_v_bg']:>10},\t'vary_one_over_v_bg':\t{stats['vary_one_over_v_bg']:>10}, 
 'sqrt_energy_bg':\t{stats['sqrt_energy_bg']:>10},\t'vary_sqrt_energy_bg':\t{stats['vary_sqrt_energy_bg']:>10},
 'exponential_bg':\t{stats['exponential_bg']:>10},\t'vary_exponential_bg':\t{stats['vary_exponential_bg']:>10},
 'exp_decay_bg':\t{stats['exp_decay_bg']:>10},\t'vary_exp_decay_bg':\t{stats['vary_exp_decay_bg']:>10},  

# broadening 
 'flight_path_spread':\t{stats['flight_path_spread']:>10},\t'vary_flight_path_spread':\t{stats['vary_flight_path_spread']:>10},
 'deltag_fwhm':\t\t{stats['deltag_fwhm']:>10},\t'vary_deltag_fwhm':\t\t{stats['vary_deltag_fwhm']:>10},
 'deltae_us':\t\t{stats['deltae_us']:>10},\t'vary_deltae_us':\t\t{stats['vary_deltae_us']:>10},

# misc. tzero    
 't0':\t{stats['t0']:>10},\t't0_err':\t{stats['t0_err']:>10},\t'vary_t0':\t{stats['vary_t0']:>10},
 'L0':\t{stats['L0']:>10},\t'L0_err':\t{stats['L0_err']:>10},\t'vary_L0':\t{stats['vary_L0']:>10},

# misc. delta-L
 'delta_L1':\t{stats['delta_L1']:>10},\t'delta_L1_err':\t{stats['delta_L1_err']:>10},\t'vary_delta_L1':\t{stats['vary_delta_L1']:>10},
 'delta_L0':\t{stats['delta_L0']:>10},\t'delta_L0_err':\t{stats['delta_L0_err']:>10},\t'vary_delta_L0':\t{stats['vary_delta_L0']:>10},

# misc. delta-E
 'DE':\t\t{stats['DE']:>10},\t'DE_err':\t{stats['DE_err']:>10},\t'vary_DE':\t{stats['vary_DE']:>10},
 'D0':\t\t{stats['D0']:>10},\t'D0_err':\t{stats['D0_err']:>10},\t'vary_D0':\t{stats['vary_D0']:>10},
 'DlnE':\t{stats['DlnE']:>10},\t'DlnE_err':\t{stats['DlnE_err']:>10},\t'vary_DlnE':\t{stats['vary_DlnE']:>10},
}}
"""
    return template


def print_stats_table(stats: dict, just_params:bool = True, 
                      vary_params: bool=False,
                      display_columns: int=None) -> "pandas.DataFrame":
    """pretty print the stats dict as a pandas table

    Args:
        stats (dict): the stats dict. 
        just_params (bool): if True only a subset of the parameters is displayed
        vary_params (bool): if True, vary param flags are also displayed
        display_columns (int): number of columns to show in each row

    Returns:
        pandas.DataFrame with the relevant parameters
    """
    name = stats["input_file"].strip(".inp")
    df = pandas.DataFrame(stats,index=[name])
    isotopes = [key for key in stats if nucData.get_mass_from_ame(key)]
    if just_params:
        df = df[isotopes + ['varied_params',"reduced_chi2",'Emin','Emax','thickness','vary_thickness','temperature','vary_temperature','normalization','vary_normalization','constant_bg','vary_constant_bg',
                 'one_over_v_bg','vary_one_over_v_bg','sqrt_energy_bg','vary_sqrt_energy_bg','exponential_bg','vary_exponential_bg',
                 'exp_decay_bg','vary_exp_decay_bg','flight_path_spread','vary_flight_path_spread','deltag_fwhm','vary_deltag_fwhm','deltae_us','vary_deltae_us',
                 't0','vary_t0','L0','vary_L0','delta_L1','vary_delta_L1','delta_L0','vary_delta_L0','DE','vary_DE','D0','vary_D0','DlnE','vary_DlnE',
]]
    if not vary_params:
        df = df.filter(regex='^(?!vary_)')
    if display_columns:
        from IPython.display import display
        for i in range(len(df.columns)//display_columns):
            display(df.iloc[:,i*display_columns:(i+1)*display_columns])
    return df

import numpy as np
SPEED_OF_LIGHT = 299792458 # m/s
MASS_OF_NEUTRON = 939.56542052 * 1e6 / (SPEED_OF_LIGHT) ** 2  # [eV s²/m²]

TOF_LABEL = "Time-of-flight [μs]"
ENERGY_LABEL = "Energy [eV]"

def time2energy(time, flight_path_length):
    r"""Convert time-of-flight to energy of the neutron.

    .. math::
        E = \left( \gamma - 1 \right) m c^2 \; ,
        \gamma = \frac{1}{\sqrt{1 - \left(\frac{L}{c \cdot t} \right)^2}} \; ,

    where :math:`E` is the energy, :math:`m` is the mass, :math:`c` is
    the speed of light, :math:`t` is the time-of-flight of the neutron,
    and :math:`L` is the flight path length.

    Args:
        time: Time-of-flight in :math:`\mathrm{s}`.
        flight_path_length: flight path length in :math:`\mathrm{m}`.

    Returns:
        Energy of the neutron in :math:`\mathrm{eV}`.
    """
    m = MASS_OF_NEUTRON  # [eV s²/m²]
    c = SPEED_OF_LIGHT # m/s
    L = flight_path_length  # m
    t = time  # s
    γ = 1 / np.sqrt (1 - (L / t) ** 2 / c ** 2 )
    return ( γ - 1 ) * m * c ** 2  # eV

def energy2time(energy, flight_path_length):
    r"""Convert energy to time-of-flight of the neutron.

    .. math::
        t = \frac{L}{c} \sqrt{ \frac{\gamma^2}{\gamma^2 - 1 }} \; ,
        \gamma = 1 + \frac{E}{mc^2}

    where :math:`E` is the energy, :math:`m` is the mass, :math:`c`
    is the speed of light, :math:`t` is the time-of-flight of the neutron,
    and :math:`L` is the flight path length.

    Args:
        energy:  Energy of the neutron in :math:`\mathrm{eV}`.
        flight_path_length: flight path length in :math:`\mathrm{m}`.

    Returns:
        Time-of-flight in :math:`\mathrm{s}`.

    """
    L = flight_path_length  # m
    m = MASS_OF_NEUTRON  # eV s²/m²
    c = SPEED_OF_LIGHT # m/s
    E = energy  # eV
    γ = 1 + E / m / c ** 2
    t = L / c * np.sqrt(γ ** 2 / ( γ ** 2 - 1 ) ) # s
    return t  # ns
    