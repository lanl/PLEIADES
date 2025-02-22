#!/usr/bin/env python
"""Unit tests for card 07::radius."""

import pytest

from pleiades.sammy.parameters.radius import RadiusCard, RadiusFormat, VaryFlag


def create_fixed_width_line(pareff: float, partru: float, ichan: int, ifleff: int, ifltru: int, spin_groups: list[int]) -> str:
    """Create properly formatted fixed-width line."""
    # Format floating point numbers with proper width
    pareff_str = f"{pareff:10.3f}"
    partru_str = f"{partru:10.3f}"

    # Format integers
    ichan_str = f"{ichan:1d}"
    ifleff_str = f"{ifleff:1d}"
    ifltru_str = f"{ifltru:2d}"

    # Format spin groups (2 columns each)
    spin_groups_str = "".join(f"{g:2d}" for g in spin_groups)

    return f"{pareff_str}{partru_str}{ichan_str}{ifleff_str}{ifltru_str}{spin_groups_str}"


def create_alternate_fixed_width_line(pareff: float, partru: float, ichan: int, ifleff: int, ifltru: int, spin_groups: list[int]) -> str:
    """Create properly formatted fixed-width line for alternate format (>=99 spin groups).

    Args:
        pareff: Effective radius value
        partru: True radius value
        ichan: Channel mode (0 or 1)
        ifleff: Flag for effective radius
        ifltru: Flag for true radius
        spin_groups: List of spin group numbers

    Returns:
        str: Formatted line following alternate fixed-width format
    """
    # Format floating point numbers (same as default format)
    pareff_str = f"{pareff:10.3f}"  # Cols 1-10
    partru_str = f"{partru:10.3f}"  # Cols 11-20

    # Format integers with 5-column width
    ichan_str = f"{ichan:5d}"  # Cols 21-25
    ifleff_str = f"{ifleff:5d}"  # Cols 26-30
    ifltru_str = f"{ifltru:5d}"  # Cols 31-35

    # Format spin groups (5 columns each, starting at col 36)
    spin_groups_str = "".join(f"{g:5d}" for g in spin_groups)

    return f"{pareff_str}{partru_str}{ichan_str}{ifleff_str}{ifltru_str}{spin_groups_str}"


def test_basic_fixed_width_format():
    """Test basic fixed-width format parsing with single line of spin groups."""

    # Create input with proper fixed-width formatting
    input_str = "RADIUs parameters follow\n" + create_fixed_width_line(3.200, 3.200, 0, 1, -1, [1, 2, 3]) + "\n"
    print("\nTest input:")
    print(input_str)
    print("\nColumn positions for content line:")
    content = input_str.splitlines()[1]
    print("Cols  1-10 (PAREFF):", f"'{content[0:10]}'")
    print("Cols 11-20 (PARTRU):", f"'{content[10:20]}'")
    print("Col     21 (ICHAN):", f"'{content[20:21]}'")
    print("Col     22 (IFLEFF):", f"'{content[21:22]}'")
    print("Cols 23-24 (IFLTRU):", f"'{content[22:24]}'")
    print("Cols 25-26 (Group1):", f"'{content[24:26]}'")
    print("Cols 27-28 (Group2):", f"'{content[26:28]}'")
    print("Cols 29-30 (Group3):", f"'{content[28:30]}'")

    # Parse the input
    card = RadiusCard.from_lines(input_str.splitlines())

    # Verify that there is only one set of parameters in the card
    assert len(card.parameters) == 1

    # Access the RadiusParameters object in the parameters list
    params = card.parameters[0]


    # Verify parsed values
    assert params.effective_radius == pytest.approx(3.200)
    assert params.true_radius == pytest.approx(3.200)
    assert params.channel_mode == 0
    assert params.vary_effective == VaryFlag.YES  # 1
    assert params.vary_true == VaryFlag.USE_FROM_PARFILE  # -1
    assert params.spin_groups == [1, 2, 3]
    assert params.channels is None  # No channels specified when mode=0

    # Test writing back to fixed-width format
    output_lines = card.to_lines(radius_format=RadiusFormat.DEFAULT)
    assert len(output_lines) == 3  # Header, content, blank line
    assert output_lines[0].strip() == "RADIUs parameters follow"

    # Verify the formatted output matches input format
    content_line = output_lines[1]
    print(card)
    print(content_line)
    assert content_line[0:10].strip() == "3.2000E+00"  # PAREFF
    assert content_line[10:20].strip() == "3.2000E+00"  # PARTRU
    assert content_line[20:21] == "0"  # ICHAN
    assert content_line[21:22] == "1"  # IFLEFF
    assert content_line[22:24] == "-1"  # IFLTRU
    assert content_line[24:26] == " 1"  # First spin group
    assert content_line[26:28] == " 2"  # Second spin group
    assert content_line[28:30] == " 3"  # Third spin group

