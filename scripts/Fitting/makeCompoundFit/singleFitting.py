import pandas
import argparse, sys
import matplotlib.pyplot as plt
import numpy as np

#import pprint

import pleiades.sammyInput as psi 
import pleiades.sammyRunner as psr 
import pleiades.sammyParFile as pspf
import pleiades.sammyOutput as pso



def main(config_inp_file: str="config_inp.ini"):
    
    # Creating file names for SAMMY inputs and parameters. 
    run_name = config_inp_file.split(".")[0]
    sammy_inp_file_name = run_name+".inp"
    sammy_inp_file_name = run_name+".inp"
    sammy_par_file_name = run_name+".par"
    
    # Use the InputFile methods read config file, process it into a input, and write an inp file
    print("--> Reading config file and creating input file")
    sammy_input = psi.InputFile(config_inp_file)
    sammy_input.process()      
    sammy_input.write(sammy_inp_file_name)    

    # Use the run_endf in sammyRunner to generate the needed par file.
    print("--> Running run_endf to generate par file")
    psr.run_endf(inpfile=sammy_inp_file_name)
    
    print("--> Reading in ENDF par file and creating Eu-153 par file")
    sammy_parameters = pspf.ParFile("archive/Eu_153/results/Eu_153.par").read()   
    sammy_parameters.write("Eu_153.par")
    
    print("--> Updating input file for actual SAMMY fit")
    # Now need to modify input file to run an actual SAMMY fit. 
    sammy_input.data["Card1"]["title"] = "Run SAMMY to find abundance of Eu-153 isotope"
    # update commands. We need to preform the REICH_MOORE and SOLVE_BAYES for this case
    sammy_input.data["Card3"]["commands"] = 'CHI_SQUARED,CSISRS,SOLVE_BAYES,QUANTUM_NUMBERS,REICH_MOORE_FORM,GENERATE ODF FILE AUTOMATICALLY,RPI TRANSMISSION RESOLUTION FUNCTION'
    # set the resolution width from flight path according to the RPI paper
    sammy_input.data["Card5"]["deltal"] = 0.0055
    sammy_input.data["Card7"]["thick"] = 0.0021 # atoms/barn

    # Update info and write it. 
    sammy_input.process()      
    sammy_input.write(sammy_inp_file_name)
    
    # Run SAMMY!!!!!!
    print("--> Running SAMMY")
    psr.run(archivename=run_name,datafile="Eu_153.dat") 
    
    # Grab lpt file
    print("--> Reading in LPT file")
    lpt = pso.LptFile("archive/Eu_153/results/Eu_153.lpt")
    lpt.register_new_stats(keyname="weight_153",start_text="  Isotopic abundance",skipped_rows=3,line_format="float(line.split()[1])")
    stats = lpt.stats()
    
    stats_df = pandas.DataFrame(stats,index=["Eu_153 fit vary abundance"])
    stats_df["real_weight_151"] = 0.4781
    stats_df["real_weight_153"] = 0.5219
    
    df = pandas.read_csv("archive/Eu_153/results/Eu_153.lst",delim_whitespace=True,header=None,names=["energy","xs_data","xs_data_err","xs_initial","xs_final","trans_data","trans_data_err","trans_initial","trans_final"])


    fig, ax = plt.subplots(2,2, sharey=False,figsize=(8,6),gridspec_kw={"width_ratios":[5,1],"height_ratios":[5,2]})
    ax = np.ravel(ax)   

    df.plot(x="energy",y="trans_data",ax=ax[0],colors=["0.8"],zorder=-1)
    df.plot(x="energy",y=["trans_initial","trans_final"],ax=ax[0],colors=["royalblue","tomato"],alpha=0.8)
    ax[0].set_xlabel("")
    ax[0].set_xticks([])
    ax[0].legend(["data","initial fit - χ2=2.69","final fit - χ2=1.3"])
    ax[0].set_ylabel("")
    ax[0].set_ylabel("transmission")
    # ax[0].set_title("fit Eu-153 data from RPI using SAMMY8.1 with ENDF8")

    ax[1].spines['right'].set_visible(False)
    ax[1].spines['top'].set_visible(False)
    ax[1].spines['bottom'].set_visible(False)
    ax[1].spines['left'].set_visible(False)
    ax[1].set_xticks([])
    ax[1].set_yticks([],[])
    
    '''
    df["residual_initial"] = (df["trans_initial"] - df["trans_data"])/df["trans_data_err"]
    df["residual_final"] = (df["trans_final"] - df["trans_data"])/df["trans_data_err"]
    df.plot(x="energy",y=["residual_initial","residual_final"],marker=".",lw=0,ms=3,ylim=(-10,10),ax=ax[2],alpha=0.8,colors=["royalblue","tomato"],legend=False)
    ax[2].set_ylabel("residuals\n(fit-data)/err [σ]")
    # ax[2].legend(["initial fit","final fit"],loc=2,frameon=True)
    ax[2].set_xlabel("energy [eV]")
    # ax[2].set_xlim(0,100)

    df.plot.hist(y=["residual_initial","residual_final"],bins=np.arange(-8,8,0.2),ax=ax[3],orientation="horizontal",legend=False,alpha=0.8,histtype="stepfilled",colors=["royalblue","tomato"])
    ax[3].set_xlabel("")
    ax[3].set_xticks([],[])
    ax[3].set_yticks([],[])
    ax[3].spines['right'].set_visible(False)
    ax[3].spines['top'].set_visible(False)
    ax[3].spines['bottom'].set_visible(False)
    ax[3].spines['left'].set_visible(False)
    ax[2].set_ylim(-10,10)
    # df.plot.hist(y=["res_initial","residual"],bins=arange(-8,8,0.2),
    #             ax=ax[1],orientation="horizontal",
    #             histtype="step",legend=False,)
    plt.subplots_adjust(wspace=0.003,hspace=0.03)
    '''
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process config file for sammy input, run sammy, and plot results.')
    parser.add_argument('--sammyConfig', type=str, default='config.ini', help='Path to the sammy config file')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    else:
        args = parser.parse_args()
        main(args.sammyConfig)
