Managing ENDF Nuclear Data
==========================

This guide covers how PLEIADES manages ENDF (Evaluated Nuclear Data File)
resonance parameters for SAMMY analysis.

Overview
--------

SAMMY requires resonance parameters for each isotope in your analysis.
These parameters define the energy positions, widths, and quantum numbers
of nuclear resonances. PLEIADES automates retrieval of this data from
the ENDF database.

**ENDF data includes:**

- Resonance energies
- Neutron widths (Gamma_n)
- Capture widths (Gamma_gamma)
- Fission widths (if applicable)
- Spin and parity assignments
- Channel radii

Automatic Data Retrieval
------------------------

PLEIADES downloads ENDF resonance data automatically when you use
:class:`~pleiades.sammy.io.json_manager.JsonManager` to create a
multi-isotope configuration.

Behind the Scenes
^^^^^^^^^^^^^^^^^

When you call ``create_json_config()``, PLEIADES:

1. Looks up each isotope's MAT number (ENDF material identifier)
2. Downloads resonance data from the IAEA Nuclear Data Services
3. Converts the data to SAMMY PAR file format
4. Caches the downloaded file for future use
5. Stages the PAR file in your working directory

Using NuclearDataManager Directly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For more control, use :class:`~pleiades.nuclear.manager.NuclearDataManager`:

.. code-block:: python

   from pathlib import Path
   from pleiades.nuclear.manager import NuclearDataManager
   from pleiades.nuclear.models import EndfLibrary

   # Create manager
   manager = NuclearDataManager()

   # Download resonance data for Au-197
   par_file = manager.download_endf_resonance_file(
       element="Au",
       mass_number=197,
       output_path=Path("./Au-197.par"),
       library=EndfLibrary.ENDF_B_VIII_0,
   )

   print(f"Downloaded: {par_file}")

Caching System
--------------

PLEIADES caches downloaded ENDF files to avoid repeated network requests.

Cache Location
^^^^^^^^^^^^^^

Files are cached in your home directory:

::

   ~/.pleiades/nuclear_data/
   ├── DataRetrievalMethod.API/
   │   └── EndfLibrary.ENDF_B_VIII_0/
   │       ├── n_079-Au-197_7925_resonance.dat
   │       └── n_072-Hf-180_7231_resonance.dat
   └── DataRetrievalMethod.DIRECT/
       └── EndfLibrary.ENDF_B_VIII_0/
           └── n_7925_079-Au-197.zip

Cache Behavior
^^^^^^^^^^^^^^

- **First request**: Downloads from IAEA and caches locally
- **Subsequent requests**: Uses cached file (fast)
- **Different libraries**: Cached separately per library version

To force re-download, delete the cached file or use a different library.

Supported ENDF Libraries
------------------------

PLEIADES supports multiple ENDF library versions through the
:class:`~pleiades.nuclear.models.EndfLibrary` enum:

.. list-table:: Supported Libraries
   :header-rows: 1
   :widths: 30 50 20

   * - Library
     - Description
     - Status
   * - ``ENDF_B_VIII_0``
     - ENDF/B-VIII.0 (US evaluation)
     - Default
   * - ``ENDF_B_VIII_1``
     - ENDF/B-VIII.1 (latest US)
     - Supported
   * - ``JEFF_3_3``
     - JEFF-3.3 (European evaluation)
     - Supported
   * - ``JENDL_5``
     - JENDL-5 (Japanese evaluation)
     - Supported
   * - ``CENDL_3_2``
     - CENDL-3.2 (Chinese evaluation)
     - Supported
   * - ``TENDL_2021``
     - TENDL-2021 (TALYS-based)
     - Supported

Specifying a Library
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pleiades.nuclear.manager import NuclearDataManager
   from pleiades.nuclear.models import EndfLibrary

   manager = NuclearDataManager()

   # Use JEFF-3.3 library
   par_file = manager.download_endf_resonance_file(
       element="Hf",
       mass_number=180,
       output_path=Path("./Hf-180.par"),
       library=EndfLibrary.JEFF_3_3,
   )

