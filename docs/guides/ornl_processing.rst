Processing ORNL VENUS Imaging Data
==================================

This guide covers processing raw neutron imaging data from the ORNL
Spallation Neutron Source (SNS) VENUS beamline.

.. note::

   This guide is specific to the ORNL SNS VENUS instrument. Other
   facilities may have different data formats and processing requirements.

Overview
--------

Neutron transmission imaging at VENUS produces time-of-flight (TOF)
resolved images that must be processed to extract transmission spectra
for SAMMY analysis.

**Processing Pipeline:**

1. Load raw TIFF image stacks (sample and open beam)
2. Apply dead pixel corrections
3. Calculate transmission: T = sample_counts / ob_counts
4. Propagate uncertainties
5. Convert time-of-flight to energy
6. Output transmission spectrum

Data Structure
--------------

VENUS Data Organization
^^^^^^^^^^^^^^^^^^^^^^^

VENUS data follows the SNS IPTS (Integrated Proposal Tracking System) structure:

::

   /SNS/VENUS/IPTS-XXXXX/
   ├── nexus/                    # NeXus metadata files
   │   ├── VENUS_XXXXX.nxs.h5
   │   └── ...
   └── shared/autoreduce/mcp/images/
       ├── Run_8021/             # Open beam run
       │   ├── *.tif             # TOF-resolved images
       │   └── *_Spectra.txt     # Integrated spectra
       ├── Run_8022/             # Sample run 1
       ├── Run_8023/             # Sample run 2
       └── ...

File Types
^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - File Type
     - Description
     - Content
   * - ``*.tif``
     - TIFF images
     - TOF-resolved 2D images (one per time bin)
   * - ``*_Spectra.txt``
     - Spectra file
     - Integrated counts vs TOF
   * - ``*.nxs.h5``
     - NeXus file
     - Experimental metadata (flight path, etc.)

Loading Raw Data
----------------

PLEIADES provides functions in :mod:`pleiades.processing.helper_ornl` for
loading VENUS data.

Loading a Single Run
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pleiades.processing.helper_ornl import load_run_from_folder

   # Load a sample run
   run = load_run_from_folder(
       folder="/SNS/VENUS/IPTS-35945/shared/autoreduce/mcp/images/Run_8022",
       nexus_path="/SNS/VENUS/IPTS-35945/nexus",
   )

   print(f"TOF bins: {run.counts.shape[0]}")
   print(f"Image size: {run.counts.shape[1]} x {run.counts.shape[2]}")

The Run Model
^^^^^^^^^^^^^

:class:`~pleiades.processing.models_ornl.Run` contains:

.. list-table::
   :header-rows: 1

   * - Attribute
     - Type
     - Description
   * - ``counts``
     - ``np.ndarray``
     - 3D array (TOF, y, x) of neutron counts
   * - ``tof``
     - ``np.ndarray``
     - Time-of-flight values (microseconds)
   * - ``shutter_counts``
     - ``np.ndarray``
     - Shutter timing counts (optional)
   * - ``dead_pixel_mask``
     - ``np.ndarray``
     - Boolean mask of dead pixels

Loading Multiple Runs
^^^^^^^^^^^^^^^^^^^^^

For combining multiple sample measurements:

.. code-block:: python

   from pleiades.processing.helper_ornl import load_multiple_runs

   sample_folders = [
       "/SNS/VENUS/IPTS-35945/shared/autoreduce/mcp/images/Run_8022",
       "/SNS/VENUS/IPTS-35945/shared/autoreduce/mcp/images/Run_8023",
       "/SNS/VENUS/IPTS-35945/shared/autoreduce/mcp/images/Run_8024",
   ]

   runs = load_multiple_runs(
       folders=sample_folders,
       nexus_dir="/SNS/VENUS/IPTS-35945/nexus",
   )

   print(f"Loaded {len(runs)} runs")

Normalization Workflow
----------------------

The main entry point for processing is :func:`~pleiades.processing.normalization.normalization`.

