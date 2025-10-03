import pytest

from pleiades.sammy.alphanumerics.physical_constants import PhysicalConstantsOptions


def test_default_options():
    """Test the default options."""
    constants_options = PhysicalConstantsOptions()

    # Check default values
    assert constants_options.use_endf_values_for_constants is True  # Default
    assert constants_options.use_1995_endf_102_constant_values is False
    assert constants_options.use_sammy_k1_defaults_for_constants is False

    # Check default alphanumeric commands - should include the default option
    commands = constants_options.get_alphanumeric_commands()
    assert "USE ENDF VALUES FOR CONSTANTS" in commands
    assert len(commands) == 1


def test_endf_1999_option():
    """Test ENDF 1999 constants option (default)."""
    constants_options = PhysicalConstantsOptions(use_endf_values_for_constants=True)
    assert constants_options.use_endf_values_for_constants is True
    commands = constants_options.get_alphanumeric_commands()
    assert "USE ENDF VALUES FOR CONSTANTS" in commands
    assert len(commands) == 1


def test_endf_1995_option():
    """Test ENDF 1995 constants option."""
    constants_options = PhysicalConstantsOptions(
        use_endf_values_for_constants=False, use_1995_endf_102_constant_values=True
    )
    assert constants_options.use_endf_values_for_constants is False
    assert constants_options.use_1995_endf_102_constant_values is True
    commands = constants_options.get_alphanumeric_commands()
    assert "USE ENDF VALUES FOR CONSTANTS" not in commands
    assert "USE 1995 ENDF-102 CONSTANT VALUES" in commands
    assert len(commands) == 1


def test_sammy_k1_option():
    """Test SAMMY K1 constants option."""
    constants_options = PhysicalConstantsOptions(
        use_endf_values_for_constants=False, use_sammy_k1_defaults_for_constants=True
    )
    assert constants_options.use_endf_values_for_constants is False
    assert constants_options.use_sammy_k1_defaults_for_constants is True
    commands = constants_options.get_alphanumeric_commands()
    assert "USE ENDF VALUES FOR CONSTANTS" not in commands
    assert "USE SAMMY-K1 DEFAULTS FOR CONSTANTS" in commands
    assert len(commands) == 1


def test_mutually_exclusive_options():
    """Test mutual exclusivity of constants options."""
    # Test ENDF 1999 and ENDF 1995 together - should raise error
    with pytest.raises(ValueError):
        PhysicalConstantsOptions(use_endf_values_for_constants=True, use_1995_endf_102_constant_values=True)

    # Test ENDF 1999 and SAMMY K1 together - should raise error
    with pytest.raises(ValueError):
        PhysicalConstantsOptions(use_endf_values_for_constants=True, use_sammy_k1_defaults_for_constants=True)

    # Test ENDF 1995 and SAMMY K1 together - should raise error
    with pytest.raises(ValueError):
        PhysicalConstantsOptions(use_1995_endf_102_constant_values=True, use_sammy_k1_defaults_for_constants=True)

    # Test all three together - should raise error
    with pytest.raises(ValueError):
        PhysicalConstantsOptions(
            use_endf_values_for_constants=True,
            use_1995_endf_102_constant_values=True,
            use_sammy_k1_defaults_for_constants=True,
        )


def test_reset_defaults():
    """Test setting multiple options to False should raise error."""
    # All three options set to False should raise error
    with pytest.raises(ValueError):
        PhysicalConstantsOptions(
            use_endf_values_for_constants=False,
            use_1995_endf_102_constant_values=False,
            use_sammy_k1_defaults_for_constants=False,
        )


if __name__ == "__main__":
    pytest.main()
