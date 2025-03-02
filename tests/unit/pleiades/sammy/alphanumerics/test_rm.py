import pytest
from pleiades.sammy.alphanumerics.rm import RMatrixOptions

def test_default_option():
    """Test the default option."""
    r_matrix_options = RMatrixOptions()
    assert r_matrix_options.reich_moore is True
    assert r_matrix_options.original_reich_moore is False
    assert r_matrix_options.multilevel_breit_wigner is False
    assert r_matrix_options.single_level_breit_wigner is False
    assert r_matrix_options.reduced_width_amplitudes is False
    assert r_matrix_options.get_alphanumeric_commands() == ["REICH-MOORE FORMALISM IS WANTED"]

def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    r_matrix_options = RMatrixOptions(original_reich_moore=True)
    assert r_matrix_options.reich_moore is False
    assert r_matrix_options.original_reich_moore is True
    assert r_matrix_options.multilevel_breit_wigner is False
    assert r_matrix_options.single_level_breit_wigner is False
    assert r_matrix_options.reduced_width_amplitudes is False
    assert r_matrix_options.get_alphanumeric_commands() == ["ORIGINAL REICH-MOORE FORMALISM"]

def test_mutually_exclusive_options():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        RMatrixOptions(reich_moore=True, original_reich_moore=True)

def test_valid_combination_of_options():
    """Test a valid combination of options."""
    r_matrix_options = RMatrixOptions(reduced_width_amplitudes=True)
    assert r_matrix_options.reich_moore is False
    assert r_matrix_options.original_reich_moore is False
    assert r_matrix_options.multilevel_breit_wigner is False
    assert r_matrix_options.single_level_breit_wigner is False
    assert r_matrix_options.reduced_width_amplitudes is True
    assert r_matrix_options.get_alphanumeric_commands() == ["REDUCED WIDTH AMPLITUDES ARE USED FOR INPUT"]

def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        RMatrixOptions(
            reich_moore=True,
            original_reich_moore=True,
            multilevel_breit_wigner=True
        )

if __name__ == "__main__":
    pytest.main()