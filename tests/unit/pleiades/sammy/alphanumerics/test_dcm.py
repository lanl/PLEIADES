import pytest
from pleiades.sammy.alphanumerics.dcm import CovarianceMatrixOptions

def test_default_option():
    """Test the default option."""
    options = CovarianceMatrixOptions()
    assert options.implicit_data_covariance is False
    assert options.user_supplied_implicit_data_covariance is False
    assert options.pup_covariance_ascii is False
    assert options.create_pup_file is False
    assert options.add_constant_term is False
    assert options.do_not_add_constant_term is True
    assert options.use_default_constant_term is False
    assert options.use_ten_percent_uncertainty is False
    assert options.data_covariance_diagonal is True
    assert options.data_off_diagonal is False
    assert options.data_covariance_file is False
    assert options.free_format_data_covariance is False
    assert options.get_alphanumeric_commands() == ["DO NOT ADD CONSTANT TERM TO DATA COVARIANCE", "DATA COVARIANCE IS DIAGONAL"]

def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    options = CovarianceMatrixOptions(user_supplied_implicit_data_covariance=True)
    assert options.implicit_data_covariance is False
    assert options.user_supplied_implicit_data_covariance is True
    assert options.get_alphanumeric_commands() == ["USER SUPPLIED IMPLICIT DATA COVARIANCE MATRIX", "DO NOT ADD CONSTANT TERM TO DATA COVARIANCE", "DATA COVARIANCE IS DIAGONAL"]

def test_mutually_exclusive_options_1():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        CovarianceMatrixOptions(implicit_data_covariance=True, user_supplied_implicit_data_covariance=True)

def test_mutually_exclusive_options_2():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        CovarianceMatrixOptions(data_off_diagonal=True, data_covariance_file=True)

def test_valid_combination_of_options_1():
    """Test a valid combination of options."""
    options = CovarianceMatrixOptions(add_constant_term=True, data_off_diagonal=True)
    assert options.data_off_diagonal is True
    assert options.add_constant_term is True
    assert options.do_not_add_constant_term is False
    assert options.get_alphanumeric_commands() == ["ADD CONSTANT TERM TO DATA COVARIANCE", "DATA HAS OFF-DIAGONAL CONTRIBUTION TO COVARIANCE MATRIX OF THE FORM (A+BEI) (A+BEJ)"]

def test_valid_combination_of_options_2():
    """Test a valid combination of options."""
    options = CovarianceMatrixOptions(use_ten_percent_uncertainty=True, implicit_data_covariance=True)
    assert options.use_ten_percent_uncertainty is True
    assert options.implicit_data_covariance is True
    assert options.get_alphanumeric_commands() == ["IMPLICIT DATA COVARIANCE IS WANTED", "DO NOT ADD CONSTANT TERM TO DATA COVARIANCE", "USE TEN PERCENT DATA UNCERTAINTY OR ADD TEN PERCENT DATA UNCERTAINTY", "DATA COVARIANCE IS DIAGONAL"] 
    
def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        CovarianceMatrixOptions(
            implicit_data_covariance=True,
            user_supplied_implicit_data_covariance=True,
            pup_covariance_ascii=True
        )

def test_switching_options():
    """Test switching options."""
    options = CovarianceMatrixOptions()
    assert options.data_covariance_diagonal is True
    assert options.get_alphanumeric_commands() == ["DO NOT ADD CONSTANT TERM TO DATA COVARIANCE", "DATA COVARIANCE IS DIAGONAL"]

    options = CovarianceMatrixOptions(data_off_diagonal=True)
    assert options.data_off_diagonal is True
    assert options.get_alphanumeric_commands() == ["DO NOT ADD CONSTANT TERM TO DATA COVARIANCE", "DATA HAS OFF-DIAGONAL CONTRIBUTION TO COVARIANCE MATRIX OF THE FORM (A+BEI) (A+BEJ)"]

    options = CovarianceMatrixOptions(data_covariance_file=True)
    assert options.data_covariance_file is True
    assert options.get_alphanumeric_commands() == ["DO NOT ADD CONSTANT TERM TO DATA COVARIANCE", "DATA COVARIANCE FILE IS NAMED YYYYYY.YYY"]

    options = CovarianceMatrixOptions(free_format_data_covariance=True)
    assert options.free_format_data_covariance is True
    assert options.get_alphanumeric_commands() == ["DO NOT ADD CONSTANT TERM TO DATA COVARIANCE", "FREE FORMAT DATA COVARIANCE YYYYYY.YYY"]

if __name__ == "__main__":
    pytest.main()
