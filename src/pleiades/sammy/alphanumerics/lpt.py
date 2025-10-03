from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   Options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

        Options for printing into SAMMY.LPT
        Define what information will be printed in output file SAMMY.LPT
        lpt_file_options = [
            ----------------------------
            *   "DO NOT PRINT ANY INPut parameters",
                "PRINT ALL INPUT PARAmeters",
                "PRINT VARIED INPUT Parameters",
            ----------------------------
            *   "DO NOT PRINT INPUT Data",
                "PRINT INPUT DATA" or "PRINT EXPERIMENTAL Values",
            ----------------------------
            *   "DO NOT PRINT THEORETical values",
                "PRINT THEORETICAL VAlues" or "PRINT THEORETICAL CRoss sections",
            ----------------------------
            *   "DO NOT PRINT PARTIAL derivatives",
                "PRINT PARTIAL DERIVAtives",
            ----------------------------
                "SUPPRESS INTERMEDIATe printout",
                "DO NOT SUPPRESS INTErmediate printout",
            *   "DO NOT SUPPRESS ANY intermediate printout",
            ----------------------------
            *   "DO NOT USE SHORT FORmat for output",
                "USE SHORT FORMAT FOR output",
            ----------------------------
            *   "DO NOT PRINT REDUCED widths",
                "PRINT REDUCED WIDTHS",
            ----------------------------
                "DO NOT PRINT SMALL Correlation coefficients",
            ----------------------------
            *   "DO NOT PRINT DEBUG Info",
                "PRINT DEBUG INFORMATion" or "DEBUG",
            ----------------------------
                "PRINT CAPTURE AREA In lpt file",
            ----------------------------
                "CHI SQUARED IS NOT Wanted" or "DO NOT PRINT LS CHI squared",
            *   "CHI SQUARED IS WANTEd" or "PRINT LS CHI SQUARED",
            ----------------------------
            *   "PRINT BAYES CHI SQUAred",
                "DO NOT PRINT BAYES Chi squared",
            ----------------------------
            *   "DO NOT PRINT WEIGHTEd Residuals" or "DO NOT PRINT LS WEIGhted residuals",
                "PRINT WEIGHTED RESIDuals" or "PRINT LS WEIGHTED REsiduals",
            ----------------------------
                "PRINT BAYES WEIGHTED residuals",
            *   "DO NOT PRINT BAYES Weighted residuals",
            ----------------------------
            *   "DO NOT PRINT PHASE Shifts",
                "PRINT PHASE SHIFTS For input parameters"
            ----------------------------
"""


class LPTOutputOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    do_not_print_any_input_parameters: bool = Field(default=True, description="DO NOT PRINT ANY INPut parameters")
    print_all_input_parameters: bool = Field(default=False, description="PRINT ALL INPUT PARAmeters")
    print_varied_input_parameters: bool = Field(default=False, description="PRINT VARIED INPUT Parameters")

    do_not_print_input_data: bool = Field(default=True, description="DO NOT PRINT INPUT Data")
    print_input_data: bool = Field(default=False, description="PRINT INPUT DATA")

    do_not_print_theoretical_values: bool = Field(default=True, description="DO NOT PRINT THEORETical values")
    print_theoretical_values: bool = Field(default=False, description="PRINT THEORETICAL VAlues")

    do_not_print_partial_derivatives: bool = Field(default=True, description="DO NOT PRINT PARTIAL derivatives")
    print_partial_derivatives: bool = Field(default=False, description="PRINT PARTIAL DERIVAtives")

    suppress_intermediate_printout: bool = Field(default=False, description="SUPPRESS INTERMEDIATe printout")
    do_not_suppress_intermediate_printout: bool = Field(
        default=False, description="DO NOT SUPPRESS INTErmediate printout"
    )
    do_not_suppress_any_intermediate_printout: bool = Field(
        default=True, description="DO NOT SUPPRESS ANY intermediate printout"
    )

    do_not_use_short_format_for_output: bool = Field(default=True, description="DO NOT USE SHORT FORmat for output")
    use_short_format_for_output: bool = Field(default=False, description="USE SHORT FORMAT FOR output")

    do_not_print_reduced_widths: bool = Field(default=True, description="DO NOT PRINT REDUCED widths")
    print_reduced_widths: bool = Field(default=False, description="PRINT REDUCED WIDTHS")

    do_not_print_small_correlation_coefficients: bool = Field(
        default=False, description="DO NOT PRINT SMALL Correlation coefficients"
    )

    do_not_print_debug_info: bool = Field(default=True, description="DO NOT PRINT DEBUG Info")
    print_debug_information: bool = Field(default=False, description="PRINT DEBUG INFORMATion")

    print_capture_area_in_lpt_file: bool = Field(default=False, description="PRINT CAPTURE AREA In lpt file")

    chi_squared_is_not_wanted: bool = Field(default=False, description="CHI SQUARE IS NOT Wanted")
    chi_squared_is_wanted: bool = Field(default=True, description="CHI SQUARED IS WANTEd")

    do_not_print_weighted_residuals: bool = Field(default=True, description="DO NOT PRINT WEIGHTEd Residuals")
    print_weighted_residuals: bool = Field(default=False, description="PRINT WEIGHTED RESIDuals")

    print_bayes_weighted_residuals: bool = Field(default=False, description="PRINT BAYES WEIGHTED residuals")
    do_not_print_bayes_weighted_residuals: bool = Field(
        default=True, description="DO NOT PRINT BAYES Weighted residuals"
    )

    do_not_print_phase_shifts: bool = Field(default=True, description="DO NOT PRINT PHASE Shifts")
    print_phase_shifts_for_input_parameters: bool = Field(
        default=False, description="PRINT PHASE SHIFTS For input parameters"
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        ["do_not_print_any_input_parameters", "print_all_input_parameters", "print_varied_input_parameters"],
        ["do_not_print_input_data", "print_input_data"],
        ["do_not_print_theoretical_values", "print_theoretical_values"],
        ["do_not_print_partial_derivatives", "print_partial_derivatives"],
        [
            "suppress_intermediate_printout",
            "do_not_suppress_intermediate_printout",
            "do_not_suppress_any_intermediate_printout",
        ],
        ["do_not_use_short_format_for_output", "use_short_format_for_output"],
        ["do_not_print_reduced_widths", "print_reduced_widths"],
        ["do_not_print_debug_info", "print_debug_information"],
        ["chi_squared_is_not_wanted", "chi_squared_is_wanted"],
        ["do_not_print_weighted_residuals", "print_weighted_residuals"],
        ["print_bayes_weighted_residuals", "do_not_print_bayes_weighted_residuals"],
        ["do_not_print_phase_shifts", "print_phase_shifts_for_input_parameters"],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "LPTOutputOptions":
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
        commands = []

        if self.do_not_print_any_input_parameters:
            commands.append("DO NOT PRINT ANY INPUT PARAMETERS")
        if self.print_all_input_parameters:
            commands.append("PRINT ALL INPUT PARAMETERS")
        if self.print_varied_input_parameters:
            commands.append("PRINT VARIED INPUT PARAMETERS")

        if self.do_not_print_input_data:
            commands.append("DO NOT PRINT INPUT DATA")
        if self.print_input_data:
            commands.append("PRINT INPUT DATA")

        if self.do_not_print_theoretical_values:
            commands.append("DO NOT PRINT THEORETICAL VALUES")
        if self.print_theoretical_values:
            commands.append("PRINT THEORETICAL VALUES")

        if self.do_not_print_partial_derivatives:
            commands.append("DO NOT PRINT PARTIAL DERIVATIVES")
        if self.print_partial_derivatives:
            commands.append("PRINT PARTIAL DERIVATIVES")

        if self.suppress_intermediate_printout:
            commands.append("SUPPRESS INTERMEDIATE PRINTOUT")
        if self.do_not_suppress_intermediate_printout:
            commands.append("DO NOT SUPPRESS INTERMEDIATE PRINTOUT")
        if self.do_not_suppress_any_intermediate_printout:
            commands.append("DO NOT SUPPRESS ANY INTERMEDIATE PRINTOUT")

        if self.do_not_use_short_format_for_output:
            commands.append("DO NOT USE SHORT FORMAT FOR OUTPUT")
        if self.use_short_format_for_output:
            commands.append("USE SHORT FORMAT FOR OUTPUT")

        if self.do_not_print_reduced_widths:
            commands.append("DO NOT PRINT REDUCED WIDTHS")
        if self.print_reduced_widths:
            commands.append("PRINT REDUCED WIDTHS")

        if self.do_not_print_small_correlation_coefficients:
            commands.append("DO NOT PRINT SMALL CORRELATION COEFFICIENTS")

        if self.do_not_print_debug_info:
            commands.append("DO NOT PRINT DEBUG INFO")
        if self.print_debug_information:
            commands.append("PRINT DEBUG INFORMATION")

        if self.print_capture_area_in_lpt_file:
            commands.append("PRINT CAPTURE AREA IN LPT FILE")

        if self.chi_squared_is_not_wanted:
            commands.append("CHI SQUARED IS NOT WANTED")
        if self.chi_squared_is_wanted:
            commands.append("CHI SQUARED IS WANTED")

        if self.do_not_print_weighted_residuals:
            commands.append("DO NOT PRINT WEIGHTED RESIDUALS")
        if self.print_weighted_residuals:
            commands.append("PRINT WEIGHTED RESIDUALS")

        if self.print_bayes_weighted_residuals:
            commands.append("PRINT BAYES WEIGHTED RESIDUALS")
        if self.do_not_print_bayes_weighted_residuals:
            commands.append("DO NOT PRINT BAYES WEIGHTED RESIDUALS")

        if self.do_not_print_phase_shifts:
            commands.append("DO NOT PRINT PHASE SHIFTS")
        if self.print_phase_shifts_for_input_parameters:
            commands.append("PRINT PHASE SHIFTS FOR INPUT PARAMETERS")

        return commands


# Example usage
if __name__ == "__main__":
    try:
        options = LPTOutputOptions(
            do_not_print_any_input_parameters=True,
            print_all_input_parameters=True,  # This should raise a ValueError
        )
    except ValueError as e:
        print(e)
