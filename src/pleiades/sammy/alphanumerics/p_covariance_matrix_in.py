from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

        Parameters input control for prior covariance matrix:
        Define the prior parameter covariance matrix
        input_covariance_matrix_options = [
        ----------------------------
            ["IGNORE INPUT BINARY covariance file","IGNORE"],
            "ENERGY UNCERTAINTIES are at end of line in par file",
        ----------------------------
            ["RETROACTIVE OLD PARAmeter file new covariance",
            "RETROACTIVE",
            "U COVARIANCE MATRIX is correct, p is not"],
            "P COVARIANCE MATRIX is correct, u is not",
        ----------------------------
            "MODIFY P COVARIANCE matrix before using",
        ----------------------------
            "INITIAL DIAGONAL U Covariance",
            "INITIAL DIAGONAL P Covariance",
        ----------------------------
            ["PERMIT NON POSITIVE definite parameter covariance matrices",
            "PERMIT ZERO UNCERTAInties on parameters"],
        ----------------------------
            ["READ COMPACT COVARIAnces for parameter priors",
            "READ COMPACT CORRELAtions for parameter priors",
            "COMPACT CORRELATIONS are to be read and used",
            "COMPACT COVARIANCES are to be read and used"],
            ["PARAMETER COVARIANCE matrix is in endf format",
            "ENDF COVARIANCE MATRix is to be read and Used"],
        ----------------------------
            "USE LEAST SQUARES TO define prior parameter covariance matrix"
        ----------------------------
        ]

"""


class CovarianceMatrixOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    ignore_input_binary_covariance_file: bool = Field(default=False, description="IGNORE INPUT BINARY covariance file")
    energy_uncertainties_at_end_of_line_in_par_file: bool = Field(
        default=False, description="ENERGY UNCERTAINTIES are at end of line in par file"
    )
    retroactive_old_parameter_file_new_covariance: bool = Field(
        default=False, description="RETROACTIVE OLD PARAmeter file new covariance"
    )
    p_covariance_matrix_is_correct_u_is_not: bool = Field(
        default=False, description="P COVARIANCE MATRIX is correct, u is not"
    )
    modify_p_covariance_matrix_before_using: bool = Field(
        default=False, description="MODIFY P COVARIANCE matrix before using"
    )
    initial_diagonal_u_covariance: bool = Field(default=False, description="INITIAL DIAGONAL U Covariance")
    initial_diagonal_p_covariance: bool = Field(default=False, description="INITIAL DIAGONAL P Covariance")
    permit_non_positive_definite_parameter_covariance_matrices: bool = Field(
        default=False, description="PERMIT NON POSITIVE definite parameter covariance matrices"
    )
    permit_zero_uncertainties_on_parameters: bool = Field(
        default=False, description="PERMIT ZERO UNCERTAInties on parameters"
    )
    read_compact_covariances_for_parameter_priors: bool = Field(
        default=False, description="READ COMPACT COVARIAnces for parameter priors"
    )
    read_compact_correlations_for_parameter_priors: bool = Field(
        default=False, description="READ COMPACT CORRELAtions for parameter priors"
    )
    compact_correlations_are_to_be_read_and_used: bool = Field(
        default=False, description="COMPACT CORRELATIONS are to be read and used"
    )
    compact_covariances_are_to_be_read_and_used: bool = Field(
        default=False, description="COMPACT COVARIANCES are to be read and used"
    )
    parameter_covariance_matrix_is_in_endf_format: bool = Field(
        default=False, description="PARAMETER COVARIANCE matrix is in endf format"
    )
    endf_covariance_matrix_is_to_be_read_and_used: bool = Field(
        default=False, description="ENDF COVARIANCE MATRix is to be read and Used"
    )
    use_least_squares_to_define_prior_parameter_covariance_matrix: bool = Field(
        default=False, description="USE LEAST SQUARES TO define prior parameter covariance matrix"
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        ["ignore_input_binary_covariance_file", "energy_uncertainties_at_end_of_line_in_par_file"],
        ["retroactive_old_parameter_file_new_covariance", "p_covariance_matrix_is_correct_u_is_not"],
        ["modify_p_covariance_matrix_before_using"],
        ["initial_diagonal_u_covariance", "initial_diagonal_p_covariance"],
        ["permit_non_positive_definite_parameter_covariance_matrices", "permit_zero_uncertainties_on_parameters"],
        [
            "read_compact_covariances_for_parameter_priors",
            "read_compact_correlations_for_parameter_priors",
            "compact_correlations_are_to_be_read_and_used",
            "compact_covariances_are_to_be_read_and_used",
            "parameter_covariance_matrix_is_in_endf_format",
            "endf_covariance_matrix_is_to_be_read_and_used",
        ],
        ["use_least_squares_to_define_prior_parameter_covariance_matrix"],
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
        if self.ignore_input_binary_covariance_file:
            commands.append("IGNORE INPUT BINARY covariance file")
        if self.energy_uncertainties_at_end_of_line_in_par_file:
            commands.append("ENERGY UNCERTAINTIES are at end of line in par file")
        if self.retroactive_old_parameter_file_new_covariance:
            commands.append("RETROACTIVE OLD PARAmeter file new covariance")
        if self.p_covariance_matrix_is_correct_u_is_not:
            commands.append("P COVARIANCE MATRIX is correct, u is not")
        if self.modify_p_covariance_matrix_before_using:
            commands.append("MODIFY P COVARIANCE matrix before using")
        if self.initial_diagonal_u_covariance:
            commands.append("INITIAL DIAGONAL U Covariance")
        if self.initial_diagonal_p_covariance:
            commands.append("INITIAL DIAGONAL P Covariance")
        if self.permit_non_positive_definite_parameter_covariance_matrices:
            commands.append("PERMIT NON POSITIVE definite parameter covariance matrices")
        if self.permit_zero_uncertainties_on_parameters:
            commands.append("PERMIT ZERO UNCERTAInties on parameters")
        if self.read_compact_covariances_for_parameter_priors:
            commands.append("READ COMPACT COVARIAnces for parameter priors")
        if self.read_compact_correlations_for_parameter_priors:
            commands.append("READ COMPACT CORRELAtions for parameter priors")
        if self.compact_correlations_are_to_be_read_and_used:
            commands.append("COMPACT CORRELATIONS are to be read and used")
        if self.compact_covariances_are_to_be_read_and_used:
            commands.append("COMPACT COVARIANCES are to be read and used")
        if self.parameter_covariance_matrix_is_in_endf_format:
            commands.append("PARAMETER COVARIANCE matrix is in endf format")
        if self.endf_covariance_matrix_is_to_be_read_and_used:
            commands.append("ENDF COVARIANCE MATRix is to be read and Used")
        if self.use_least_squares_to_define_prior_parameter_covariance_matrix:
            commands.append("USE LEAST SQUARES TO define prior parameter covariance matrix")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        options = CovarianceMatrixOptions(
            ignore_input_binary_covariance_file=True,
            energy_uncertainties_at_end_of_line_in_par_file=True,  # This should raise a ValueError
        )
    except ValueError as e:
        print(e)
