Preparing SAMMY Input Files
============================

This guide covers creating the input files required by SAMMY using PLEIADES
automation tools.

Overview
--------

SAMMY requires three primary input files:

- **INP file**: Control file specifying analysis parameters, energy range,
  broadening settings, and output options
- **PAR file**: Parameter file containing resonance parameters (from ENDF
  or previous fits)
- **Data file**: Experimental transmission data in SAMMY's twenty format

PLEIADES provides tools to generate these files programmatically:

- :class:`~pleiades.sammy.io.inp_manager.InpManager` - Creates INP files
- :class:`~pleiades.sammy.io.json_manager.JsonManager` - Creates JSON
  configuration and stages ENDF parameter files
- :mod:`pleiades.sammy.io.data_manager` - Converts data to SAMMY format

Data Format Conversion
----------------------

SAMMY uses a specific "twenty" format for transmission data. PLEIADES can
convert CSV or text-based transmission data to this format.

Converting Transmission Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :func:`~pleiades.sammy.io.data_manager.convert_csv_to_sammy_twenty` to
convert transmission files:

.. code-block:: python

   from pathlib import Path
   from pleiades.sammy.io.data_manager import (
       convert_csv_to_sammy_twenty,
       validate_sammy_twenty_format,
   )

   # Convert transmission data to SAMMY twenty format
   input_file = Path("spectra/Run_8022_transmission.txt")
   output_file = Path("twenty/Run_8022_transmission.twenty")

   convert_csv_to_sammy_twenty(input_file, output_file)

   # Validate the output format
   if validate_sammy_twenty_format(output_file):
       print(f"Valid SAMMY twenty file: {output_file}")

Input File Format
^^^^^^^^^^^^^^^^^

The input CSV/text file should contain columns for:

- Energy (eV)
- Transmission (dimensionless, 0-1)
- Uncertainty (standard deviation)

The columns can be comma or whitespace separated.

INP File Generation
-------------------

The INP file controls SAMMY execution parameters. PLEIADES generates
INP files through :class:`~pleiades.sammy.io.inp_manager.InpManager`.

Dataset Metadata
^^^^^^^^^^^^^^^^

Define typed dataset metadata and fit configuration:

.. code-block:: python

   from pleiades.sammy.fitting.config import FitConfig
   from pleiades.sammy.io.inp_manager import InpDatasetMetadata

   fit_config = FitConfig()
   fit_config.physics_params.broadening_parameters.crfn = 8.0

   dataset_metadata = InpDatasetMetadata(
       element="Au",
       mass_number=197,
       density_g_cm3=19.32,
       thickness_mm=0.025,
       atomic_mass_amu=196.966569,
       min_energy_eV=1.0,
       max_energy_eV=200.0,
       temperature_K=293.6,
   )

Creating the INP File
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pathlib import Path
   from pleiades.sammy.fitting.config import FitConfig
   from pleiades.sammy.io.inp_manager import InpDatasetMetadata, InpManager

   fit_config = FitConfig()
   fit_config.physics_params.broadening_parameters.crfn = 8.0
   dataset_metadata = InpDatasetMetadata(
       element="Au",
       mass_number=197,
       density_g_cm3=19.32,
       thickness_mm=0.025,
       atomic_mass_amu=196.966569,
       min_energy_eV=1.0,
       max_energy_eV=200.0,
       temperature_K=293.6,
   )

   # Resolution function file (facility-specific)
   resolution_file = Path("/path/to/resolution_function.dat")

   # Create INP file
   inp_file = Path("./working/analysis.inp")
   InpManager.create_multi_isotope_inp(
       inp_file,
       fit_config=fit_config,
       title="Au-197 neutron transmission analysis",
       dataset_metadata=dataset_metadata,
       resolution_file_path=resolution_file,
   )

Resolution Function
^^^^^^^^^^^^^^^^^^^

The resolution function describes the instrument's energy resolution and is
facility-specific. For ORNL VENUS, this file describes the time-of-flight
resolution characteristics.

.. note::

   Resolution function files are typically provided by your facility. Contact
   your instrument scientist for the appropriate file.

JSON Configuration for Multi-Isotope Analysis
---------------------------------------------

For multi-isotope fitting, PLEIADES uses a JSON configuration file that
links isotopes to their ENDF parameter files.

Using JsonManager
^^^^^^^^^^^^^^^^^

:class:`~pleiades.sammy.io.json_manager.JsonManager` automates:

1. Downloading ENDF resonance data for each isotope
2. Staging parameter files in the working directory
3. Creating a JSON configuration file

.. code-block:: python

   from pleiades.sammy.io.json_manager import JsonManager

   json_manager = JsonManager()

   # Create configuration for single isotope
   json_path = json_manager.create_json_config(
       isotopes=["Au-197"],
       abundances=[1.0],
       working_dir="./working",
   )

   print(f"JSON configuration: {json_path}")

Multi-Isotope Example
^^^^^^^^^^^^^^^^^^^^^

