from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   Options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

        Experimental data input control for covariance matrix
        Define the format for input of data covariance matrix
        covariance_matrix_data_input_options = [
        ----------------------------
            ["IMPLICIT DATA COVARIance is wanted","IDC"],
            ["USER SUPPLIED IMPLICit data covariance matrix","USER IDC"],
        ----------------------------
            "PUP COVARIANCE IS IN an ascii file",
        ----------------------------
            "CREATE PUP FILE FROM varied parameters used in this run",
        ----------------------------
            ["ADD CONSTANT TERM TO data covariance ","ADD CONSTANT TO DATA covariance matrix"],
        *   "DO NOT ADD CONSTANT term to data covariance",
            "USE DEFAULT FOR CONStant term to add to data covariance",
        ----------------------------
            "USE TEN PERCENT DATA uncertainty "or "ADD TEN PERCENT DATA uncertainty",
        ----------------------------
        *   "DATA COVARIANCE IS Diagonal"
            "DATA HAS OFF-DIAGONAl contribution to covariance matrix of the form (a+bEi) (a+bEj)",
            "DATA COVARIANCE FILE is named YYYYYY.YYY",
            "FREE FORMAT DATA COVariance YYYYYY.YYY",
        ]
"""


class CovarianceMatrixOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    implicit_data_covariance: bool = Field(default=False, description="IMPLICIT DATA COVARIANCE is wanted")
    user_supplied_implicit_data_covariance: bool = Field(
        default=False, description="USER SUPPLIED IMPLICIT data covariance matrix"
    )
    pup_covariance_ascii: bool = Field(default=False, description="PUP COVARIANCE IS IN an ascii file")
    create_pup_file: bool = Field(default=False, description="CREATE PUP FILE FROM varied parameters used in this run")
    add_constant_term: bool = Field(default=False, description="ADD CONSTANT TERM TO data covariance")
    do_not_add_constant_term: bool = Field(default=True, description="DO NOT ADD CONSTANT term to data covariance")
    use_default_constant_term: bool = Field(
        default=False, description="USE DEFAULT FOR CONSTANT term to add to data covariance"
    )
    use_ten_percent_uncertainty: bool = Field(
        default=False, description="USE TEN PERCENT DATA uncertainty or ADD TEN PERCENT DATA uncertainty"
    )
    data_covariance_diagonal: bool = Field(default=True, description="DATA COVARIANCE IS Diagonal")
    data_off_diagonal: bool = Field(
        default=False, description="DATA HAS OFF-DIAGONAL contribution to covariance matrix of the form (a+bEi) (a+bEj)"
    )
    data_covariance_file: bool = Field(default=False, description="DATA COVARIANCE FILE is named YYYYYY.YYY")
    free_format_data_covariance: bool = Field(default=False, description="FREE FORMAT DATA COVARIANCE YYYYYY.YYY")

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        ["implicit_data_covariance", "user_supplied_implicit_data_covariance"],
        ["pup_covariance_ascii"],
        ["create_pup_file"],
        ["add_constant_term", "do_not_add_constant_term", "use_default_constant_term"],
        ["use_ten_percent_uncertainty"],
        ["data_covariance_diagonal", "data_off_diagonal", "data_covariance_file", "free_format_data_covariance"],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "CovarianceMatrixOptions":
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
        if self.implicit_data_covariance:
            commands.append("IMPLICIT DATA COVARIANCE IS WANTED")
        if self.user_supplied_implicit_data_covariance:
            commands.append("USER SUPPLIED IMPLICIT DATA COVARIANCE MATRIX")
        if self.pup_covariance_ascii:
            commands.append("PUP COVARIANCE IS IN AN ASCII FILE")
        if self.create_pup_file:
            commands.append("CREATE PUP FILE FROM VARIED PARAMETERS USED IN THIS RUN")
        if self.add_constant_term:
            commands.append("ADD CONSTANT TERM TO DATA COVARIANCE")
        if self.do_not_add_constant_term:
            commands.append("DO NOT ADD CONSTANT TERM TO DATA COVARIANCE")
        if self.use_default_constant_term:
            commands.append("USE DEFAULT FOR CONSTANT TERM TO ADD TO DATA COVARIANCE")
        if self.use_ten_percent_uncertainty:
            commands.append("USE TEN PERCENT DATA UNCERTAINTY OR ADD TEN PERCENT DATA UNCERTAINTY")
        if self.data_covariance_diagonal:
            commands.append("DATA COVARIANCE IS DIAGONAL")
        if self.data_off_diagonal:
            commands.append("DATA HAS OFF-DIAGONAL CONTRIBUTION TO COVARIANCE MATRIX OF THE FORM (A+BEI) (A+BEJ)")
        if self.data_covariance_file:
            commands.append("DATA COVARIANCE FILE IS NAMED YYYYYY.YYY")
        if self.free_format_data_covariance:
            commands.append("FREE FORMAT DATA COVARIANCE YYYYYY.YYY")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        options = CovarianceMatrixOptions(
            implicit_data_covariance=True,
            user_supplied_implicit_data_covariance=True,  # This should raise a ValueError
        )
    except ValueError as e:
        print(e)
