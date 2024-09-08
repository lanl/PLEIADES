# SammyRunner.py
# Version: 1.0
# Authors: 
#   - Alexander M. Long
#       - Los Alamos National Laboratory
#       - ORCID: 0000-0003-4300-9454
#   - Tsviki Hirsh 
#       - Soreq Nuclear Research Center
#       - ORCID: 0000-0001-5889-4500
# About: 
#   This file is part of the PLEIADES package and contains functions to run the SAMMY fitting process.
# Functions:
#   - check_sammy_environment: Check if the SAMMY executable is in the path or if a docker container is running.
#   - run_sammy_fit: Run the SAMMY fitting process.
#   - run_endf: Run the SAMMY fitting process with ENDF isotopes tables file.
# How to use:
#   - Import the this class with 'from pleiades import sammyRunner'
#   Note: 
#       also need to import SammyFitConfig from pleiades.sammyStructures 
#       with 'from pleiades.sammyStructures import SammyFitConfig'

# General imports
import pathlib
import glob
import os
import shutil
import subprocess
import textwrap
import numpy as np
import datetime

# SammyFitConfig imports from PLEIADES 
from pleiades.sammyStructures import SammyFitConfig, sammyRunConfig

print_header_check = "\033[1;34m<SAMMY Runner>\033[0m "
print_header_good = "\033[1;32m<SAMMY Runner>\033[0m "
print_header_bad = "\033[1;31m<SAMMY Runner>\033[0m "
    
def check_sammy_environment(config: SammyFitConfig, verbose_level: int = 0) -> bool:
    """
    Check if the SAMMY executable is in the path or if a docker container is running.
    
    Args:
        config (SammyFitConfig): A SammyFitConfig object
        verbose_level (int): The level of verbosity for printing information. Default is 0.
    
    Returns:
        bool: True if SAMMY is available, False otherwise

    Note:
        This function is an absolute shit show, and needs work!
    """
    
    
    sammy_call = config.params['sammy_run_method']
    sammy_command = config.params['sammy_command']
    
    sammy_exists = False
    if verbose_level > 0: print(f"{print_header_check} Checking SAMMY environment for a <{sammy_call}> version of SAMMY")
    
    if sammy_call == "compiled":
        # Check if the sammy executable is in the path
        if shutil.which(sammy_command) is None:
            if verbose_level > 1: print(f"{print_header_bad} SAMMY executable not found in the path")
            sammy_exists = False
        else: 
            if verbose_level > 1: print(f"{print_header_good} Found compiled version of SAMMY")
            sammy_exists = True

    elif sammy_call == "docker":
        # Check if Docker image exists
        docker_image = 'sammy-docker'
        docker_command = f'docker image inspect {docker_image}'
        try:
            subprocess.check_output(docker_command, shell=True, stderr=subprocess.STDOUT)
            sammy_exists = True
            if verbose_level > 1: print(f"{print_header_good} Found docker version of SAMMY")
        except subprocess.CalledProcessError:
            print(f"{print_header_bad} Docker image {docker_image} not found")
            sammy_exists = False

    return sammy_exists
  

