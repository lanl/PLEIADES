from pydantic import BaseModel, Field, model_validator

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

    @model_validator(mode='after')
    def check_exclusivity(cls, values):
        """Ensure that only one R-matrix approximation is selected using boolean flags."""
        mutually_exclusive_groups = [
            ["reich_moore", "original_reich_moore", "multilevel_breit_wigner", "single_level_breit_wigner", "reduced_width_amplitudes"]
        ]

        for group in mutually_exclusive_groups:
            selected_flags = [key for key in group if getattr(values, key)]
            if len(selected_flags) > 1:
                raise ValueError(f"Only one option can be selected from the group: {selected_flags}")

        return values