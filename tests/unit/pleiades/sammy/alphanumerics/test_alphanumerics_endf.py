import pytest

from pleiades.sammy.alphanumerics.endf import ENDFOptions


def test_default_options():
    """Test the default options."""
    endf_options = ENDFOptions()
    # Check default values - all should be False by default
    assert endf_options.input_is_endf_file_2 is False
    assert endf_options.use_energy_range_from_endf_file_2 is False
    assert endf_options.parameter_covariance_matrix_is_in_endf_format is False
    assert endf_options.data_are_endf_file is False
    assert endf_options.preserve_gamma_n_not_g_gamma_n_from_endf is False
    assert endf_options.endf_b_vi_file_2_is_wanted is False
    assert endf_options.ndf_file_is_in_key_word_format is False
    assert endf_options.generate_file_3_point_wise_cross_section is False
    assert endf_options.file_33_lb_1_covariance_is_wanted is False
    assert endf_options.automatic_ndf_file_creation is False
    assert endf_options.include_min_and_max_energies_in_endf_file is False

    # Check default alphanumeric commands
    commands = endf_options.get_alphanumeric_commands()
    assert len(commands) == 0


def test_input_is_endf_file_2():
    """Test the input is ENDF/B file 2 option."""
    endf_options = ENDFOptions(input_is_endf_file_2=True)
    assert endf_options.input_is_endf_file_2 is True
    assert "INPUT IS ENDF/B FILE 2" in endf_options.get_alphanumeric_commands()


def test_endf_related_data_options():
    """Test ENDF-related data options."""
    # Test data are ENDF/B file
    endf_options = ENDFOptions(data_are_endf_file=True)
    assert endf_options.data_are_endf_file is True
    assert "DATA ARE ENDF/B FILE" in endf_options.get_alphanumeric_commands()

    # Test NDF file is in key-word format
    endf_options = ENDFOptions(ndf_file_is_in_key_word_format=True)
    assert endf_options.ndf_file_is_in_key_word_format is True
    assert "NDF FILE IS IN KEY-WORD FORMAT" in endf_options.get_alphanumeric_commands()


def test_endf_covariance_options():
    """Test ENDF-related covariance options."""
    # Test parameter covariance matrix is in ENDF format
    endf_options = ENDFOptions(parameter_covariance_matrix_is_in_endf_format=True)
    assert endf_options.parameter_covariance_matrix_is_in_endf_format is True
    assert "PARAMETER COVARIANCE MATRIX IS IN ENDF FORMAT" in endf_options.get_alphanumeric_commands()

    # Test file 33 LB=1 covariance is wanted
    endf_options = ENDFOptions(file_33_lb_1_covariance_is_wanted=True)
    assert endf_options.file_33_lb_1_covariance_is_wanted is True
    assert "FILE 33 LB=1 COVARIANCE IS WANTED" in endf_options.get_alphanumeric_commands()


def test_file_dependency_checks():
    """Test dependency checks between related options."""
    # Test automatic NDF file creation requires input_is_endf_file_2
    with pytest.raises(ValueError):
        ENDFOptions(automatic_ndf_file_creation=True)


def test_endf_file_2_related_options():
    """Test related ENDF file 2 options."""
    # Test use energy range from ENDF file 2
    endf_options = ENDFOptions(input_is_endf_file_2=True, use_energy_range_from_endf_file_2=True)
    assert endf_options.input_is_endf_file_2 is True
    assert endf_options.use_energy_range_from_endf_file_2 is True
    commands = endf_options.get_alphanumeric_commands()
    assert "INPUT IS ENDF/B FILE 2" in commands
    assert "USE ENERGY RANGE FROM ENDF/B FILE 2" in commands

    # Test preserve gamma_n not g_gamma_n from ENDF
    endf_options = ENDFOptions(input_is_endf_file_2=True, preserve_gamma_n_not_g_gamma_n_from_endf=True)
    assert endf_options.input_is_endf_file_2 is True
    assert endf_options.preserve_gamma_n_not_g_gamma_n_from_endf is True
    commands = endf_options.get_alphanumeric_commands()
    assert "INPUT IS ENDF/B FILE 2" in commands
    assert "PRESERVE GAMMA_N NOT g_gamma_n FROM ENDF" in commands

    # Test use_energy_range_from_endf_file_2 requires input_is_endf_file_2
    with pytest.raises(ValueError):
        ENDFOptions(use_energy_range_from_endf_file_2=True)

    # Test preserve_gamma_n_not_g_gamma_n_from_endf requires input_is_endf_file_2
    with pytest.raises(ValueError):
        ENDFOptions(preserve_gamma_n_not_g_gamma_n_from_endf=True)


