import pytest
from pleiades.sammy.alphanumerics.broad import BroadeningOptions

def test_default_option():
    """Test the default option."""
    options = BroadeningOptions()
    assert options.broadening_is_wanted is True
    assert options.broadening_is_not_wanted is False
    assert options.get_alphanumeric_commands() == ["BROADENING IS WANTED"]

def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    options = BroadeningOptions(broadening_is_not_wanted=True)
    assert options.broadening_is_wanted is False
    assert options.broadening_is_not_wanted is True
    assert options.get_alphanumeric_commands() == ["BROADENING IS NOT WANTED"]

def test_mutually_exclusive_options():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        BroadeningOptions(broadening_is_wanted=True, broadening_is_not_wanted=True)

def test_valid_combination_of_options():
    """Test a valid combination of options."""
    options = BroadeningOptions(broadening_is_not_wanted=True)
    assert options.broadening_is_wanted is False
    assert options.broadening_is_not_wanted is True
    assert options.get_alphanumeric_commands() == ["BROADENING IS NOT WANTED"]

def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        BroadeningOptions(
            broadening_is_wanted=True,
            broadening_is_not_wanted=True
        )

def test_switching_options():
    """Test switching options."""
    options = BroadeningOptions()
    assert options.broadening_is_wanted is True
    assert options.get_alphanumeric_commands() == ["BROADENING IS WANTED"]

    options = BroadeningOptions(broadening_is_not_wanted=True)
    assert options.broadening_is_not_wanted is True
    assert options.get_alphanumeric_commands() == ["BROADENING IS NOT WANTED"]

    options = BroadeningOptions(broadening_is_wanted=True)
    assert options.broadening_is_wanted is True
    assert options.get_alphanumeric_commands() == ["BROADENING IS WANTED"]

if __name__ == "__main__":
    pytest.main()