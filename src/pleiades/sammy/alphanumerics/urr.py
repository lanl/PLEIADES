from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    Unresolved Resonance Region (URR) options = [
    ----------------------------
        "UNRESOLVED RESONANCE region",
        "EXPERIMENTAL DATA ARe in separate files",
        "NO ANNOTATED PARAMETer file for urr input",
        "ANNOTATED PARAMETER file for urr", *
        "OUTPUT IN ANNOTATED parameter file for urr", * (always true for output)
        "USE ALL EXPERIMENTAL data points", * (Default for URR)
        "USE ENERGY LIMITS AS Given in the input file",
        "CALCULATE WIDTH FLUCtuation factors more acc",
        "MOLDAUER PRESCRIPTIOn is to be used",
    ----------------------------
    ]
"""


class URROptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # Basic URR mode option
    unresolved_resonance_region: bool = Field(
        default=False,
        description="Use the SAMMY version of Fritz Froehner's code FITACS for analysis of the unresolved resonance region (URR)",
    )

    # Data file options
    experimental_data_are_in_separate_files: bool = Field(
        default=False,
        description="For URR, experimental data are in separate files rather than in URR PARameter file",
    )

    # Parameter file format options (mutually exclusive)
    no_annotated_parameter_file_for_urr_input: bool = Field(
        default=False,
        description="For URR, PARameter file is in original FITACS format (Table VIII B.1)",
    )
    annotated_parameter_file_for_urr: bool = Field(
        default=True,
        description="For URR, PARameter file is in annotated, key-word based format (Table VIII B.2). (Default)",
    )
    output_in_annotated_parameter_file_for_urr: bool = Field(
        default=True,
        description="For URR, output PARameter file is annotated (Always true for output)",
    )

    # Data point selection options (mutually exclusive)
    use_all_experimental_data_points: bool = Field(
        default=True,
        description="For URR, use all data points in URR PARameter file or separate data files. Ignore EMIN/EMAX from INPut file. (Default for URR)",
    )
    use_energy_limits_as_given_in_the_input_file: bool = Field(
        default=False,
        description="For URR, use EMIN/EMAX from INPut file card set 2 to define which data points are analyzed",
    )

    # Calculation options
    calculate_width_fluctuation_factors_more_accurately: bool = Field(
        default=False,
        description="For URR, use 1001 grid points (instead of 101) for Dresner integrals",
    )
    moldauer_prescription_is_to_be_used: bool = Field(
        default=False,
        description="For URR, use Moldauer's 'effective degree of freedom' to compensate for strong resonance overlap",
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        ["no_annotated_parameter_file_for_urr_input", "annotated_parameter_file_for_urr"],
        ["use_all_experimental_data_points", "use_energy_limits_as_given_in_the_input_file"],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "URROptions":
        """Validate mutually exclusive fields."""
        # Parameter file format options - cannot have both
        if self.no_annotated_parameter_file_for_urr_input and self.annotated_parameter_file_for_urr:
            raise ValueError(
                "NO ANNOTATED PARAMETER FILE FOR URR INPUT and ANNOTATED PARAMETER FILE FOR URR cannot both be enabled"
            )

        # Data point selection options - cannot have both
        if self.use_all_experimental_data_points and self.use_energy_limits_as_given_in_the_input_file:
            raise ValueError(
                "USE ALL EXPERIMENTAL DATA POINTS and USE ENERGY LIMITS AS GIVEN IN THE INPUT FILE cannot both be enabled"
            )

        return self

    def get_alphanumeric_commands(self) -> List[str]:
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.unresolved_resonance_region:
            commands.append("UNRESOLVED RESONANCE REGION")
        if self.experimental_data_are_in_separate_files:
            commands.append("EXPERIMENTAL DATA ARE IN SEPARATE FILES")
        if self.no_annotated_parameter_file_for_urr_input:
            commands.append("NO ANNOTATED PARAMETER FILE FOR URR INPUT")
        if self.annotated_parameter_file_for_urr:
            commands.append("ANNOTATED PARAMETER FILE FOR URR")
        if self.output_in_annotated_parameter_file_for_urr:
            commands.append("OUTPUT IN ANNOTATED PARAMETER FILE FOR URR")
        if self.use_all_experimental_data_points:
            commands.append("USE ALL EXPERIMENTAL DATA POINTS")
        if self.use_energy_limits_as_given_in_the_input_file:
            commands.append("USE ENERGY LIMITS AS GIVEN IN THE INPUT FILE")
        if self.calculate_width_fluctuation_factors_more_accurately:
            commands.append("CALCULATE WIDTH FLUCTUATION FACTORS MORE ACCURATELY")
        if self.moldauer_prescription_is_to_be_used:
            commands.append("MOLDAUER PRESCRIPTION IS TO BE USED")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        # Example valid configuration
        options = URROptions(
            unresolved_resonance_region=True,
            experimental_data_are_in_separate_files=True,
            no_annotated_parameter_file_for_urr_input=True,
            annotated_parameter_file_for_urr=False,
        )
        print("Valid configuration:")
        print(options.get_alphanumeric_commands())

        # Example with mutually exclusive error
        options = URROptions(
            no_annotated_parameter_file_for_urr_input=True,
            annotated_parameter_file_for_urr=True,  # This should fail
        )
    except ValueError as e:
        print(f"Validation error: {e}")
