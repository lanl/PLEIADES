Usage Guide
===========

This guide provides instructions on how to use the PLEIADES library, focusing on initializing key components, processing input data, and running simulations.

Setup
-----

Before using PLEIADES, make sure it is installed and that you have SAMMY installed or configured. You can check the SAMMY environment with the following function:

.. code-block:: python

    from pleiades.sammyRunner import check_sammy_environment
    from pleiades.sammyUtils import SammyFitConfig

    config = SammyFitConfig()
    sammy_compiled_exists, sammy_docker_exists = check_sammy_environment(config)
    if sammy_compiled_exists:
        print("Compiled version of SAMMY is available.")
    if sammy_docker_exists:
        print("Docker version of SAMMY is available.")

Basic Usage: Input Files
------------------------

To get started, you'll want to load and manipulate input files using the `sammyInput` module.

**Creating and Processing an Input File**

1. Initialize an `InputFile` object without a config.
2. Update it with a custom configuration.
3. Process the file and write it to disk.

.. code-block:: python

    from pleiades import sammyInput
    from pleiades.sammyStructures import SammyFitConfig

    # Create a new input file object
    input_file = sammyInput.InputFile()

    # Update with a custom config for isotopes
    config = SammyFitConfig()
    config.params['isotopes'] = {'names': ['U-235', 'U-238']}
    input_file.update_with_config(config)

    # Process and write the file
    input_file.process().write('output_file.inp')

    print("SAMMY input file created and written to 'output_file.inp'.")

Advanced Usage: Running Simulations
-----------------------------------

Once the input file is prepared, you can run simulations using the `sammyRunner` module.

**Setting the SAMMY Call Method**

To run SAMMY, you can set the call method using either a compiled version or Docker.

.. code-block:: python

    from pleiades.sammyRunner import set_sammy_call_method

    # Set the call method for SAMMY using Docker
    sammy_call, sammy_command = set_sammy_call_method(docker_image_name='sammy-docker', verbose_level=1)

    # Output the command that will be run
    print(f"Sammy call: {sammy_call}")
    print(f"Sammy command: {sammy_command}")

**Running a SAMMY Simulation**

Once the environment and input are set, run the SAMMY simulation.

.. code-block:: python

    from pleiades.sammyRunner import Runner
    from pleiades.sammyUtils import SammyFitConfig

    # Configure and run a SAMMY simulation
    config = SammyFitConfig()
    runner = Runner(config=config)
    runner.run()

    # Fetch the results
    results = runner.get_results()

    # Print or analyze results
    print("Simulation results:", results)

Formatting Methods
------------------

The `sammyInput` module includes several formatting utilities for handling SAMMY input formatting:

**Formatting a String (`format_type_A`)**

This function formats a string to a fixed width.

.. code-block:: python

    formatted_str = sammyInput.InputFile.format_type_A("Test", 10)
    print(f"Formatted string: '{formatted_str}'")  # Output: 'Test      '

**Formatting a Float (`format_type_F`)**

This function formats a floating point number to a fixed width.

.. code-block:: python

    formatted_float = sammyInput.InputFile.format_type_F(1.2345, 10)
    print(f"Formatted float: '{formatted_float}'")  # Output: '  1.2345'

**Formatting an Integer (`format_type_I`)**

This function formats an integer to a fixed width.

.. code-block:: python

    formatted_int = sammyInput.InputFile.format_type_I(123, 5)
    print(f"Formatted int: '{formatted_int}'")  # Output: '  123'

More Examples
-------------

Refer to the :doc:`examples` section for more detailed use cases and code snippets for PLEIADES.
