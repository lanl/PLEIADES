import sys, os
import pleiades.sammyInput as psi   #  
import pleiades.nucData as pnd      # grabbing nucData for Pleiades.

def main(config_file=None):

    # Read config files 
    sammy_input = psi.InputFile("config.ini",auto_update=True)
    
    # Process input data and format the cards.
    sammy_input.process()       
    
    # Write formatted input cards to a specified file.
    sammy_input.write("example.inp")


if __name__ == "__main__":

    main(sys.argv[1] if len(sys.argv) > 1 else None)