def run_sammy_fit(config: sammyRunConfig, verbose_level: int = 0) -> None:
    """ 
    Run the SAMMY fitting process.
    Parameters:
    - config (sammyRunConfig): A sammyRunConfig object needed to execute a SAMMY fit.
    - verbose_level (int): The level of verbosity for printing information. Default is 0.
    Raises:
    - ValueError: If input_file, par_file, or data_file is not provided.
    - FileNotFoundError: If input_file or par_file is not found.
    Returns:
    - None
    """
    
    # Grab the directory from which the pleiades script was called.
    pleiades_call_dir = pathlib.Path.cwd()
    
    # Set the SAMMY run method
    sammy_call = config.params['sammy_run_method']
    sammy_command = config.params['sammy_command']
    sammy_fit_name = config.params['sammy_fit_name']

    # Set directories and file names
    data_dir = config.params['directories']['data_dir']
    fit_dir = config.params['directories']['sammy_fit_dir']
    params_dir = config.params['directories']['params_dir']
    input_dir = config.params['directories']['input_dir']
    input_file = config.params['filenames']['input_file_name']
    params_file = config.params['filenames']['params_file_name']
    output_file = config.params['filenames']['output_file_name']
    data_file = config.params['filenames']['data_file_name']

    # Create full paths to the files
    full_path_to_data_file = pathlib.Path(data_dir) / data_file
    full_path_to_input_file = pathlib.Path(input_dir) / input_file
    full_path_to_params_file = pathlib.Path(params_dir) / params_file
    full_path_to_output_file = pathlib.Path(fit_dir) / output_file
    full_path_to_result_files = pathlib.Path(fit_dir) / 'results'
    
    # Print info based on verbosity level
    if verbose_level > 0: 
        print(f"{print_header_check} ----------------------- Running SAMMY for {sammy_fit_name}")  
        if verbose_level > 1:
            print(f"{print_header_check} input_file: {full_path_to_input_file}")
            print(f"{print_header_check} par_file: {full_path_to_params_file}")
            print(f"{print_header_check} data_file: {full_path_to_data_file}")
            print(f"{print_header_check} output_file: {full_path_to_output_file}")
            print(f"{print_header_check} results_dir: {full_path_to_result_files}")
    
    # Check if files input, parameter, and data files exist
    if not os.path.isfile(full_path_to_input_file):
        raise FileNotFoundError(f"{print_header_bad} Input file {input_file} not found")
    if not os.path.isfile(full_path_to_params_file):
        raise FileNotFoundError(f"{print_header_bad} Parameter file {params_file} not found")
    if not os.path.isfile(full_path_to_data_file):
        raise FileNotFoundError(f"{print_header_bad} Data file {data_file} not found")
    
    # Create results directory if it does not exist
    os.makedirs(full_path_to_result_files, exist_ok=True)

    # Check if we are running SAMMY to produce a par file from ENDF tables
    if config.params['run_endf_for_par'] == True:
        
        # Create SAMMY run command depending on the call type
        if sammy_call == "compiled":
            sammy_run_command = textwrap.dedent(f"""\
            sammy <<EOF
            {input_file}
            res_endf8.endf
            {data_file}

            EOF""")
            
        elif sammy_call == "docker":
            sammy_run_command = textwrap.dedent(f"""\
            docker run -i -v {fit_dir}:/sammy_fit_dir -v {data_dir}:/data_dir -v {params_dir}:/params_dir -w /sammy_fit_dir  {sammy_command} sammy <<EOF
            /sammy_fit_dir/{input_file}
            /params_dir/res_endf8.endf
            /data_dir/{data_file}
            
            EOF""")
    else:
        # Create SAMMY run command depending on the call type compiled or docker
        if sammy_call == "compiled":
            sammy_run_command = textwrap.dedent(f"""\
            sammy <<EOF
            {input_file}
            {params_file}
            {data_file}

            EOF""")
        
        elif sammy_call == "docker":
            sammy_run_command = textwrap.dedent(f"""\
            docker run -i -v {fit_dir}:/sammy_fit_dir -v {data_dir}:/data_dir -w /sammy_fit_dir  {sammy_command} sammy <<EOF
            /sammy_fit_dir/{input_file}
            /sammy_fit_dir/{params_file}
            /data_dir/{data_file}

            EOF""")
    
    # Print the run command if verbose level is high enough
    if verbose_level > 1: print(sammy_run_command)
    
    # Change directories to the working dir
    os.chdir(fit_dir)
    if verbose_level > 0: print(f"{print_header_check} Changing to directory to: {fit_dir}")
    
    # Open the output file in write mode
    with open(output_file, "w+") as output:
        # Get the current timestamp
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Write the timestamp to the output file
        output.write(f"\n=== SAMMY Run Started at {current_time} ===")
        
        # Run the command and redirect output and error to the file
        subprocess.run(sammy_run_command, shell=True, executable='/bin/bash', stdout=output, stderr=subprocess.STDOUT)
    
    # Check if the SAMMY run was successful by opening the output file and checking for the line " Normal finish to SAMMY"
    with open(output_file, "r") as output:
        if verbose_level > 0: print(f"{print_header_check} Checking SAMMY output file: {full_path_to_output_file}")
        for line in output:
            if " Normal finish to SAMMY" in line:
                if verbose_level > 0: print(f"{print_header_good} SAMMY fit was successful for {sammy_fit_name}")
                break
        else:
            raise RuntimeError(f"{print_header_bad} SAMMY fit was not successful for {sammy_fit_name} - Check the output file: {full_path_to_output_file}")
        
    # Move all SAMMY output files with the prefix SAM to the results folder
    for file in glob.glob("SAM*"):
        # Construct the full path for the destination
        destination_file = os.path.join(full_path_to_result_files, os.path.basename(file))
        # Check if the file already exists in the destination folder
        if os.path.exists(destination_file):
            # Remove the existing file in the destination folder
            os.remove(destination_file)
        # Move the file to the results folder
        shutil.move(file, full_path_to_result_files)

    # Change back to the original directory where the pleiades python script was called
    os.chdir(pleiades_call_dir)


