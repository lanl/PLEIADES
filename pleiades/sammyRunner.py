
import pathlib
import inspect
import glob
import time
import os
import shutil
import subprocess
import datetime
import textwrap


def single_run(fit_dir: str= "", input_file: str = "", par_file: str = "", data_file: str = "", output_dir: str = "results", verbose_level: int = 0) -> None:
    
    # Check for files 
    if not input_file:
        raise ValueError("Input file is required")
    if not par_file:
        raise ValueError("Parameter file is required")
    if not data_file:
        raise ValueError("Data file is required")
        
    # Create a symbolic link to the data file in the fit_dir
    data_file_name = pathlib.Path(data_file).name

    # Check if the symbolic link already exists
    if os.path.islink(pathlib.Path(fit_dir) / data_file_name): 
        os.unlink(pathlib.Path(fit_dir) / data_file_name)           # unlink old symlink

    os.symlink(data_file, pathlib.Path(fit_dir) / data_file_name)   # create new symlink
    
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
        destination_file = os.path.join(output_dir, os.path.basename(file))
        # Check if the file already exists in the destination folder
        if os.path.exists(destination_file):
            # Remove the existing file in the destination folder
            os.remove(destination_file)
        # Move the file to the results folder
        shutil.move(file, output_dir)

    # Change back to the original directory where the pleiades python script was called
    os.chdir(pleiades_call_dir)


def run_endf(run_handle: str="",endf_dir: str="", input_file: str = "", verbose_level: int = 0) -> None:
    """
    run sammy input with endf isotopes tables file to create a par file
    - This can only be done for a single isotope at a time
    - we don't need a data file, we create a fake dat file with only Emin and Emax data points
    - archive path name will be deducd from input name
    
    TODO: Need to think about how to clean up paths and names. SAMMY should run in the working directory, wheather it is the current directory or an archived one. Right now I am using names sometimes and paths other times. 

    Args:
        run_handle (str): run or handle name. This is what will be used for the dat and par file names
        endf_dir (str): working directory name
        inpfile (str): input file name
        verbose_level (int): verbosity level
    """    
    # Print info based on verbosity level
    if verbose_level > 0: print("\nRunning SAMMY to create a par file from an ENDF file")
    
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

    sammy_run_command = textwrap.dedent(f"""\
    sammy <<EOF
    {input_file}
    res_endf8.endf
    {data_file_name}

    EOF""")
    
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


    
def run(archivename: str="example",
            inpfile: str = "",
            parfile: str = "",
            datafile: str = "") -> None:
    """run the sammy program inside an archive directory

    Args:
        archivename (str): archive directory name. If only archivename is provided
                           the other file names will be assumed to have the same name 
                           at the archive has with the associate extension, e.g. {archivename}.inp
        inpfile (str, optional): input file name
        parfile (str, optional): parameter file name
        datafile (str, optional): data file name
    """

    # if no file names are provided, assume they are the same as the archive name
    if not inpfile:
        inpfile = f"{archivename}.inp"
    if not parfile:
        parfile = f"{archivename}.par"
    if not datafile:
        datafile = f"{archivename}.dat"

    # Set the archive path
    archive_path = pathlib.Path(f"archive/{archivename}") 

    # create an archive directory
    os.makedirs(archive_path,exist_ok=True)
    os.makedirs(archive_path / "results",exist_ok=True)


    # copy files into archive
    try:
        shutil.copy(inpfile, archive_path / f'{archivename}.inp')
        inpfile = f'{archivename}.inp'
        shutil.copy(parfile, archive_path / f'{archivename}.par')
        parfile = f'{archivename}.par'
        shutil.copy(datafile, archive_path / f'{archivename}.dat')
        datafile = f'{archivename}.dat'
    except FileNotFoundError:
        # print(f"grab files from within the {archive_path} directory")
        pass

    outputfile = f'{archivename}.out'

    # generate the run command
    run_command = f"""sammy > {outputfile} 2>/dev/null << EOF
                      {inpfile}
                      {parfile}
                      {datafile}

                      EOF 
                      """
    # remove indentation
    run_command = inspect.cleandoc(run_command) # remove indentation
    
    # 
    pwd = pathlib.Path.cwd()

    # change directory to the archive, run sammy, and return to the original directory
    os.chdir(archive_path)
    os.system(run_command) 
    os.chdir(pwd)

    # move files

    try:
        shutil.move(archivepath /'SAMMY.LST', archivepath / f'results/{archivename}.lst')
    except FileNotFoundError:
        print("lst file is not found")
    try:
        shutil.move(archivepath /'SAMMY.LPT', archivepath / f'results/{archivename}.lpt')
    except FileNotFoundError:
        print("lpt file is not found")
    try:
        shutil.move(archivepath /'SAMMY.IO', archivepath / f'results/{archivename}.io')
    except FileNotFoundError:
        print("io file is not found")
    try:
        shutil.move(archivepath /'SAMMY.PAR', archivepath / f'results/{archivename}.par')
        # remove SAM*.*
        filelist = glob.glob(f"{archivepath}/SAM*")
        for f in filelist:
            os.remove(f)
    except FileNotFoundError:
        print("par file is not found")
    return