@pytest.mark.skip(reason="Alternate fixed-width format is unsupported at the moment")
def test_alternate_fixed_width_format():
    """Test alternate fixed-width format parsing (for >=99 spin groups)."""

    # Create test input with large spin group numbers
    spin_groups = [101, 102, 103]  # Using 3-digit group numbers

    input_str = "RADIUs parameters follow\n" + create_alternate_fixed_width_line(3.200, 3.200, 0, 1, -1, spin_groups) + "\n"

    print("\nTest input:")
    print(input_str)
    print("\nColumn positions for content line:")
    content = input_str.splitlines()[1]
    print("Cols  1-10 (PAREFF):", f"'{content[0:10]}'")
    print("Cols 11-20 (PARTRU):", f"'{content[10:20]}'")
    print("Cols 21-25 (ICHAN):", f"'{content[20:25]}'")
    print("Cols 26-30 (IFLEFF):", f"'{content[25:30]}'")
    print("Cols 31-35 (IFLTRU):", f"'{content[30:35]}'")
    print("Cols 36-40 (Group1):", f"'{content[35:40]}'")
    print("Cols 41-45 (Group2):", f"'{content[40:45]}'")
    print("Cols 46-50 (Group3):", f"'{content[45:50]}'")

    # Parse the input
    card = RadiusCard.from_lines(input_str.splitlines())

    # Verify parsed values
    assert card.parameters.effective_radius == pytest.approx(3.200)
    assert card.parameters.true_radius == pytest.approx(3.200)
    assert card.parameters.channel_mode == 0
    assert card.parameters.vary_effective == VaryFlag.YES  # 1
    assert card.parameters.vary_true == VaryFlag.USE_FROM_PARFILE  # -1
    assert card.parameters.spin_groups == [101, 102, 103]
    assert card.parameters.channels is None  # No channels specified when mode=0

    # Test writing back to alternate format
    output_lines = card.to_lines(radius_format=RadiusFormat.ALTERNATE)
    assert len(output_lines) == 3  # Header, content, blank line
    assert output_lines[0].strip() == "RADIUs parameters follow"

    # Verify the formatted output matches input format
    content_line = output_lines[1]
    print("\nGenerated output:")
    print(content_line)
    assert content_line[0:10].strip() == "3.2000E+00"  # PAREFF
    assert content_line[10:20].strip() == "3.2000E+00"  # PARTRU
    assert content_line[20:25] == "    0"  # ICHAN (5 cols)
    assert content_line[25:30] == "    1"  # IFLEFF (5 cols)
    assert content_line[30:35] == "   -1"  # IFLTRU (5 cols)
    assert content_line[35:40] == "  101"  # First spin group (5 cols)
    assert content_line[40:45] == "  102"  # Second spin group (5 cols)
    assert content_line[45:50] == "  103"  # Third spin group (5 cols)

@pytest.mark.skip(reason="Alternate keyword format is unsupported at the moment")
def test_basic_radius_keyword_format():
    """Test basic keyword format parsing with single radius value."""

    input_str = """RADII are in KEY-WORD format
Radius= 3.200
Group= 1
"""
    print("\nTest input:")
    print(input_str)

    # Parse the input
    card = RadiusCard.from_lines(input_str.splitlines())

    # Verify parsed values
    assert card.parameters.effective_radius == pytest.approx(3.200)
    assert card.parameters.true_radius == pytest.approx(3.200)  # Should equal effective_radius
    assert card.parameters.spin_groups == [1]
    assert card.parameters.channels is None

    # Test writing back to keyword format
    output_lines = card.to_lines(radius_format=RadiusFormat.KEYWORD)
    print("\nGenerated output:")
    print("\n".join(output_lines))

    # Verify format and content
    assert output_lines[0].strip() == "RADII are in KEY-WORD format"
    assert any(line.startswith("Radius= 3.2") for line in output_lines)
    assert any(line.startswith("Group= 1") for line in output_lines)

