import pytest

from pleiades.sammy.alphanumerics.urr import URROptions


def test_default_options():
    """Test the default options."""
    urr_options = URROptions()
    # Check default values
    assert urr_options.unresolved_resonance_region is False
    assert urr_options.experimental_data_are_in_separate_files is False
    assert urr_options.no_annotated_parameter_file_for_urr_input is False
    assert urr_options.annotated_parameter_file_for_urr is True  # Default
    assert urr_options.output_in_annotated_parameter_file_for_urr is True  # Default (always true)
    assert urr_options.use_all_experimental_data_points is True  # Default for URR
    assert urr_options.use_energy_limits_as_given_in_the_input_file is False
    assert urr_options.calculate_width_fluctuation_factors_more_accurately is False
    assert urr_options.moldauer_prescription_is_to_be_used is False

    # Check default alphanumeric commands - should only include defaults that are True
    commands = urr_options.get_alphanumeric_commands()
    assert "ANNOTATED PARAMETER FILE FOR URR" in commands
    assert "USE ALL EXPERIMENTAL DATA POINTS" in commands
    assert "OUTPUT IN ANNOTATED PARAMETER FILE FOR URR" in commands
    assert len(commands) == 3


def test_urr_mode_basic():
    """Test basic URR mode."""
    urr_options = URROptions(unresolved_resonance_region=True)
    assert urr_options.unresolved_resonance_region is True
    commands = urr_options.get_alphanumeric_commands()
    assert "UNRESOLVED RESONANCE REGION" in commands
    assert "ANNOTATED PARAMETER FILE FOR URR" in commands
    assert "USE ALL EXPERIMENTAL DATA POINTS" in commands
    assert "OUTPUT IN ANNOTATED PARAMETER FILE FOR URR" in commands
    assert len(commands) == 4


def test_data_file_options():
    """Test experimental data file options."""
    urr_options = URROptions(experimental_data_are_in_separate_files=True)
    assert urr_options.experimental_data_are_in_separate_files is True
    assert "EXPERIMENTAL DATA ARE IN SEPARATE FILES" in urr_options.get_alphanumeric_commands()


def test_parameter_file_format_options():
    """Test parameter file format options."""
    # Test no annotated parameter file
    urr_options = URROptions(no_annotated_parameter_file_for_urr_input=True, annotated_parameter_file_for_urr=False)
    assert urr_options.no_annotated_parameter_file_for_urr_input is True
    assert urr_options.annotated_parameter_file_for_urr is False
    commands = urr_options.get_alphanumeric_commands()
    assert "NO ANNOTATED PARAMETER FILE FOR URR INPUT" in commands
    assert "ANNOTATED PARAMETER FILE FOR URR" not in commands
    assert "OUTPUT IN ANNOTATED PARAMETER FILE FOR URR" in commands

    # Test annotated parameter file (default)
    urr_options = URROptions(no_annotated_parameter_file_for_urr_input=False, annotated_parameter_file_for_urr=True)
    assert urr_options.no_annotated_parameter_file_for_urr_input is False
    assert urr_options.annotated_parameter_file_for_urr is True
    commands = urr_options.get_alphanumeric_commands()
    assert "NO ANNOTATED PARAMETER FILE FOR URR INPUT" not in commands
    assert "ANNOTATED PARAMETER FILE FOR URR" in commands
    assert "OUTPUT IN ANNOTATED PARAMETER FILE FOR URR" in commands


def test_mutually_exclusive_parameter_file_format():
    """Test mutually exclusive parameter file format options."""
    # Both no_annotated and annotated set to True should raise error
    with pytest.raises(ValueError):
        URROptions(no_annotated_parameter_file_for_urr_input=True, annotated_parameter_file_for_urr=True)


def test_data_point_selection_options():
    """Test data point selection options."""
    # Test use all experimental data points (default)
    urr_options = URROptions(use_all_experimental_data_points=True, use_energy_limits_as_given_in_the_input_file=False)
    assert urr_options.use_all_experimental_data_points is True
    assert urr_options.use_energy_limits_as_given_in_the_input_file is False
    commands = urr_options.get_alphanumeric_commands()
    assert "USE ALL EXPERIMENTAL DATA POINTS" in commands
    assert "USE ENERGY LIMITS AS GIVEN IN THE INPUT FILE" not in commands

    # Test use energy limits
    urr_options = URROptions(use_all_experimental_data_points=False, use_energy_limits_as_given_in_the_input_file=True)
    assert urr_options.use_all_experimental_data_points is False
    assert urr_options.use_energy_limits_as_given_in_the_input_file is True
    commands = urr_options.get_alphanumeric_commands()
    assert "USE ALL EXPERIMENTAL DATA POINTS" not in commands
    assert "USE ENERGY LIMITS AS GIVEN IN THE INPUT FILE" in commands


def test_mutually_exclusive_data_point_selection():
    """Test mutually exclusive data point selection options."""
    # Both use_all_experimental and use_energy_limits set to True should raise error
    with pytest.raises(ValueError):
        URROptions(use_all_experimental_data_points=True, use_energy_limits_as_given_in_the_input_file=True)


def test_calculation_options():
    """Test calculation options."""
    # Test calculate width fluctuation factors more accurately
    urr_options = URROptions(calculate_width_fluctuation_factors_more_accurately=True)
    assert urr_options.calculate_width_fluctuation_factors_more_accurately is True
    assert "CALCULATE WIDTH FLUCTUATION FACTORS MORE ACCURATELY" in urr_options.get_alphanumeric_commands()

    # Test Moldauer prescription
    urr_options = URROptions(moldauer_prescription_is_to_be_used=True)
    assert urr_options.moldauer_prescription_is_to_be_used is True
    assert "MOLDAUER PRESCRIPTION IS TO BE USED" in urr_options.get_alphanumeric_commands()


def test_all_non_conflicting_options():
    """Test setting multiple non-conflicting options."""
    urr_options = URROptions(
        unresolved_resonance_region=True,
        experimental_data_are_in_separate_files=True,
        no_annotated_parameter_file_for_urr_input=True,
        annotated_parameter_file_for_urr=False,
        output_in_annotated_parameter_file_for_urr=True,
        use_all_experimental_data_points=False,
        use_energy_limits_as_given_in_the_input_file=True,
        calculate_width_fluctuation_factors_more_accurately=True,
        moldauer_prescription_is_to_be_used=True,
    )

    commands = urr_options.get_alphanumeric_commands()
    assert "UNRESOLVED RESONANCE REGION" in commands
    assert "EXPERIMENTAL DATA ARE IN SEPARATE FILES" in commands
    assert "NO ANNOTATED PARAMETER FILE FOR URR INPUT" in commands
    assert "OUTPUT IN ANNOTATED PARAMETER FILE FOR URR" in commands
    assert "USE ENERGY LIMITS AS GIVEN IN THE INPUT FILE" in commands
    assert "CALCULATE WIDTH FLUCTUATION FACTORS MORE ACCURATELY" in commands
    assert "MOLDAUER PRESCRIPTION IS TO BE USED" in commands
    assert len(commands) == 7


if __name__ == "__main__":
    pytest.main()
