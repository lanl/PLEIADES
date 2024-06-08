Examples
========

Here are several examples illustrating the use of several utilities within the PLEIADES package.

Example 1: Simulating a neutron transmission spectrum
-----------------------------------------------------
Simulating a neutron transmission spectrum using the pleiades.simulate module

This example is located in the examples directory under ```examples/plotTransmission/```

It has the following files:

* ```plotTrans.py```: A python script that uses the pleiades.simulate module to simulate a neutron transmission spectrum
* ```isotope.ini``` : A configuration file that contains the isotopic information needed to simulate the neutron transmission spectrum

In ```plotTrans.py```, the pleiades module, along with other needed modules, as loaded using the following code:

.. code-block:: python

    import argparse, sys            # For parsing command line arguments
    import pleiades.simulate as psd # For simulating neutron transmission spectra
    import numpy as np              # For generating energy grids

additionaly, ```plotTrans.py`` uses a main function is defined as follows:

.. code-block:: python
    
    if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process config file for isotopes and plot transmission.')
    parser.add_argument('--isoConfig', type=str, default='config.ini', help='Path to the isotope config file')
    parser.add_argument('--energy_min', type=float, default=1, help='Minimum energy for the plot [eV]')
    parser.add_argument('--energy_max', type=float, default=100, help='Maximum energy for the plot [eV]')
    parser.add_argument('--energy_points', type=int, default=100000, help='Number of energy points for the plot')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    else:
        args = parser.parse_args()
        main(args.isoConfig, args.energy_min, args.energy_max, args.energy_points)

The ```argparse``` module is used to parse command line arguments. The ```--isoConfig``` argument is used to specify the location of the isotope configuration file. The ```--energy_min```, ```--energy_max```, and ```--energy_points``` arguments are used to specify the energy range and number of points for the plot. The command ```python plotTrans.py --help``` can be used to print the help message for the command line arguments.

The isotope.ini file contains the following information:

.. code-block:: ini
    
    [Isotope1]
    name = U-238
    thickness = 0.01
    thickness_unit = cm
    abundance = 0.99
    xs_file_location = ../../nucDataLibs/xSections/u-n.tot
    density = 19.1
    density_unit = g/cm3
    ignore = false

This file contains the information for one isotope. There can be multiple isotopes in the file where the information for each isotope is contained in separate sections, and the section names can be arbitrary, but unique. If any of the given fields are not listed, then defualt values are used. 

* ```name = U-238```: The name of the isotope, should be in the form of ```element-massNumber```
* ```thickness = 0.01``` : The thickness of the sample
* ```thickness_unit = cm```: The units of the thickness
* ```abundance = 0.99```: The abundance of the isotope. This can be used to simulate a mixture of isotopes.
* ```xs_file_location = ../../nucDataLibs/xSections/u-n.tot```: The location of the cross section file
* ```density = 19.1```: The density of the isotope
* ```density_unit = g/cm3```: The units of the density
* ```ignore = false```: A flag to ignore the isotope. If set to true, then the isotope is ignored.

To load the isotope.ini file, use the following code:

.. code-block:: python

    # Read the isotope config file
    isotopes = psd.load_isotopes_from_config(config_file)

Once loaded in the an array of isotope objects, the information can be accessed using the following code:

.. code-block:: python

    # Generate a linear energy grid
    energy_grid = np.linspace(energy_min, energy_max, energy_points)

    # Loop over all isotopes in isotope_info.isotopes
    for isotope in isotopes:
        
        # Generate transmission data
        transmission_data = psd.create_transmission(energy_grid,isotope)
        grid_energies, interp_transmission = zip(*transmission_data)
        transmissions.append(interp_transmission)

        # Plot the transmission data
        ax.semilogx(grid_energies, interp_transmission, alpha=0.75, label=isotope.name)

Here the main function of ```psd.create_transmission(energy_grid,isotope)``` is used to generate the transmission data. The first argument is the energy grid, and the second argument is the isotope information. The function returns a list of tuples where the first element of the tuple is the energy and the second element is the transmission. The ```zip(*transmission_data)``` function is used to unzip the list of tuples into two lists, one for the energy and one for the transmission. The ```transmissions``` list is used to store the transmission data for each isotope. Once stored the transmissison can be ploted using the ```ax.semilogx``` function. 

Once all the transmission data is stored in the ```transmissions``` list, the total transmission can be calculated using the following code:

.. code-block:: python

    #combine transmissions for all isotopes
    combined_transmission = np.prod(transmissions, axis=0)
    
    # Plot the combined transmission data
    ax.semilogx(energy_grid, combined_transmission, color='black', alpha=0.75, linestyle='dashed', label="Total")

Using the isotope.ini file and the ```plotTrans.py``` script, the following plot is generated:

.. figure:: _images/example1.jpg
   :alt: The transmission of U-238 and U-235 as a function of energy. 
   :width: 600px
   :align: center

   Reading in the file isotope.ini giving in the example should result in the transmission of U-238 and U-235 as a function of energy. 

A transmission output file can also be generated by calling the ```psd.write_transmission_data(energy_data, transmission_data, output_file)``` function. The first argument is the energy data, the second argument is the transmission data, and the third argument is the output file name. The output file is writing in the SAMMY twenty format, which mean each entry takes up twenty characters. 

Example 2: Generating SAMMY input files
----------------------------
Making a SAMMY input file with the pleiades.sammyInput module

This example is located in the examples directory under ```examples/makeSammyInput/```

It has the following files:

* ```makeInputFile.py```: A python script that uses the pleiades.sammyInput module to create a SAMMY input file
* ```config.ini``` : A configuration file that contains the information needed to create the SAMMY input file

Example 3: Generating SAMMY parameter files