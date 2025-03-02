import pytest
from pleiades.sammy.alphanumerics.msc import MultipleScatteringCorrectionsOptions

def test_default_option():
    """Test the default option."""
    options = MultipleScatteringCorrectionsOptions()
    assert options.do_not_include_self_shielding is True
    assert options.use_self_shielding_only is False
    assert options.use_single_scattering_plus_self_shielding is False
    assert options.include_double_scattering_corrections is False
    assert options.infinite_slab is False
    assert options.finite_slab is True
    assert options.make_new_file_with_edge_effects is True
    assert options.file_with_edge_effects_already_exists is False
    assert options.make_plot_file_of_multiple_scattering_pieces is False
    assert options.normalize_as_cross_section is False
    assert options.normalize_as_yield is False
    assert options.normalize_as_1_minus_e_sigma is False
    assert options.print_multiple_scattering_corrections is False
    assert options.prepare_input_for_monte_carlo_simulation is False
    assert options.y2_values_are_tabulated is False
    assert options.use_quadratic_interpolation_for_y1 is False
    assert options.use_linear_interpolation_for_y1 is False
    assert options.version_7_for_multiple_scattering is False
    assert options.do_not_calculate_y0 is False
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects"
    ]

def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    options = MultipleScatteringCorrectionsOptions(use_self_shielding_only=True)
    assert options.do_not_include_self_shielding is False
    assert options.use_self_shielding_only is True
    assert options.use_single_scattering_plus_self_shielding is False
    assert options.include_double_scattering_corrections is False
    assert options.get_alphanumeric_commands() == [
        "USE SELF SHIELDING Only no scattering",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects"
    ]

def test_mutually_exclusive_options():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        MultipleScatteringCorrectionsOptions(do_not_include_self_shielding=True, use_self_shielding_only=True)

def test_valid_combination_of_options():
    """Test a valid combination of options."""
    options = MultipleScatteringCorrectionsOptions(normalize_as_yield=True)
    assert options.normalize_as_cross_section is False
    assert options.normalize_as_yield is True
    assert options.normalize_as_1_minus_e_sigma is False
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects",
        "NORMALIZE AS YIELD Rather than cross section"
    ]

def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        MultipleScatteringCorrectionsOptions(
            do_not_include_self_shielding=True,
            use_self_shielding_only=True,
            use_single_scattering_plus_self_shielding=True
        )

def test_switching_options():
    """Test switching options."""
    options = MultipleScatteringCorrectionsOptions()
    assert options.do_not_include_self_shielding is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects"
    ]

    options = MultipleScatteringCorrectionsOptions(use_self_shielding_only=True)
    assert options.use_self_shielding_only is True
    assert options.get_alphanumeric_commands() == [
        "USE SELF SHIELDING Only no scattering",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects"
    ]

    options = MultipleScatteringCorrectionsOptions(use_single_scattering_plus_self_shielding=True)
    assert options.use_single_scattering_plus_self_shielding is True
    assert options.get_alphanumeric_commands() == [
        "USE SINGLE SCATTERINg plus self shielding",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects"
    ]

    options = MultipleScatteringCorrectionsOptions(include_double_scattering_corrections=True)
    assert options.include_double_scattering_corrections is True
    assert options.get_alphanumeric_commands() == [
        "INCLUDE DOUBLE SCATTering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects"
    ]

    options = MultipleScatteringCorrectionsOptions(infinite_slab=True)
    assert options.infinite_slab is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "INFINITE SLAB",
        "MAKE NEW FILE WITH Edge effects"
    ]

    options = MultipleScatteringCorrectionsOptions(file_with_edge_effects_already_exists=True)
    assert options.file_with_edge_effects_already_exists is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "FILE WITH EDGE EFFECts already exists"
    ]

    options = MultipleScatteringCorrectionsOptions(normalize_as_cross_section=True)
    assert options.normalize_as_cross_section is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects",
        "NORMALIZE AS CROSS Section rather than yield"
    ]

    options = MultipleScatteringCorrectionsOptions(normalize_as_yield=True)
    assert options.normalize_as_yield is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects",
        "NORMALIZE AS YIELD Rather than cross section"
    ]

    options = MultipleScatteringCorrectionsOptions(normalize_as_1_minus_e_sigma=True)
    assert options.normalize_as_1_minus_e_sigma is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects",
        "NORMALIZE AS (1-E)SIgma"
    ]

    options = MultipleScatteringCorrectionsOptions(use_quadratic_interpolation_for_y1=True)
    assert options.use_quadratic_interpolation_for_y1 is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects",
        "USE QUADRATIC INTERPolation for y1"
    ]

    options = MultipleScatteringCorrectionsOptions(use_linear_interpolation_for_y1=True)
    assert options.use_linear_interpolation_for_y1 is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects",
        "USE LINEAR INTERPOLAtion for y1"
    ]

    options = MultipleScatteringCorrectionsOptions(version_7_for_multiple_scattering=True)
    assert options.version_7_for_multiple_scattering is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects",
        "VERSION 7.0.0 FOR Multiple scattering"
    ]

    options = MultipleScatteringCorrectionsOptions(do_not_calculate_y0=True)
    assert options.do_not_calculate_y0 is True
    assert options.get_alphanumeric_commands() == [
        "DO NOT INCLUDE SELF-shielding multiple-scattering corrections",
        "FINITE SLAB",
        "MAKE NEW FILE WITH Edge effects",
        "DO NOT CALCULATE Y0"
    ]

if __name__ == "__main__":
    pytest.main()