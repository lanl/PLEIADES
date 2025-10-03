import pytest

from pleiades.sammy.alphanumerics.cross_section import CrossSectionOptions


def test_default_options():
    """Test the default options."""
    cs_options = CrossSectionOptions()
    # Check default values
    assert cs_options.use_polar_coordinates_for_fission_widths is False
    assert cs_options.numerical_derivatives_for_resonance_parameters is False
    assert cs_options.do_not_use_s_wave_cutoff is True
    assert cs_options.use_s_wave_cutoff is False
    assert cs_options.use_no_cutoffs_for_derivatives is False
    assert cs_options.use_alternative_coulomb_functions is False
    assert cs_options.add_direct_capture_component is False
    assert cs_options.lab_non_coulomb_excitation_energies is True
    assert cs_options.cm_non_coulomb_excitation_energies is False
    assert cs_options.lab_coulomb_excitation_energies is True
    assert cs_options.cm_coulomb_excitation_energies is False
    assert cs_options.add_eliminated_capture_channel is False

    # Check default alphanumeric commands
    commands = cs_options.get_alphanumeric_commands()
    assert "DO NOT USE S-WAVE CUTOFF" in commands
    assert "LAB NON COULOMB EXCITATION ENERGIES" in commands
    assert "LAB COULOMB EXCITATION ENERGIES" in commands
    assert len(commands) == 3


def test_s_wave_cutoff_options():
    """Test the s-wave cutoff options."""
    # Test use_s_wave_cutoff
    cs_options = CrossSectionOptions(use_s_wave_cutoff=True)
    assert cs_options.do_not_use_s_wave_cutoff is False
    assert cs_options.use_s_wave_cutoff is True
    assert cs_options.use_no_cutoffs_for_derivatives is False
    assert "USE S-WAVE CUTOFF" in cs_options.get_alphanumeric_commands()

    # Test use_no_cutoffs_for_derivatives
    cs_options = CrossSectionOptions(use_no_cutoffs_for_derivatives=True)
    assert cs_options.do_not_use_s_wave_cutoff is False
    assert cs_options.use_s_wave_cutoff is False
    assert cs_options.use_no_cutoffs_for_derivatives is True
    assert "USE NO CUTOFFS FOR DERIVATIVES OR CROSS SECTIONS" in cs_options.get_alphanumeric_commands()


def test_excitation_energy_options():
    """Test the excitation energy options."""
    # Test non-Coulomb cm
    cs_options = CrossSectionOptions(cm_non_coulomb_excitation_energies=True)
    assert cs_options.lab_non_coulomb_excitation_energies is False
    assert cs_options.cm_non_coulomb_excitation_energies is True
    assert "CM NON COULOMB EXCITATION ENERGIES" in cs_options.get_alphanumeric_commands()

    # Test Coulomb cm
    cs_options = CrossSectionOptions(cm_coulomb_excitation_energies=True)
    assert cs_options.lab_coulomb_excitation_energies is False
    assert cs_options.cm_coulomb_excitation_energies is True
    assert "CM COULOMB EXCITATION ENERGIES" in cs_options.get_alphanumeric_commands()


def test_mutually_exclusive_options():
    """Test mutually exclusive options."""
    # Test s-wave cutoff options are mutually exclusive
    with pytest.raises(ValueError):
        CrossSectionOptions(do_not_use_s_wave_cutoff=True, use_s_wave_cutoff=True)

    with pytest.raises(ValueError):
        CrossSectionOptions(use_s_wave_cutoff=True, use_no_cutoffs_for_derivatives=True)

    with pytest.raises(ValueError):
        CrossSectionOptions(do_not_use_s_wave_cutoff=True, use_no_cutoffs_for_derivatives=True)

    # Test non-Coulomb excitation energy options are mutually exclusive
    with pytest.raises(ValueError):
        CrossSectionOptions(lab_non_coulomb_excitation_energies=True, cm_non_coulomb_excitation_energies=True)

    # Test Coulomb excitation energy options are mutually exclusive
    with pytest.raises(ValueError):
        CrossSectionOptions(lab_coulomb_excitation_energies=True, cm_coulomb_excitation_energies=True)


def test_other_options():
    """Test other cross section calculation options."""
    # Test polar coordinates for fission widths
    cs_options = CrossSectionOptions(use_polar_coordinates_for_fission_widths=True)
    assert cs_options.use_polar_coordinates_for_fission_widths is True
    assert "USE POLAR COORDINATES FOR FISSION WIDTHS" in cs_options.get_alphanumeric_commands()

    # Test numerical derivatives
    cs_options = CrossSectionOptions(numerical_derivatives_for_resonance_parameters=True)
    assert cs_options.numerical_derivatives_for_resonance_parameters is True
    assert "NUMERICAL DERIVATIVES FOR RESONANCE PARAMETERS" in cs_options.get_alphanumeric_commands()

    # Test alternative Coulomb functions
    cs_options = CrossSectionOptions(use_alternative_coulomb_functions=True)
    assert cs_options.use_alternative_coulomb_functions is True
    assert "USE ALTERNATIVE COULOMB FUNCTIONS" in cs_options.get_alphanumeric_commands()

    # Test direct capture component
    cs_options = CrossSectionOptions(add_direct_capture_component=True)
    assert cs_options.add_direct_capture_component is True
    assert "ADD DIRECT CAPTURE COMPONENT TO CROSS SECTION" in cs_options.get_alphanumeric_commands()

    # Test eliminated capture channel
    cs_options = CrossSectionOptions(add_eliminated_capture_channel=True)
    assert cs_options.add_eliminated_capture_channel is True
    assert "ADD ELIMINATED CAPTURE CHANNEL TO FINAL STATE" in cs_options.get_alphanumeric_commands()


def test_all_options():
    """Test setting multiple non-conflicting options."""
    cs_options = CrossSectionOptions(
        use_polar_coordinates_for_fission_widths=True,
        numerical_derivatives_for_resonance_parameters=True,
        use_no_cutoffs_for_derivatives=True,
        use_alternative_coulomb_functions=True,
        add_direct_capture_component=True,
        cm_non_coulomb_excitation_energies=True,
        cm_coulomb_excitation_energies=True,
        add_eliminated_capture_channel=True,
    )

    commands = cs_options.get_alphanumeric_commands()
    assert "USE POLAR COORDINATES FOR FISSION WIDTHS" in commands
    assert "NUMERICAL DERIVATIVES FOR RESONANCE PARAMETERS" in commands
    assert "USE NO CUTOFFS FOR DERIVATIVES OR CROSS SECTIONS" in commands
    assert "USE ALTERNATIVE COULOMB FUNCTIONS" in commands
    assert "ADD DIRECT CAPTURE COMPONENT TO CROSS SECTION" in commands
    assert "CM NON COULOMB EXCITATION ENERGIES" in commands
    assert "CM COULOMB EXCITATION ENERGIES" in commands
    assert "ADD ELIMINATED CAPTURE CHANNEL TO FINAL STATE" in commands
    assert len(commands) == 8


if __name__ == "__main__":
    pytest.main()
