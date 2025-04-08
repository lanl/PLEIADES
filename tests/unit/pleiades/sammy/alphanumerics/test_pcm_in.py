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
    assert options.get_alphanumeric_commands() == ["IGNORE INPUT BINARY covariance file"]


def test_mutually_exclusive_options_1():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        CovarianceMatrixOptions(
            retroactive_old_parameter_file_new_covariance=True, p_covariance_matrix_is_correct_u_is_not=True
        )


def test_mutually_exclusive_options_2():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        CovarianceMatrixOptions(
            read_compact_covariances_for_parameter_priors=True, read_compact_correlations_for_parameter_priors=True
        )


def test_valid_combination_of_options_1():
    """Test a valid combination of options."""
    options = CovarianceMatrixOptions(
        energy_uncertainties_at_end_of_line_in_par_file=True,
        initial_diagonal_u_covariance=True,
        permit_non_positive_definite_parameter_covariance_matrices=True,
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
        "ENERGY UNCERTAINTIES are at end of line in par file",
        "INITIAL DIAGONAL U Covariance",
        "PERMIT NON POSITIVE definite parameter covariance matrices",
    ]


def test_valid_combination_of_options_2():
    """Test a valid combination of options."""
    options = CovarianceMatrixOptions(
        modify_p_covariance_matrix_before_using=True,
        read_compact_covariances_for_parameter_priors=True,
        use_least_squares_to_define_prior_parameter_covariance_matrix=True,
    )
    assert options.modify_p_covariance_matrix_before_using is True
    assert options.read_compact_covariances_for_parameter_priors is True
    assert options.use_least_squares_to_define_prior_parameter_covariance_matrix is True
    assert options.get_alphanumeric_commands() == [
        "MODIFY P COVARIANCE matrix before using",
        "READ COMPACT COVARIAnces for parameter priors",
        "USE LEAST SQUARES TO define prior parameter covariance matrix",
    ]


def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        CovarianceMatrixOptions(
            read_compact_covariances_for_parameter_priors=True, read_compact_correlations_for_parameter_priors=True
        )


def test_switching_options():
    """Test switching options."""
    options = CovarianceMatrixOptions()
    assert options.get_alphanumeric_commands() == []

    options = CovarianceMatrixOptions(ignore_input_binary_covariance_file=True)
    assert options.ignore_input_binary_covariance_file is True
    assert options.get_alphanumeric_commands() == ["IGNORE INPUT BINARY covariance file"]

    options = CovarianceMatrixOptions(energy_uncertainties_at_end_of_line_in_par_file=True)
    assert options.energy_uncertainties_at_end_of_line_in_par_file is True
    assert options.get_alphanumeric_commands() == ["ENERGY UNCERTAINTIES are at end of line in par file"]

    options = CovarianceMatrixOptions(retroactive_old_parameter_file_new_covariance=True)
    assert options.retroactive_old_parameter_file_new_covariance is True
    assert options.get_alphanumeric_commands() == ["RETROACTIVE OLD PARAmeter file new covariance"]

    options = CovarianceMatrixOptions(p_covariance_matrix_is_correct_u_is_not=True)
    assert options.p_covariance_matrix_is_correct_u_is_not is True
    assert options.get_alphanumeric_commands() == ["P COVARIANCE MATRIX is correct, u is not"]

    options = CovarianceMatrixOptions(modify_p_covariance_matrix_before_using=True)
    assert options.modify_p_covariance_matrix_before_using is True
    assert options.get_alphanumeric_commands() == ["MODIFY P COVARIANCE matrix before using"]

    options = CovarianceMatrixOptions(initial_diagonal_u_covariance=True)
    assert options.initial_diagonal_u_covariance is True
    assert options.get_alphanumeric_commands() == ["INITIAL DIAGONAL U Covariance"]

    options = CovarianceMatrixOptions(initial_diagonal_p_covariance=True)
    assert options.initial_diagonal_p_covariance is True
    assert options.get_alphanumeric_commands() == ["INITIAL DIAGONAL P Covariance"]

    options = CovarianceMatrixOptions(permit_non_positive_definite_parameter_covariance_matrices=True)
    assert options.permit_non_positive_definite_parameter_covariance_matrices is True
    assert options.get_alphanumeric_commands() == ["PERMIT NON POSITIVE definite parameter covariance matrices"]

    options = CovarianceMatrixOptions(permit_zero_uncertainties_on_parameters=True)
    assert options.permit_zero_uncertainties_on_parameters is True
    assert options.get_alphanumeric_commands() == ["PERMIT ZERO UNCERTAInties on parameters"]

    options = CovarianceMatrixOptions(read_compact_covariances_for_parameter_priors=True)
    assert options.read_compact_covariances_for_parameter_priors is True
    assert options.get_alphanumeric_commands() == ["READ COMPACT COVARIAnces for parameter priors"]

    options = CovarianceMatrixOptions(read_compact_correlations_for_parameter_priors=True)
    assert options.read_compact_correlations_for_parameter_priors is True
    assert options.get_alphanumeric_commands() == ["READ COMPACT CORRELAtions for parameter priors"]

    options = CovarianceMatrixOptions(compact_correlations_are_to_be_read_and_used=True)
    assert options.compact_correlations_are_to_be_read_and_used is True
    assert options.get_alphanumeric_commands() == ["COMPACT CORRELATIONS are to be read and used"]

    options = CovarianceMatrixOptions(compact_covariances_are_to_be_read_and_used=True)
    assert options.compact_covariances_are_to_be_read_and_used is True
    assert options.get_alphanumeric_commands() == ["COMPACT COVARIANCES are to be read and used"]

    options = CovarianceMatrixOptions(parameter_covariance_matrix_is_in_endf_format=True)
    assert options.parameter_covariance_matrix_is_in_endf_format is True
    assert options.get_alphanumeric_commands() == ["PARAMETER COVARIANCE matrix is in endf format"]

    options = CovarianceMatrixOptions(endf_covariance_matrix_is_to_be_read_and_used=True)
    assert options.endf_covariance_matrix_is_to_be_read_and_used is True
    assert options.get_alphanumeric_commands() == ["ENDF COVARIANCE MATRix is to be read and Used"]

    options = CovarianceMatrixOptions(use_least_squares_to_define_prior_parameter_covariance_matrix=True)
    assert options.use_least_squares_to_define_prior_parameter_covariance_matrix is True
    assert options.get_alphanumeric_commands() == ["USE LEAST SQUARES TO define prior parameter covariance matrix"]


if __name__ == "__main__":
    pytest.main()
