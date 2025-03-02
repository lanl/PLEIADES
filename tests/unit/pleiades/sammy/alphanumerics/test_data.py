import pytest
from pleiades.sammy.alphanumerics.data import ExperimentalDataInputOptions

def test_default_option():
    """Test the default option."""
    options = ExperimentalDataInputOptions()
    assert options.data_in_original_multi_style_format is True
    assert options.data_format_is_one_point_per_line is False
    assert options.use_csisrs_format_for_data is False
    assert options.use_twenty_significant_digits is False
    assert options.data_are_in_standard_odf_format is False
    assert options.data_are_in_odf_file is False
    assert options.data_are_endf_b_file is False
    assert options.use_endf_b_energies_and_data is False
    assert options.differential_data_are_in_ascii_file is False
    assert options.do_not_divide_data_into_regions is True
    assert options.divide_data_into_regions is False
    assert options.get_alphanumeric_commands() == ["DATA ARE IN ORIGINAL multi-style format", "DO NOT DIVIDE DATA Into regions"]

def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    options = ExperimentalDataInputOptions(data_format_is_one_point_per_line=True)
    assert options.data_in_original_multi_style_format is False
    assert options.data_format_is_one_point_per_line is True
    assert options.use_csisrs_format_for_data is False
    assert options.use_twenty_significant_digits is False
    assert options.data_are_in_standard_odf_format is False
    assert options.data_are_in_odf_file is False
    assert options.data_are_endf_b_file is False
    assert options.use_endf_b_energies_and_data is False
    assert options.differential_data_are_in_ascii_file is False
    assert options.do_not_divide_data_into_regions is True
    assert options.divide_data_into_regions is False
    assert options.get_alphanumeric_commands() == ["DATA FORMAT IS ONE Point per line", "DO NOT DIVIDE DATA Into regions"]

def test_mutually_exclusive_options():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        ExperimentalDataInputOptions(data_in_original_multi_style_format=True, data_format_is_one_point_per_line=True)

def test_valid_combination_of_options():
    """Test a valid combination of options."""
    options = ExperimentalDataInputOptions(data_are_in_standard_odf_format=True, divide_data_into_regions=True)
    assert options.data_in_original_multi_style_format is False
    assert options.data_format_is_one_point_per_line is False
    assert options.use_csisrs_format_for_data is False
    assert options.use_twenty_significant_digits is False
    assert options.data_are_in_standard_odf_format is True
    assert options.data_are_in_odf_file is False
    assert options.data_are_endf_b_file is False
    assert options.use_endf_b_energies_and_data is False
    assert options.differential_data_are_in_ascii_file is False
    assert options.do_not_divide_data_into_regions is False
    assert options.divide_data_into_regions is True
    assert options.get_alphanumeric_commands() == ["DATA ARE IN STANDARD odf format", "DIVIDE DATA INTO REGions with a fixed number of data points per region"]

def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        ExperimentalDataInputOptions(
            data_in_original_multi_style_format=True,
            data_format_is_one_point_per_line=True,
            use_csisrs_format_for_data=True
        )

def test_switching_options():
    """Test switching options."""
    options = ExperimentalDataInputOptions()
    assert options.data_in_original_multi_style_format is True
    assert options.get_alphanumeric_commands() == ["DATA ARE IN ORIGINAL multi-style format", "DO NOT DIVIDE DATA Into regions"]

    options = ExperimentalDataInputOptions(data_format_is_one_point_per_line=True)
    assert options.data_format_is_one_point_per_line is True
    assert options.get_alphanumeric_commands() == ["DATA FORMAT IS ONE Point per line", "DO NOT DIVIDE DATA Into regions"]

    options = ExperimentalDataInputOptions(use_csisrs_format_for_data=True)
    assert options.use_csisrs_format_for_data is True
    assert options.get_alphanumeric_commands() == ["USE CSISRS FORMAT For data", "DO NOT DIVIDE DATA Into regions"]

    options = ExperimentalDataInputOptions(use_twenty_significant_digits=True)
    assert options.use_twenty_significant_digits is True
    assert options.get_alphanumeric_commands() == ["USE TWENTY SIGNIFICANT digits", "DO NOT DIVIDE DATA Into regions"]

    options = ExperimentalDataInputOptions(data_are_in_standard_odf_format=True)
    assert options.data_are_in_standard_odf_format is True
    assert options.get_alphanumeric_commands() == ["DATA ARE IN STANDARD odf format", "DO NOT DIVIDE DATA Into regions"]

    options = ExperimentalDataInputOptions(data_are_in_odf_file=True)
    assert options.data_are_in_odf_file is True
    assert options.get_alphanumeric_commands() == ["DATA ARE IN ODF FILE", "DO NOT DIVIDE DATA Into regions"]

    options = ExperimentalDataInputOptions(data_are_endf_b_file=True)
    assert options.data_are_endf_b_file is True
    assert options.get_alphanumeric_commands() == ["DATA ARE ENDF/B FILE", "DO NOT DIVIDE DATA Into regions"]

    options = ExperimentalDataInputOptions(use_endf_b_energies_and_data=True)
    assert options.use_endf_b_energies_and_data is True
    assert options.get_alphanumeric_commands() == ["USE ENDF/B ENERGIES and data, with MAT=9999", "DO NOT DIVIDE DATA Into regions"]

    options = ExperimentalDataInputOptions(differential_data_are_in_ascii_file=True)
    assert options.differential_data_are_in_ascii_file is True
    assert options.get_alphanumeric_commands() == ["DATA ARE IN ORIGINAL multi-style format","DIFFERENTIAL DATA ARE in ascii file", "DO NOT DIVIDE DATA Into regions"]

    options = ExperimentalDataInputOptions(divide_data_into_regions=True)
    assert options.divide_data_into_regions is True
    assert options.get_alphanumeric_commands() == ["DATA ARE IN ORIGINAL multi-style format", "DIVIDE DATA INTO REGions with a fixed number of data points per region"]

if __name__ == "__main__":
    pytest.main()