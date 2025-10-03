"""Unit tests for SAMMY input file - Card 07a (radii) classes."""

import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.par07a_radii import Card07a
from pleiades.utils.helper import VaryFlag


@pytest.fixture
def radii_key_word_block1():
    return [
        "Channel radii in key-word format",
        "Radii=  4.136420,  4.136420    Flags=0,0",
        "   Group=  1   Chan=  1,  2,",
        "   Group=  4   Chan=  1,  2,  3,",
        "   Group=  5   Chan=  1,  2,  3,",
        "Radii=  4.943720,  4.943720    Flags=0,0",
        "   Group=  2   Chan=  1,  2,",
        "   Group=  3   Chan=  1,  2,",
        "   Group=  6   Chan=  1,  2,  3,",
        "   Group=  7   Chan=  1,  2,  3,",
        "Radii=  4.400000,  4.400000    Flags=0,0",
        "   Group=  8   Chan=  1,",
        "   Group=  9   Chan=  1,",
        "   Group= 10   Chan=  1,",
        "   Group= 11   Chan=  1,",
        "   Group= 12   Chan=  1,",
        "   Group= 13   Chan=  1,",
        "   Group= 14   Chan=  1,",
        "   Group= 15   Chan=  1,",
        "   Group= 16   Chan=  1,",
        "   Group= 17   Chan=  1,",
        "Radii=  4.200000,  4.200000    Flags=0,0",
        "   Group= 18   Chan=  1,",
        "   Group= 19   Chan=  1,",
        "   Group= 20   Chan=  1,",
        "   Group= 21   Chan=  1,",
        "   Group= 22   Chan=  1,",
        "Radii=  4.200000,  4.200000    Flags=0,0",
        "   Group= 23   Chan=  1,",
        "   Group= 24   Chan=  1,",
        "   Group= 25   Chan=  1,",
        "   Group= 26   Chan=  1,",
        "   Group= 27   Chan=  1,",
        "   Group= 28   Chan=  1,",
        "   Group= 29   Chan=  1,",
    ]


@pytest.fixture
def radii_key_word_block2():
    return [
        "Channel radii in key-word format",
        "Radii=  6.303510,  6.303510    Flags=0, 0",
        "   Group=  1   Chan=  1,",
        "   Group=  4   Chan=  1,",
        "   Group=  5   Chan=  1,",
        "Radii=  4.233810,  4.233810    Flags=0, 0",
        "   Group=  2   Chan=  1,",
        "   Group=  3   Chan=  1,",
        "Radii=  3.570000,  3.570000    Flags=0, 0",
        "   Group=  6   Chan=  1,",
    ]


@pytest.fixture
def radii_key_word_block3():
    return [
        "Channel radii in key-word format",
        "Radii=  9.602000,  9.602000    Flags=0, 0",
        "   Group=  1   Chan=  1,  2,  3,",
        "   Group=  2   Chan=  1,  2,  3,",
        "   Group=  3   Chan=  1,",
        "   Group=  4   Chan=  1,",
        "   Group=  5   Chan=  1,",
        "   Group=  6   Chan=  1,",
        "   Group=  7   Chan=  1,",
        "   Group=  8   Chan=  1,",
        "   Group=  9   Chan=  1,",
        "   Group= 10   Chan=  1,",
        "   Group= 11   Chan=  1,",
        "   Group= 12   Chan=  1,",
        "   Group= 13   Chan=  1,",
        "   Group= 14   Chan=  1,",
        "   Group= 15   Chan=  1,",
        "   Group= 16   Chan=  1,",
        "   Group= 17   Chan=  1,",
        "   Group= 18   Chan=  1,",
        "   Group= 19   Chan=  1,",
        "   Group= 20   Chan=  1,",
        "   Group= 21   Chan=  1,",
        "   Group= 22   Chan=  1,",
        "   Group= 23   Chan=  1,",
        "   Group= 24   Chan=  1,",
        "   Group= 25   Chan=  1,",
        "   Group= 26   Chan=  1,",
        "   Group= 27   Chan=  1,",
        "   Group= 28   Chan=  1,",
        "   Group= 29   Chan=  1,",
        "   Group= 30   Chan=  1,",
        "   Group= 31   Chan=  1,",
        "   Group= 32   Chan=  1,",
        "   Group= 33   Chan=  1,",
        "   Group= 34   Chan=  1,",
        "   Group= 35   Chan=  1,",
        "   Group= 36   Chan=  1,",
        "   Group= 37   Chan=  1,",
        "   Group= 38   Chan=  1,",
        "   Group= 39   Chan=  1,",
        "   Group= 40   Chan=  1,",
        "   Group= 41   Chan=  1,",
        "   Group= 42   Chan=  1,",
        "   Group= 43   Chan=  1,",
        "   Group= 44   Chan=  1,",
        "   Group= 45   Chan=  1,",
        "   Group= 46   Chan=  1,",
        "   Group= 47   Chan=  1,",
        "   Group= 48   Chan=  1,",
    ]