Basic Normalization
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from pleiades.processing.normalization import normalization
   from pleiades.processing import Facility

   # Define data folders
   sample_folders = [
       "/SNS/VENUS/IPTS-35945/shared/autoreduce/mcp/images/Run_8022",
       "/SNS/VENUS/IPTS-35945/shared/autoreduce/mcp/images/Run_8023",
   ]
   ob_folders = [
       "/SNS/VENUS/IPTS-35945/shared/autoreduce/mcp/images/Run_8021",
   ]

   # Process data
   transmissions = normalization(
       list_sample_folders=sample_folders,
       list_obs_folders=ob_folders,
       nexus_path="/SNS/VENUS/IPTS-35945/nexus",
       facility=Facility.ornl,
       output_folder="./spectra",
   )

   print(f"Processed {len(transmissions)} transmission spectra")

The ``transmissions`` list contains :class:`~pleiades.processing.models_ornl.Transmission`
objects for each sample run.

Key Parameters
^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1

   * - Parameter
     - Description
     - Default
   * - ``list_sample_folders``
     - Paths to sample measurement folders
     - Required
   * - ``list_obs_folders``
     - Paths to open beam (OB) folders
     - Required
   * - ``nexus_path``
     - Path to NeXus files directory
     - Required
   * - ``facility``
     - Facility enum (``Facility.ornl``)
     - Required
   * - ``combine_mode``
     - Combine runs before normalization
     - ``False``
   * - ``pc_uncertainty``
     - Minimum fractional uncertainty
     - ``0.005``
   * - ``output_folder``
     - Directory for output files
     - Required

Processing Modes
^^^^^^^^^^^^^^^^

**Individual mode** (``combine_mode=False``):
   Process each sample run separately against the combined OB. Produces
   one transmission spectrum per sample folder.

**Combined mode** (``combine_mode=True``):
   Combine all sample runs before normalizing. Produces a single
   transmission spectrum with improved statistics.

Dead Pixel Detection
--------------------

PLEIADES automatically detects and masks dead pixels.

Automatic Detection
^^^^^^^^^^^^^^^^^^^

During normalization, :func:`~pleiades.processing.helper_ornl.detect_persistent_dead_pixels`
identifies pixels with:

- Zero counts across all TOF bins
- Anomalously high counts (saturated pixels)

.. code-block:: python

   from pleiades.processing.helper_ornl import detect_persistent_dead_pixels

   # Detect dead pixels in a run
   dead_mask = detect_persistent_dead_pixels(run.counts)

   dead_count = dead_mask.sum()
   total_pixels = dead_mask.size
   print(f"Dead pixels: {dead_count}/{total_pixels} ({100*dead_count/total_pixels:.2f}%)")

Region of Interest (ROI)
------------------------

Select a spatial region for analysis using :class:`~pleiades.processing.Roi`.

Defining an ROI
^^^^^^^^^^^^^^^

.. code-block:: python

   from pleiades.processing import Roi

   # Define ROI by coordinates
   roi = Roi(x1=100, y1=100, x2=400, y2=400)

   # Or by corner + dimensions
   roi = Roi(x1=100, y1=100, width=300, height=300)

   # Get ROI bounds
   bounds = roi.get_roi()
   print(f"ROI: {bounds}")

Using ROI in Normalization
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

   ROI support in the ``normalization()`` function may require additional
   configuration depending on the specific workflow. The current implementation
   processes the full detector area by default.

Time-of-Flight to Energy Conversion
-----------------------------------

PLEIADES converts TOF to energy using the neutron flight path.

Conversion Function
^^^^^^^^^^^^^^^^^^^

:func:`~pleiades.processing.helper_ornl.tof_to_energy` performs the conversion:

.. code-block:: python

   from pleiades.processing.helper_ornl import tof_to_energy

   # Convert TOF (microseconds) to energy (eV)
   energies = tof_to_energy(
       tof=run.tof,
       flight_path=25.0,  # meters (VENUS flight path)
   )

   print(f"Energy range: {energies.min():.2e} - {energies.max():.2e} eV")

The conversion uses the kinetic energy relation:

.. math::

   E = \frac{1}{2} m_n \left(\frac{L}{t}\right)^2

Where:

- :math:`m_n` is the neutron mass
- :math:`L` is the flight path length
- :math:`t` is the time-of-flight

