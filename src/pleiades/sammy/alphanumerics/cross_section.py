from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

        Cross section calculation details = [
        ----------------------------
            "USE POLAR COORDINATES for fission widths",
            "NUMERICAL DERIVATIVES for resonance parameters",
        ----------------------------
        *   "DO NOT USE S-WAVE CUtoff",
            "USE S-WAVE CUTOFF",
            "USE NO CUTOFFS FOR DErivatives or cross sections",
        ----------------------------
            "USE ALTERNATIVE COULomb functions",
            "ADD DIRECT CAPTURE Component to cross section",
        ----------------------------
        *   "LAB NON COULOMB EXCItation energies",
            "CM NON COULOMB EXCITation energies",
        ----------------------------
        *   "LAB COULOMB EXCITATIon energies",
            "CM COULOMB EXCITATIOn energies",
        ----------------------------
            "ADD ELIMINATED CAPTUre channel to final state",
        ----------------------------
        ]
"""


class CrossSectionOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # Fission and resonance params options
    use_polar_coordinates_for_fission_widths: bool = Field(
        default=False, description="USE POLAR COORDINATES for fission widths"
    )
    numerical_derivatives_for_resonance_parameters: bool = Field(
        default=False, description="NUMERICAL DERIVATIVES for resonance parameters"
    )

    # Cutoff options
    do_not_use_s_wave_cutoff: bool = Field(default=True, description="DO NOT USE S-WAVE CUtoff")
    use_s_wave_cutoff: bool = Field(default=False, description="USE S-WAVE CUTOFF")
    use_no_cutoffs_for_derivatives: bool = Field(
        default=False, description="USE NO CUTOFFS FOR DErivatives or cross sections"
    )

    # Function options
    use_alternative_coulomb_functions: bool = Field(default=False, description="USE ALTERNATIVE COULomb functions")
    add_direct_capture_component: bool = Field(
        default=False, description="ADD DIRECT CAPTURE Component to cross section"
    )

    # Excitation energy options (non-Coulomb)
    lab_non_coulomb_excitation_energies: bool = Field(default=True, description="LAB NON COULOMB EXCItation energies")
    cm_non_coulomb_excitation_energies: bool = Field(default=False, description="CM NON COULOMB EXCITation energies")

    # Excitation energy options (Coulomb)
    lab_coulomb_excitation_energies: bool = Field(default=True, description="LAB COULOMB EXCITATIon energies")
    cm_coulomb_excitation_energies: bool = Field(default=False, description="CM COULOMB EXCITATIOn energies")

    # Eliminated capture channel option
    add_eliminated_capture_channel: bool = Field(
        default=False, description="ADD ELIMINATED CAPTUre channel to final state"
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        ["do_not_use_s_wave_cutoff", "use_s_wave_cutoff", "use_no_cutoffs_for_derivatives"],
        ["lab_non_coulomb_excitation_energies", "cm_non_coulomb_excitation_energies"],
        ["lab_coulomb_excitation_energies", "cm_coulomb_excitation_energies"],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "CrossSectionOptions":
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
        if self.use_polar_coordinates_for_fission_widths:
            commands.append("USE POLAR COORDINATES FOR FISSION WIDTHS")
        if self.numerical_derivatives_for_resonance_parameters:
            commands.append("NUMERICAL DERIVATIVES FOR RESONANCE PARAMETERS")
        if self.do_not_use_s_wave_cutoff:
            commands.append("DO NOT USE S-WAVE CUTOFF")
        if self.use_s_wave_cutoff:
            commands.append("USE S-WAVE CUTOFF")
        if self.use_no_cutoffs_for_derivatives:
            commands.append("USE NO CUTOFFS FOR DERIVATIVES OR CROSS SECTIONS")
        if self.use_alternative_coulomb_functions:
            commands.append("USE ALTERNATIVE COULOMB FUNCTIONS")
        if self.add_direct_capture_component:
            commands.append("ADD DIRECT CAPTURE COMPONENT TO CROSS SECTION")
        if self.lab_non_coulomb_excitation_energies:
            commands.append("LAB NON COULOMB EXCITATION ENERGIES")
        if self.cm_non_coulomb_excitation_energies:
            commands.append("CM NON COULOMB EXCITATION ENERGIES")
        if self.lab_coulomb_excitation_energies:
            commands.append("LAB COULOMB EXCITATION ENERGIES")
        if self.cm_coulomb_excitation_energies:
            commands.append("CM COULOMB EXCITATION ENERGIES")
        if self.add_eliminated_capture_channel:
            commands.append("ADD ELIMINATED CAPTURE CHANNEL TO FINAL STATE")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        options = CrossSectionOptions(do_not_use_s_wave_cutoff=True, use_s_wave_cutoff=True)
    except ValueError as e:
        print(e)
