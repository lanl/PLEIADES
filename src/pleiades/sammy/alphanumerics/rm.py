from pydantic import BaseModel, Field 
from typing import ClassVar

"""
# These notes are taken from the SAMMY manual. 
# * denotes a default options
# Mutually exclusive options are grouped together starting with -------------- and ending with -------------
# options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

# Commands for R-matrix approximation
# Define which approximation to the R-matrix is to be used for this calculation
r_matrix_options = [
    --------------
    *["REICH-MOORE FORMALISm is wanted","MORE ACCURATE REICHmoore","XCT"],
    ["ORIGINAL REICH-MOORE formalism","CRO"],
    ["MULTILEVEL BREITWIGner is wanted","MLBW FORMALISM IS WAnted","MLBW"],
    ["SINGLE LEVEL BREITWigner is wanted","SLBW FORMALISM IS WAnted","SLBW"], 
    "REDUCED WIDTH AMPLITudes are used for input"
    --------------
    ]
"""

class RMatrixOptions(BaseModel):
    """Model to enforce mutually exclusive selection of R-matrix approximations using boolean flags."""
    
    # Boolean flags for mutual exclusivity
    reich_moore: bool = Field(default=True, description="REICH-MOORE formalism is wanted")
    original_reich_moore: bool = Field(default=False, description="ORIGINAL REICH-MOORE formalism")
    multilevel_breit_wigner: bool = Field(default=False, description="MULTILEVEL BREIT-WIGNER formalism is wanted")
    single_level_breit_wigner: bool = Field(default=False, description="SINGLE LEVEL BREIT-WIGNER formalism is wanted")
    reduced_width_amplitudes: bool = Field(default=False, description="REDUCED WIDTH AMPLITUDES are used for input")

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: ClassVar[list[list[str]]] = [
        ["reich_moore", "original_reich_moore", "multilevel_breit_wigner", "single_level_breit_wigner", "reduced_width_amplitudes"]
    ]
    
    def __init__(self, **data):
        super().__init__(**data)
        for name, value in data.items():
            self.__setattr__(name, value)
        self.check_exclusivity()

    def __setattr__(self, name, value):
        """Custom setattr to handle mutually exclusive options."""
        for group in self.mutually_exclusive_groups:
            if name in group and value is True:
                for option in group:
                    if option != name:
                        super().__setattr__(option, False)
        super().__setattr__(name, value)

    def get_alphanumeric_commands(self):
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.reich_moore:
            commands.append("REICH-MOORE FORMALISM IS WANTED")
        if self.original_reich_moore:
            commands.append("ORIGINAL REICH-MOORE FORMALISM")
        if self.multilevel_breit_wigner:
            commands.append("MULTILEVEL BREIT-WIGNER FORMALISM IS WANTED")
        if self.single_level_breit_wigner:
            commands.append("SINGLE LEVEL BREIT-WIGNER FORMALISM IS WANTED")
        if self.reduced_width_amplitudes:
            commands.append("REDUCED WIDTH AMPLITUDES ARE USED FOR INPUT")
        return commands

    def check_exclusivity(self):
        """Ensure that only one R-matrix approximation is selected using boolean flags."""
        for group in self.mutually_exclusive_groups:
            selected_flags = [key for key in group if getattr(self, key)]
            if len(selected_flags) > 1:
                raise ValueError(f"Only one option can be selected from the group: {selected_flags}")

# Example usage
try:
    options = RMatrixOptions(
        reich_moore=True,
        original_reich_moore=True  # This will automatically switch off reich_moore
    )
except ValueError as e:
    print(e)