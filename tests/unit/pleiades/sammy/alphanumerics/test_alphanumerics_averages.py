import pytest

from pleiades.sammy.alphanumerics.averages import AveragesOptions


def test_default_options():
    """Test the default options."""
    averages_options = AveragesOptions()

    # Check default values
    assert averages_options.average_over_energy_ranges is False
    assert averages_options.group_average_over_energy_ranges is False
    assert averages_options.energy_average_using_constant_flux is False
    assert averages_options.maxwellian_averaged_capture_cross_sections is False
    assert averages_options.calculate_maxwellian_averages_after_reconstruction is False
    assert averages_options.make_no_corrections_to_theoretical_values is False
    assert averages_options.add_cross_sections_from_endf_b_file_3 is False
    assert averages_options.print_averaged_sensitivities_for_endf_parameters is False

    # Check default alphanumeric commands - should be empty
    commands = averages_options.get_alphanumeric_commands()
    assert len(commands) == 0


def test_average_type_options():
    """Test mutually exclusive average type options."""
    # Test average over energy ranges
    averages_options = AveragesOptions(average_over_energy_ranges=True)
    assert averages_options.average_over_energy_ranges is True
    assert "AVERAGE OVER ENERGY RANGES" in averages_options.get_alphanumeric_commands()

    # Test group average over energy ranges
    averages_options = AveragesOptions(group_average_over_energy_ranges=True)
    assert averages_options.group_average_over_energy_ranges is True
    assert "GROUP AVERAGE OVER ENERGY RANGES" in averages_options.get_alphanumeric_commands()

    # Test energy average using constant flux
    averages_options = AveragesOptions(energy_average_using_constant_flux=True)
    assert averages_options.energy_average_using_constant_flux is True
    assert "ENERGY AVERAGE USING CONSTANT FLUX" in averages_options.get_alphanumeric_commands()


def test_mutually_exclusive_average_types():
    """Test mutually exclusive validation between average type options."""
    # Test two average types together - should raise error
    with pytest.raises(ValueError):
        AveragesOptions(average_over_energy_ranges=True, group_average_over_energy_ranges=True)

    with pytest.raises(ValueError):
        AveragesOptions(average_over_energy_ranges=True, energy_average_using_constant_flux=True)

    with pytest.raises(ValueError):
        AveragesOptions(group_average_over_energy_ranges=True, energy_average_using_constant_flux=True)

    # Test all three together - should raise error
    with pytest.raises(ValueError):
        AveragesOptions(
            average_over_energy_ranges=True,
            group_average_over_energy_ranges=True,
            energy_average_using_constant_flux=True,
        )


def test_maxwellian_average_options():
    """Test Maxwellian average options."""
    # Test maxwellian-averaged capture cross sections
    averages_options = AveragesOptions(maxwellian_averaged_capture_cross_sections=True)
    assert averages_options.maxwellian_averaged_capture_cross_sections is True
    assert "MAXWELLIAN-AVERAGED CAPTURE CROSS SECTIONS" in averages_options.get_alphanumeric_commands()

    # Test calculate maxwellian averages after reconstruction
    averages_options = AveragesOptions(calculate_maxwellian_averages_after_reconstruction=True)
    assert averages_options.calculate_maxwellian_averages_after_reconstruction is True
    assert "CALCULATE MAXWELLIAN AVERAGES AFTER RECONSTRUCTION" in averages_options.get_alphanumeric_commands()


def test_maxwellian_dependency_validation():
    """Test dependencies between Maxwellian average options."""
    # Test add_cross_sections_from_endf_b_file_3 requires maxwellian option
    with pytest.raises(ValueError):
        AveragesOptions(add_cross_sections_from_endf_b_file_3=True)

    # Valid combinations
    averages_options = AveragesOptions(
        maxwellian_averaged_capture_cross_sections=True, add_cross_sections_from_endf_b_file_3=True
    )
    assert averages_options.maxwellian_averaged_capture_cross_sections is True
    assert averages_options.add_cross_sections_from_endf_b_file_3 is True

    averages_options = AveragesOptions(
        calculate_maxwellian_averages_after_reconstruction=True, add_cross_sections_from_endf_b_file_3=True
    )
    assert averages_options.calculate_maxwellian_averages_after_reconstruction is True
    assert averages_options.add_cross_sections_from_endf_b_file_3 is True


def test_theoretical_corrections_option():
    """Test make no corrections to theoretical values option."""
    # Test make no corrections to theoretical values
    averages_options = AveragesOptions(average_over_energy_ranges=True, make_no_corrections_to_theoretical_values=True)
    assert averages_options.average_over_energy_ranges is True
    assert averages_options.make_no_corrections_to_theoretical_values is True
    commands = averages_options.get_alphanumeric_commands()
    assert "AVERAGE OVER ENERGY RANGES" in commands
    assert "MAKE NO CORRECTIONS TO THEORETICAL VALUES" in commands

    # Test with other average types
    averages_options = AveragesOptions(
        group_average_over_energy_ranges=True, make_no_corrections_to_theoretical_values=True
    )
    assert averages_options.group_average_over_energy_ranges is True
    assert averages_options.make_no_corrections_to_theoretical_values is True

    averages_options = AveragesOptions(
        energy_average_using_constant_flux=True, make_no_corrections_to_theoretical_values=True
    )
    assert averages_options.energy_average_using_constant_flux is True
    assert averages_options.make_no_corrections_to_theoretical_values is True


def test_theoretical_corrections_dependency():
    """Test dependencies for make no corrections option."""
    # Test make_no_corrections_to_theoretical_values requires an average type
    with pytest.raises(ValueError):
        AveragesOptions(make_no_corrections_to_theoretical_values=True)


def test_averaged_sensitivities_option():
    """Test print averaged sensitivities option."""
    averages_options = AveragesOptions(print_averaged_sensitivities_for_endf_parameters=True)
    assert averages_options.print_averaged_sensitivities_for_endf_parameters is True
    assert "PRINT AVERAGED SENSITIVITIES FOR ENDF PARAMETERS" in averages_options.get_alphanumeric_commands()


def test_multiple_options():
    """Test multiple non-conflicting options together."""
    averages_options = AveragesOptions(
        energy_average_using_constant_flux=True,
        make_no_corrections_to_theoretical_values=True,
        maxwellian_averaged_capture_cross_sections=True,
        add_cross_sections_from_endf_b_file_3=True,
        print_averaged_sensitivities_for_endf_parameters=True,
    )

    commands = averages_options.get_alphanumeric_commands()
    assert "ENERGY AVERAGE USING CONSTANT FLUX" in commands
    assert "MAKE NO CORRECTIONS TO THEORETICAL VALUES" in commands
    assert "MAXWELLIAN-AVERAGED CAPTURE CROSS SECTIONS" in commands
    assert "ADD CROSS SECTIONS FROM ENDF/B FILE 3" in commands
    assert "PRINT AVERAGED SENSITIVITIES FOR ENDF PARAMETERS" in commands
    assert len(commands) == 5


if __name__ == "__main__":
    pytest.main()
