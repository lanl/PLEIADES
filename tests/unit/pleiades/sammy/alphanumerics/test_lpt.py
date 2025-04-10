import pytest

from pleiades.sammy.alphanumerics.lpt import LPTOutputOptions


def test_default_option():
    """Test the default option."""
    options = LPTOutputOptions()
    assert options.do_not_print_any_input_parameters is True
    assert options.print_all_input_parameters is False
    assert options.print_varied_input_parameters is False
    assert options.do_not_print_input_data is True
    assert options.print_input_data is False
    assert options.do_not_print_theoretical_values is True
    assert options.print_theoretical_values is False
    assert options.do_not_print_partial_derivatives is True
    assert options.print_partial_derivatives is False
    assert options.suppress_intermediate_printout is False
    assert options.do_not_suppress_intermediate_printout is False
    assert options.do_not_suppress_any_intermediate_printout is True
    assert options.do_not_use_short_format_for_output is True
    assert options.use_short_format_for_output is False
    assert options.do_not_print_reduced_widths is True
    assert options.print_reduced_widths is False
    assert options.do_not_print_small_correlation_coefficients is False
    assert options.do_not_print_debug_info is True
    assert options.print_debug_information is False
    assert options.print_capture_area_in_lpt_file is False
    assert options.chi_squared_is_not_wanted is False
    assert options.chi_squared_is_wanted is True
    assert options.do_not_print_weighted_residuals is True
    assert options.print_weighted_residuals is False
    assert options.print_bayes_weighted_residuals is False
    assert options.do_not_print_bayes_weighted_residuals is True
    assert options.do_not_print_phase_shifts is True
    assert options.print_phase_shifts_for_input_parameters is False
    assert options.get_alphanumeric_commands() == [
        "DO NOT PRINT ANY INPUT PARAMETERS",
        "DO NOT PRINT INPUT DATA",
        "DO NOT PRINT THEORETICAL VALUES",
        "DO NOT PRINT PARTIAL DERIVATIVES",
        "DO NOT SUPPRESS ANY INTERMEDIATE PRINTOUT",
        "DO NOT USE SHORT FORMAT FOR OUTPUT",
        "DO NOT PRINT REDUCED WIDTHS",
        "DO NOT PRINT DEBUG INFO",
        "CHI SQUARED IS WANTED",
        "DO NOT PRINT WEIGHTED RESIDUALS",
        "DO NOT PRINT BAYES WEIGHTED RESIDUALS",
        "DO NOT PRINT PHASE SHIFTS",
    ]


def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    options = LPTOutputOptions(print_all_input_parameters=True)
    assert options.do_not_print_any_input_parameters is False
    assert options.print_all_input_parameters is True
    assert options.get_alphanumeric_commands() == [
        "PRINT ALL INPUT PARAMETERS",
        "DO NOT PRINT INPUT DATA",
        "DO NOT PRINT THEORETICAL VALUES",
        "DO NOT PRINT PARTIAL DERIVATIVES",
        "DO NOT SUPPRESS ANY INTERMEDIATE PRINTOUT",
        "DO NOT USE SHORT FORMAT FOR OUTPUT",
        "DO NOT PRINT REDUCED WIDTHS",
        "DO NOT PRINT DEBUG INFO",
        "CHI SQUARED IS WANTED",
        "DO NOT PRINT WEIGHTED RESIDUALS",
        "DO NOT PRINT BAYES WEIGHTED RESIDUALS",
        "DO NOT PRINT PHASE SHIFTS",
    ]


def test_mutually_exclusive_options_1():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        LPTOutputOptions(do_not_print_any_input_parameters=True, print_all_input_parameters=True)


def test_mutually_exclusive_options_2():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        LPTOutputOptions(do_not_print_input_data=True, print_input_data=True)


def test_valid_combination_of_options_1():
    """Test a valid combination of options."""
    options = LPTOutputOptions(print_all_input_parameters=True, print_input_data=True)
    assert options.do_not_print_any_input_parameters is False
    assert options.print_all_input_parameters is True
    assert options.print_input_data is True
    assert options.get_alphanumeric_commands() == [
        "PRINT ALL INPUT PARAMETERS",
        "PRINT INPUT DATA",
        "DO NOT PRINT THEORETICAL VALUES",
        "DO NOT PRINT PARTIAL DERIVATIVES",
        "DO NOT SUPPRESS ANY INTERMEDIATE PRINTOUT",
        "DO NOT USE SHORT FORMAT FOR OUTPUT",
        "DO NOT PRINT REDUCED WIDTHS",
        "DO NOT PRINT DEBUG INFO",
        "CHI SQUARED IS WANTED",
        "DO NOT PRINT WEIGHTED RESIDUALS",
        "DO NOT PRINT BAYES WEIGHTED RESIDUALS",
        "DO NOT PRINT PHASE SHIFTS",
    ]