Output Format
-------------

The Transmission Model
^^^^^^^^^^^^^^^^^^^^^^

:class:`~pleiades.processing.models_ornl.Transmission` contains:

.. list-table::
   :header-rows: 1

   * - Attribute
     - Type
     - Description
   * - ``energy``
     - ``np.ndarray``
     - Energy values (eV)
   * - ``transmission``
     - ``np.ndarray``
     - Transmission values (0-1)
   * - ``uncertainty``
     - ``np.ndarray``
     - Uncertainties (standard deviation)
   * - ``metadata``
     - ``dict``
     - Run metadata

Accessing Results
^^^^^^^^^^^^^^^^^

.. code-block:: python

   # After normalization
   for trans in transmissions:
       print(f"\nRun: {trans.metadata.get('sample_folder', 'Unknown')}")
       print(f"  Energy range: {trans.energy.min():.2e} - {trans.energy.max():.2e} eV")
       print(f"  Data points: {len(trans.energy)}")
       print(f"  Mean transmission: {trans.transmission.mean():.3f}")

Saving Results
^^^^^^^^^^^^^^

Transmission data is automatically saved to the output folder:

.. code-block:: python

   # Saved automatically as:
   # ./spectra/Run_8022_transmission.txt
   # ./spectra/Run_8023_transmission.txt

Files are saved in CSV format with columns: energy, transmission, uncertainty.

Combining Multiple Runs
-----------------------

Statistical Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

When combining runs:

- **Same sample, different runs**: Combine to improve counting statistics
- **Different samples**: Process separately

.. code-block:: python

   from pleiades.processing.helper_ornl import combine_runs

   # Combine runs from the same sample
   combined = combine_runs(runs)

   print(f"Combined TOF bins: {combined.counts.shape[0]}")

Combining with combine_mode
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Process with combining
   transmissions = normalization(
       list_sample_folders=sample_folders,
       list_obs_folders=ob_folders,
       nexus_path=nexus_path,
       facility=Facility.ornl,
       combine_mode=True,  # Combine before normalization
       output_folder="./spectra",
   )

   # Returns single transmission spectrum

Complete Processing Example
---------------------------

.. code-block:: python

   import os
   from pathlib import Path
   import matplotlib.pyplot as plt
   from pleiades.processing.normalization import normalization
   from pleiades.processing import Facility

   # VENUS data paths
   ipts_path = "/SNS/VENUS/IPTS-35945"
   autoreduce_base = f"{ipts_path}/shared/autoreduce/mcp/images"

   # Define runs
   ob_folders = [f"{autoreduce_base}/Run_8021"]
   sample_folders = [
       f"{autoreduce_base}/Run_8022",
       f"{autoreduce_base}/Run_8023",
       f"{autoreduce_base}/Run_8024",
   ]

   # Output directory
   output_dir = Path("./au_analysis/spectra")
   output_dir.mkdir(parents=True, exist_ok=True)

   # Process data
   transmissions = normalization(
       list_sample_folders=sample_folders,
       list_obs_folders=ob_folders,
       nexus_path=f"{ipts_path}/nexus",
       facility=Facility.ornl,
       combine_mode=False,
       pc_uncertainty=0.005,
       output_folder=str(output_dir),
   )

   # Visualize results
   fig, ax = plt.subplots(figsize=(10, 6))

   for trans in transmissions:
       label = Path(trans.metadata.get("sample_folder", "")).name
       ax.plot(trans.energy, trans.transmission, label=label, alpha=0.8)

   ax.set_xlabel("Energy (eV)")
   ax.set_ylabel("Transmission")
   ax.set_xscale("log")
   ax.set_title("Au-197 Transmission Spectra")
   ax.legend()
   ax.grid(True, alpha=0.3)

   plt.tight_layout()
   plt.savefig("transmission_spectra.png", dpi=150)
   plt.show()

   print(f"Processed {len(transmissions)} transmission spectra")

Next Steps
----------

After processing ORNL data:

1. Convert to SAMMY format: :doc:`input_preparation`
2. Set up SAMMY analysis: :doc:`sammy_workflow`
3. Analyze results: :doc:`results_analysis`
