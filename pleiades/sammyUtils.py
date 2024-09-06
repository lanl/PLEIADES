# sammyUtils.py
# Version: 1.0
# Authors: 
#   - Alexander M. Long
#       - Los Alamos National Laboratory
#       - ORCID: 0000-0003-4300-9454
#   - Tsviki Hirsh 
#       - Soreq Nuclear Research Center
#       - ORCID: 0000-0001-5889-4500
# About: 
#   This file is part of the PLEIADES package and contains high level functions to setup the SAMMY fitting process.
# Functions:
#   - create_parFile_from_endf(config: SammyFitConfig, archive: bool = True, verbose_level: int = 0) -> None
#   - configure_sammy_run(config: SammyFitConfig, verbose_level: int = 0)
#   - run_sammy(config: SammyFitConfig, verbose_level: int = 0)
# How to use:
#   - Import the this class with 'from pleiades import sammyUtils'
#   Note: 
#       also need to import SammyFitConfig from pleiades.sammyStructures 
#       with 'from pleiades.sammyStructures import SammyFitConfig'

# General imports
from pathlib import Path
import pathlib
import os
import shutil

# PLEIADES imports
from pleiades.sammyStructures import SammyFitConfig
from pleiades import sammyParFile, sammyInput, sammyRunner, nucData

