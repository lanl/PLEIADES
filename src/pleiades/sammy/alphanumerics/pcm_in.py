from pydantic import BaseModel, Field, model_validator

"""
# Parameters input control for prior covariance matrix:
# Define the prior parameter covariance matrix
input_covariance_matrix_options = 
[
["IGNORE INPUT BINARY covariance file","IGNORE"],
"ENERGY UNCERTAINTIES are at end of line in par file",
--------------
["RETROACTIVE OLD PARAmeter file new covariance","RETROACTIVE","U COVARIANCE MATRIX is correct, p is not"],
"P COVARIANCE MATRIX is correct, u is not",
--------------
"MODIFY P COVARIANCE matrix before using",
--------------
"INITIAL DIAGONAL U Covariance",
"INITIAL DIAGONAL P Covariance",
--------------
["PERMIT NON POSITIVE definite parameter covariance matrices","PERMIT ZERO UNCERTAInties on parameters"],
--------------
["READ COMPACT COVARIAnces for parameter priors","READ COMPACT CORRELAtions for parameter priors","COMPACT CORRELATIONS are to be read and used","COMPACT COVARIANCES are to be read and used"], 
["PARAMETER COVARIANCE matrix is in endf format","ENDF COVARIANCE MATRix is to be read and Used"],
--------------
"USE LEAST SQUARES TO define prior parameter covariance matrix"
]

"""

class CovarianceMatrixOptions(BaseModel):
    """Model to enforce mutually exclusive selection of prior covariance matrix input options using boolean flags."""
    
    # Boolean flags for mutual exclusivity
    ignore_input_binary_covariance_file: bool = Field(default=False, description="Ignore input binary covariance file")
    energy_uncertainties_at_end_of_line_in_par_file: bool = Field(default=False, description="Energy uncertainties are at end of line in par file")
    retroactive_old_parameter_file_new_covariance: bool = Field(default=False, description="Retroactive old parameter file new covariance")
    p_covariance_matrix_is_correct_u_is_not: bool = Field(default=False, description="P covariance matrix is correct, U is not")
    modify_p_covariance_matrix_before_using: bool = Field(default=False, description="Modify P covariance matrix before using")
    initial_diagonal_u_covariance: bool = Field(default=False, description="Initial diagonal U covariance")
    initial_diagonal_p_covariance: bool = Field(default=False, description="Initial diagonal P covariance")
    permit_non_positive_definite_parameter_covariance_matrices: bool = Field(default=False, description="Permit non-positive definite parameter covariance matrices")
    permit_zero_uncertainties_on_parameters: bool = Field(default=False, description="Permit zero uncertainties on parameters")
    read_compact_covariances_for_parameter_priors: bool = Field(default=False, description="Read compact covariances for parameter priors")
    read_compact_correlations_for_parameter_priors: bool = Field(default=False, description="Read compact correlations for parameter priors")
    compact_correlations_are_to_be_read_and_used: bool = Field(default=False, description="Compact correlations are to be read and used")
    compact_covariances_are_to_be_read_and_used: bool = Field(default=False, description="Compact covariances are to be read and used")
    parameter_covariance_matrix_is_in_endf_format: bool = Field(default=False, description="Parameter covariance matrix is in ENDF format")
    endf_covariance_matrix_is_to_be_read_and_used: bool = Field(default=False, description="ENDF covariance matrix is to be read and used")
    use_least_squares_to_define_prior_parameter_covariance_matrix: bool = Field(default=False, description="Use least squares to define prior parameter covariance matrix")

    def get_alphanumeric_commands(self):
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        
        if self.ignore_input_binary_covariance_file:
            commands.append("IGNORE INPUT BINARY COVARIANCE FILE")
        if self.energy_uncertainties_at_end_of_line_in_par_file:
            commands.append("ENERGY UNCERTAINTIES ARE AT END OF LINE IN PAR FILE")
        if self.retroactive_old_parameter_file_new_covariance:
            commands.append("RETROACTIVE OLD PARAMETER FILE NEW COVARIANCE")
        if self.p_covariance_matrix_is_correct_u_is_not:
            commands.append("P COVARIANCE MATRIX IS CORRECT, U IS NOT")
        if self.modify_p_covariance_matrix_before_using:
            commands.append("MODIFY P COVARIANCE MATRIX BEFORE USING")
        if self.initial_diagonal_u_covariance:
            commands.append("INITIAL DIAGONAL U COVARIANCE")
        if self.initial_diagonal_p_covariance:
            commands.append("INITIAL DIAGONAL P COVARIANCE")
        if self.permit_non_positive_definite_parameter_covariance_matrices:
            commands.append("PERMIT NON POSITIVE DEFINITE PARAMETER COVARIANCE MATRICES")
        if self.permit_zero_uncertainties_on_parameters:    
            commands.append("PERMIT ZERO UNCERTAINTIES ON PARAMETERS")
        if self.read_compact_covariances_for_parameter_priors:
            commands.append("READ COMPACT COVARIANCES FOR PARAMETER PRIORS")
        if self.read_compact_correlations_for_parameter_priors:
            commands.append("READ COMPACT CORRELATIONS FOR PARAMETER PRIORS")
        if self.compact_correlations_are_to_be_read_and_used:
            commands.append("COMPACT CORRELATIONS ARE TO BE READ AND USED")
        if self.compact_covariances_are_to_be_read_and_used:
            commands.append("COMPACT COVARIANCES ARE TO BE READ AND USED")
        if self.parameter_covariance_matrix_is_in_endf_format:
            commands.append("PARAMETER COVARIANCE MATRIX IS IN ENDF FORMAT")
        if self.endf_covariance_matrix_is_to_be_read_and_used:
            commands.append("ENDF COVARIANCE MATRIX IS TO BE READ AND USED")
        if self.use_least_squares_to_define_prior_parameter_covariance_matrix:
            commands.append("USE LEAST SQUARES TO DEFINE PRIOR PARAMETER COVARIANCE MATRIX")
        return commands
    
    @model_validator(mode='after')
    def check_exclusivity(cls, values):
        """Ensure that only one option is selected using boolean flags."""
        mutually_exclusive_groups = [
            ["ignore_input_binary_covariance_file"], 
            ["energy_uncertainties_at_end_of_line_in_par_file"],
            ["retroactive_old_parameter_file_new_covariance", "p_covariance_matrix_is_correct_u_is_not"],
            ["modify_p_covariance_matrix_before_using"],
            ["initial_diagonal_u_covariance", "initial_diagonal_p_covariance"],
            ["permit_non_positive_definite_parameter_covariance_matrices", "permit_zero_uncertainties_on_parameters"],
            ["read_compact_covariances_for_parameter_priors", "read_compact_correlations_for_parameter_priors", "compact_correlations_are_to_be_read_and_used", "compact_covariances_are_to_be_read_and_used","parameter_covariance_matrix_is_in_endf_format", "endf_covariance_matrix_is_to_be_read_and_used"],
            ["use_least_squares_to_define_prior_parameter_covariance_matrix"]
        ]

        for group in mutually_exclusive_groups:
            selected_flags = [key for key in group if getattr(values, key)]
            if len(selected_flags) > 1:
                raise ValueError(f"Only one option can be selected from the group: {selected_flags}")

        return values