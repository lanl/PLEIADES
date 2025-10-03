from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with -------------- and ending with -------------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    #   Experimental data input control
    #   Define the format for the experimental data
        experimental_data_input_options = [
        ----------------------------
            *"DATA ARE IN ORIGINAL multi-style format",
            ["DATA FORMAT IS ONE Point per line","USE CSISRS FORMAT FOr data","CSISRS"],
            ["USE TWENTY SIGNIFICAnt digits","TWENTY"],
            "DATA ARE IN STANDARD odf format",
            "DATA ARE IN ODF FILE",
            ["DATA ARE ENDF/B FILE","USE ENDF/B ENERGIES and data, with MAT=9999"],
        ----------------------------
            "DIFFERENTIAL DATA ARe in ascii file",
        ----------------------------
            *"DO NOT DIVIDE DATA Into regions",
            "DIVIDE DATA INTO REGions with a fixed number of data points per region"
        ----------------------------
        ]
"""


class ExperimentalDataInputOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    data_in_original_multi_style_format: bool = Field(
        default=True, description="DATA ARE IN ORIGINAL multi-style format"
    )
    data_format_is_one_point_per_line: bool = Field(default=False, description="DATA FORMAT IS ONE Point per line")
    use_csisrs_format_for_data: bool = Field(default=False, description="USE CSISRS FORMAT For data")
    use_twenty_significant_digits: bool = Field(default=False, description="USE TWENTY SIGNIFICANT digits")
    data_are_in_standard_odf_format: bool = Field(default=False, description="DATA ARE IN STANDARD odf format")
    data_are_in_odf_file: bool = Field(default=False, description="DATA ARE IN ODF FILE")
    data_are_endf_b_file: bool = Field(default=False, description="DATA ARE ENDF/B FILE")
    use_endf_b_energies_and_data: bool = Field(default=False, description="USE ENDF/B ENERGIES and data, with MAT=9999")
    differential_data_are_in_ascii_file: bool = Field(default=False, description="DIFFERENTIAL DATA ARE in ascii file")
    do_not_divide_data_into_regions: bool = Field(default=True, description="DO NOT DIVIDE DATA Into regions")
    divide_data_into_regions: bool = Field(
        default=False, description="DIVIDE DATA INTO REGions with a fixed number of data points per region"
    )

    # Mutually exclusive groups
    mutually_exclusive_groups: List[List[str]] = [
        [
            "data_in_original_multi_style_format",
            "data_format_is_one_point_per_line",
            "use_csisrs_format_for_data",
            "use_twenty_significant_digits",
            "data_are_in_standard_odf_format",
            "data_are_in_odf_file",
            "data_are_endf_b_file",
            "use_endf_b_energies_and_data",
        ],
        ["differential_data_are_in_ascii_file"],
        [
            "do_not_divide_data_into_regions",
            "divide_data_into_regions",
        ],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "ExperimentalDataInputOptions":
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
        if self.data_in_original_multi_style_format:
            commands.append("DATA ARE IN ORIGINAL MULTI-STYLE FORMAT")
        if self.data_format_is_one_point_per_line:
            commands.append("DATA FORMAT IS ONE POINT PER LINE")
        if self.use_csisrs_format_for_data:
            commands.append("USE CSISRS FORMAT FOR DATA")
        if self.use_twenty_significant_digits:
            commands.append("USE TWENTY SIGNIFICANT DIGITS")
        if self.data_are_in_standard_odf_format:
            commands.append("DATA ARE IN STANDARD ODF FORMAT")
        if self.data_are_in_odf_file:
            commands.append("DATA ARE IN ODF FILE")
        if self.data_are_endf_b_file:
            commands.append("DATA ARE ENDF/B FILE")
        if self.use_endf_b_energies_and_data:
            commands.append("USE ENDF/B ENERGIES AND DATA, WITH MAT=9999")
        if self.differential_data_are_in_ascii_file:
            commands.append("DIFFERENTIAL DATA ARE IN ASCII FILE")
        if self.do_not_divide_data_into_regions:
            commands.append("DO NOT DIVIDE DATA INTO REGIONS")
        if self.divide_data_into_regions:
            commands.append("DIVIDE DATA INTO REGIONS WITH A FIXED NUMBER OF DATA POINTS PER REGION")
        return commands


if __name__ == "__main__":
    # Example usage:
    # Create an instance
    opts = ExperimentalDataInputOptions(use_twenty_significant_digits=True)
    # Print out the final model
    print(opts.model_dump())
    # Get the commands
    commands_list = opts.get_alphanumeric_commands()
    print("\nAlphanumeric commands:")
    for c in commands_list:
        print(f"  - {c}")