def test_endf_output_options():
    """Test ENDF output options."""
    # Test ENDF/B-VI file 2 is wanted
    endf_options = ENDFOptions(endf_b_vi_file_2_is_wanted=True)
    assert endf_options.endf_b_vi_file_2_is_wanted is True
    assert "ENDF/B-VI FILE 2 IS WANTED" in endf_options.get_alphanumeric_commands()

    # Test generate file 3 point-wise cross section
    endf_options = ENDFOptions(generate_file_3_point_wise_cross_section=True)
    assert endf_options.generate_file_3_point_wise_cross_section is True
    assert "GENERATE FILE 3 POINT-WISE CROSS SECTION" in endf_options.get_alphanumeric_commands()

    # Test automatic NDF file creation
    endf_options = ENDFOptions(input_is_endf_file_2=True, automatic_ndf_file_creation=True)
    assert endf_options.automatic_ndf_file_creation is True
    commands = endf_options.get_alphanumeric_commands()
    assert "AUTOMATIC NDF FILE CREATION" in commands
    assert "INPUT IS ENDF/B FILE 2" in commands

    # Test include min and max energies in ENDF file
    endf_options = ENDFOptions(include_min_and_max_energies_in_endf_file=True)
    assert endf_options.include_min_and_max_energies_in_endf_file is True
    assert "INCLUDE MIN & MAX ENERGIES IN ENDF FILE" in endf_options.get_alphanumeric_commands()


def test_additional_dependency_checks():
    """Test additional dependency checks."""
    # Test use_energy_range_from_endf_file_2 requires input_is_endf_file_2
    with pytest.raises(ValueError):
        ENDFOptions(use_energy_range_from_endf_file_2=True)

    # Valid combination
    endf_options = ENDFOptions(input_is_endf_file_2=True, use_energy_range_from_endf_file_2=True)
    assert endf_options.input_is_endf_file_2 is True
    assert endf_options.use_energy_range_from_endf_file_2 is True


def test_all_non_conflicting_options():
    """Test setting multiple non-conflicting options."""
    endf_options = ENDFOptions(
        input_is_endf_file_2=True,
        use_energy_range_from_endf_file_2=True,
        preserve_gamma_n_not_g_gamma_n_from_endf=True,
        parameter_covariance_matrix_is_in_endf_format=True,
        data_are_endf_file=True,
        endf_b_vi_file_2_is_wanted=True,
        ndf_file_is_in_key_word_format=True,
        generate_file_3_point_wise_cross_section=True,
        file_33_lb_1_covariance_is_wanted=True,
        automatic_ndf_file_creation=True,
        include_min_and_max_energies_in_endf_file=True,
    )

    commands = endf_options.get_alphanumeric_commands()
    assert "INPUT IS ENDF/B FILE 2" in commands
    assert "USE ENERGY RANGE FROM ENDF/B FILE 2" in commands
    assert "PRESERVE GAMMA_N NOT g_gamma_n FROM ENDF" in commands
    assert "PARAMETER COVARIANCE MATRIX IS IN ENDF FORMAT" in commands
    assert "DATA ARE ENDF/B FILE" in commands
    assert "ENDF/B-VI FILE 2 IS WANTED" in commands
    assert "NDF FILE IS IN KEY-WORD FORMAT" in commands
    assert "GENERATE FILE 3 POINT-WISE CROSS SECTION" in commands
    assert "FILE 33 LB=1 COVARIANCE IS WANTED" in commands
    assert "AUTOMATIC NDF FILE CREATION" in commands
    assert "INCLUDE MIN & MAX ENERGIES IN ENDF FILE" in commands
    assert len(commands) == 11


if __name__ == "__main__":
    pytest.main()
