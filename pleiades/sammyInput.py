import configparser
from pleiades import nucData as pnd
from typing import List, Dict
from contextlib import suppress
import numpy as np

class InputFile:
    """ InputFile class for the Sammy input file.
    """

    def __init__(self, config_file: str, auto_update: bool = True) -> None:
        """Reads an .ini config file to create a structured SAMMY inp file

        Args:
            - config_file (str): config file name
            - auto_update (bool): True will replace atomic mass and values set to "auto" 
        """
        # read config file
        self._config = configparser.ConfigParser()
        self._config.read(config_file)

        # turn the configparser object into a dict of dicts data-structure
        self._config_data = {section:dict(self._config[section]) for section in self._config.sections()}
        
        # TODO: right now Card10 is not required 
        # since we are specifing spin group data in the par file
        # so I'm just ignoring this part of config file right now        
        with suppress(KeyError): del self._config_data["Card10"] 

        # populate the default database at self.data
        self._set_default_params()

        # update the defaults with config file data
        self._update_default_params_with_config()

        # populate the database of predefined commands 
        self._set_predefined_commands()

        # update auto values
        self._update_and_calculate_values(auto_update=auto_update)

        return


    def process(self, auto_update: bool=True) -> "InputFile":
        """
        Process input data and format the cards.

        Args:
            - auto_update (bool): True will replace atomic mass and values set to "auto" 

        This function processes the data in the self.data dictionary, formats the input
        cards according to specified parameters, and stores the formatted cards in the
        self.inp_cards attribute. It handles different card types and their respective
        parameters, ensuring proper formatting for later use.

        Returns: the InputFIle instance
        """
        # update auto values
        self._update_and_calculate_values(auto_update=auto_update)

        # List to store formatted input card lines
        lines = []

        # Iterate through each card in the data dictionary
        for card in self.data.keys():
            line = ""

            # Iterate through parameters of the current card
            for parameter in self.data[card]:
                # Extract parameter type and width information
                par_type, par_width = self._default_data[card][parameter][1:3]

                # Check if the parameter has a specific width
                if par_width:
                    # Format parameter based on its type and width
                    if par_type == str:
                        line += self.format_type_A(self.data[card][parameter], par_width)
                    elif par_type == int:
                        line += self.format_type_I(int(self.data[card][parameter]), par_width)
                    elif par_type == float:
                        line += self.format_type_F(float(self.data[card][parameter]), par_width)
                    else:
                        # Raise an error for unsupported parameter types
                        raise ValueError("Parameter can only have float, int, or str types")
                else:
                    # Handle free format cards like Card3
                    if card == "Card3":
                        commands = []

                        # Split and process individual commands
                        for command in self.data[card][parameter].split(','):
                            if command.strip() in self._commands_dict.keys():
                                commands.append(self._commands_dict[command])
                            else:
                                commands.append(command)
                        
                        # Join commands with newline characters
                        line = "\n".join(commands) + "\n"

            # Add formatted line to the list of lines
            lines.append(line)

        # Add a newline at the end of the input cards
        self.processed_cards = lines + ["\n"]

        # add optional user-defined resolution function
        if hasattr(self,"_resolution_commands"):
            self.processed_cards += [self._resolution_commands]

        return self


    def write(self, filename: str = "sammy.inp") -> "InputFile":
        """
        Write formatted input cards to a specified file.

        Args:
            filename (str, optional): Name of the output file. Defaults to "sammy.inp".

        Returns: the InputFIle instance
        """
        with open(filename, 'w') as fid:
            fid.write("\n".join(self.processed_cards))

        return self

    def _set_default_params(self) -> None:
        # set default for each parameter three entries specify the default value, type, and width
        self._default_data = dict(
            Card1={
                'title': ('GENERAL TITLE FOR SAMMY RUN',str,80) # title
                  },
            Card2={
                'elmnt': ('Si_28',str,10),    # Element name. Defaults to None.
                'aw':     ('auto',float,10),  # Atomic weight in amu. Defaults to 0.
                'emin':   ('0.001',float,10), # Minimum energy. Defaults to 0.
                'emax':   ('100.',float,10),  # Maximum energy. Defaults to 0.
                'nepnts': ('10001',int,5),    # Number of points to be used in generating artificial energy grid. Defaults to 10001.
                'itmax':  ('2',int,5),        # Number of iterations. Defaults to 2.
                'icorr':  ('50',int,2),       # Correlation option. Defaults to 50.
                'nxtra':  ('0',int,3),        # Number of extra points to be added between each pair of data points for auxiliary energy grid. Defaults to 0. 
                'iptdop': ('9',int,2),        # Number of points to be added to auxiliary energy grid across small resonances. Defaults to 9.
                'iptwid': ('5',int,2),        # Determines the number of points to be added to auxiliary grid in tails of small resonances. Defaults to 5
                'ixxchn': ('0',int,10),       # Number of energy channels in ODF-type data file to be ignored 
                'ndigit': ('2',int,2),        # Number of digits for compact format for covariance matrix (Default = 2)
                'idropp': ('2',int,2),        # The input resonance parameter covariance matrix will be modified before being used in the fitting procedure. Defaults to 2
                'matnum': ('0',int,6),         # ENDF Material number. Defaults to 0.
                },     
            Card3={
                'commands': ('CHI_SQUARED,TWENTY,SOLVE_BAYES,PUT_QUANTUM_NUMS_IN_PARAM',str,None)
                },
            Card5={
                'temp':   ('300.5',float,10),
                'dist':   ('100.2',float,10),
                'deltal': ('0.0',float,10),
                'deltae': ('0.0',float,10),
                'deltag': ('0.0',float,10),
                'delttt': ('0.0',float,10),
                'elowbr': ('0.0',float,10),
                },
            # Card6={
            #     'deltag': ("0.0",float,10),
            #     'deltab': ("0.0",float,10),
            #     'ncf':    ("0",int,5),
            #     'bcf':    ('',float,None),
            #     'cf':     ('',float,None),
            # },
            Card7={
                'crfn':   ('1.0',float,10),
                'thick':  ('1.0',float,10),
                'dcova':  ('0.0',float,10),
                'dcovb':  ('0.0',float,10),
                'vmin':   ('0.0',float,10),
                },
            Card8={
                'cross': ('TRANSMISSION',str,80),
                },
            # Card10={
            #     'isotopes':   ('Si28,Si29,Si30',str,80),
            #     'spingroups': ('7,10,5',str,80),
            #     },
            )
        
        # sets the default data dictionary
        self.data = {}
        for card in self._default_data:
            self.data[card] = {}
            for parameter in self._default_data[card]:
                self.data[card][parameter] = self._default_data[card][parameter][0]
                
        return

    def _update_default_params_with_config(self) -> None:
        """Update the default parameters with config file data, only if they exist in both."""
        for card, params in self._config_data.items():
            if card in self.data:
                for param, value in params.items():
                    if param in self.data[card]:
                        self.data[card][param] = value



    def _set_predefined_commands(self) -> None:
        """dictoinary that holds keywords that expands to SAMMY alphanumerical commands
        """
        self._commands_dict = dict(
            REICH_MOORE_FORM="REICH-MOORE FORMALISm is wanted",
            ORIG_REICH_MOORE_FORM = "ORIGINAL REICH-MOORE formalism",
            MULTI_BREIT = "MULTILEVEL BREITWIGner is wanted",
            SINGLE_BREIT = "SINGLE LEVEL BREITWigner is wanted",
            RED_WIDTH_AMPS = "REDUCED WIDTH AMPLITudes are used for input",
            NEW_SPIN_FORMAT = "USE NEW SPIN GROUP Format",
            PARTICL_PAIR_DEF = "PARTICLE PAIR DEFINItions are used",
            KEY_WORD_PARTICLE_PAIR= "KEY-WORD PARTICLE-PAir definitions are given",
            QUANTUM_NUMBERS = "QUANTUM NUMBERS ARE in parameter file",
            PUT_QUANTUM_NUMS_IN_PARAM = "PUT QUANTUM NUMBERS into parameter file" ,   
            INPUT_ENDF = "INPUT IS ENDF/B FILE",
            USE_ENDF_ENERGY = "USE ENERGY RANGE FROm endf/b file",
            FLAG_ALL_RES = "FLAG ALL RESONANCE Parameters",
            SOLVE_BAYES = "SOLVE BAYES EQUATIONs",
            NO_SOLVE_BAYES = "DO NOT SOLVE BAYES EQUATIONS",
            TWENTY = "USE TWENTY SIGNIFICAnt digits",
            BROADENING = "BROADENING IS WANTED",
            CHI_SQUARED = "CHI SQUARED IS WANTEd",
            NO_CHI_SQUARED = "CHI SQUARED IS NOT Wanted"
            )
        
    def _update_and_calculate_values(self,auto_update: bool=True) -> None:
        """
        Update and calculate values in the self.data dictionary.

        This function iterates through the self.data dictionary, updates existing
        values, and performs calculations where necessary. It modifies the
        dictionary in-place.

        Args:
            auto_update (bool): if True 'auto' tagged parameters are updated

        Returns:
            None
        """
        # get atomic weight
        isotopic_str = self.data["Card2"]["elmnt"]
        atomic_weight = pnd.get_mass_from_ame(isotopic_str.replace("_","-"))

        if auto_update:
            #replace atomic weight based on the isotope name
            if self.data["Card2"]["aw"] == "auto":
                self.data["Card2"]["aw"] = f"{atomic_weight:.8f}"

            # get mat number
            mat_number = pnd.get_mat_number(isotopic_str)

        # update mat number in ENDF command
        commands = self.data["Card3"]["commands"].split(',')
        for i, command in enumerate(commands):
            if auto_update and command.startswith("INPUT IS ENDF"):
                commands[i] = f"INPUT IS ENDF/B FILE MAT={mat_number}"
            if command.startswith("FILE="):
                self._resolution_commands = f"USER-DEFINED RESOLUTION FUNCTION\n{command}\n"
                commands.pop(i)

        self.data["Card3"]["commands"] = ",".join(commands)


        return
    
   
    @staticmethod
    def format_type_A(data, width):
        """ Format a string to be left-justified in a character field of the given width.

        Args:
            data (string): The string to be formatted.
            width (int): Integer width of the field.

        Returns:
            string: character field of the given width with the string left-justified.
        """
        return f"{data:<{width}}"

    @staticmethod
    def format_type_F(data, width):
        """ Format a float to be right-justified in a float field of the given width.

        Args:
            data (float): The float to be formatted.
            width (int): Integer width of the field.

        Returns:
            string: float field of the given width with the float right-justified.
        """
        # The ".4f" here denotes 4 decimal places. You can adjust if needed.
        return f"{data:>{width}}"

    @staticmethod
    def format_type_I(data, width):
        """ Format an integer to be right-justified in an integer field of the given width.

        Args:
            data (int): integer to be formatted.
            width (int): Integer width of the field.

        Returns:
            _string: integer field of the given width with the integer right-justified.
        """
        return f"{data:>{width}d}"

