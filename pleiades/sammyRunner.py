
import pathlib
import inspect
import glob
import time
import os
import shutil
import subprocess
import datetime
import textwrap

def check_sammy_enviornment(sammy_call: str = "compiled", sammy_command: str = "sammy", verbose_level: int = 0) -> bool:
    """
    Check if the SAMMY executable is in the path or if a docker container is running.
    
    Args:
        sammy_call (str): compiled or docker
        sammy_command (str): either sammy or docker image name (such as "sammy-docker")
    
    Returns:
        bool: True if SAMMY is available, False otherwise
    """
    if sammy_call == "compiled":
        # Check if the sammy executable is in the path
        if shutil.which(sammy_command) is None:
            sammy_exists = False
        else: 
            sammy_exists = True

    elif sammy_call == "docker":
        # Check if Docker image exists
        docker_image = 'sammy-docker'
        docker_command = f'docker image inspect {docker_image}'
        try:
            subprocess.check_output(docker_command, shell=True, stderr=subprocess.STDOUT)
            sammy_exists = True
        except subprocess.CalledProcessError:
            sammy_exists = False

    if sammy_exists:
        return True

def run_sammy_fit(sammy_call = "compiled", fit_dir: str= "", input_file: str = "", par_file: str = "", data_file: str = "", output_dir: str = "results", verbose_level: int = 0) -> None:

    # check if SAMMY is compiled and sammy executable is in the path, or if a docker container is running
    if sammy_call == "compiled":
        # Check if the sammy executable is in the path
        if shutil.which("sammy") is None:
            raise FileNotFoundError("SAMMY executable not found in the path")
    elif sammy_call == "docker":
        # Check if the docker container is running
        if not os.path.exists("/.dockerenv"):
            raise FileNotFoundError("Docker container not running")

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

    # Create SAMMY run command
    sammy_run_command = textwrap.dedent(f"""\
    sammy <<EOF
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


def run_endf(sammy_call = "compiled", sammy_command = "sammy", run_handle: str="", endf_dir: str="", input_file: str = "", verbose_level: int = 0) -> None:
    """
    run sammy input with endf isotopes tables file to create a par file
    - This can only be done for a single isotope at a time
    - we don't need a data file, we create a fake dat file with only Emin and Emax data points
    - archive path name will be deducd from input name
    
    TODO: Need to think about how to clean up paths and names. SAMMY should run in the working directory, wheather it is the current directory or an archived one. Right now I am using names sometimes and paths other times. 

    Args:
        sammy_call (str): compiled or docker
        sammy_command (str): either sammy or docker image name (such as "sammy-docker")
        run_handle (str): run or handle name. This is what will be used for the dat and par file names
        endf_dir (str): working directory name
        inpfile (str): input file name
        verbose_level (int): verbosity level
    """    
    # Print info based on verbosity level
    if verbose_level > 0: print("\nRunning SAMMY to create a par file from an ENDF file")

    # Check sammy environment
    sammy_sucess = check_sammy_enviornment(sammy_call, sammy_command, verbose_level)
    
    if not sammy_sucess:
        raise FileNotFoundError("SAMMY executable not found in the path")
    else:
        if verbose_level > 1: print(f"SAMMY executable found in the path")

    # Grab the directory from which the pleiades script was called.
    pleiades_call_dir = pathlib.Path.cwd()
    
    # Set the working directory path
    endf_path = pathlib.Path(endf_dir)
    if verbose_level > 0: print(f"Working directory: {endf_path}")
    
    # create an results folder within the working directory
    # We will be moving all the SAMMY results to this dir. 
    result_dir_name = 'results'
    os.makedirs(endf_path,exist_ok=True)
    os.makedirs(endf_path / result_dir_name,exist_ok=True)
    sammy_results_path = endf_path / result_dir_name
    if verbose_level > 0: print(f"Results will be saved in: {sammy_results_path}")

    # Need to create a fake data file with only Emin and Emax data points
    # read the input file to get the Emin and Emax:
    if verbose_level > 0: print(f"Using input file: {input_file}")
    with open(endf_path / input_file) as fid:
        next(fid)           # The first line is the isotope name
        line = next(fid)    # Read the second line with Emin and Emax
        Emin = line[20:30].strip()  # Extract Emin using character positions and strip spaces
        Emax = line[30:40].strip()  # Extract Emax using character positions and strip spaces
        
        if verbose_level > 1: print(f"Emin: {Emin}, Emax: {Emax}")
        
    
    # Creating the name of the data file based on the input file name
    data_file_name = run_handle + "_ENDF-dummy.dat"
    data_file = endf_path / data_file_name
    
    # open the data file and write the Emin and Emax
    with open(data_file, "w") as fid:
        fid.write(f"{Emax} 0 0\n")
        fid.write(f"{Emin} 0 0\n")
    
    if verbose_level > 0: print(f"Data file created: {data_file}")
    
    # Creating a par file based on ENDF file
    symlink_path = endf_path / "res_endf8.endf"
    # First check if file already exists
    if os.path.islink(symlink_path):
        endf_file = symlink_path
    else:
        # Create a symbolic link to the original endf file
        original_endf_file = pathlib.Path(__file__).parent.parent / "nucDataLibs/resonanceTables/res_endf8.endf"
        os.symlink(original_endf_file, symlink_path)
        endf_file = endf_path / "res_endf8.endf"
    
    if verbose_level > 0: print(f"ENDF file: {endf_file}")
    
    # Create an output file in the working dir. 
    output_file_name = run_handle + ".out"
    output_file = endf_path / output_file_name
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
        docker run -v {endf_path}:/data {sammy_command} <<EOF
        {input_file}
        res_endf8.endf
        {data_file_name}

        EOF""")

    # Print the run command if verbose level is high enough    
    if verbose_level > 1: print(sammy_run_command)
    
    # Change directories to the working dir
    os.chdir(endf_path)
    
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
