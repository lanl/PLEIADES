import pandas
import argparse, sys
#import shutil
#import matplotlib.pyplot as plt

import pleiades.sammyInput as psi 
import pleiades.sammyRunner as psr 
import pleiades.sammyParFile as pspf
import pleiades.sammyOutput as pso
import pleiades.sammyPlotter as psp



def main(config_inp_file: str="config_inp.ini"):
    
    # Creating file names for SAMMY inputs and parameters. 
    run_name = config_inp_file.split(".")[0]
    sammy_inp_endf_file_name = run_name+"-endf.inp"
    sammy_inp_file_name = run_name+".inp"
    sammy_par_file_name = run_name+".par"
    sammy_data_file_name = run_name+".twenty"
    
    print("--> Reading config file and creating input file")
    # Use the InputFile methods read config file, process it into a input, and write an inp file
    sammy_input = psi.InputFile(config_inp_file)
    sammy_input.process()      
    sammy_input.write(sammy_inp_endf_file_name)    

    print("--> Running run_endf to generate par file")
    # Use the run_endf in sammyRunner to generate the needed par file.
    psr.run_endf(inpfile=sammy_inp_endf_file_name)
    
    print("--> Reading in ENDF par file and creating U_235 par file")
    sammy_parameters = pspf.ParFile("archive/U_235-endf/results/U_235-endf.par").read()   
    sammy_parameters.write("U_235.par")
    
    print("--> Updating input file for actual SAMMY fit")
    # Now need to modify input file to run an actual SAMMY fit. 
    sammy_input.data["Card1"]["title"] = "Run SAMMY to find abundance of uranium-235 isotope"  # modifying Title
    sammy_input.data["Card2"]["itmax"] = 4  # Modifying number of sammy fit iterations
    # update commands. We need to preform the REICH_MOORE and SOLVE_BAYES for this case
    sammy_input.data["Card3"]["commands"] = 'CHI_SQUARED,TWENTY,SOLVE_BAYES,QUANTUM_NUMBERS,GENERATE ODF FILE AUTOMATICALLY,REICH_MOORE_FORM'

    # Update info and write it. 
    sammy_input.process()      
    sammy_input.write(sammy_inp_file_name)
    
    print("--> Running SAMMY")
    # Run SAMMY!!!!!!
    psr.run(archivename=run_name,datafile=sammy_data_file_name)
    
    
    # Grab lpt file
    print("--> Reading in LPT file")
    siNat_lptResults = pso.lptResults("archive/U_235/results/U_235.LPT")

    # Plot the results
    print("--> Plotting LPT file")
    psp.process_and_plot_lst_file("archive/U_235/results/U_235.LST", residual=True, quantity='transmission')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process config file for sammy input, run sammy, and plot results.')
    parser.add_argument('--sammyConfig', type=str, default='config.ini', help='Path to the sammy config file')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    else:
        args = parser.parse_args()
        main(args.sammyConfig)