.. note::

   Different libraries may have different resonance parameters for the
   same isotope. Choose based on your analysis requirements and the
   isotopes of interest.

Manual File Management
----------------------

You can bypass automatic download and provide your own parameter files.

Providing Custom PAR Files
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have existing PAR files (from previous SAMMY runs or custom
evaluations):

.. code-block:: python

   from pleiades.sammy.interface import SammyFiles

   # Use your own PAR file directly
   files = SammyFiles(
       input_file=Path("analysis.inp"),
       parameter_file=Path("my_custom.par"),  # Your file
       data_file=Path("transmission.twenty"),
   )

Staging Files Manually
^^^^^^^^^^^^^^^^^^^^^^

For multi-isotope JSON mode, place PAR files in the ENDF directory:

.. code-block:: python

   from pleiades.sammy.interface import SammyFilesMultiMode

   # Manually staged PAR files in ./endf_files/
   files = SammyFilesMultiMode(
       input_file=Path("analysis.inp"),
       json_config_file=Path("config.json"),
       data_file=Path("transmission.twenty"),
       endf_directory=Path("./endf_files"),  # Contains your .par files
   )

The JSON configuration must reference the correct filenames in
``endf_directory``.

Isotope Information
-------------------

PLEIADES includes utilities for looking up isotope properties.

Using IsotopeManager
^^^^^^^^^^^^^^^^^^^^

:class:`~pleiades.nuclear.isotopes.manager.IsotopeManager` provides
isotope data:

.. code-block:: python

   from pleiades.nuclear.isotopes.manager import IsotopeManager

   manager = IsotopeManager()

   # Get isotope information
   info = manager.get_isotope_info("Au-197")

   print(f"Element: {info.element}")
   print(f"Mass number: {info.mass_number}")
   print(f"Atomic mass: {info.atomic_mass} amu")
   print(f"Natural abundance: {info.abundance}")

Natural Abundance
^^^^^^^^^^^^^^^^^

For natural abundance calculations:

.. code-block:: python

   from pleiades.nuclear.isotopes.manager import IsotopeManager

   manager = IsotopeManager()

   # Hafnium natural isotopes
   hf_isotopes = ["Hf-174", "Hf-176", "Hf-177", "Hf-178", "Hf-179", "Hf-180"]

   for iso in hf_isotopes:
       info = manager.get_isotope_info(iso)
       print(f"{iso}: {info.abundance:.4f} ({info.abundance*100:.2f}%)")

MAT Numbers
^^^^^^^^^^^

ENDF uses MAT numbers to identify materials. PLEIADES handles this
automatically, but you can look them up:

.. code-block:: python

   # MAT number is part of isotope info
   info = manager.get_isotope_info("U-238")
   print(f"U-238 MAT number: {info.mat}")

Data Retrieval Methods
----------------------

PLEIADES supports two retrieval methods:

.. list-table::
   :header-rows: 1

   * - Method
     - Description
     - Use Case
   * - ``API``
     - Downloads resonance data only via IAEA API
     - Default, faster, smaller files
   * - ``DIRECT``
     - Downloads complete ENDF files
     - When full evaluation is needed

The API method is used by default and is recommended for most users.

Troubleshooting
---------------

**"No resonance data found"**
   Some isotopes may not have resolved resonance data in the selected
   library. Try a different library or check if the isotope has
   unresolved resonance region (URR) data only.

**Network timeout**
   The IAEA server may be slow. Try again later or check your network
   connection.

**Cache permissions**
   Ensure you have write permissions to ``~/.pleiades/nuclear_data/``.

Next Steps
----------

- :doc:`input_preparation` - Create SAMMY input files
- :doc:`sammy_workflow` - Execute SAMMY analysis
- :doc:`results_analysis` - Analyze results