def test_valid_combination_of_options_2():
    """Test a valid combination of options."""
    options = LPTOutputOptions(print_theoretical_values=True, print_partial_derivatives=True)
    assert options.do_not_print_theoretical_values is False
    assert options.print_theoretical_values is True
    assert options.print_partial_derivatives is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT PRINT ANY INPUT PARAMETERS",
        "DO NOT PRINT INPUT DATA",
        "PRINT THEORETICAL VALUES",
        "PRINT PARTIAL DERIVATIVES",
        "DO NOT SUPPRESS ANY INTERMEDIATE PRINTOUT",
        "DO NOT USE SHORT FORMAT FOR OUTPUT",
        "DO NOT PRINT REDUCED WIDTHS",
        "DO NOT PRINT DEBUG INFO",
        "CHI SQUARED IS WANTED",
        "DO NOT PRINT WEIGHTED RESIDUALS",
        "DO NOT PRINT BAYES WEIGHTED RESIDUALS",
        "DO NOT PRINT PHASE SHIFTS",
    ]


def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        LPTOutputOptions(do_not_print_any_input_parameters=True, print_all_input_parameters=True, print_varied_input_parameters=True)


def test_switching_options():
    """Test switching options."""
    options = LPTOutputOptions()
    assert options.do_not_print_any_input_parameters is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT PRINT ANY INPUT PARAMETERS",
        "DO NOT PRINT INPUT DATA",
        "DO NOT PRINT THEORETICAL VALUES",
        "DO NOT PRINT PARTIAL DERIVATIVES",
        "DO NOT SUPPRESS ANY INTERMEDIATE PRINTOUT",
        "DO NOT USE SHORT FORMAT FOR OUTPUT",
        "DO NOT PRINT REDUCED WIDTHS",
        "DO NOT PRINT DEBUG INFO",
        "CHI SQUARED IS WANTED",
        "DO NOT PRINT WEIGHTED RESIDUALS",
        "DO NOT PRINT BAYES WEIGHTED RESIDUALS",
        "DO NOT PRINT PHASE SHIFTS",
    ]

    options = LPTOutputOptions(print_all_input_parameters=True)
    assert options.print_all_input_parameters is True
    assert options.get_alphanumeric_commands() == [
        "PRINT ALL INPUT PARAMETERS",
        "DO NOT PRINT INPUT DATA",
        "DO NOT PRINT THEORETICAL VALUES",
        "DO NOT PRINT PARTIAL DERIVATIVES",
        "DO NOT SUPPRESS ANY INTERMEDIATE PRINTOUT",
        "DO NOT USE SHORT FORMAT FOR OUTPUT",
        "DO NOT PRINT REDUCED WIDTHS",
        "DO NOT PRINT DEBUG INFO",
        "CHI SQUARED IS WANTED",
        "DO NOT PRINT WEIGHTED RESIDUALS",
        "DO NOT PRINT BAYES WEIGHTED RESIDUALS",
        "DO NOT PRINT PHASE SHIFTS",
    ]

    options = LPTOutputOptions(print_input_data=True)
    assert options.print_input_data is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT PRINT ANY INPUT PARAMETERS",
        "PRINT INPUT DATA",
        "DO NOT PRINT THEORETICAL VALUES",
        "DO NOT PRINT PARTIAL DERIVATIVES",
        "DO NOT SUPPRESS ANY INTERMEDIATE PRINTOUT",
        "DO NOT USE SHORT FORMAT FOR OUTPUT",
        "DO NOT PRINT REDUCED WIDTHS",
        "DO NOT PRINT DEBUG INFO",
        "CHI SQUARED IS WANTED",
        "DO NOT PRINT WEIGHTED RESIDUALS",
        "DO NOT PRINT BAYES WEIGHTED RESIDUALS",
        "DO NOT PRINT PHASE SHIFTS",
    ]


if __name__ == "__main__":
    pytest.main()
