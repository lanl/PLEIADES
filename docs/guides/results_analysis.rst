Analyzing SAMMY Results
=======================

This guide covers interpreting and visualizing SAMMY output using PLEIADES
analysis tools.

Overview
--------

After SAMMY execution, output files are collected in the output directory.
PLEIADES provides tools to parse and visualize these results.

**SAMMY Output Files:**

.. list-table::
   :header-rows: 1

   * - File
     - Description
   * - ``SAMMY.LPT``
     - Detailed log with fit iterations, chi-squared, parameters
   * - ``SAMMY.LST``
     - ASCII listing with calculated cross sections and data
   * - ``SAMMY.ODF``
     - Plot file with energy-dependent quantities
   * - ``SAMNDF.PAR``
     - Updated parameter file (after fitting)
   * - ``SAMNDF.INP``
     - Updated input file

Using ResultsManager
--------------------

:class:`~pleiades.sammy.results.manager.ResultsManager` is the primary
interface for loading and analyzing SAMMY results.

Loading Results
^^^^^^^^^^^^^^^

.. code-block:: python

   from pathlib import Path
   from pleiades.sammy.results.manager import ResultsManager

   # Paths to output files
   lpt_file = Path("./sammy_output/SAMMY.LPT")
   lst_file = Path("./sammy_output/SAMMY.LST")

   # Create results manager
   results_manager = ResultsManager(
       lpt_file_path=lpt_file,
       lst_file_path=lst_file,
   )

   # Access parsed data
   data = results_manager.get_data()

   print(f"Energy range: {data.energy.min():.3e} - {data.energy.max():.3e} eV")
   print(f"Data points: {len(data.energy)}")

Accessing Data Arrays
^^^^^^^^^^^^^^^^^^^^^

The ``get_data()`` method returns an object with NumPy arrays:

.. code-block:: python

   data = results_manager.get_data()

   # Energy array (eV)
   energies = data.energy

   # Experimental transmission
   exp_transmission = data.transmission

   # Calculated (fitted) transmission
   calc_transmission = data.calculated

   # Uncertainties
   uncertainties = data.uncertainty

Understanding LPT Files
-----------------------

The LPT file contains detailed information about the fitting process.
PLEIADES extracts key information using :class:`~pleiades.sammy.io.lpt_manager.LptManager`.

Fit Iterations
^^^^^^^^^^^^^^

Access information from each fitting iteration:

.. code-block:: python

   # Access fit results
   if results_manager.run_results.fit_results:
       for i, fit_result in enumerate(results_manager.run_results.fit_results):
           print(f"\nIteration {i+1}:")

           # Chi-squared metrics
           chi_sq = fit_result.get_chi_squared_results()
           if chi_sq.chi_squared is not None:
               print(f"  Chi-squared: {chi_sq.chi_squared:.4f}")
               print(f"  Degrees of freedom: {chi_sq.dof}")
               print(f"  Reduced chi-squared: {chi_sq.reduced_chi_squared:.6f}")

           # Physics parameters
           physics = fit_result.get_physics_data()
           if hasattr(physics, 'broadening_parameters'):
               bp = physics.broadening_parameters
               if bp.thick is not None:
                   print(f"  Number density: {bp.thick:.6e} atoms/barn-cm")
               if bp.temp is not None:
                   print(f"  Temperature: {bp.temp:.2f} K")

Final Fit Results
^^^^^^^^^^^^^^^^^

Get the final iteration results:

.. code-block:: python

   fit_results = results_manager.run_results.fit_results

   if fit_results:
       final = fit_results[-1]
       chi = final.get_chi_squared_results()

       print(f"Final reduced chi-squared: {chi.reduced_chi_squared:.6f}")

Understanding LST Files
-----------------------

The LST file contains the ASCII listing of calculated and experimental
transmission values. PLEIADES parses this using
:class:`~pleiades.sammy.io.lst_manager.LstManager`.

The LST data is automatically loaded when you create a ``ResultsManager``
with the ``lst_file_path`` parameter.

Plotting Results
----------------

PLEIADES provides built-in plotting functionality for visualizing
transmission fits.

Basic Transmission Plot
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   results_manager.plot_transmission()

This creates a plot showing:

- Experimental data points with error bars
- Fitted (calculated) transmission curve
- Legend with labels

Customized Plot
^^^^^^^^^^^^^^^

.. code-block:: python

   import matplotlib.pyplot as plt

   fig = results_manager.plot_transmission(
       figsize=(12, 8),
       title="Au-197 Neutron Transmission Fit",
       xscale="log",           # Logarithmic energy axis
       data_color="blue",      # Experimental data color
       final_color="red",      # Fit curve color
       show_diff=True,         # Show residual plot
       plot_uncertainty=True,  # Include error bars
       show=False,             # Don't display immediately
   )

   plt.tight_layout()
   plt.savefig("transmission_fit.png", dpi=150)
   plt.show()

