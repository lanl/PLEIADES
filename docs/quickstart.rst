Quick Start
===========

This guide demonstrates a minimal PLEIADES workflow to execute SAMMY
in under 5 minutes.

Basic Workflow
--------------

PLEIADES uses a factory pattern to create SAMMY runners that abstract
the execution backend (local, Docker, or NOVA).

.. code-block:: python

   from pathlib import Path
   from pleiades.sammy.factory import SammyFactory
   from pleiades.sammy.interface import SammyFiles

   # 1. Define your input files
   files = SammyFiles(
       input_file=Path("path/to/input.inp"),
       parameter_file=Path("path/to/params.par"),
       data_file=Path("path/to/data.dat"),
   )

   # 2. Create a runner (auto-selects best available backend)
   runner = SammyFactory.auto_select(
       working_dir=Path("./sammy_work"),
       output_dir=Path("./sammy_output"),
   )

   # 3. Execute SAMMY
   try:
       runner.prepare_environment(files)
       result = runner.execute_sammy(files)

       if result.success:
           print(f"SAMMY completed in {result.runtime_seconds:.2f}s")
           runner.collect_outputs(result)
       else:
           print(f"SAMMY failed: {result.error_message}")
           print(result.console_output)

   finally:
       runner.cleanup()

Understanding the Components
----------------------------

SammyFiles
^^^^^^^^^^

:class:`~pleiades.sammy.interface.SammyFiles` is a container for the three
required SAMMY input files:

- ``input_file``: The SAMMY input file (``.inp``)
- ``parameter_file``: The parameter file (``.par``)
- ``data_file``: The experimental data file (``.dat``)

.. code-block:: python

   from pleiades.sammy.interface import SammyFiles

   files = SammyFiles(
       input_file=Path("ex012a.inp"),
       parameter_file=Path("ex012a.par"),
       data_file=Path("ex012a.dat"),
   )

   # Validate files exist
   files.validate()

SammyFactory
^^^^^^^^^^^^

:class:`~pleiades.sammy.factory.SammyFactory` creates configured runners.
The simplest approach is :meth:`~pleiades.sammy.factory.SammyFactory.auto_select`,
which chooses the best available backend:

.. code-block:: python

   from pleiades.sammy.factory import SammyFactory

   # Auto-select best backend
   runner = SammyFactory.auto_select(
       working_dir=Path("./work"),
   )

Backend priority: local (fastest) > docker (portable) > nova (remote).

Execution Pipeline
^^^^^^^^^^^^^^^^^^

The runner workflow has three stages:

1. **prepare_environment**: Validates files and sets up the execution environment
2. **execute_sammy**: Runs SAMMY and returns results
3. **collect_outputs**: Moves output files to the output directory

.. code-block:: python

   # Stage 1: Prepare
   runner.prepare_environment(files)

   # Stage 2: Execute
   result = runner.execute_sammy(files)

   # Stage 3: Collect (only on success)
   if result.success:
       runner.collect_outputs(result)

   # Always cleanup
   runner.cleanup()

Checking Results
----------------

:class:`~pleiades.sammy.interface.SammyExecutionResult` contains execution details:

.. code-block:: python

   result = runner.execute_sammy(files)

   # Check success
   if result.success:
       print(f"Execution ID: {result.execution_id}")
       print(f"Runtime: {result.runtime_seconds:.2f} seconds")
   else:
       print(f"Error: {result.error_message}")
       print(f"Console output:\n{result.console_output}")

Output Files
------------

After successful execution and :meth:`~pleiades.sammy.interface.SammyRunner.collect_outputs`,
standard SAMMY output files are available in the output directory:

- ``SAMMY.LPT``: Log file
- ``SAMMY.LST``: ASCII listing with detailed results
- ``SAMMY.ODF``: Plot file with calculated cross sections
- ``SAMNDF.PAR``: Updated parameter file
- ``SAMNDF.INP``: Updated input file

Next Steps
----------

- :doc:`guides/sammy_workflow` - Complete workflow guide with error handling
- :doc:`guides/backends` - Backend selection and configuration
- :doc:`api/index` - API reference
