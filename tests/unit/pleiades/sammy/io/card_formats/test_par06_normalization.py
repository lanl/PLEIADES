"""Unit tests for SAMMY parameter file - Card 6 (normalization) classes."""

import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.par06_normalization import Card06
from pleiades.utils.helper import VaryFlag


@pytest.fixture
def normalization_block1():
    return [
        "NORMALIZATION AND CONSTANT BACKGROUND FOLLOW",
        "1.00000000 .00700000 0.        0.        0.        0.        0 0 0 0 0 0",
        ".100000000 .00100000 0.        0.        0.        0.        ",
    ]


@pytest.fixture
def normalization_block2():
    return [
        "NORMALIZATION AND CONSTANT BACKGROUND FOLLOW",
        "1.0000000 0.00000100 0.0000010 0.0000010 0.        0.        1 1 1 1 0 0",
        "0.0300100 0.00001000 0.0000100 0.0000100 0.        0.       ",
    ]


@pytest.fixture
def normalization_block3():
    return [
        "NORMALIZATION AND CONSTANT BACKGROUND FOLLOW",
        ".944398457 .00703768 0.        0.        0.        0.        1 1 0 0 0 0",
        ".094439847 .00070377 0.        0.        0.        0.       ",
    ]


@pytest.fixture
def normalization_block_no_lines():
    return []


@pytest.fixture
def fit_config():
    # Create a minimal FitConfig instance
    return FitConfig()


def test_is_header_line():
    assert Card06.is_header_line("NORMALIZATION")
    assert Card06.is_header_line("  NORMALIZATION   ")
    assert not Card06.is_header_line(" BACKGROUND?")
    assert not Card06.is_header_line("")


def test_bad_lines(fit_config):
    with pytest.raises(ValueError):
        Card06.from_lines(["NORMALIZATION AND CONSTANT BACKGROUND FOLLOW", "INVALID LINE"], fit_config)


def test_bad_fit_config(fit_config, normalization_block3):
    with pytest.raises(ValueError):
        Card06.from_lines(normalization_block3, fit_config="")


def test_from_lines_empty_lines(fit_config):
    with pytest.raises(ValueError):
        Card06.from_lines([], fit_config)


def test_normalization_block1(fit_config, normalization_block1):
    Card06.from_lines(normalization_block1, fit_config)

    normalization_params = fit_config.physics_params.normalization_parameters

    assert normalization_params.anorm == 1.000
    assert normalization_params.backa == 0.007
    assert normalization_params.backb == 0.0
    assert normalization_params.backc == 0.0
    assert normalization_params.backd == 0.0
    assert normalization_params.backf == 0.0
    assert normalization_params.flag_anorm is VaryFlag.NO
    assert normalization_params.flag_backa is VaryFlag.NO
    assert normalization_params.flag_backb is VaryFlag.NO
    assert normalization_params.flag_backc is VaryFlag.NO
    assert normalization_params.flag_backd is VaryFlag.NO
    assert normalization_params.flag_backf is VaryFlag.NO

    assert normalization_params.d_anorm == 0.1
    assert normalization_params.d_backa == 0.001
    assert normalization_params.d_backb == 0.0
    assert normalization_params.d_backc == 0.0
    assert normalization_params.d_backd == 0.0
    assert normalization_params.d_backf == 0.0


def test_normalization_block2(fit_config, normalization_block2):
    Card06.from_lines(normalization_block2, fit_config)

    normalization_params = fit_config.physics_params.normalization_parameters

    assert normalization_params.anorm == 1.000
    assert normalization_params.backa == 0.00000100
    assert normalization_params.backb == 0.000001
    assert normalization_params.backc == 0.000001
    assert normalization_params.backd == 0.0
    assert normalization_params.backf == 0.0
    assert normalization_params.flag_anorm is VaryFlag.YES
    assert normalization_params.flag_backa is VaryFlag.YES
    assert normalization_params.flag_backb is VaryFlag.YES
    assert normalization_params.flag_backc is VaryFlag.YES
    assert normalization_params.flag_backd is VaryFlag.NO
    assert normalization_params.flag_backf is VaryFlag.NO

    assert normalization_params.d_anorm == 0.030010
    assert normalization_params.d_backa == 0.00001
    assert normalization_params.d_backb == 0.00001
    assert normalization_params.d_backc == 0.00001
    assert normalization_params.d_backd == 0.0
    assert normalization_params.d_backf == 0.0


def test_broadening_block3(fit_config, normalization_block3):
    Card06.from_lines(normalization_block3, fit_config)

    normalization_params = fit_config.physics_params.normalization_parameters

    assert normalization_params.anorm == 0.944398457
    assert normalization_params.backa == 0.00703768
    assert normalization_params.backb == 0.0
    assert normalization_params.backc == 0.0
    assert normalization_params.backd == 0.0
    assert normalization_params.backf == 0.0
    assert normalization_params.flag_anorm is VaryFlag.YES
    assert normalization_params.flag_backa is VaryFlag.YES
    assert normalization_params.flag_backb is VaryFlag.NO
    assert normalization_params.flag_backc is VaryFlag.NO
    assert normalization_params.flag_backd is VaryFlag.NO
    assert normalization_params.flag_backf is VaryFlag.NO

    assert normalization_params.d_anorm == 0.094439847
    assert normalization_params.d_backa == 0.00070377
    assert normalization_params.d_backb == 0.0
    assert normalization_params.d_backc == 0.0
    assert normalization_params.d_backd == 0.0
    assert normalization_params.d_backf == 0.0


def test_to_lines_from_lines_round_trip(fit_config, normalization_block1):
    Card06.from_lines(normalization_block1, fit_config)
    lines = Card06.to_lines(fit_config)
    fit_config_new = FitConfig()
    Card06.from_lines(lines, fit_config_new)
    assert fit_config_new.physics_params.normalization_parameters == fit_config.physics_params.normalization_parameters