@pytest.fixture
def blank_block():
    return []


@pytest.fixture
def fit_config():
    # Create a minimal FitConfig instance
    return FitConfig()


def test_radii_block1(fit_config, radii_key_word_block1):
    Card07a.from_lines(radii_key_word_block1, fit_config=fit_config)

    assert len(fit_config.nuclear_params.isotopes[0].radius_parameters) == 5

    # Check the values of the first radius parameter
    first_radius_param = fit_config.nuclear_params.isotopes[0].radius_parameters[0]
    assert first_radius_param.effective_radius == 4.136420
    assert first_radius_param.true_radius == 4.136420
    assert first_radius_param.vary_effective == VaryFlag.NO

    # grab all the channels from each radius parameter using the new SpinGroupChannels structure
    total_number_of_sping_groups = 0
    total_number_of_channels = 0
    for radius_param in fit_config.nuclear_params.isotopes[0].radius_parameters:
        if radius_param.spin_groups:
            total_number_of_sping_groups += len(radius_param.spin_groups)
            for spin_group_channels in radius_param.spin_groups:
                number_of_channels = len(spin_group_channels.channels)
                total_number_of_channels += number_of_channels

    assert total_number_of_sping_groups == 29
    assert total_number_of_channels == 40


def test_radii_block2(fit_config, radii_key_word_block2):
    Card07a.from_lines(radii_key_word_block2, fit_config=fit_config)

    assert len(fit_config.nuclear_params.isotopes[0].radius_parameters) == 3

    # Check the values of the first radius parameter
    first_radius_param = fit_config.nuclear_params.isotopes[0].radius_parameters[0]
    assert first_radius_param.effective_radius == 6.303510
    assert first_radius_param.true_radius == 6.303510
    assert first_radius_param.vary_effective == VaryFlag.NO
    assert first_radius_param.vary_true == VaryFlag.NO

    # grab all the spin groups and channels from each radius parameter
    total_number_of_spin_groups = 0
    total_number_of_channels = 0
    for radius_param in fit_config.nuclear_params.isotopes[0].radius_parameters:
        if radius_param.spin_groups:
            total_number_of_spin_groups += len(radius_param.spin_groups)
            for spin_group_channels in radius_param.spin_groups:
                number_of_channels = len(spin_group_channels.channels)
                total_number_of_channels += number_of_channels

    assert total_number_of_spin_groups == 6  # Groups 1, 4, 5, 2, 3, 6
    assert total_number_of_channels == 6  # All groups have 1 channel each


def test_radii_block3(fit_config, radii_key_word_block3):
    Card07a.from_lines(radii_key_word_block3, fit_config=fit_config)

    assert len(fit_config.nuclear_params.isotopes[0].radius_parameters) == 1

    # Check the values of the first radius parameter
    first_radius_param = fit_config.nuclear_params.isotopes[0].radius_parameters[0]
    assert first_radius_param.effective_radius == 9.602000
    assert first_radius_param.true_radius == 9.602000
    assert first_radius_param.vary_effective == VaryFlag.NO
    assert first_radius_param.vary_true == VaryFlag.NO

    # grab all the spin groups and channels from each radius parameter
    total_number_of_spin_groups = 0
    total_number_of_channels = 0
    for radius_param in fit_config.nuclear_params.isotopes[0].radius_parameters:
        if radius_param.spin_groups:
            total_number_of_spin_groups += len(radius_param.spin_groups)
            for spin_group_channels in radius_param.spin_groups:
                number_of_channels = len(spin_group_channels.channels)
                total_number_of_channels += number_of_channels

    assert total_number_of_spin_groups == 48  # Groups 1-48
    assert (
        total_number_of_channels == 52
    )  # Group 1: 3 channels, Group 2: 3 channels, Groups 3-48: 1 channel each (3+3+46=52)


def test_blank_block(fit_config, blank_block):
    with pytest.raises(ValueError):
        Card07a.from_lines(blank_block, fit_config=fit_config)


def test_radii_block1_round_trip(fit_config, radii_key_word_block1):
    Card07a.from_lines(radii_key_word_block1, fit_config)
    lines = Card07a.to_lines(fit_config)

    # check if "channel" is in the first line.
    assert any("channel" in line.lower() for line in lines)

    # check if radii are listed in any of the lines
    assert any("4.13642" in line for line in lines)
    assert any("4.94372" in line for line in lines)
    assert any("4.400" in line for line in lines)

    fit_config_2 = FitConfig()
    Card07a.from_lines(lines, fit_config_2)

    # Check if the second fit_config is equivalent to the first
    assert fit_config == fit_config_2
