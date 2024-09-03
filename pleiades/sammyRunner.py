
import pathlib
import inspect
import glob
import time
import os
import shutil
import subprocess
import datetime
import textwrap

from pleiades.sammyStructures import SammyFitConfig

def check_sammy_enviornment(config: SammyFitConfig, verbose_level: int = 0) -> bool:
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
    if verbose_level > 0: print(f"Checking SAMMY enviornment for a <{sammy_call}> version of SAMMY")
    
    if sammy_call == "compiled":
        # Check if the sammy executable is in the path
        if shutil.which(sammy_command) is None:
            if verbose_level > 1: print("SAMMY executable not found in the path")
            sammy_exists = False
        else: 
            if verbose_level > 1: print("Found compiled version of SAMMY")
            sammy_exists = True

    elif sammy_call == "docker":
        # Check if Docker image exists
        docker_image = 'sammy-docker'
        docker_command = f'docker image inspect {docker_image}'
        try:
            subprocess.check_output(docker_command, shell=True, stderr=subprocess.STDOUT)
            sammy_exists = True
            if verbose_level > 1: print("Found docker version of SAMMY")
        except subprocess.CalledProcessError:
            print(f"Docker image {docker_image} not found")
            sammy_exists = False

    return sammy_exists
  

def run_sammy_fit(sammy_call = "compiled", sammy_command = "sammy", fit_dir: str= "", input_file: str = "", par_file: str = "", data_file: str = "", output_dir: str = "results", verbose_level: int = 0) -> None:
    """ 
    Run the SAMMY fitting process.
    Parameters:
    - sammy_call (str): The SAMMY call type. Default is "compiled".
    - fit_dir (str): The directory where the fitting process will be performed.
    - input_file (str): The input file for the SAMMY fitting process.
    - par_file (str): The parameter file for the SAMMY fitting process.
    - data_file (str): The data file for the SAMMY fitting process.
    - output_dir (str): The directory where the output files will be stored. Default is "results".
    - verbose_level (int): The level of verbosity for printing information. Default is 0.
    Raises:
    - ValueError: If input_file, par_file, or data_file is not provided.
    - FileNotFoundError: If input_file or par_file is not found.
    Returns:
    - None
    """
    # Check for files 
    if not input_file:
        raise ValueError("Input file is required")
    if not par_file:
        raise ValueError("Parameter file is required")
    if not data_file:
        raise ValueError("Data file is required")


    # Check if files exist
    full_path_to_input_file = pathlib.Path(fit_dir) / input_file
    if not os.path.isfile(full_path_to_input_file):
        raise FileNotFoundError(f"Input file {input_file} not found")
    full_path_to_par_file = pathlib.Path(fit_dir) / par_file
    if not os.path.isfile(full_path_to_par_file):
        raise FileNotFoundError(f"Parameter file {par_file} not found")
    
    # Grab the directory from which the pleiades script was called.
    pleiades_call_dir = pathlib.Path.cwd()
    
    # Grab a run handle from the fit_dir
    run_handle = pathlib.Path(fit_dir).name

    # print info based on verbosity level
    if verbose_level > 0: print(f"Running SAMMY for {fit_dir}")    
    
    # Set the output directory
    sammy_output_dir = pathlib.Path(fit_dir) / output_dir 
    
    # Create the output directory
    os.makedirs(sammy_output_dir,exist_ok=True)
    
    # Create an output file in the working dir. 
    output_file_name = "output.out"
    output_file = pathlib.Path(fit_dir) / output_file_name
    if verbose_level > 0: print(f"Output file: {output_file}")


    # Create SAMMY run command depending on the call type compiled or docker
    if sammy_call == "compiled":
        sammy_run_command = textwrap.dedent(f"""\
        sammy <<EOF
        {input_file}
        {par_file}
        {data_file}

        EOF""")
    elif sammy_call == "docker":
        sammy_run_command = textwrap.dedent(f"""\
        docker run -i -v $(dirname $PWD):/data-parent -w /data-parent/{run_handle} {sammy_command} sammy <<EOF
        {input_file}
        {par_file}
        {data_file}

        EOF""")
    
    # Print the run command if verbose level is high enough
    if verbose_level > 1: print(sammy_run_command)
    
    # Change directories to the working dir
    os.chdir(fit_dir)
    
    # Open the output file in write mode
    with open(output_file_name, "w") as output:
        # Run the command and redirect output and error to the file
        if verbose_level > 0: print(f"Running SAMMY for {run_handle}...")
        subprocess.run(sammy_run_command, shell=True, executable='/bin/bash', stdout=output, stderr=subprocess.STDOUT)
    
    # Move the SAMNDF output files
    #  to the results folder
    for file in glob.glob("SAM*"):
        # Construct the full path for the destination
        destination_file = os.path.join(output_dir, os.path.basename(file))
        # Check if the file already exists in the destination folder
        if os.path.exists(destination_file):
            # Remove the existing file in the destination folder
            os.remove(destination_file)
        # Move the file to the results folder
        shutil.move(file, output_dir)

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
    fit_dir = config.params['directories']['sammy_fit_dir']
    input_file = config.params['input_file']
       
    # Print info based on verbosity level
    if verbose_level > 0: print("\nRunning SAMMY to create a par file from an ENDF file")

    # Check sammy environment
    sammy_sucess = check_sammy_enviornment(config, verbose_level)
    
    if not sammy_sucess:
        raise FileNotFoundError("SAMMY executable not found in the path")
    else:
        if verbose_level > 1: print(f"SAMMY executable found in the path")

    # Grab the directory from which the pleiades script was called.
    pleiades_call_dir = pathlib.Path.cwd()
    
    # Set the working directory path
    fit_dir = pathlib.Path(fit_dir)
    if verbose_level > 0: print(f"Working directory: {fit_dir}")
    
    # create an results folder within the working directory
    # We will be moving all the SAMMY results to this dir. 
    result_dir_name = 'results'
    os.makedirs(fit_dir,exist_ok=True)
    os.makedirs(fit_dir / result_dir_name,exist_ok=True)
    sammy_results_path = fit_dir / result_dir_name
    if verbose_level > 0: print(f"Results will be saved in: {sammy_results_path}")

    # Need to create a fake data file with only Emin and Emax data points
    # read the input file to get the Emin and Emax:
    if verbose_level > 0: print(f"Using input file: {input_file}")
    with open(fit_dir / input_file) as fid:
        next(fid)           # The first line is the isotope name
        line = next(fid)    # Read the second line with Emin and Emax
        Emin = line[20:30].strip()  # Extract Emin using character positions and strip spaces
        Emax = line[30:40].strip()  # Extract Emax using character positions and strip spaces
        
        if verbose_level > 1: print(f"Emin: {Emin}, Emax: {Emax}")
        
    
    # Creating the name of the data file based on the input file name
    data_file_name = run_handle + "_ENDF-dummy.dat"
    data_file = fit_dir / data_file_name
    
    # open the data file and write the Emin and Emax
    with open(data_file, "w") as fid:
        fid.write(f"{Emax} 0 0\n")
        fid.write(f"{Emin} 0 0\n")
    
    if verbose_level > 0: print(f"Data file created: {data_file}")
    

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
    
    if verbose_level > 0: print(f"ENDF file: {endf_file}")
    
    # Create an output file in the working dir. 
    output_file_name = run_handle + ".out"
    output_file = fit_dir / output_file_name
    if verbose_level > 0: print(f"Output file: {output_file}")

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
        docker run -i -v $(dirname $PWD):/data-parent -w /data-parent/{run_handle} {sammy_command} sammy <<EOF
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
        if verbose_level > 0: print(f"Running SAMMY for {run_handle}...")
        subprocess.run(sammy_run_command, shell=True, executable='/bin/bash', stdout=output, stderr=subprocess.STDOUT)
    
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
