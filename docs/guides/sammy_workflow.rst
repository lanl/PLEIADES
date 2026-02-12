SammyFactory Workflow Guide
===========================

This guide covers the complete workflow for executing SAMMY using
:class:`~pleiades.sammy.factory.SammyFactory`.

Creating Runners
----------------

PLEIADES provides three ways to create a SAMMY runner:

1. :meth:`~pleiades.sammy.factory.SammyFactory.auto_select` - Automatic backend selection
2. :meth:`~pleiades.sammy.factory.SammyFactory.create_runner` - Explicit backend selection
3. :meth:`~pleiades.sammy.factory.SammyFactory.from_config` - Load from YAML configuration

auto_select (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest approach. Automatically selects the best available backend:

.. code-block:: python

   from pathlib import Path
   from pleiades.sammy.factory import SammyFactory

   runner = SammyFactory.auto_select(
       working_dir=Path("./work"),
       output_dir=Path("./output"),  # optional, defaults to working_dir/output
   )

Selection priority: local > docker > nova.

You can suggest a preferred backend (falls back to alternatives if unavailable):

.. code-block:: python

   runner = SammyFactory.auto_select(
       working_dir=Path("./work"),
       preferred_backend="docker",
       image_name="custom/sammy:latest",  # backend-specific option
   )

create_runner (Explicit)
^^^^^^^^^^^^^^^^^^^^^^^^

Directly specify the backend type:

.. code-block:: python

   runner = SammyFactory.create_runner(
       backend_type="local",
       working_dir=Path("./work"),
       output_dir=Path("./output"),
       sammy_executable="/path/to/sammy",  # optional
   )

Raises :class:`~pleiades.sammy.factory.BackendNotAvailableError` if the
requested backend is not available.

from_config (YAML)
^^^^^^^^^^^^^^^^^^

Load configuration from a YAML file:

.. code-block:: python

   runner = SammyFactory.from_config("sammy_config.yaml")

Example configuration file:

.. code-block:: yaml

   backend: local
   working_dir: /path/to/work
   output_dir: /path/to/output

   local:
     sammy_executable: sammy
     shell_path: /bin/bash

   docker:
     image_name: kedokudo/sammy-docker
     container_working_dir: /sammy/work
     container_data_dir: /sammy/data

   nova:
     url: ${NOVA_URL}
     api_key: ${NOVA_API_KEY}
     tool_id: neutrons_imaging_sammy
     timeout: 3600

Environment variables (``${VAR_NAME}``) are automatically expanded.

Input Files
-----------

SammyFiles (Traditional Mode)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For standard SAMMY runs with three input files:

.. code-block:: python

   from pleiades.sammy.interface import SammyFiles

   files = SammyFiles(
       input_file=Path("input.inp"),
       parameter_file=Path("params.par"),
       data_file=Path("data.dat"),
   )

   # Validate all files exist
   files.validate()

SammyFilesMultiMode (JSON Mode)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For multi-isotope analysis using JSON configuration:

.. code-block:: python

   from pleiades.sammy.interface import SammyFilesMultiMode

   files = SammyFilesMultiMode(
       input_file=Path("input.inp"),
       json_config_file=Path("config.json"),
       data_file=Path("data.twenty"),
       endf_directory=Path("./endf_files/"),
   )

   files.validate()

The JSON configuration references ENDF parameter files in the ``endf_directory``.

Execution Pipeline
------------------

The standard execution pipeline has four stages:

.. code-block:: python

   from pleiades.sammy.factory import SammyFactory
   from pleiades.sammy.interface import SammyFiles

   files = SammyFiles(
       input_file=Path("input.inp"),
       parameter_file=Path("params.par"),
       data_file=Path("data.dat"),
   )

   runner = SammyFactory.auto_select(working_dir=Path("./work"))

   try:
       # 1. Prepare: validate files, setup environment
       runner.prepare_environment(files)

       # 2. Execute: run SAMMY
       result = runner.execute_sammy(files)

       # 3. Collect: move outputs (only on success)
       if result.success:
           runner.collect_outputs(result)
           print(f"Completed in {result.runtime_seconds:.2f}s")
       else:
           print(f"Failed: {result.error_message}")

   finally:
       # 4. Cleanup: release resources
       runner.cleanup()

Stage Details
^^^^^^^^^^^^^

**prepare_environment(files)**
   Validates input files exist and prepares the execution environment.
   For local backend, copies/symlinks files to working directory.
   Raises :class:`~pleiades.sammy.interface.EnvironmentPreparationError` on failure.

**execute_sammy(files)**
   Runs SAMMY and returns :class:`~pleiades.sammy.interface.SammyExecutionResult`.
   Raises :class:`~pleiades.sammy.interface.SammyExecutionError` on failure.

**collect_outputs(result)**
   Moves SAMMY output files from working directory to output directory.
   Raises :class:`~pleiades.sammy.interface.OutputCollectionError` on failure.

**cleanup()**
   Releases resources (removes temp files, closes connections).

Error Handling
--------------

PLEIADES provides specific exception types for different failure modes:

.. code-block:: python

   from pleiades.sammy.interface import (
       EnvironmentPreparationError,
       SammyExecutionError,
       OutputCollectionError,
   )
   from pleiades.sammy.factory import (
       BackendNotAvailableError,
       ConfigurationError,
   )

   try:
       runner = SammyFactory.auto_select(working_dir=Path("./work"))
       runner.prepare_environment(files)
       result = runner.execute_sammy(files)

       if result.success:
           runner.collect_outputs(result)

   except BackendNotAvailableError as e:
       print(f"No backend available: {e}")

   except ConfigurationError as e:
       print(f"Configuration error: {e}")

   except EnvironmentPreparationError as e:
       print(f"Environment setup failed: {e}")

   except SammyExecutionError as e:
       print(f"SAMMY execution failed: {e}")

   except OutputCollectionError as e:
       print(f"Failed to collect outputs: {e}")

   finally:
       if 'runner' in locals():
           runner.cleanup()

Checking Backend Availability
-----------------------------

Before creating a runner, you can check which backends are available:

.. code-block:: python

   from pleiades.sammy.factory import SammyFactory, BackendType

   available = SammyFactory.list_available_backends()

   # Returns dict like:
   # {
   #     BackendType.LOCAL: True,
   #     BackendType.DOCKER: True,
   #     BackendType.NOVA: False
   # }

   for backend, is_available in available.items():
       status = "available" if is_available else "not available"
       print(f"{backend.value}: {status}")

Working with Results
--------------------

:class:`~pleiades.sammy.interface.SammyExecutionResult` provides execution details:

.. code-block:: python

   result = runner.execute_sammy(files)

   # Basic status
   print(f"Success: {result.success}")
   print(f"Execution ID: {result.execution_id}")

   # Timing
   print(f"Start: {result.start_time}")
   print(f"End: {result.end_time}")
   print(f"Runtime: {result.runtime_seconds:.2f}s")

   # Output
   print(f"Console output:\n{result.console_output}")

   # Error details (if failed)
   if not result.success:
       print(f"Error: {result.error_message}")

Output Files
^^^^^^^^^^^^

After :meth:`~pleiades.sammy.interface.SammyRunner.collect_outputs`, standard
SAMMY outputs are in the output directory:

========== ==========================================
File       Description
========== ==========================================
SAMMY.LPT  Log file
SAMMY.LST  ASCII listing with detailed results
SAMMY.ODF  Plot file with calculated cross sections
SAMNDF.PAR Updated parameter file
SAMNDF.INP Updated input file
SAMMY.IO   Terminal output from SAMMY
========== ==========================================

Complete Example
----------------

.. code-block:: python

   """Complete SAMMY execution example with error handling."""
   from pathlib import Path
   from pleiades.sammy.factory import SammyFactory, BackendNotAvailableError
   from pleiades.sammy.interface import (
       SammyFiles,
       EnvironmentPreparationError,
       SammyExecutionError,
   )

   # Configuration
   data_dir = Path("./test_data")
   working_dir = Path("./sammy_work")
   output_dir = Path("./sammy_output")

   # Input files
   files = SammyFiles(
       input_file=data_dir / "example.inp",
       parameter_file=data_dir / "example.par",
       data_file=data_dir / "example.dat",
   )

   runner = None
   try:
       # Validate inputs before creating runner
       files.validate()

       # Create runner with auto-selection
       runner = SammyFactory.auto_select(
           working_dir=working_dir,
           output_dir=output_dir,
       )
       print(f"Using backend: {type(runner).__name__}")

       # Execute pipeline
       runner.prepare_environment(files)
       result = runner.execute_sammy(files)

       if result.success:
           runner.collect_outputs(result)
           print(f"SAMMY completed successfully ({result.runtime_seconds:.2f}s)")
           print(f"Outputs available in: {output_dir}")
       else:
           print(f"SAMMY failed: {result.error_message}")
           print("Console output:")
           print(result.console_output)

   except FileNotFoundError as e:
       print(f"Input file not found: {e}")

   except BackendNotAvailableError as e:
       print(f"No suitable backend: {e}")

   except (EnvironmentPreparationError, SammyExecutionError) as e:
       print(f"Execution error: {e}")

   finally:
       if runner is not None:
           runner.cleanup()
