from pleiades import sammyUtils, sammyPlotter, sammyOutput

# Load the configuration file from the ini file in the parent directory
natEu = sammyUtils.SammyFitConfig('makeCompoundFit_Eu.ini')
print(natEu.params['broadening'])

# Create the needed parFiles from ENDF for the isotopes in the configuration file
sammyUtils.create_parFile_from_endf(natEu,verbose_level=1)

# Configure the sammy run, this will create a compound parFile. 
sammyUtils.configure_sammy_run(natEu,verbose_level=1)

# Run the sammy fit.
sammyUtils.run_sammy(natEu,verbose_level=2)

# Plot results
sammyPlotter.process_and_plot_lst_file(natEu.params['directories']['sammy_fit_dir'] + '/results/SAMMY.LST',residual=True,quantity='transmission')


sammy_results = sammyOutput.lptResults(natEu.params['directories']['sammy_fit_dir'] + '/results/SAMMY.LPT')

'''
# update abundances 
for i in range(len(natEu.params['isotopes']['abundances'])):
    natEu.params['isotopes']['abundances'][i] = float(sammy_results._results["Iteration Results"][-1]["Nuclides"][i]['Abundance'])

# update thickness
natEu.params["broadening"]['thickness'] = float(sammy_results._results["Iteration Results"][-1]["Thickness"])

# Toggle the broadening to vary the flight path spread
natEu.params["broadening"]['vary_flight_path_spread'] = 'True'

# Configure a new sammy par file from updated config and run sammy 
sammyUtils.configure_sammy_run(natEu,verbose_level=1)
sammyUtils.run_sammy(natEu,verbose_level=2)

# Plot results
sammyPlotter.process_and_plot_lst_file(natEu.params['directories']['sammy_fit_dir'] + '/results/SAMMY.LST',residual=True,quantity='transmission')
'''