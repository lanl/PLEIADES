
import pathlib
import inspect
import glob
import time
import os
import shutil

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

    Args:
        run_handle (str): run or handle name. This is what will be used for the dat and par file names
        working_dir (str): working directory name
        inpfile (str): input file name
        verbose_level (int): verbosity level
    """    
    
    if verbose_level > 0: print("Running SAMMY to create a par file from an ENDF file")
    
    # Set the working directory path
    working_dir_path = pathlib.Path(working_dir)
    if verbose_level > 0: print(f"Working directory: {working_dir_path}")
    
    # create an results folder within the working directory
    # We will be moving all the SAMMY results to this dir. 
    os.makedirs(working_dir_path,exist_ok=True)
    os.makedirs(working_dir_path / "results",exist_ok=True)
    sammy_results_path = working_dir_path / "results"
    if verbose_level > 0: print(f"Results will be saved in: {sammy_results_path}")

    # Need to create a fake data file with only Emin and Emax data points
    # read the input file to get the Emin and Emax:
    if verbose_level > 0: print(f"Using input file: {input_file}")
    with open(input_file) as fid:
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

    run_command = f"""sammy > {output_file} 2>/dev/null << EOF
                      {input_file}
                      {endf_file}
                      {data_file}

                      EOF 
                      """
                      
    # remove indentation
    run_command = inspect.cleandoc(run_command) # remove indentation
    
    if verbose_level > 0: print(run_command)
        
    # run the commande in the working directory
    os.system(run_command) # run sammy
    '''
    pwd = pathlib.Path.cwd()

    os.chdir(archive_path)
    os.system(run_command) # run sammy
    os.chdir(pwd)

    # move files
    shutil.move(archive_path /'SAMNDF.PAR', archive_path / f'results/{archivename}.par')
    shutil.move(archive_path /'SAMNDF.INP', archive_path / f'results/{archivename}.inp')
    shutil.move(archive_path /'SAMMY.LPT', archive_path / f'results/{archivename}.lpt')


    # remove SAM*.*
    filelist = glob.glob(f"{archive_path}/SAM*")
    for f in filelist:
        os.remove(f)

    '''
    
    return
    