@pytest.mark.skip(reason="Alternate keyword format is unsupported at the moment")
def test_separate_radii_keyword_format():
    """Test keyword format parsing with different effective/true radius values."""

    input_str = """RADII are in KEY-WORD format
Radius= 3.200 3.400
Flags= 1 3
Group= 1 2 3
"""
    print("\nTest input:")
    print(input_str)

    card = RadiusCard.from_lines(input_str.splitlines())

    assert card.parameters.effective_radius == pytest.approx(3.200)
    assert card.parameters.true_radius == pytest.approx(3.400)
    assert card.parameters.vary_effective == VaryFlag.YES  # 1
    assert card.parameters.vary_true == VaryFlag.PUP  # 3
    assert card.parameters.spin_groups == [1, 2, 3]

    output_lines = card.to_lines(radius_format=RadiusFormat.KEYWORD)
    print("\nGenerated output:")
    print("\n".join(output_lines))

@pytest.mark.skip(reason="Alternate keyword format is unsupported at the moment")
def test_uncertainties_keyword_format():
    """Test keyword format parsing with uncertainty specifications."""

    input_str = """RADII are in KEY-WORD format
Radius= 3.200 3.200
Flags= 1 3
Relative= 0.05 0.1
Absolute= 0.002 0.003
Group= 1
"""
    print("\nTest input:")
    print(input_str)

    card = RadiusCard.from_lines(input_str.splitlines())

    assert card.relative_uncertainty == pytest.approx(0.05)
    assert card.absolute_uncertainty == pytest.approx(0.002)

    output_lines = card.to_lines(radius_format=RadiusFormat.KEYWORD)
    print("\nGenerated output:")
    print("\n".join(output_lines))

    assert any(line.startswith("Relative= 0.05") for line in output_lines)
    assert any(line.startswith("Absolute= 0.002") for line in output_lines)

@pytest.mark.skip(reason="Alternate keyword format is unsupported at the moment")
def test_particle_pair_keyword_format():
    """Test keyword format parsing with particle pair and orbital momentum."""

    input_str = """RADII are in KEY-WORD format
Radius= 3.200 3.200
PP=n+16O L=all
Flags= 1 3
"""
    print("\nTest input:")
    print(input_str)

    card = RadiusCard.from_lines(input_str.splitlines())

    assert card.particle_pair == "n+16O"
    assert card.orbital_momentum == ["all"]

    output_lines = card.to_lines(radius_format=RadiusFormat.KEYWORD)
    print("\nGenerated output:")
    print("\n".join(output_lines))

    assert any(line.startswith("PP= n+16O") for line in output_lines)
    assert any("L= all" in line for line in output_lines)

@pytest.mark.skip(reason="Alternate keyword format is unsupported at the moment")
def test_groups_channels_keyword_format():
    """Test keyword format parsing with group and channel specifications."""

    input_str = """RADII are in KEY-WORD format
Radius= 3.200 3.200
Flags= 1 3
Group= 1 Channels= 1 2 3
"""
    print("\nTest input:")
    print(input_str)

    card = RadiusCard.from_lines(input_str.splitlines())

    print(card)

    assert card.parameters.spin_groups == [1]
    assert card.parameters.channels == [1, 2, 3]
    assert card.parameters.channel_mode == 1  # Specific channels mode

    output_lines = card.to_lines(radius_format=RadiusFormat.KEYWORD)
    print("\nGenerated output:")
    print("\n".join(output_lines))

@pytest.mark.skip(reason="Alternate keyword format is unsupported at the moment")
def test_invalid_keyword_format():
    """Test error handling for invalid keyword format."""

    # Missing radius value
    invalid_input = """RADII are in KEY-WORD format
Flags= 1 3
Group= 1
"""
    with pytest.raises(ValueError, match="2 validation errors for RadiusParameters"):
        RadiusCard.from_lines(invalid_input.splitlines())

    # Missing group specification
    invalid_input = """RADII are in KEY-WORD format
Radius= 3.200 3.200
Flags= 1 3
"""
    with pytest.raises(ValueError, match="Must specify either spin groups or"):
        RadiusCard.from_lines(invalid_input.splitlines())


