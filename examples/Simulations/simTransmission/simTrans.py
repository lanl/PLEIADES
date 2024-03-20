import argparse, sys
import matplotlib.pyplot as plt
import numpy as np
import pleiades.simData as psd

def main(config_file='config.ini', energy_min=1, energy_max=100, energy_points=10000, write_output=False):
    
    # Read the isotope config file
    isotopes = psd.load_isotopes_from_config(config_file)
    
    # Generate a linear energy grid
    energy_grid = np.linspace(energy_min, energy_max, energy_points)
    
    # Create a list for the transmission data for each isotope
    transmissions = []
    
    # Create a figure and axis
    fig, ax = plt.subplots(1,1)
    
    # Loop over all isotopes in isotope_info.isotopes
    for isotope in isotopes:
        
        # Generate transmission data
        transmission_data = psd.create_transmission(energy_grid,isotope)
        grid_energies, interp_transmission = zip(*transmission_data)
        transmissions.append(interp_transmission)
        
        # Plot the transmission data
        ax.semilogx(grid_energies, interp_transmission, alpha=0.75, label=isotope.name)
    
    #combine transmissions for all isotopes
    combined_transmission = np.prod(transmissions, axis=0)
    
    # Plot the combined transmission data
    ax.semilogx(energy_grid, combined_transmission, color='black', alpha=0.75, linestyle='dashed', label="Total")
    
    plt.legend()
    plt.show()
    
    # If the "--write_output" is given, then write the output to file. 
    if write_output:
        
        # grab name of input config file an create output twenty file. 
        output_file_name = config_file.split(".")[0]+".twenty"
        
        # Write the transmission data to a file, do not include error. 
        psd.write_transmission_data(grid_energies,combined_transmission,output_file_name, include_error=True, verbose=True)
    



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process config file for isotopes and plot transmission.')
    parser.add_argument('--isoConfig', type=str, default='config.ini', help='Path to the isotope config file')
    parser.add_argument('--energy_min', type=float, default=1, help='Minimum energy for the plot [eV]')
    parser.add_argument('--energy_max', type=float, default=100, help='Maximum energy for the plot [eV]')
    parser.add_argument('--energy_points', type=int, default=100000, help='Number of energy points for the plot')
    parser.add_argument('--write_output', action='store_true', help='Flag to write transmission data to a file')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    else:
        args = parser.parse_args()
        main(args.isoConfig, args.energy_min, args.energy_max, args.energy_points, args.write_output)
    
