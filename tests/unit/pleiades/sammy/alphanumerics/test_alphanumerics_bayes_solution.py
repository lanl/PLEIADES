import pytest

from pleiades.sammy.alphanumerics.bayes_solution import BayesSolutionOptions


def test_default_option():
    """Test the default option."""
    options = BayesSolutionOptions()
    assert options.solve_bayes_equations is True
    assert options.do_not_solve_bayes_equations is False
    assert options.let_sammy_choose_which_inversion_scheme_to_use is True
    assert options.use_npv_inversion_scheme is False
    assert options.use_ipq_inversion_scheme is False
    assert options.use_mpw_inversion_scheme is False
    assert options.use_least_squares_to_define_prior_parameter_covariance_matrix is False
    assert options.take_baby_steps_with_least_squares_method is False
    assert options.remember_original_parameter_values is False
    assert options.use_remembered_original_parameter_values is False
    assert options.get_alphanumeric_commands() == [
        "SOLVE BAYES EQUATIONS",
        "LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE",
    ]


def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    options = BayesSolutionOptions(do_not_solve_bayes_equations=True)
    assert options.solve_bayes_equations is False
    assert options.do_not_solve_bayes_equations is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT SOLVE BAYES EQUATIONS",
        "LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE",
    ]


def test_mutually_exclusive_options_1():
    """Test mutually exclusive options for solving Bayes equations."""
    with pytest.raises(ValueError):
        BayesSolutionOptions(solve_bayes_equations=True, do_not_solve_bayes_equations=True)


def test_mutually_exclusive_options_2():
    """Test mutually exclusive options for inversion schemes."""
    with pytest.raises(ValueError):
        BayesSolutionOptions(let_sammy_choose_which_inversion_scheme_to_use=True, use_npv_inversion_scheme=True)


def test_valid_combination_of_options_1():
    """Test a valid combination of options using NPV and least squares."""
    options = BayesSolutionOptions(
        use_npv_inversion_scheme=True, use_least_squares_to_define_prior_parameter_covariance_matrix=True
    )
    assert options.let_sammy_choose_which_inversion_scheme_to_use is False
    assert options.use_npv_inversion_scheme is True
    assert options.use_least_squares_to_define_prior_parameter_covariance_matrix is True
    assert options.get_alphanumeric_commands() == [
        "SOLVE BAYES EQUATIONS",
        "USE (N+V) INVERSION SCHEME",
        "USE LEAST SQUARES TO DEFINE PRIOR PARAMETER COVARIANCE MATRIX",
    ]


def test_valid_combination_of_options_2():
    """Test a valid combination of options using IPQ and baby steps."""
    options = BayesSolutionOptions(use_ipq_inversion_scheme=True, take_baby_steps_with_least_squares_method=True)
    assert options.let_sammy_choose_which_inversion_scheme_to_use is False
    assert options.use_ipq_inversion_scheme is True
    assert options.take_baby_steps_with_least_squares_method is True
    assert options.get_alphanumeric_commands() == [
        "SOLVE BAYES EQUATIONS",
        "USE (I+Q) INVERSION SCHEME",
        "TAKE BABY STEPS WITH LEAST-SQUARES METHOD",
    ]


def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        BayesSolutionOptions(
            solve_bayes_equations=True, do_not_solve_bayes_equations=True, use_npv_inversion_scheme=True
        )


def test_switching_options():
    """Test switching options."""
    # Default options
    options = BayesSolutionOptions()
    assert options.solve_bayes_equations is True
    assert options.get_alphanumeric_commands() == [
        "SOLVE BAYES EQUATIONS",
        "LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE",
    ]

    # Test different Bayes solving options
    options = BayesSolutionOptions(do_not_solve_bayes_equations=True)
    assert options.do_not_solve_bayes_equations is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT SOLVE BAYES EQUATIONS",
        "LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE",
    ]

    # Test different inversion schemes
    options = BayesSolutionOptions(use_npv_inversion_scheme=True)
    assert options.use_npv_inversion_scheme is True
    assert options.get_alphanumeric_commands() == ["SOLVE BAYES EQUATIONS", "USE (N+V) INVERSION SCHEME"]

    options = BayesSolutionOptions(use_ipq_inversion_scheme=True)
    assert options.use_ipq_inversion_scheme is True
    assert options.get_alphanumeric_commands() == ["SOLVE BAYES EQUATIONS", "USE (I+Q) INVERSION SCHEME"]

    options = BayesSolutionOptions(use_mpw_inversion_scheme=True)
    assert options.use_mpw_inversion_scheme is True
    assert options.get_alphanumeric_commands() == ["SOLVE BAYES EQUATIONS", "USE (M+W) INVERSION SCHEME"]

    # Test special fitting options
    options = BayesSolutionOptions(use_least_squares_to_define_prior_parameter_covariance_matrix=True)
    assert options.use_least_squares_to_define_prior_parameter_covariance_matrix is True
    assert options.get_alphanumeric_commands() == [
        "SOLVE BAYES EQUATIONS",
        "LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE",
        "USE LEAST SQUARES TO DEFINE PRIOR PARAMETER COVARIANCE MATRIX",
    ]

    options = BayesSolutionOptions(take_baby_steps_with_least_squares_method=True)
    assert options.take_baby_steps_with_least_squares_method is True
    assert options.get_alphanumeric_commands() == [
        "SOLVE BAYES EQUATIONS",
        "LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE",
        "TAKE BABY STEPS WITH LEAST-SQUARES METHOD",
    ]

    options = BayesSolutionOptions(remember_original_parameter_values=True)
    assert options.remember_original_parameter_values is True
    assert options.get_alphanumeric_commands() == [
        "SOLVE BAYES EQUATIONS",
        "LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE",
        "REMEMBER ORIGINAL PARAMETER VALUES",
    ]

    options = BayesSolutionOptions(use_remembered_original_parameter_values=True)
    assert options.use_remembered_original_parameter_values is True
    assert options.get_alphanumeric_commands() == [
        "SOLVE BAYES EQUATIONS",
        "LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE",
        "USE REMEMBERED ORIGINAL PARAMETER VALUES",
    ]


if __name__ == "__main__":
    pytest.main()