def test_minimal_radius_creation():
    """Test creating RadiusCard with minimal required parameters."""

    print("\nTest minimal parameter creation:")
    # Create with just effective radius and spin groups
    card = RadiusCard.from_values(effective_radius=3.200, spin_groups=[1, 2, 3])

    # Verify that there is only one set of parameters in the card
    assert len(card.parameters) == 1

    print(f"Card parameters: {card.parameters[0]}")

    # Verify defaults
    assert card.parameters[0].effective_radius == pytest.approx(3.200)
    assert card.parameters[0].true_radius == pytest.approx(3.200)  # Should equal effective_radius
    assert card.parameters[0].spin_groups == [1, 2, 3]
    assert card.parameters[0].channel_mode == 0  # Default
    assert card.parameters[0].vary_effective == VaryFlag.NO  # Default
    assert card.parameters[0].vary_true == VaryFlag.NO  # Default
    assert card.parameters[0].channels is None  # Default


def test_full_radius_creation():
    """Test creating RadiusCard with full parameter set."""

    print("\nTest full parameter creation:")
    card = RadiusCard.from_values(
        effective_radius=3.200,
        true_radius=3.400,
        spin_groups=[1, 2],
        channels=[1, 2, 3],
        vary_effective=VaryFlag.YES,
        vary_true=VaryFlag.PUP,
    )

    # Verify that there is only one set of parameters in the card
    assert len(card.parameters) == 1

    print(f"Card parameters: {card.parameters[0]}")

    # Verify all parameters
    assert card.parameters[0].effective_radius == pytest.approx(3.200)
    assert card.parameters[0].true_radius == pytest.approx(3.400)
    assert card.parameters[0].spin_groups == [1, 2]
    assert card.parameters[0].channel_mode == 1  # Auto-set when channels provided
    assert card.parameters[0].channels == [1, 2, 3]
    assert card.parameters[0].vary_effective == VaryFlag.YES
    assert card.parameters[0].vary_true == VaryFlag.PUP


def test_radius_with_extras():
    """Test creating RadiusCard with keyword format extras."""

    print("\nTest creation with extras:")
    card = RadiusCard.from_values(
        effective_radius=3.200,
        spin_groups=[1],
        particle_pair="n+16O",
        orbital_momentum=["all"],
        relative_uncertainty=0.05,
        absolute_uncertainty=0.002,
    )

    print(f"Card parameters: {card.parameters}")
    print(
        f"Card extras: particle_pair={card.particle_pair}, "
        f"orbital_momentum={card.orbital_momentum}, "
        f"uncertainties={card.relative_uncertainty}, {card.absolute_uncertainty}"
    )

    # Verify that there is only one set of parameters in the card
    assert len(card.parameters) == 1


    # Verify core parameters
    assert card.parameters[0].effective_radius == pytest.approx(3.200)
    assert card.parameters[0].true_radius == pytest.approx(3.200)
    assert card.parameters[0].spin_groups == [1]

    # Verify extras
    assert card.particle_pair == "n+16O"
    assert card.orbital_momentum == ["all"]
    assert card.relative_uncertainty == pytest.approx(0.05)
    assert card.absolute_uncertainty == pytest.approx(0.002)


def test_invalid_radius_creation():
    """Test error cases for direct parameter creation."""

    print("\nTesting invalid parameter combinations:")

    # Missing required parameters
    with pytest.raises(TypeError) as exc_info:
        RadiusCard.from_values()
    print(f"Missing params error: {exc_info.value}")

    # Invalid radius value
    with pytest.raises(ValueError) as exc_info:
        RadiusCard.from_values(effective_radius=-1.0, spin_groups=[1])
    print(f"Invalid radius error: {exc_info.value}")

    # Inconsistent vary flags with radii
    with pytest.raises(ValueError) as exc_info:
        RadiusCard.from_values(
            effective_radius=3.200,
            true_radius=3.400,
            spin_groups=[1],
            vary_true=VaryFlag.USE_FROM_PARFILE,  # Can't use -1 when radii differ
        )
    print(f"Inconsistent flags error: {exc_info.value}")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
