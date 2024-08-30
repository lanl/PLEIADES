import json
from pleiades import sammyUtils, sammyOutput, sammyPlotter

# Load the configuration file from the ini file in the parent directory
uranium = sammyUtils.SammyFitConfig('../configFiles/uranium.ini')

# Create the needed parFiles from ENDF for the isotopes in the configuration file
sammyUtils.create_parFile_from_endf(uranium,verbose_level=1)

# Configure the sammy run, this will create a compound parFile. 
sammyUtils.configure_sammy_run(uranium,verbose_level=1)

# Run the sammy fit.
success = sammyUtils.run_sammy(uranium,verbose_level=1)

uranium_fit = sammyOutput.lptResults(uranium.params['directories']['sammy_fit_dir']+"/results/SAMMY.LPT")

# Print the final iteration of the fit which are the results we are interested in.
print(json.dumps(uranium_fit._results['Iteration Results'][-1],indent=4))

# Plot the results
sammyPlotter.process_and_plot_lst_file(uranium.params['directories']['sammy_fit_dir']+"/results/SAMMY.LST", residual=True,quantity='transmission')