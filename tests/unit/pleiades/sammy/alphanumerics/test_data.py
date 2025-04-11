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
    assert options.get_alphanumeric_commands() == ["DATA ARE IN ORIGINAL MULTI-STYLE FORMAT", "DO NOT DIVIDE DATA INTO REGIONS"]


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
    assert options.get_alphanumeric_commands() == ["DATA FORMAT IS ONE POINT PER LINE", "DO NOT DIVIDE DATA INTO REGIONS"]


def test_mutually_exclusive_options_1():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        ExperimentalDataInputOptions(data_in_original_multi_style_format=True, data_format_is_one_point_per_line=True)


def test_mutually_exclusive_options_2():
    with pytest.raises(ValueError):
        ExperimentalDataInputOptions(do_not_divide_data_into_regions=True, divide_data_into_regions=True)


def test_valid_combination_of_options_1():
    """Test a valid combination of options."""
    options = ExperimentalDataInputOptions(divide_data_into_regions=True, use_twenty_significant_digits=True)
    assert options.data_in_original_multi_style_format is False
    assert options.data_format_is_one_point_per_line is False
    assert options.use_csisrs_format_for_data is False
    assert options.use_twenty_significant_digits is True
    assert options.data_are_in_standard_odf_format is False
    assert options.data_are_in_odf_file is False
    assert options.data_are_endf_b_file is False
    assert options.use_endf_b_energies_and_data is False
    assert options.differential_data_are_in_ascii_file is False
    assert options.do_not_divide_data_into_regions is False
    assert options.divide_data_into_regions is True
    assert options.get_alphanumeric_commands() == [
        "USE TWENTY SIGNIFICANT DIGITS",
        "DIVIDE DATA INTO REGIONS WITH A FIXED NUMBER OF DATA POINTS PER REGION",
    ]


def test_valid_combination_of_options_2():
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
    assert options.get_alphanumeric_commands() == [
        "DATA ARE IN STANDARD ODF FORMAT",
        "DIVIDE DATA INTO REGIONS WITH A FIXED NUMBER OF DATA POINTS PER REGION",
    ]


def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        ExperimentalDataInputOptions(
            data_in_original_multi_style_format=True, data_format_is_one_point_per_line=True, use_csisrs_format_for_data=True
        )


def test_switching_options():
    """Test switching options."""
    options = ExperimentalDataInputOptions()
    assert options.data_in_original_multi_style_format is True
    assert options.get_alphanumeric_commands() == ["DATA ARE IN ORIGINAL MULTI-STYLE FORMAT", "DO NOT DIVIDE DATA INTO REGIONS"]

    options = ExperimentalDataInputOptions(data_format_is_one_point_per_line=True)
    assert options.data_format_is_one_point_per_line is True
    assert options.get_alphanumeric_commands() == ["DATA FORMAT IS ONE POINT PER LINE", "DO NOT DIVIDE DATA INTO REGIONS"]

    options = ExperimentalDataInputOptions(use_csisrs_format_for_data=True)
    assert options.use_csisrs_format_for_data is True
    assert options.get_alphanumeric_commands() == ["USE CSISRS FORMAT FOR DATA", "DO NOT DIVIDE DATA INTO REGIONS"]

    options = ExperimentalDataInputOptions(use_twenty_significant_digits=True)
    assert options.use_twenty_significant_digits is True
    assert options.get_alphanumeric_commands() == ["USE TWENTY SIGNIFICANT DIGITS", "DO NOT DIVIDE DATA INTO REGIONS"]

    options = ExperimentalDataInputOptions(data_are_in_standard_odf_format=True)
    assert options.data_are_in_standard_odf_format is True
    assert options.get_alphanumeric_commands() == ["DATA ARE IN STANDARD ODF FORMAT", "DO NOT DIVIDE DATA INTO REGIONS"]

    options = ExperimentalDataInputOptions(data_are_in_odf_file=True)
    assert options.data_are_in_odf_file is True
    assert options.get_alphanumeric_commands() == ["DATA ARE IN ODF FILE", "DO NOT DIVIDE DATA INTO REGIONS"]

    options = ExperimentalDataInputOptions(data_are_endf_b_file=True)
    assert options.data_are_endf_b_file is True
    assert options.get_alphanumeric_commands() == ["DATA ARE ENDF/B FILE", "DO NOT DIVIDE DATA INTO REGIONS"]

    options = ExperimentalDataInputOptions(use_endf_b_energies_and_data=True)
    assert options.use_endf_b_energies_and_data is True
    assert options.get_alphanumeric_commands() == ["USE ENDF/B ENERGIES AND DATA, WITH MAT=9999", "DO NOT DIVIDE DATA INTO REGIONS"]

    options = ExperimentalDataInputOptions(differential_data_are_in_ascii_file=True)
    assert options.differential_data_are_in_ascii_file is True
    assert options.get_alphanumeric_commands() == [
        "DATA ARE IN ORIGINAL MULTI-STYLE FORMAT",
        "DIFFERENTIAL DATA ARE IN ASCII FILE",
        "DO NOT DIVIDE DATA INTO REGIONS",
    ]

    options = ExperimentalDataInputOptions(divide_data_into_regions=True)
    assert options.divide_data_into_regions is True
    assert options.get_alphanumeric_commands() == [
        "DATA ARE IN ORIGINAL MULTI-STYLE FORMAT",
        "DIVIDE DATA INTO REGIONS WITH A FIXED NUMBER OF DATA POINTS PER REGION",
    ]


if __name__ == "__main__":
    pytest.main()