def run_endf(config: SammyFitConfig, isotope: str = "", verbose_level: int = 0) -> None:
    """
    run sammy input with endf isotopes tables file to create a par file
    - This can only be done for a single isotope at a time
    - we don't need a data file, we create a fake dat file with only Emin and Emax data points
    - archive path name will be deducd from input name
    
    Args:
        config (SammyFitConfig): A SammyFitConfig object
        isotope (str): The isotope to run the SAMMY fit for. Default is "".
        verbose_level (int): The level of verbosity for printing information. Default is 0.

    Returns:   
        None

    Notes:
        - This function is not complete and needs more work
    """ 
    
    sammy_call = config.params['sammy_run_method']
    sammy_command = config.params['sammy_command']
    fit_dir = config.params['directories']['endf_dir'] +"/"+ isotope
    input_file = config.params['filenames']['input_file_name']
    
    # Set the working directory path
    fit_dir = pathlib.Path(fit_dir)

    
    # create an results folder within the working directory
    # We will be moving all the SAMMY results to this dir. 
    result_dir_name = 'results'
    os.makedirs(fit_dir,exist_ok=True)
    os.makedirs(fit_dir / result_dir_name,exist_ok=True)
    sammy_results_path = fit_dir / result_dir_name
    if verbose_level > 0: print(f"{print_header_check} Results will be saved in: {sammy_results_path}")

    # Need to create a fake data file with only Emin and Emax data points
    # read the input file to get the Emin and Emax:
    if verbose_level > 0: print(f"{print_header_check} Using input file: {input_file}")
    with open(fit_dir / input_file) as fid:
        next(fid)           # The first line is the isotope name
        line = next(fid)    # Read the second line with Emin and Emax
        Emin = float(line[20:30].strip())  # Extract Emin using character positions and strip spaces
        Emax = float(line[30:40].strip())  # Extract Emax using character positions and strip spaces
        
        if verbose_level > 1: print(f"{print_header_check} Emin: {Emin}, Emax: {Emax}")
        
    # Determine the number of points (at least 100) and create a list of energies
    num_points = 100
    energy_values = np.linspace(Emax, Emin, num_points)
    
    # Creating the name of the data file based on the input file name
    data_file_name = isotope + "_ENDF-dummy.dat"
    data_file = fit_dir / data_file_name
    
    # Open the data file and write the energy, transmission, and error values
    # Note: this is the twenty character format that SAMMY expects with the TWENTY command
    with open(data_file, "w") as fid:
        for energy in energy_values:
            transmission = 1.0
            error = 0.1
            # Write each line with 20 characters width, right justified
            fid.write(f"{energy:>20.8f}{transmission:>20.8f}{error:>20.8f}\n")
    
    if verbose_level > 0:
        print(f"{print_header_check} Dummy data file with {num_points} points written to {data_file}")


    # Creating a par file based on ENDF file
    symlink_path = fit_dir / "res_endf8.endf"
    # First check if file already exists
    if os.path.islink(symlink_path):
        endf_file = symlink_path
    else:
        # Create a symbolic link to the original endf file
        original_endf_file = "../res_endf8.endf"
        os.symlink(original_endf_file, symlink_path)
        endf_file = fit_dir / "res_endf8.endf"
    
    if verbose_level > 0: print(f"{print_header_check} ENDF file: {endf_file}")
    
    # Create an output file in the working dir. 
    output_file_name = isotope + ".out"
    output_file = fit_dir / output_file_name
    if verbose_level > 0: print(f"{print_header_check} Output file: {output_file}")

    # Create SAMMY run command depending on the call type
    if sammy_call == "compiled":
        sammy_run_command = textwrap.dedent(f"""\
        sammy <<EOF
        {input_file}
        res_endf8.endf
        {data_file_name}

        EOF""")
        
    elif sammy_call == "docker":
        sammy_run_command = textwrap.dedent(f"""\
        docker run -i -v $(dirname $PWD):/data-parent -w /data-parent/{isotope} {sammy_command} sammy <<EOF
        {input_file}
        ./res_endf8.endf
        {data_file_name}

        EOF""")

    # Print the run command if verbose level is high enough    
    if verbose_level > 1: print(sammy_run_command)
    
    # Change directories to the working dir
    os.chdir(fit_dir)
    
    # Open the output file in write mode
    with open(output_file_name, "w") as output:
        # Run the command and redirect output and error to the file
        if verbose_level > 0: print(f"{print_header_check} Running SAMMY for {isotope}...")
        subprocess.run(sammy_run_command, shell=True, executable='/bin/bash', stdout=output, stderr=subprocess.STDOUT)
    
    # Check if the SAMMY run was successful by opening the output file and checking for the line " Normal finish to SAMMY"
    with open(output_file_name, "r") as output_file:
        for line in output_file:
            if " Normal finish to SAMMY" in line:
                if verbose_level > 0: print(f"{print_header_good} SAMMY ENDF run was successful for {isotope}")
                break
        else:
            raise RuntimeError(f"{print_header_bad} SAMMY ENDF run was not successful for {isotope}")
    
    # Move the SAMNDF output files to the results folder
    for file in glob.glob("SAM*"):
        # Construct the full path for the destination
        destination_file = os.path.join(result_dir_name, os.path.basename(file))
        # Check if the file already exists in the destination folder
        if os.path.exists(destination_file):
            # Remove the existing file in the destination folder
            os.remove(destination_file)
        # Move the file to the results folder
        shutil.move(file, result_dir_name)
    
    # Change back to the original directory where the pleiades python script was called
    os.chdir(pleiades_call_dir)
    
    return
