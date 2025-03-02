from pydantic import BaseModel, Field, model_validator

"""
# Parameters input control for quantum numbers
# Define which type of input is to be used for spin group information and other parameters
input_quantum_numbers_options = [
    --------------
    *"USE NEW SPIN GROUP Format", 
    "PARTICLE PAIR DEFINItions are used",
    "KEY-WORD PARTICLE-PAir definitions are given",
    --------------
    --------------
    "QUANTUM NUMBERS ARE in parameter file",
    "PUT QUANTUM NUMBERS into parameter file"
    --------------,
    ["SPIN OF INCIDENT PARticle is +","SPIN OF INCIDENT PARticle is -"],
    "USE I4 FORMAT TO REAd spin group number",
    "INPUT IS ENDF/B FILE",
    "USE ENERGY RANGE FROm endf/b file 2",
    "FLAG ALL RESONANCE Parameters"
    ]

"""

class QuantumNumbersOptions(BaseModel):
    """ Model to enforce mutually exclusive selection of quantum numbers input options using boolean flags. """
    
    # Boolean flags for mutual exclusivity
    new_spin_group_format: bool = Field(default=True, description="Use new spin group format")
    particle_pair_definitions: bool = Field(default=False, description="Particle pair definitions are used")
    keyword_particle_pair_definitions: bool = Field(default=False, description="Keyword particle-pair definitions are given")
    quantum_numbers_in_parameter_file: bool = Field(default=False, description="Quantum numbers are in parameter file")
    put_quantum_numbers_into_parameter_file: bool = Field(default=False, description="Put quantum numbers into parameter file")
    spin_of_incident_particle_is_plus: bool = Field(default=False, description="Spin of incident particle is +")
    spin_of_incident_particle_is_minus: bool = Field(default=False, description="Spin of incident particle is -")
    i4_format_to_read_spin_group_number: bool = Field(default=False, description="Use I4 format to read spin group number")
    input_is_endf_b_file: bool = Field(default=False, description="Input is ENDF/B file")
    use_energy_range_from_endf_b_file_2: bool = Field(default=False, description="Use energy range from ENDF/B file 2")
    flag_all_resonance_parameters: bool = Field(default=False, description="Flag all resonance parameters")

    def get_alphanumeric_commands(self):
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.new_spin_group_format:
            commands.append("USE NEW SPIN GROUP FORMAT")
        if self.particle_pair_definitions:
            commands.append("PARTICLE PAIR DEFINITIONS")
        if self.keyword_particle_pair_definitions:
            commands.append("KEY-WORD PARTICLE-PAIR DEFINITIONS")
        if self.quantum_numbers_in_parameter_file:
            commands.append("QUANTUM NUMBERS IN PARAMETER FILE")
        if self.put_quantum_numbers_into_parameter_file:
            commands.append("PUT QUANTUM NUMBERS INTO PARAMETER FILE")
        if self.spin_of_incident_particle_is_plus:
            commands.append("SPIN OF INCIDENT PARTICLE IS +")
        if self.spin_of_incident_particle_is_minus:
            commands.append("SPIN OF INCIDENT PARTICLE IS -")
        if self.i4_format_to_read_spin_group_number:
            commands.append("I4 FORMAT TO READ SPIN GROUP NUMBER")
        if self.input_is_endf_b_file:
            commands.append("INPUT IS ENDF/B FILE")
        if self.use_energy_range_from_endf_b_file_2:
            commands.append("USE ENERGY RANGE FROM ENDF/B FILE 2")
        if self.flag_all_resonance_parameters:
            commands.append("FLAG ALL RESONANCE PARAMETERS")
        return commands

    @model_validator(mode='after')
    def check_exclusivity(cls, values):
        """Ensure that only one quantum numbers input option is selected using boolean flags."""
        mutually_exclusive_groups = [
            ["new_spin_group_format", "particle_pair_definitions", "keyword_particle_pair_definitions"],
            ["quantum_numbers_in_parameter_file", "put_quantum_numbers_into_parameter_file"],
            ["spin_of_incident_particle_is_plus", "spin_of_incident_particle_is_minus"],
            ["i4_format_to_read_spin_group_number"],
            ["input_is_endf_b_file", "use_energy_range_from_endf_b_file_2"],
            ["flag_all_resonance_parameters"]
        ]

        for group in mutually_exclusive_groups:
            selected_flags = [key for key in group if getattr(values, key)]
            if len(selected_flags) > 1:
                raise ValueError(f"Only one option can be selected from the group: {selected_flags}")

        return values
