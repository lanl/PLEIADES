import pandas
from pleiades import sammyUtils, sammyPlotter

# Load the configuration file from the ini file in the parent directory
natEu = sammyUtils.SammyFitConfig('makeCompoundFit_Eu.ini')

# Create the needed parFiles from ENDF for the isotopes in the configuration file
sammyUtils.create_parFile_from_endf(natEu,verbose_level=0)

# Configure the sammy run, this will create a compound parFile. 
sammyUtils.configure_sammy_run(natEu,verbose_level=0)

# Run the sammy fit.
sammyUtils.run_sammy(natEu,verbose_level=2)

# Plot the results
sammyPlotter.process_and_plot_lst_file(natEu.params['directories']['sammy_fit_dir']+"/results/SAMMY.LST", quantity='transmission')