print_header_check = "\033[1;34m<SAMMY Utilities>\033[0m "
print_header_good = "\033[1;32m<SAMMY Utilities>\033[0m "
print_header_bad = "\033[1;31m<SAMMY Utilities>\033[0m "

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

    Notes:
        #TODO: Need to figure out a better way to deal with commands in card3.
        #TODO: Need to add a check to see if the .par file was created successfully and print a message if not.   
    """
    # First grab the isotopesfrom the configuration class
    isotopes = config.params['isotopes']['names']
    # Ensure isotopes is a list
    if isinstance(isotopes, str): isotopes = [iso.strip() for iso in isotopes.split(',')]  

    if verbose_level > 0: print(f"{print_header_check} Creating SAMMY parFile files from ENDF data for isotopes: {isotopes}")

    # Then Grab the rest of the nessessary parameters from the configuration class
    flight_path_length = config.params['flight_path_length']
    endf_dir = config.params['directories']['endf_dir']
    
    # Path to the "res_endf8.endf" file in the repo
    pleiades_base_path = pathlib.Path(__file__).resolve().parent.parent  # Adjust based on actual location
    source_res_endf = pleiades_base_path / "nucDataLibs/resonanceTables/res_endf8.endf"
    
    # Check if archive is True and create the .archive directory if it doesn't exist
    if archive:
        endf_dir_path = pathlib.Path(endf_dir)
        endf_dir_path.mkdir(parents=True, exist_ok=True)
        if verbose_level > 0: print(f"{print_header_check} ENDF directory created at {endf_dir_path}")
        
        # copy res_endf8.endf to the endf directory
        destination_res_endf = endf_dir_path / "res_endf8.endf"
        shutil.copy(source_res_endf, destination_res_endf)
        if verbose_level > 0:
            print(f"{print_header_check} Copied {source_res_endf} to {destination_res_endf}")

    # Loop through the isotope list: Create a SAMMY input file and run SAMMY with ENDF data to generate .par file
    for isotope in isotopes:
        
        if verbose_level > 0: print(f"\n{print_header_check} Creating SAMMY parFile for isotope: {isotope}")

        # Create a SAMMY input file data structure
        inp = sammyInput.InputFile()

        # Update input data with isotope-specific information
        inp.data["Card2"]["elmnt"] = isotope
        inp.data["Card2"]["aw"] = "auto"
        inp.data["Card5"]["dist"] = flight_path_length
        inp.data["Card5"]["deltag"] = 0.001
        inp.data["Card5"]["deltae"] = 0.001
        inp.data["Card7"]["crfn"] = 0.001

        # Resetting the commands for running SAMMY to generate output par files based on ENDF.
        inp.data["Card3"]['commands'] = 'TWENTY,DO NOT SOLVE BAYES EQUATIONS,INPUT IS ENDF/B FILE'
    
        # Print the input data structure if desired
        if verbose_level > 1: 
            print(f"{print_header_check} SAMMY input data for isotope {isotope}:")
            print(inp.data)
            print(f"{print_header_check} -------------------------------")
    
        # Create a run name or handle based on the isotope name
        #sammy_run_handle = isotope.replace("-", "").replace("_", "")
        #sammy_input_file_name = sammy_run_handle + ".inp"
    
        # if archive is 'True', then create directories for the isotope sammy fit (if it doesn't already exist)
        if archive:
            # Create a directory in the endf_dir_path that corresponds to the sammy_run_handle
            run_sammy_dir = endf_dir_path / Path(isotope)
            
            # add new output directory to the archive_path
            run_sammy_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a SAMMY input file in the output directory
            sammy_input_file = run_sammy_dir / (config.params['filenames']['input_file_name'])
            
            if verbose_level > 0: print(f"{print_header_check} SAMMY input file created at {sammy_input_file}")
            
        else:
            # determine the current working directory
            run_sammy_dir = Path.cwd()
            sammy_input_file = run_sammy_dir / (config.params['filenames']['input_file_name'])

        # Write the SAMMY input file to the specified location. 
        inp.process().write(sammy_input_file)
    
        sammyRunner.run_endf(config, isotope, verbose_level=verbose_level)
        

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
    
    Notes:
        - TODO: This assumes that parfiles were created via ENDF data. This might not always be the case.
    """
    isotopeParFiles = []
    
    # setting up the directories that we will need to use
    archive_dir = config.params['directories']['archive_dir']
    endf_dir = config.params['directories']['endf_dir']
    sammy_fit_dir = config.params['directories']['sammy_fit_dir']
    data_dir = config.params['directories']['data_dir']
    
    # Grabbing the isotopes, abundances, and fudge factor from the config file
    isotopes = config.params['isotopes']['names']
    if isinstance(isotopes, str): isotopes = [iso.strip() for iso in isotopes.split(',')] 
    abundances = config.params['isotopes']['abundances']
    if isinstance(abundances, str): abundances = [abd.strip() for abd in abundances.split(',')] 
    fudge_factor = config.params['fudge_factor']
    
    # setting the resonance energy min and max, this will clip the resonances in the parFile to the specified energy range
    res_emin = config.params['resonances']['resonance_energy_min']
    res_emax = config.params['resonances']['resonance_energy_max']
    
    # Create a SAMMY parFile for each isotope 
    if verbose_level > 0: print(f"\n{print_header_check} Merging SAMMY parameter files for isotopes: {isotopes}, with abundances: {abundances}")


    # TODO: This assumes that parfiles were created via ENDF data. This might not always be the case.
    for isotope, abundance in zip(isotopes, abundances):        
        # turn the abundance into a float
        abundance = float(abundance)
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
    output_par_file = Path(archive_dir) / Path(sammy_fit_dir) / Path('params').with_suffix(".par")
    if verbose_level > 0: print(f"{print_header_check} Writing output parFile: {output_par_file}")
    outputParFile.write(output_par_file)

    # Now create a SAMMY input file
    if verbose_level > 0: print(f"{print_header_check} Creating SAMMY inpFile files for isotopes: {isotopes} with abundances: {abundances}")
    
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
    if verbose_level > 0: print(f"{print_header_check} Created compound input file: {output_inp_file}")

    # Create a symbolic link inside the sammy_fit_dir that points to the data file 
    data_file = os.path.join(data_dir, config.params['filenames']['data_file_name'])
    data_file_name = pathlib.Path(data_file).name

    if verbose_level > 0: print(f"{print_header_check} Symlinking data file: {data_file} into {sammy_fit_dir}")

    # Check if the symbolic link already exists
    symlink_path = pathlib.Path(sammy_fit_dir) / data_file_name
    if os.path.islink(symlink_path):
        os.unlink(symlink_path)  # unlink old symlink

    os.symlink(data_file, pathlib.Path(sammy_fit_dir) / data_file_name)   # create new symlink


def run_sammy(config: SammyFitConfig, verbose_level: int = 0):
    """
    Runs SAMMY based on a SammyFitConfig object.

    This function takes a SammyFitConfig object and uses it to run sammy. 

    Args:
        config (SammyFitConfig): SammyFitConfig object containing the configuration parameters.
    """

    # Run SAMMY
    sammyRunner.run_sammy_fit(config, verbose_level=verbose_level)

