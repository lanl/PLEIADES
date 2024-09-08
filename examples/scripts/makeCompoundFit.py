import json
from pleiades import sammyUtils, sammyRunner, sammyOutput, sammyPlotter

# Load the configuration file from the ini file in the parent directory
uranium = sammyUtils.SammyFitConfig('../configFiles/uranium.ini')

# If parFiles as needed, then create them from ENDF for each isotope
if uranium.params['run_endf_for_par'] == True:
    sammyUtils.create_parFile_from_endf(uranium,verbose_level=1)

# Configure the sammy run, this will create a compound parFile. 
sammyUtils.configure_sammy_run(uranium,verbose_level=1)

'''
# Run a sammy fit.
sammyRunner.run_sammy_fit(uranium,verbose_level=2)

# Grab the results from the SAMMY fit
uranium_fit = sammyOutput.lptResults(uranium.params['directories']['sammy_fit_dir']+"/results/SAMMY.LPT")

# Plot the results
sammyPlotter.process_and_plot_lst_file(uranium.params['directories']['sammy_fit_dir']+"/results/SAMMY.LST", residual=True,quantity='transmission')

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

# Update the `sammy_fit_dir` to a new directory name
uranium.params['directories']['sammy_fit_dir'] = uranium.params['directories']['sammy_fit_dir'] + "-ta181"

# check your work!
print(f"New fit directory: {uranium.params['directories']['sammy_fit_dir']}")

# Add Ta to the isotopes names and set initial abundance to 0.01
uranium.params['isotopes']['names'].append('Ta-181')
uranium.params['isotopes']['abundances'].append(0.01)

# check your work!
print(f"Names: {uranium.params['isotopes']['names']}")
print(f"Abundance: {uranium.params['isotopes']['abundances']}")

# Create the needed parFiles from ENDF for the isotopes in the configuration file
sammyUtils.create_parFile_from_endf(uranium,verbose_level=0)

# Configure the sammy run, this will create a compound parFile. 
sammyUtils.configure_sammy_run(uranium,verbose_level=1)

# Run the sammy fit.
success = sammyUtils.run_sammy(uranium,verbose_level=1)

uranium_fit = sammyOutput.lptResults(uranium.params['directories']['sammy_fit_dir']+"/results/SAMMY.LPT")

# Plot the results
sammyPlotter.process_and_plot_lst_file(uranium.params['directories']['sammy_fit_dir']+"/results/SAMMY.LST", residual=True,quantity='transmission')

'''