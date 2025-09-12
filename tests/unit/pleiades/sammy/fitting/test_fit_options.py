import pytest

from pleiades.sammy.alphanumerics import (
    BayesSolutionOptions,
    BroadeningOptions,
    ENDFOptions,
    ExperimentalDataInputOptions,
    LPTOutputOptions,
    QuantumNumbersOptions,
    RMatrixOptions,
)
from pleiades.sammy.fitting.options import FitOptions


def test_fit_options_defaults():
    """Test that FitOptions initializes with proper default values."""
    fit_options = FitOptions()

    # Check that all required component options are initialized
    assert isinstance(fit_options.r_matrix, RMatrixOptions)
    assert isinstance(fit_options.quantum_numbers, QuantumNumbersOptions)
    assert isinstance(fit_options.experimental_data, ExperimentalDataInputOptions)
    assert isinstance(fit_options.broadening, BroadeningOptions)
    assert isinstance(fit_options.endf, ENDFOptions)
    assert isinstance(fit_options.bayes_solution, BayesSolutionOptions)
    assert isinstance(fit_options.lpt_output, LPTOutputOptions)

    # Check default values for common options
    assert fit_options.r_matrix.reich_moore is True  # Default R-matrix option
    assert fit_options.bayes_solution.solve_bayes_equations is True  # Default is to solve Bayes
    assert fit_options.broadening.broadening_is_wanted is True  # Default is to apply broadening


def test_fit_options_custom_values():
    """Test that FitOptions can be initialized with custom values."""
    # Create options with custom components
    custom_r_matrix = RMatrixOptions(reich_moore=False, original_reich_moore=True)
    custom_quantum_numbers = QuantumNumbersOptions(
        quantum_numbers_in_parameter_file=False, put_quantum_numbers_into_parameter_file=True
    )
    custom_data = ExperimentalDataInputOptions(data_are_endf_b_file=True)
    custom_broadening = BroadeningOptions(broadening_is_wanted=False)
    custom_bayes = BayesSolutionOptions(solve_bayes_equations=False)

    # Create FitOptions with custom components
    fit_options = FitOptions(
        r_matrix=custom_r_matrix,
        quantum_numbers=custom_quantum_numbers,
        experimental_data=custom_data,
        broadening=custom_broadening,
        bayes_solution=custom_bayes,
    )

    # Verify custom values were applied
    assert fit_options.r_matrix.reich_moore is False
    assert fit_options.r_matrix.original_reich_moore is True
    assert fit_options.quantum_numbers.quantum_numbers_in_parameter_file is False
    assert fit_options.quantum_numbers.put_quantum_numbers_into_parameter_file is True
    assert fit_options.experimental_data.data_are_endf_b_file is True
    assert fit_options.broadening.broadening_is_wanted is False
    assert fit_options.bayes_solution.solve_bayes_equations is False


def test_get_alphanumeric_commands():
    """Test that FitOptions can generate alphanumeric commands."""
    # Create options with specific settings that generate commands
    r_matrix = RMatrixOptions(reich_moore=True)
    bayes = BayesSolutionOptions(solve_bayes_equations=True)

    fit_options = FitOptions(
        r_matrix=r_matrix,
        bayes_solution=bayes,
    )

    # Get commands
    commands = fit_options.get_alphanumeric_commands()

    # Verify we get expected commands
    assert isinstance(commands, list)
    assert len(commands) > 0
    assert "REICH-MOORE FORMALISM IS WANTED" in commands
    assert "SOLVE BAYES EQUATIONS" in commands


def test_from_endf_config():
    """Test the factory method that creates FitOptions for ENDF extraction."""
    fit_options = FitOptions.from_endf_config()

    # Verify ENDF mode settings
    assert fit_options.quantum_numbers.put_quantum_numbers_into_parameter_file is True
    assert fit_options.endf.input_is_endf_file_2 is True  # Notice the correct attribute name
    assert fit_options.experimental_data.data_are_endf_b_file is True
    assert fit_options.bayes_solution.solve_bayes_equations is False

    # Check generated commands
    commands = fit_options.get_alphanumeric_commands()
    assert "PUT QUANTUM NUMBERS into parameter file" in commands
    assert "INPUT IS ENDF/B FILE 2" in commands
    assert "DATA ARE ENDF/B FILE" in commands
    assert "DO NOT SOLVE BAYES EQUATIONS" in commands


