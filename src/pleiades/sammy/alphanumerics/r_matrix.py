from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

        Commands for R-matrix approximation and general options
        Define which approximation to the R-matrix is to be used for this calculation
        r_matrix_options = [
        ----------------------------
        *   ["REICH-MOORE FORMALISm is wanted","MORE ACCURATE REICHmoore","XCT"],
            ["ORIGINAL REICH-MOORE formalism","CRO"],
            ["MULTILEVEL BREITWIGner is wanted","MLBW FORMALISM IS WAnted","MLBW"],
            ["SINGLE LEVEL BREITWigner is wanted","SLBW FORMALISM IS WAnted","SLBW"],
            "REDUCED WIDTH AMPLITudes are used for input"
        ----------------------------
        ]

        General options = [
        ----------------------------
            "UNRESOLVED RESONANCE region", or "FRITZ FROEHNERS FITACS", or "FITACS"
        ----------------------------
        ]
"""


class RMatrixOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # R-Matrix approximation options
    reich_moore: bool = Field(default=True, description="REICH-MOORE FORMALISM IS WANTED")
    original_reich_moore: bool = Field(default=False, description="ORIGINAL REICH-MOORE FORMALISM")
    multilevel_breit_wigner: bool = Field(default=False, description="MULTILEVEL BREIT-WIGNER FORMALISM IS WANTED")
    single_level_breit_wigner: bool = Field(default=False, description="SINGLE LEVEL BREIT-WIGNER FORMALISM IS WANTED")
    reduced_width_amplitudes: bool = Field(default=False, description="REDUCED WIDTH AMPLITUDES ARE USED FOR INPUT")

    # General options
    unresolved_resonance_region: bool = Field(default=False, description="UNRESOLVED RESONANCE REGION")

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        [
            "reich_moore",
            "original_reich_moore",
            "multilevel_breit_wigner",
            "single_level_breit_wigner",
            "reduced_width_amplitudes",
            "unresolved_resonance_region",
        ]
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "RMatrixOptions":
        for group in self.mutually_exclusive_groups:
            true_fields = [f for f in group if getattr(self, f)]
            if not true_fields:
                continue

            user_true = [f for f in true_fields if f in self.model_fields_set]
            default_true = [f for f in true_fields if f not in self.model_fields_set]

            # If >1 user-specified in same group => error
            if len(user_true) > 1:
                raise ValueError(
                    f"Multiple user-specified fields {user_true} are True in group {group}. Only one allowed."
                )

            # If exactly 1 user-specified => turn off all defaults in that group
            if len(user_true) == 1:
                for f in default_true:
                    setattr(self, f, False)
                continue

            # If all True fields are defaults, and more than 1 => error
            if len(default_true) > 1:
                raise ValueError(f"Multiple default fields {default_true} are True in group {group}. Only one allowed.")
        return self

    def get_alphanumeric_commands(self) -> List[str]:
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
        if self.unresolved_resonance_region:
            commands.append("UNRESOLVED RESONANCE REGION")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        options = RMatrixOptions(
            reich_moore=True,
            original_reich_moore=True,  # This should raise a ValueError
        )
    except ValueError as e:
        print(e)
