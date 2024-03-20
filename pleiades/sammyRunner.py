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

    # Define the files to move
    files_to_move = ['SAMMY.PAR', 'SAMMY.LST', 'SAMMY.LPT', 'SAMMY.IO']

    # Move files
    for file in files_to_move:
        source = archive_path / file
        destination = archive_path / f'results/{archivename}.{file.split(".")[-1]}'
        
        if pathlib.Path(source).exists():
            shutil.move(source, destination)
        else:
            print(f"File {source} does not exist.")

    # remove SAM*.*
    filelist = glob.glob(f"{archive_path}/SAM*")
    for f in filelist:
        os.remove(f)
    
    return


def run_endf(archivename: str="example",inpfile: str = "") -> None:
    """
    run sammy input with endf isotopes tables file to create a par file
    - This can only be done for a single isotope at a time
    - we don't need a data file, we create a fake dat file with only Emin and Emax data points
    - archive path name will be deducd from input name

    Args:
        inpfile (str): input file name
    """    

    inpfile= pathlib.Path(inpfile)
    archivename = pathlib.Path(inpfile.stem)

    # read the input file to get the Emin and Emax:
    with open(inpfile) as fid:
        next(fid)
        Emin, Emax = next(fid).split()[2:4]

    archive_path = pathlib.Path("archive") / archivename

    # create an archive directory
    os.makedirs(archive_path,exist_ok=True)
    os.makedirs(archive_path / "results",exist_ok=True)


    # copy files into archive
    shutil.copy(inpfile, archive_path / archivename.with_suffix(".inp"))
    inpfile = archivename.with_suffix(".inp")
    



    # write a fake datafile with two entries of Emin and Emax
    with open(archive_path / f'{archivename}.dat',"w") as fid:
        fid.write(f"{Emax} 0 0\n")
        fid.write(f"{Emin} 0 0\n")
    
    datafile = f'{archivename}.dat'

    endffile = pathlib.Path(__file__).parent.parent / "nucDataLibs/resonanceTables/res_endf8.endf"
    try:
        os.symlink(endffile,archive_path / 'res_endf8.endf')
    except FileExistsError:
        pass
    endffile = 'res_endf8.endf'

    outputfile = f'{archivename}.out'

    run_command = f"""sammy > {outputfile} 2>/dev/null << EOF
                      {inpfile}
                      {endffile}
                      {datafile}

                      EOF 
                      """
    run_command = inspect.cleandoc(run_command) # remove indentation
    
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

    return