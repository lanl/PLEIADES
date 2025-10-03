from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    ENDF/B file input/output options = [
    ----------------------------
        "INPUT IS ENDF/B FILE 2",
        "USE ENERGY RANGE FROm endf/b file 2",
        "PARAMETER COVARIANCE matrix is in endf forma",
        "DATA ARE ENDF/B FILE",
        "PRESERVE GAMMA_N NOT g_gamma_n from endf",
        "ENDF/B-VI FILE 2 IS wanted",
        "NDF FILE IS IN KEY-Word Format",
        "GENERATE FILE 3 POINt-wise cross section",
        "FILE 33 LB=1 COVARIAnce is wanted",
        "AUTOMATIC NDF FILE Creation",
        "INCLUDE MIN & MAX ENergies in endf file",
    ----------------------------
    ]
"""


class ENDFOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # ENDF input options
    input_is_endf_file_2: bool = Field(
        default=False,
        description="Resonance parameters and spin-group quantum number information are taken from an ENDF/B File 2",
    )
    use_energy_range_from_endf_file_2: bool = Field(
        default=False, description="Use energy range from ENDF File 2 instead of INPut file or interactive input"
    )
    parameter_covariance_matrix_is_in_endf_format: bool = Field(
        default=False, description="Parameter covariance matrix is taken from an ENDF File 32"
    )
    data_are_endf_file: bool = Field(
        default=False, description="Data file is an ENDF File 3 (point-wise cross sections)"
    )
    preserve_gamma_n_not_g_gamma_n_from_endf: bool = Field(
        default=False,
        description="When reading ENDF File 2 where J is not well-determined (AJ=I), assume ENDF neutron width is Γn not gΓn",
    )

    # ENDF output options
    endf_b_vi_file_2_is_wanted: bool = Field(
        default=False, description="Output resonance parameters in ENDF/B-VI File 2 format to SAMMY.NDF"
    )
    ndf_file_is_in_key_word_format: bool = Field(
        default=False,
        description="The 'ndf' file (for ENDF output options) uses key-word format instead of fixed format",
    )
    generate_file_3_point_wise_cross_section: bool = Field(
        default=False, description="Output point-wise cross sections in ENDF File 3 format to SAMMY.FL3"
    )
    file_33_lb_1_covariance_is_wanted: bool = Field(
        default=False,
        description="Output group average cross sections (SAMMY.CRS) and covariance matrix (SAMMY.N33, similar to ENDF File 33)",
    )
    automatic_ndf_file_creation: bool = Field(
        default=False,
        description="When input is ENDF File 2, SAMMY automatically creates the *.ndf file for ENDF File 32 output",
    )
    include_min_and_max_energies_in_endf_file: bool = Field(
        default=False, description="For URR ENDF File 2 output, include Emin and Emax from SAMMY run in the energy list"
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        # Note: ENDF options don't have mutually exclusive groups explicitly specified
        # in the YAML file, but we can define logical groupings if needed
    ]

    @model_validator(mode="after")
    def validate_dependencies(self) -> "ENDFOptions":
        """Validate logical dependencies between options."""
        # Check if use_energy_range_from_endf_file_2 requires input_is_endf_file_2
        if self.use_energy_range_from_endf_file_2 and not self.input_is_endf_file_2:
            raise ValueError("USE ENERGY RANGE FROM ENDF/B FILE 2 requires INPUT IS ENDF/B FILE 2 to be enabled")

        # Check if preserve_gamma_n_not_g_gamma_n_from_endf requires input_is_endf_file_2
        if self.preserve_gamma_n_not_g_gamma_n_from_endf and not self.input_is_endf_file_2:
            raise ValueError("PRESERVE GAMMA_N NOT g_gamma_n FROM ENDF requires INPUT IS ENDF/B FILE 2 to be enabled")

        # Check if automatic_ndf_file_creation requires input_is_endf_file_2
        if self.automatic_ndf_file_creation and not self.input_is_endf_file_2:
            raise ValueError("AUTOMATIC NDF FILE CREATION requires INPUT IS ENDF/B FILE 2 to be enabled")

        return self

    def get_alphanumeric_commands(self) -> List[str]:
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.input_is_endf_file_2:
            commands.append("INPUT IS ENDF/B FILE 2")
        if self.use_energy_range_from_endf_file_2:
            commands.append("USE ENERGY RANGE FROM ENDF/B FILE 2")
        if self.parameter_covariance_matrix_is_in_endf_format:
            commands.append("PARAMETER COVARIANCE MATRIX IS IN ENDF FORMAT")
        if self.data_are_endf_file:
            commands.append("DATA ARE ENDF/B FILE")
        if self.preserve_gamma_n_not_g_gamma_n_from_endf:
            commands.append("PRESERVE GAMMA_N NOT g_gamma_n FROM ENDF")
        if self.endf_b_vi_file_2_is_wanted:
            commands.append("ENDF/B-VI FILE 2 IS WANTED")
        if self.ndf_file_is_in_key_word_format:
            commands.append("NDF FILE IS IN KEY-WORD FORMAT")
        if self.generate_file_3_point_wise_cross_section:
            commands.append("GENERATE FILE 3 POINT-WISE CROSS SECTION")
        if self.file_33_lb_1_covariance_is_wanted:
            commands.append("FILE 33 LB=1 COVARIANCE IS WANTED")
        if self.automatic_ndf_file_creation:
            commands.append("AUTOMATIC NDF FILE CREATION")
        if self.include_min_and_max_energies_in_endf_file:
            commands.append("INCLUDE MIN & MAX ENERGIES IN ENDF FILE")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        # Example valid configuration
        options = ENDFOptions(
            input_is_endf_file_2=True, use_energy_range_from_endf_file_2=True, endf_b_vi_file_2_is_wanted=True
        )
        print("Valid configuration:")
        print(options.get_alphanumeric_commands())

        # Example with dependency error
        options = ENDFOptions(
            use_energy_range_from_endf_file_2=True  # This should fail without input_is_endf_file_2
        )
    except ValueError as e:
        print(f"Validation error: {e}")