For natural hafnium with multiple isotopes:

.. code-block:: python

   json_manager = JsonManager()

   # Natural hafnium isotopes with abundances
   json_path = json_manager.create_json_config(
       isotopes=["Hf-174", "Hf-176", "Hf-177", "Hf-178", "Hf-179", "Hf-180"],
       abundances=[0.0016, 0.0526, 0.186, 0.2728, 0.1362, 0.3508],
       working_dir="./hf_analysis",
       custom_global_settings={
           "forceRMoore": "yes",
           "purgeSpinGroups": "yes",
           "fudge": "0.7",
       }
   )

Custom Settings
^^^^^^^^^^^^^^^

The ``custom_global_settings`` parameter accepts SAMMY configuration options:

- ``forceRMoore``: Force Reich-Moore formalism ("yes"/"no")
- ``purgeSpinGroups``: Remove unused spin groups ("yes"/"no")
- ``fudge``: Fudge factor for convergence

Working with File Containers
----------------------------

PLEIADES uses container classes to bundle input files for execution.

SammyFiles (Traditional Mode)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For standard single-isotope analysis with separate PAR file:

.. code-block:: python

   from pathlib import Path
   from pleiades.sammy.interface import SammyFiles

   files = SammyFiles(
       input_file=Path("analysis.inp"),
       parameter_file=Path("Au-197.par"),
       data_file=Path("transmission.twenty"),
   )

   # Validate all files exist
   files.validate()

SammyFilesMultiMode (JSON Mode)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For multi-isotope analysis using JSON configuration:

.. code-block:: python

   from pathlib import Path
   from pleiades.sammy.interface import SammyFilesMultiMode

   files = SammyFilesMultiMode(
       input_file=Path("./working/analysis.inp"),
       json_config_file=Path("./working/config.json"),
       data_file=Path("./twenty/transmission.twenty"),
       endf_directory=Path("./working"),  # Contains staged .par files
   )

   files.validate()

Directory Structure
^^^^^^^^^^^^^^^^^^^

A typical analysis directory structure:

::

   analysis/
   ├── working/
   │   ├── analysis.inp          # INP file
   │   ├── config.json           # JSON configuration
   │   └── 079-Au-197.B-VIII.0.par  # Staged ENDF file
   ├── twenty/
   │   └── transmission.twenty   # Data in SAMMY format
   ├── sammy_working/            # SAMMY execution directory
   └── sammy_output/             # Results directory

Complete Example
----------------

Putting it all together:

.. code-block:: python

   from pathlib import Path
   from pleiades.sammy.fitting.config import FitConfig
   from pleiades.sammy.io.inp_manager import InpDatasetMetadata, InpManager
   from pleiades.sammy.io.json_manager import JsonManager
   from pleiades.sammy.io.data_manager import convert_csv_to_sammy_twenty
   from pleiades.sammy.interface import SammyFilesMultiMode

   # Directories
   working_dir = Path("./au_analysis")
   twenty_dir = working_dir / "twenty"
   sammy_working = working_dir / "sammy_working"
   sammy_output = working_dir / "sammy_output"

   for d in [working_dir, twenty_dir, sammy_working, sammy_output]:
       d.mkdir(exist_ok=True)

   # 1. Convert transmission data
   convert_csv_to_sammy_twenty(
       Path("spectra/transmission.txt"),
       twenty_dir / "transmission.twenty",
   )

   # 2. Create JSON config (downloads ENDF data)
   json_manager = JsonManager()
   json_path = json_manager.create_json_config(
       isotopes=["Au-197"],
       abundances=[1.0],
       working_dir=str(working_dir),
   )

   # 3. Create INP file from FitConfig + typed metadata
   fit_config = FitConfig()
   fit_config.physics_params.broadening_parameters.crfn = 8.0

   dataset_metadata = InpDatasetMetadata(
       element="Au",
       mass_number=197,
       density_g_cm3=19.32,
       thickness_mm=0.025,
       atomic_mass_amu=196.966569,
       min_energy_eV=1.0,
       max_energy_eV=200.0,
       temperature_K=293.6,
   )

   inp_file = working_dir / "au_fitting.inp"
   InpManager.create_multi_isotope_inp(
       inp_file,
       fit_config=fit_config,
       title="Au-197 analysis",
       dataset_metadata=dataset_metadata,
       resolution_file_path=Path("/path/to/resolution.dat"),
   )

   # 4. Create file container
   files = SammyFilesMultiMode(
       input_file=inp_file,
       json_config_file=Path(json_path),
       data_file=twenty_dir / "transmission.twenty",
       endf_directory=working_dir,
   )

   # Ready for SAMMY execution
   files.validate()
   print("Input files prepared successfully")

Next Steps
----------

- :doc:`endf_data` - Learn about ENDF data management
- :doc:`sammy_workflow` - Execute SAMMY with your input files
- :doc:`results_analysis` - Analyze SAMMY output