def test_from_fitting_config():
    """Test the factory method that creates FitOptions for Bayesian fitting."""
    fit_options = FitOptions.from_fitting_config()

    # Verify fitting mode settings
    assert fit_options.r_matrix.reich_moore is True
    assert fit_options.quantum_numbers.keyword_particle_pair_definitions is True
    assert fit_options.quantum_numbers.quantum_numbers_in_parameter_file is True
    assert fit_options.experimental_data.use_twenty_significant_digits is True
    assert fit_options.broadening.broadening_is_wanted is True
    assert fit_options.bayes_solution.solve_bayes_equations is True
    assert fit_options.lpt_output.chi_squared_is_wanted is True

    # Check generated commands
    commands = fit_options.get_alphanumeric_commands()
    assert "REICH-MOORE FORMALISM IS WANTED" in commands
    assert "KEY-WORD PARTICLE-PAir definitions are given" in commands
    assert "QUANTUM NUMBERS ARE in parameter file" in commands
    assert "USE TWENTY SIGNIFICANT DIGITS" in commands
    assert "BROADENING IS WANTED" in commands
    assert "SOLVE BAYES EQUATIONS" in commands
    assert "CHI SQUARED IS WANTED" in commands


def test_from_custom_config():
    """Test the factory method that creates FitOptions with custom settings."""
    # Create custom components to pass to factory method
    custom_r_matrix = RMatrixOptions(reich_moore=False, original_reich_moore=True)
    custom_bayes = BayesSolutionOptions(solve_bayes_equations=False, do_not_solve_bayes_equations=True)

    # Use factory method with custom components
    fit_options = FitOptions.from_custom_config(
        r_matrix=custom_r_matrix,
        bayes_solution=custom_bayes,
    )

    # Verify custom settings
    assert fit_options.r_matrix.reich_moore is False
    assert fit_options.r_matrix.original_reich_moore is True
    assert fit_options.bayes_solution.solve_bayes_equations is False

    # Check generated commands
    commands = fit_options.get_alphanumeric_commands()
    assert "ORIGINAL REICH-MOORE FORMALISM" in commands
    assert "DO NOT SOLVE BAYES EQUATIONS" in commands


def test_from_multi_isotope_config():
    """Test the factory method that creates FitOptions for multi-isotope JSON mode fitting."""
    fit_options = FitOptions.from_multi_isotope_config()

    # Verify multi-isotope mode settings (updated per SAMMY expert recommendations)
    assert fit_options.endf.input_is_endf_file_2 is True
    assert fit_options.endf.use_energy_range_from_endf_file_2 is False  # Removed per expert recommendation
    assert fit_options.experimental_data.use_twenty_significant_digits is True
    assert fit_options.broadening.broadening_is_wanted is True
    assert fit_options.bayes_solution.solve_bayes_equations is True
    assert fit_options.lpt_output.chi_squared_is_wanted is True

    # Check generated commands for multi-isotope mode (essential commands only per expert)
    commands = fit_options.get_alphanumeric_commands()

    # Essential commands that expert recommended to keep
    essential_commands = [
        "REICH-MOORE FORMALISM IS WANTED",
        "USE NEW SPIN GROUP Format",
        "USE TWENTY SIGNIFICANT DIGITS",
        "BROADENING IS WANTED",
        "INPUT IS ENDF/B FILE 2",
        "SOLVE BAYES EQUATIONS",
        "CHI SQUARED IS WANTED",
    ]

    for cmd in essential_commands:
        assert cmd in commands, f"Essential command missing: {cmd}"

    # Commands that expert specifically marked for removal should NOT be present
    removed_commands = [
        "USE ENERGY RANGE FROM ENDF/B FILE 2",  # Expert marked for removal
        "DO NOT DIVIDE DATA INTO REGIONS",  # Expert marked for removal
        "LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE",  # Expert marked for removal
    ]

    for cmd in removed_commands:
        assert cmd not in commands, f"Command should be removed per expert: {cmd}"


def test_mutually_exclusive_options():
    """Test that mutually exclusive options are handled correctly."""
    # Create RMatrixOptions with mutually exclusive options
    # This should raise a ValueError
    with pytest.raises(ValueError):
        RMatrixOptions(reich_moore=True, original_reich_moore=True)

    # Similar test for BroadeningOptions
    with pytest.raises(ValueError):
        BroadeningOptions(broadening_is_wanted=True, broadening_is_not_wanted=True)

    # We need to test mutually exclusive options in BayesSolutionOptions.
    # Since in BayesSolutionOptions, solve_bayes_equations is a boolean,
    # we'll need to check a different mutually exclusive option pair.
    # Use any other mutually exclusive pair from BayesSolutionOptions
    with pytest.raises(ValueError):
        BayesSolutionOptions(use_npv_inversion_scheme=True, use_ipq_inversion_scheme=True)


if __name__ == "__main__":
    pytest.main()
