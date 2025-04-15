import pytest

from pleiades.sammy.alphanumerics.params import QuantumNumbersOptions


def test_default_option():
    """Test the default option."""
    options = QuantumNumbersOptions()
    assert options.new_spin_group_format is True
    assert options.particle_pair_definitions is False
    assert options.keyword_particle_pair_definitions is False
    assert options.quantum_numbers_in_parameter_file is False
    assert options.put_quantum_numbers_into_parameter_file is False
    assert options.spin_of_incident_particle_is_plus is False
    assert options.spin_of_incident_particle_is_minus is False
    assert options.i4_format_to_read_spin_group_number is False
    assert options.input_is_endf_b_file is False
    assert options.use_energy_range_from_endf_b_file_2 is False
    assert options.flag_all_resonance_parameters is False
    assert options.get_alphanumeric_commands() == ["USE NEW SPIN GROUP Format"]


def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    options = QuantumNumbersOptions(particle_pair_definitions=True)
    assert options.new_spin_group_format is False
    assert options.particle_pair_definitions is True
    assert options.keyword_particle_pair_definitions is False
    assert options.quantum_numbers_in_parameter_file is False
    assert options.put_quantum_numbers_into_parameter_file is False
    assert options.spin_of_incident_particle_is_plus is False
    assert options.spin_of_incident_particle_is_minus is False
    assert options.i4_format_to_read_spin_group_number is False
    assert options.input_is_endf_b_file is False
    assert options.use_energy_range_from_endf_b_file_2 is False
    assert options.flag_all_resonance_parameters is False
    assert options.get_alphanumeric_commands() == ["PARTICLE PAIR DEFINItions are used"]


def test_mutually_exclusive_options_1():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        QuantumNumbersOptions(new_spin_group_format=True, particle_pair_definitions=True)


def test_mutually_exclusive_options_2():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        QuantumNumbersOptions(quantum_numbers_in_parameter_file=True, put_quantum_numbers_into_parameter_file=True)


def test_valid_combination_of_options_1():
    """Test a valid combination of options."""
    options = QuantumNumbersOptions(
        quantum_numbers_in_parameter_file=True,
        spin_of_incident_particle_is_plus=True,
        i4_format_to_read_spin_group_number=True,
    )
    assert options.new_spin_group_format is True
    assert options.particle_pair_definitions is False
    assert options.keyword_particle_pair_definitions is False
    assert options.quantum_numbers_in_parameter_file is True
    assert options.put_quantum_numbers_into_parameter_file is False
    assert options.spin_of_incident_particle_is_plus is True
    assert options.spin_of_incident_particle_is_minus is False
    assert options.i4_format_to_read_spin_group_number is True
    assert options.input_is_endf_b_file is False
    assert options.use_energy_range_from_endf_b_file_2 is False
    assert options.flag_all_resonance_parameters is False
    assert options.get_alphanumeric_commands() == [
        "USE NEW SPIN GROUP Format",
        "QUANTUM NUMBERS ARE in parameter file",
        "SPIN OF INCIDENT PARticle is +",
        "USE I4 FORMAT TO REAd spin group number",
    ]


def test_valid_combination_of_options_2():
    """Test a valid combination of options."""
    options = QuantumNumbersOptions(
        keyword_particle_pair_definitions=True, input_is_endf_b_file=True, flag_all_resonance_parameters=True
    )
    assert options.new_spin_group_format is False
    assert options.particle_pair_definitions is False
    assert options.keyword_particle_pair_definitions is True
    assert options.quantum_numbers_in_parameter_file is False
    assert options.put_quantum_numbers_into_parameter_file is False
    assert options.spin_of_incident_particle_is_plus is False
    assert options.spin_of_incident_particle_is_minus is False
    assert options.i4_format_to_read_spin_group_number is False
    assert options.input_is_endf_b_file is True
    assert options.use_energy_range_from_endf_b_file_2 is False
    assert options.flag_all_resonance_parameters is True
    assert options.get_alphanumeric_commands() == [
        "KEY-WORD PARTICLE-PAir definitions are given",
        "INPUT IS ENDF/B FILE",
        "FLAG ALL RESONANCE Parameters",
    ]


def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        QuantumNumbersOptions(
            new_spin_group_format=True, particle_pair_definitions=True, keyword_particle_pair_definitions=True
        )


def test_switching_options():
    """Test switching options."""
    options = QuantumNumbersOptions()
    assert options.new_spin_group_format is True
    assert options.get_alphanumeric_commands() == ["USE NEW SPIN GROUP Format"]

    options = QuantumNumbersOptions(particle_pair_definitions=True)
    assert options.particle_pair_definitions is True
    assert options.get_alphanumeric_commands() == ["PARTICLE PAIR DEFINItions are used"]

    options = QuantumNumbersOptions(keyword_particle_pair_definitions=True)
    assert options.keyword_particle_pair_definitions is True
    assert options.get_alphanumeric_commands() == ["KEY-WORD PARTICLE-PAir definitions are given"]

    options = QuantumNumbersOptions(quantum_numbers_in_parameter_file=True)
    assert options.quantum_numbers_in_parameter_file is True
    assert options.get_alphanumeric_commands() == ["USE NEW SPIN GROUP Format", "QUANTUM NUMBERS ARE in parameter file"]

    options = QuantumNumbersOptions(put_quantum_numbers_into_parameter_file=True)
    assert options.put_quantum_numbers_into_parameter_file is True
    assert options.get_alphanumeric_commands() == [
        "USE NEW SPIN GROUP Format",
        "PUT QUANTUM NUMBERS into parameter file",
    ]

    options = QuantumNumbersOptions(spin_of_incident_particle_is_plus=True)
    assert options.spin_of_incident_particle_is_plus is True
    assert options.get_alphanumeric_commands() == ["USE NEW SPIN GROUP Format", "SPIN OF INCIDENT PARticle is +"]

    options = QuantumNumbersOptions(spin_of_incident_particle_is_minus=True)
    assert options.spin_of_incident_particle_is_minus is True
    assert options.get_alphanumeric_commands() == ["USE NEW SPIN GROUP Format", "SPIN OF INCIDENT PARticle is -"]

    options = QuantumNumbersOptions(i4_format_to_read_spin_group_number=True)
    assert options.i4_format_to_read_spin_group_number is True
    assert options.get_alphanumeric_commands() == [
        "USE NEW SPIN GROUP Format",
        "USE I4 FORMAT TO REAd spin group number",
    ]

    options = QuantumNumbersOptions(input_is_endf_b_file=True)
    assert options.input_is_endf_b_file is True
    assert options.get_alphanumeric_commands() == ["USE NEW SPIN GROUP Format", "INPUT IS ENDF/B FILE"]

    options = QuantumNumbersOptions(use_energy_range_from_endf_b_file_2=True)
    assert options.use_energy_range_from_endf_b_file_2 is True
    assert options.get_alphanumeric_commands() == ["USE NEW SPIN GROUP Format", "USE ENERGY RANGE FROm endf/b file 2"]

    options = QuantumNumbersOptions(flag_all_resonance_parameters=True)
    assert options.flag_all_resonance_parameters is True
    assert options.get_alphanumeric_commands() == ["USE NEW SPIN GROUP Format", "FLAG ALL RESONANCE Parameters"]


if __name__ == "__main__":
    pytest.main()
