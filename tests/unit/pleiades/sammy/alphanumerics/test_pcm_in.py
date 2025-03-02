import pytest
from pleiades.sammy.alphanumerics.pcm_in import CovarianceMatrixOptions

def test_default_option():
    """Test the default option."""
    options = CovarianceMatrixOptions()
    assert options.ignore_input_binary_covariance_file is False
    assert options.energy_uncertainties_at_end_of_line_in_par_file is False
    assert options.retroactive_old_parameter_file_new_covariance is False
    assert options.p_covariance_matrix_is_correct_u_is_not is False
    assert options.modify_p_covariance_matrix_before_using is False
    assert options.initial_diagonal_u_covariance is False
    assert options.initial_diagonal_p_covariance is False
    assert options.permit_non_positive_definite_parameter_covariance_matrices is False
    assert options.permit_zero_uncertainties_on_parameters is False
    assert options.read_compact_covariances_for_parameter_priors is False
    assert options.read_compact_correlations_for_parameter_priors is False
    assert options.compact_correlations_are_to_be_read_and_used is False
    assert options.compact_covariances_are_to_be_read_and_used is False
    assert options.parameter_covariance_matrix_is_in_endf_format is False
    assert options.endf_covariance_matrix_is_to_be_read_and_used is False
    assert options.use_least_squares_to_define_prior_parameter_covariance_matrix is False
    assert options.get_alphanumeric_commands() == []

def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    options = CovarianceMatrixOptions(ignore_input_binary_covariance_file=True)
    assert options.ignore_input_binary_covariance_file is True
    assert options.energy_uncertainties_at_end_of_line_in_par_file is False
    assert options.retroactive_old_parameter_file_new_covariance is False
    assert options.p_covariance_matrix_is_correct_u_is_not is False
    assert options.modify_p_covariance_matrix_before_using is False
    assert options.initial_diagonal_u_covariance is False
    assert options.initial_diagonal_p_covariance is False
    assert options.permit_non_positive_definite_parameter_covariance_matrices is False
    assert options.permit_zero_uncertainties_on_parameters is False
    assert options.read_compact_covariances_for_parameter_priors is False
    assert options.read_compact_correlations_for_parameter_priors is False
    assert options.compact_correlations_are_to_be_read_and_used is False
    assert options.compact_covariances_are_to_be_read_and_used is False
    assert options.parameter_covariance_matrix_is_in_endf_format is False
    assert options.endf_covariance_matrix_is_to_be_read_and_used is False
    assert options.use_least_squares_to_define_prior_parameter_covariance_matrix is False
    assert options.get_alphanumeric_commands() == ["IGNORE INPUT BINARY COVARIANCE FILE"]

def test_mutually_exclusive_options():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        CovarianceMatrixOptions(retroactive_old_parameter_file_new_covariance=True, p_covariance_matrix_is_correct_u_is_not=True)

def test_valid_combination_of_options():
    """Test a valid combination of options."""
    options = CovarianceMatrixOptions(
        energy_uncertainties_at_end_of_line_in_par_file=True,
        initial_diagonal_u_covariance=True,
        permit_non_positive_definite_parameter_covariance_matrices=True
    )
    assert options.ignore_input_binary_covariance_file is False
    assert options.energy_uncertainties_at_end_of_line_in_par_file is True
    assert options.retroactive_old_parameter_file_new_covariance is False
    assert options.p_covariance_matrix_is_correct_u_is_not is False
    assert options.modify_p_covariance_matrix_before_using is False
    assert options.initial_diagonal_u_covariance is True
    assert options.initial_diagonal_p_covariance is False
    assert options.permit_non_positive_definite_parameter_covariance_matrices is True
    assert options.permit_zero_uncertainties_on_parameters is False
    assert options.read_compact_covariances_for_parameter_priors is False
    assert options.read_compact_correlations_for_parameter_priors is False
    assert options.compact_correlations_are_to_be_read_and_used is False
    assert options.compact_covariances_are_to_be_read_and_used is False
    assert options.parameter_covariance_matrix_is_in_endf_format is False
    assert options.endf_covariance_matrix_is_to_be_read_and_used is False
    assert options.use_least_squares_to_define_prior_parameter_covariance_matrix is False
    assert options.get_alphanumeric_commands() == [
        "ENERGY UNCERTAINTIES ARE AT END OF LINE IN PAR FILE",
        "INITIAL DIAGONAL U COVARIANCE",
        "PERMIT NON POSITIVE DEFINITE PARAMETER COVARIANCE MATRICES"
    ]

def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        CovarianceMatrixOptions(
            read_compact_covariances_for_parameter_priors=True,
            read_compact_correlations_for_parameter_priors=True
        )

if __name__ == "__main__":
    pytest.main()