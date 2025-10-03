from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

        Parameters input control for quantum numbers
        Define which type of input is to be used for spin group information and other parameters
        input_quantum_numbers_options = [
        ----------------------------
        *   "USE NEW SPIN GROUP Format",
            "PARTICLE PAIR DEFINItions are used",
            "KEY-WORD PARTICLE-PAir definitions are given",
        ----------------------------
        ----------------------------
            "QUANTUM NUMBERS ARE in parameter file",
            "PUT QUANTUM NUMBERS into parameter file"
        ----------------------------,
            ["SPIN OF INCIDENT PARticle is +","SPIN OF INCIDENT PARticle is -"],
        ----------------------------,
            "USE I4 FORMAT TO REAd spin group number",
        ----------------------------,
            "INPUT IS ENDF/B FILE",
        ----------------------------,
            "USE ENERGY RANGE FROm endf/b file 2",
        ----------------------------,
            "FLAG ALL RESONANCE Parameters"
        ]

"""


class QuantumNumbersOptions(BaseModel):
    """Define which type of input is to be used for spin group information and other parameters"""

    model_config = ConfigDict(validate_default=True)

    new_spin_group_format: bool = Field(default=True, description="USE NEW SPIN GROUP Format")
    particle_pair_definitions: bool = Field(default=False, description="PARTICLE PAIR DEFINItions are used")
    keyword_particle_pair_definitions: bool = Field(
        default=False, description="KEY-WORD PARTICLE-PAir definitions are given"
    )
    quantum_numbers_in_parameter_file: bool = Field(default=False, description="QUANTUM NUMBERS ARE in parameter file")
    put_quantum_numbers_into_parameter_file: bool = Field(
        default=False, description="PUT QUANTUM NUMBERS into parameter file"
    )
    spin_of_incident_particle_is_plus: bool = Field(default=False, description="SPIN OF INCIDENT PARticle is +")
    spin_of_incident_particle_is_minus: bool = Field(default=False, description="SPIN OF INCIDENT PARticle is -")
    i4_format_to_read_spin_group_number: bool = Field(
        default=False, description="USE I4 FORMAT TO REAd spin group number"
    )
    input_is_endf_b_file: bool = Field(default=False, description="INPUT IS ENDF/B FILE")
    use_energy_range_from_endf_b_file_2: bool = Field(default=False, description="USE ENERGY RANGE FROm endf/b file 2")
    flag_all_resonance_parameters: bool = Field(default=False, description="FLAG ALL RESONANCE Parameters")

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        ["new_spin_group_format", "particle_pair_definitions", "keyword_particle_pair_definitions"],
        ["quantum_numbers_in_parameter_file", "put_quantum_numbers_into_parameter_file"],
        ["spin_of_incident_particle_is_plus", "spin_of_incident_particle_is_minus"],
        ["i4_format_to_read_spin_group_number"],
        ["input_is_endf_b_file"],
        ["use_energy_range_from_endf_b_file_2"],
        ["flag_all_resonance_parameters"],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "QuantumNumbersOptions":
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
        if self.new_spin_group_format:
            commands.append("USE NEW SPIN GROUP Format")
        if self.particle_pair_definitions:
            commands.append("PARTICLE PAIR DEFINItions are used")
        if self.keyword_particle_pair_definitions:
            commands.append("KEY-WORD PARTICLE-PAir definitions are given")
        if self.quantum_numbers_in_parameter_file:
            commands.append("QUANTUM NUMBERS ARE in parameter file")
        if self.put_quantum_numbers_into_parameter_file:
            commands.append("PUT QUANTUM NUMBERS into parameter file")
        if self.spin_of_incident_particle_is_plus:
            commands.append("SPIN OF INCIDENT PARticle is +")
        if self.spin_of_incident_particle_is_minus:
            commands.append("SPIN OF INCIDENT PARticle is -")
        if self.i4_format_to_read_spin_group_number:
            commands.append("USE I4 FORMAT TO REAd spin group number")
        if self.input_is_endf_b_file:
            commands.append("INPUT IS ENDF/B FILE")
        if self.use_energy_range_from_endf_b_file_2:
            commands.append("USE ENERGY RANGE FROm endf/b file 2")
        if self.flag_all_resonance_parameters:
            commands.append("FLAG ALL RESONANCE Parameters")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        options = QuantumNumbersOptions(
            new_spin_group_format=True,
            particle_pair_definitions=True,  # This should raise a ValueError
        )
    except ValueError as e:
        print(e)
