
import pathlib
import inspect
import glob
import time
import os
import shutil
import subprocess
import datetime
import textwrap

def run_sammy()

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


def run_endf(run_handle: str="",working_dir: str="", input_file: str = "", verbose_level: int = 0) -> None:
    """
    run sammy input with endf isotopes tables file to create a par file
    - This can only be done for a single isotope at a time
    - we don't need a data file, we create a fake dat file with only Emin and Emax data points
    - archive path name will be deducd from input name
    
    TODO: Need to think about how to clean up paths and names. SAMMY should run in the working directory, wheather it is the current directory or an archived one. Right now I am using names sometimes and paths other times. 

    Args:
        run_handle (str): run or handle name. This is what will be used for the dat and par file names
        working_dir (str): working directory name
        inpfile (str): input file name
        verbose_level (int): verbosity level
    """    
    # Print info based on verbosity level
    if verbose_level > 0: print("\nRunning SAMMY to create a par file from an ENDF file")
    
    # Grab the directory from which the pleiades script was called.
    pleiades_call_dir = pathlib.Path.cwd()
    
    # Set the working directory path
    working_dir_path = pathlib.Path(working_dir)
    if verbose_level > 0: print(f"Working directory: {working_dir_path}")
    
    # create an results folder within the working directory
    # We will be moving all the SAMMY results to this dir. 
    result_dir_name = 'results'
    os.makedirs(working_dir_path,exist_ok=True)
    os.makedirs(working_dir_path / result_dir_name,exist_ok=True)
    sammy_results_path = working_dir_path / result_dir_name
    if verbose_level > 0: print(f"Results will be saved in: {sammy_results_path}")

    # Need to create a fake data file with only Emin and Emax data points
    # read the input file to get the Emin and Emax:
    if verbose_level > 0: print(f"Using input file: {input_file}")
    with open(working_dir_path / input_file) as fid:
        next(fid)           # The first line is the isotope name
        line = next(fid)    # Read the second line with Emin and Emax
        Emin = line[20:30].strip()  # Extract Emin using character positions and strip spaces
        Emax = line[30:40].strip()  # Extract Emax using character positions and strip spaces
        
        if verbose_level > 1: print(f"Emin: {Emin}, Emax: {Emax}")
        
    
    # Creating the name of the data file based on the input file name
    data_file_name = run_handle + "_ENDF-dummy.dat"
    data_file = working_dir_path / data_file_name
    
    # open the data file and write the Emin and Emax
    with open(data_file, "w") as fid:
        fid.write(f"{Emax} 0 0\n")
        fid.write(f"{Emin} 0 0\n")
    
    if verbose_level > 0: print(f"Data file created: {data_file}")
    
    # Creating a par file based on ENDF file
    symlink_path = working_dir_path / "res_endf8.endf"
    # First check if file already exists
    if os.path.islink(symlink_path):
        endf_file = symlink_path
    else:
        # Create a symbolic link to the original endf file
        original_endf_file = pathlib.Path(__file__).parent.parent / "nucDataLibs/resonanceTables/res_endf8.endf"
        os.symlink(original_endf_file, symlink_path)
        endf_file = working_dir_path / "res_endf8.endf"
    
    if verbose_level > 0: print(f"ENDF file: {endf_file}")
    
    # Create an output file in the working dir. 
    output_file_name = run_handle + ".out"
    output_file = working_dir_path / output_file_name
    if verbose_level > 0: print(f"Output file: {output_file}")

    sammy_run_command = textwrap.dedent(f"""\
    sammy <<EOF
    {input_file}
    res_endf8.endf
    {data_file_name}

    EOF""")
    
    if verbose_level > 1: print(sammy_run_command)
    
    # Change directories to the working dir
    os.chdir(working_dir_path)
    
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
    