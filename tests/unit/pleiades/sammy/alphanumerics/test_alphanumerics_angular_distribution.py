import pytest

from pleiades.sammy.alphanumerics.angular_distribution import AngularDistributionOptions


def test_default_options():
    """Test the default options."""
    angular_options = AngularDistributionOptions()

    # Check default values
    assert angular_options.use_laboratory_cross_sections is False
    assert angular_options.use_center_of_mass_cross_sections is True  # Default
    assert angular_options.prepare_legendre_coefficients_in_endf_format is False
    assert angular_options.omit_finite_size_corrections is False
    assert angular_options.incident_neutron_attenuation_is_included is False
    assert angular_options.approximate_scattered_neutron_attenuation is False
    assert angular_options.angle_average_for_differential_cross_section is False

    # Check default alphanumeric commands - should include the default option
    commands = angular_options.get_alphanumeric_commands()
    assert "USE CENTER-OF-MASS CROSS SECTIONS" in commands
    assert len(commands) == 1


def test_reference_frame_options():
    """Test reference frame options."""
    # Test laboratory frame
    angular_options = AngularDistributionOptions(
        use_laboratory_cross_sections=True, use_center_of_mass_cross_sections=False
    )
    assert angular_options.use_laboratory_cross_sections is True
    assert angular_options.use_center_of_mass_cross_sections is False
    commands = angular_options.get_alphanumeric_commands()
    assert "USE LABORATORY CROSS SECTIONS" in commands
    assert "USE CENTER-OF-MASS CROSS SECTIONS" not in commands
    assert len(commands) == 1

    # Test center-of-mass frame (default)
    angular_options = AngularDistributionOptions(
        use_laboratory_cross_sections=False, use_center_of_mass_cross_sections=True
    )
    assert angular_options.use_laboratory_cross_sections is False
    assert angular_options.use_center_of_mass_cross_sections is True
    commands = angular_options.get_alphanumeric_commands()
    assert "USE LABORATORY CROSS SECTIONS" not in commands
    assert "USE CENTER-OF-MASS CROSS SECTIONS" in commands
    assert len(commands) == 1


def test_mutually_exclusive_reference_frame():
    """Test mutual exclusivity of reference frame options."""
    # Both laboratory and center-of-mass set to True should raise error
    with pytest.raises(ValueError):
        AngularDistributionOptions(use_laboratory_cross_sections=True, use_center_of_mass_cross_sections=True)

    # Both laboratory and center-of-mass set to False should raise error
    with pytest.raises(ValueError):
        AngularDistributionOptions(use_laboratory_cross_sections=False, use_center_of_mass_cross_sections=False)


def test_legendre_coefficients_option():
    """Test prepare Legendre coefficients option."""
    angular_options = AngularDistributionOptions(prepare_legendre_coefficients_in_endf_format=True)
    assert angular_options.prepare_legendre_coefficients_in_endf_format is True
    commands = angular_options.get_alphanumeric_commands()
    assert "PREPARE LEGENDRE COEFFICIENTS IN ENDF FORMAT" in commands
    assert "USE CENTER-OF-MASS CROSS SECTIONS" in commands  # Default is still included
    assert len(commands) == 2


def test_finite_size_corrections_option():
    """Test omit finite size corrections option."""
    angular_options = AngularDistributionOptions(omit_finite_size_corrections=True)
    assert angular_options.omit_finite_size_corrections is True
    commands = angular_options.get_alphanumeric_commands()
    assert "OMIT FINITE SIZE CORRECTIONS" in commands
    assert "USE CENTER-OF-MASS CROSS SECTIONS" in commands  # Default is still included
    assert len(commands) == 2


def test_neutron_attenuation_options():
    """Test neutron attenuation options."""
    # Test incident neutron attenuation
    angular_options = AngularDistributionOptions(incident_neutron_attenuation_is_included=True)
    assert angular_options.incident_neutron_attenuation_is_included is True
    commands = angular_options.get_alphanumeric_commands()
    assert "INCIDENT NEUTRON ATTENUATION IS INCLUDED" in commands
    assert "USE CENTER-OF-MASS CROSS SECTIONS" in commands  # Default is still included
    assert len(commands) == 2

    # Test approximate scattered neutron attenuation
    angular_options = AngularDistributionOptions(approximate_scattered_neutron_attenuation=True)
    assert angular_options.approximate_scattered_neutron_attenuation is True
    commands = angular_options.get_alphanumeric_commands()
    assert "APPROXIMATE SCATTERED NEUTRON ATTENUATION" in commands
    assert "USE CENTER-OF-MASS CROSS SECTIONS" in commands  # Default is still included
    assert len(commands) == 2


def test_angle_average_option():
    """Test angle average option."""
    angular_options = AngularDistributionOptions(angle_average_for_differential_cross_section=True)
    assert angular_options.angle_average_for_differential_cross_section is True
    commands = angular_options.get_alphanumeric_commands()
    assert "ANGLE-AVERAGE FOR DIFFERENTIAL CROSS SECTION" in commands
    assert "USE CENTER-OF-MASS CROSS SECTIONS" in commands  # Default is still included
    assert len(commands) == 2


def test_multiple_options():
    """Test multiple non-conflicting options together."""
    angular_options = AngularDistributionOptions(
        use_laboratory_cross_sections=True,
        use_center_of_mass_cross_sections=False,
        prepare_legendre_coefficients_in_endf_format=True,
        omit_finite_size_corrections=True,
        incident_neutron_attenuation_is_included=True,
        approximate_scattered_neutron_attenuation=True,
        angle_average_for_differential_cross_section=True,
    )

    commands = angular_options.get_alphanumeric_commands()
    assert "USE LABORATORY CROSS SECTIONS" in commands
    assert "PREPARE LEGENDRE COEFFICIENTS IN ENDF FORMAT" in commands
    assert "OMIT FINITE SIZE CORRECTIONS" in commands
    assert "INCIDENT NEUTRON ATTENUATION IS INCLUDED" in commands
    assert "APPROXIMATE SCATTERED NEUTRON ATTENUATION" in commands
    assert "ANGLE-AVERAGE FOR DIFFERENTIAL CROSS SECTION" in commands
    assert "USE CENTER-OF-MASS CROSS SECTIONS" not in commands
    assert len(commands) == 6


if __name__ == "__main__":
    pytest.main()
