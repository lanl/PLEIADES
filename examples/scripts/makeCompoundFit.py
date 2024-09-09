import json
from pleiades import sammyUtils, sammyRunner, sammyOutput, sammyPlotter

# Load the configuration file from the ini file in the parent directory
uranium = sammyUtils.SammyFitConfig('../configFiles/uranium.ini')

# If parFiles as needed, then create them from ENDF for each isotope
if uranium.params['run_endf_for_par'] == True:
    sammyUtils.create_parFile_from_endf(uranium,verbose_level=0)

# Configure the sammy run, this will create a compound parFile. 
sammy_run = sammyUtils.configure_sammy_run(uranium,verbose_level=0)

# Run a sammy fit.
sammyRunner.run_sammy_fit(sammy_run, verbose_level=0)

# Grab the results from the SAMMY fit and plot the fit
results_lpt = uranium.params['directories']['sammy_fit_dir'] / 'results/SAMMY.LPT'
results_lst = uranium.params['directories']['sammy_fit_dir'] / 'results/SAMMY.LST'
uranium_fit = sammyOutput.lptResults(results_lpt)
sammyPlotter.process_and_plot_lst_file(results_lst, residual=True,quantity='transmission')

# Print out the initial parameters for the isotopes (names and abundances)
print(f"Isotopes: {uranium.params['isotopes']['names']}")
print(f"Initial Abundance: {uranium.params['isotopes']['abundances']}")
print(f"Initial Thickness: {uranium.params['broadening']['thickness']}")

# Update the isotope abundances with the new results from the SAMMY fit
for i, isotope in enumerate(uranium.params['isotopes']['names']):
    uranium.params['isotopes']['abundances'][i] = float(uranium_fit._results['Iteration Results'][-1]['Nuclides'][i]['Abundance'])
    
# Update the sample thickness with the new results from the SAMMY fit
uranium.params['broadening']['thickness'] = float(uranium_fit._results['Iteration Results'][-1]['Thickness'])

# check your work!
print(f"New Abundance: {uranium.params['isotopes']['abundances']}")
print(f"New Thickness: {uranium.params['broadening']['thickness']}")

#Create new fit directory
uranium.params['directories']['sammy_fit_dir'] = uranium.params['directories']['working_dir'] / "u235-u238-ta181"

# check your work!
print(f"New fit directory: {uranium.params['directories']['sammy_fit_dir']}")

# Add Ta to the isotopes names and set initial abundance to 0.01
uranium.params['isotopes']['names'].append('Ta-181')
uranium.params['isotopes']['abundances'].append(0.01)

# check your work!
print(f"Names: {uranium.params['isotopes']['names']}")
print(f"Abundance: {uranium.params['isotopes']['abundances']}")

# Create a new par file for the additional isotope Ta-181
if uranium.params['run_endf_for_par'] == True:
    sammyUtils.create_parFile_from_endf(uranium,verbose_level=0)


# Configure the sammy run, this will create a compound parFile. 
sammy_run = sammyUtils.configure_sammy_run(uranium,verbose_level=0)

# Run the new sammy fit.
sammyRunner.run_sammy_fit(sammy_run, verbose_level=0)

# Grab the results from the SAMMY fit and plot the fit
updated_results_lpt = uranium.params['directories']['sammy_fit_dir'] / 'results/SAMMY.LPT'
updated_results_lst = uranium.params['directories']['sammy_fit_dir'] / 'results/SAMMY.LST'
updated_uranium_fit = sammyOutput.lptResults(results_lpt)
sammyPlotter.process_and_plot_lst_file(updated_results_lst, residual=True,quantity='transmission')