Plot Options
^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Parameter
     - Description
     - Default
   * - ``figsize``
     - Figure size (width, height)
     - ``(10, 6)``
   * - ``title``
     - Plot title
     - ``None``
   * - ``xscale``
     - X-axis scale ("linear" or "log")
     - ``"linear"``
   * - ``show_diff``
     - Show residual subplot
     - ``False``
   * - ``plot_uncertainty``
     - Show error bars
     - ``True``
   * - ``data_color``
     - Color for experimental data
     - ``"blue"``
   * - ``final_color``
     - Color for calculated fit
     - ``"red"``

Fit Quality Metrics
-------------------

Understanding Chi-Squared
^^^^^^^^^^^^^^^^^^^^^^^^^

Chi-squared measures the agreement between experimental data and the fit:

.. math::

   \chi^2 = \sum_{i=1}^{N} \frac{(T_{\text{exp},i} - T_{\text{calc},i})^2}{\sigma_i^2}

Where:

- :math:`T_{\text{exp}}` is experimental transmission
- :math:`T_{\text{calc}}` is calculated transmission
- :math:`\sigma` is uncertainty
- :math:`N` is number of data points

Reduced Chi-Squared
^^^^^^^^^^^^^^^^^^^

Reduced chi-squared normalizes by degrees of freedom:

.. math::

   \chi^2_{\text{red}} = \frac{\chi^2}{\text{DOF}}

Interpretation:

- :math:`\chi^2_{\text{red}} \approx 1`: Good fit
- :math:`\chi^2_{\text{red}} >> 1`: Poor fit (underestimated uncertainties or bad model)
- :math:`\chi^2_{\text{red}} << 1`: Overfitting or overestimated uncertainties

Accessing Metrics
^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Get final chi-squared
   final_fit = results_manager.run_results.fit_results[-1]
   chi = final_fit.get_chi_squared_results()

   print(f"Chi-squared: {chi.chi_squared:.2f}")
   print(f"DOF: {chi.dof}")
   print(f"Reduced chi-squared: {chi.reduced_chi_squared:.4f}")

Extracting Fitted Parameters
----------------------------

Broadening Parameters
^^^^^^^^^^^^^^^^^^^^^

After fitting, access updated broadening parameters:

.. code-block:: python

   final_fit = results_manager.run_results.fit_results[-1]
   physics = final_fit.get_physics_data()

   if hasattr(physics, 'broadening_parameters'):
       bp = physics.broadening_parameters
       print(f"Number density: {bp.thick:.6e} atoms/barn-cm")
       print(f"Temperature: {bp.temp:.2f} K")

Updated Parameter File
^^^^^^^^^^^^^^^^^^^^^^

The fitted resonance parameters are written to ``SAMNDF.PAR``. This file
can be used as input for subsequent SAMMY runs:

.. code-block:: python

   from pleiades.sammy.interface import SammyFiles

   # Use fitted parameters for next analysis
   files = SammyFiles(
       input_file=Path("analysis.inp"),
       parameter_file=Path("sammy_output/SAMNDF.PAR"),  # Fitted params
       data_file=Path("new_data.twenty"),
   )

Complete Analysis Example
-------------------------

.. code-block:: python

   from pathlib import Path
   import matplotlib.pyplot as plt
   from pleiades.sammy.results.manager import ResultsManager

   # Load results
   results = ResultsManager(
       lpt_file_path=Path("sammy_output/SAMMY.LPT"),
       lst_file_path=Path("sammy_output/SAMMY.LST"),
   )

   # Print summary
   data = results.get_data()
   print(f"Energy range: {data.energy.min():.2e} - {data.energy.max():.2e} eV")
   print(f"Data points: {len(data.energy)}")

   # Chi-squared evolution
   print("\nFit Convergence:")
   for i, fit in enumerate(results.run_results.fit_results):
       chi = fit.get_chi_squared_results()
       print(f"  Iteration {i+1}: chi²_red = {chi.reduced_chi_squared:.4f}")

   # Final metrics
   final_chi = results.run_results.fit_results[-1].get_chi_squared_results()
   print(f"\nFinal reduced chi-squared: {final_chi.reduced_chi_squared:.4f}")

   # Create publication-quality plot
   fig = results.plot_transmission(
       figsize=(10, 8),
       title="Neutron Transmission Fit",
       xscale="log",
       show_diff=True,
       plot_uncertainty=True,
       show=False,
   )

   plt.savefig("fit_results.png", dpi=300, bbox_inches="tight")
   plt.show()

Troubleshooting
---------------

**Empty results**
   Ensure SAMMY completed successfully. Check ``SAMMY.LPT`` for error
   messages.

**Missing chi-squared**
   Chi-squared is only calculated during fitting runs, not initial
   calculations. Ensure your INP file requests fitting.

**No plot data**
   The LST file must contain the DATA column. Check that your SAMMY
   run produced output correctly.

Next Steps
----------

- :doc:`input_preparation` - Modify inputs for re-analysis
- :doc:`sammy_workflow` - Run additional SAMMY iterations
- :doc:`backends` - Try different execution backends
