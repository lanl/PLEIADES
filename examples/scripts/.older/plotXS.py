import argparse,sys
import pleiades.simData as psd
import matplotlib.pyplot as plt


def main(config_file='config.ini'):
    
    # Grab the isotopes and accompanying info from the config file
    info = psd.Isotopes(config_file)
    
    # Create a figure to plot the cross-sections
    plt.figure()

    # Loop over the isotopes and plot the cross-sections
    for isotope in info.isotopes:
        
        # grab the xs data.
        xs_data = isotope.xs_data
        
        # Unpack the data into two arrays, one for the energies and one for the cross-sections
        energies, cross_sections = zip(*xs_data)
        
        # Plot the cross-sections
        plt.loglog(energies, cross_sections, label=f"{isotope.name}")
    
    # Add a legend and labels to the plot, and show it
    plt.title("Cross-sections for Isotopes")
    plt.xlabel("Energy")
    plt.ylabel("Cross-section")
    plt.legend()
    plt.grid(True)
    plt.show()
    

if __name__ == "__main__":
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description='Process config file for isotopes.')
    
    # Add the arguments
    parser.add_argument('--config', type=str, default=" ", help='Path to the config file')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    else:
        args = parser.parse_args()
        main(args.config)