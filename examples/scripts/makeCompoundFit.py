Usage Guide
===========

This guide walks you through a complete workflow using the PLEIADES library to configure and run SAMMY fits, update isotope parameters, and plot the results.

Setup
-----

Ensure that you have a configuration file (like `uranium.ini`) set up, and SAMMY is installed in your environment. The example below demonstrates how to use a configuration file to set up a SAMMY run, update parameters, and plot the results.

Example: Running a SAMMY Fit
----------------------------

1. **Load the Configuration**: Start by loading a SAMMY configuration file.

.. code-block:: python

    from pleiades import sammyUtils, sammyRunner, sammyOutput, sammyPlotter

    # Load the configuration from the INI file
    uranium = sammyUtils.SammyFitConfig('../configFiles/uranium.ini')

2. **Generate Par Files**: If required, create the parameter files from ENDF data for each isotope.

.. code-block:: python

    # Check if ENDF par files need to be generated
    if uranium.params['run_endf_for_par'] == True:
        sammyUtils.create_parFile_from_endf(uranium, verbose_level=1)

3. **Configure the SAMMY Run**: Configure the SAMMY run by generating a compound parameter file.

.. code-block:: python

    # Configure the SAMMY run
    sammy_run = sammyUtils.configure_sammy_run(uranium, verbose_level=1)

4. **Run the SAMMY Fit**: Now, run the SAMMY fit with the generated configuration.

.. code-block:: python

    # Run the SAMMY fit
    sammyRunner.run_sammy_fit(sammy_run, verbose_level=1)

5. **Process and Plot Results**: After the fit, retrieve the results and plot the output using the `sammyPlotter`.

.. code-block:: python

    # Define the paths to the SAMMY output files
    results_lpt = uranium.params['directories']['sammy_fit_dir'] / 'results/SAMMY.LPT'
    results_lst = uranium.params['directories']['sammy_fit_dir'] / 'results/SAMMY.LST'

    # Load the SAMMY results and plot
    uranium_fit = sammyOutput.lptResults(results_lpt)
    sammyPlotter.process_and_plot_lst_file(results_lst, residual=True, quantity='transmission')

6. **Inspect Initial Parameters**: Print out the initial isotope parameters such as names and abundances.

.. code-block:: python

    print(f"Isotopes: {uranium.params['isotopes']['names']}")
    print(f"Initial Abundance: {uranium.params['isotopes']['abundances']}")
    print(f"Initial Thickness: {uranium.params['broadening']['thickness']}")

Updating Parameters after the Fit
---------------------------------

1. **Update Isotope Abundances**: After running the SAMMY fit, update the isotope abundances based on the results.

.. code-block:: python

    # Update the isotope abundances with the SAMMY fit results
    for i, isotope in enumerate(uranium.params['isotopes']['names']):
        uranium.params['isotopes']['abundances'][i] = float(uranium_fit._results['Iteration Results'][-1]['Nuclides'][i]['Abundance'])

2. **Update Sample Thickness**: Similarly, update the sample thickness with the new fit results.

.. code-block:: python

    # Update the sample thickness
    uranium.params['broadening']['thickness'] = float(uranium_fit._results['Iteration Results'][-1]['Thickness'])

3. **Check Your Work**: Print the updated abundances and thickness.

.. code-block:: python

    print(f"New Abundance: {uranium.params['isotopes']['abundances']}")
    print(f"New Thickness: {uranium.params['broadening']['thickness']}")

Adding New Isotopes
-------------------

You can modify the configuration by adding new isotopes to the existing list and running another SAMMY fit.

1. **Set Up a New Fit Directory**: First, create a new directory for the updated SAMMY fit.

.. code-block:: python

    # Create a new fit directory
    uranium.params['directories']['sammy_fit_dir'] = uranium.params['directories']['working_dir'] / "u235-u238-ta181"
    print(f"New fit directory: {uranium.params['directories']['sammy_fit_dir']}")

2. **Add a New Isotope**: Add a new isotope (`Ta-181`) to the isotope list with an initial abundance.

.. code-block:: python

    # Add Ta-181 to the isotopes with initial abundance
    uranium.params['isotopes']['names'].append('Ta-181')
    uranium.params['isotopes']['abundances'].append(0.01)

    # Check the updated isotopes
    print(f"Names: {uranium.params['isotopes']['names']}")
    print(f"Abundance: {uranium.params['isotopes']['abundances']}")

3. **Create New Par Files**: If necessary, generate new par files for the added isotopes.

.. code-block:: python

    # Create par file for Ta-181 if needed
    if uranium.params['run_endf_for_par'] == True:
        sammyUtils.create_parFile_from_endf(uranium, verbose_level=1)

4. **Run the New SAMMY Fit**: Configure and run another SAMMY fit with the updated configuration.

.. code-block:: python

    # Configure the new SAMMY run
    sammy_run = sammyUtils.configure_sammy_run(uranium, verbose_level=1)

    # Run the SAMMY fit
    sammyRunner.run_sammy_fit(sammy_run, verbose_level=1)

5. **Process and Plot the Updated Results**: Finally, retrieve the updated results and plot them.

.. code-block:: python

    updated_results_lpt = uranium.params['directories']['sammy_fit_dir'] / 'results/SAMMY.LPT'
    updated_results_lst = uranium.params['directories']['sammy_fit_dir'] / 'results/SAMMY.LST'

    # Load and plot the updated SAMMY results
    updated_uranium_fit = sammyOutput.lptResults(updated_results_lpt)
    sammyPlotter.process_and_plot_lst_file(updated_results_lst, residual=True, quantity='transmission')
