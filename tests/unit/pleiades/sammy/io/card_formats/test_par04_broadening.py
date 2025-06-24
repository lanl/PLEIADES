"""Unit tests for SAMMY parameter file - Card 10 (isotopes and abundances) classes."""

import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.par04_broadening import Card04


@pytest.fixture
def broadening_block1():
    return [
        "BROADENING PARAMETERS FOLLOW",
        "9.602     104.309   .002335   .024      -.020     .088       0 3 3 3 3",
        "1.0         1.0     1.0       0.1       0.1",
    ]


@pytest.fixture
def broadening_block2():
    return ["BROADENING PARAMETERS FOLLOW", "9.540     000.      0.10      0.038     0.010     0.0"]


@pytest.fixture
def broadening_block3():
    return [
        "BROADENING PARAMETERS FOLLOW",
        "9.45000000 300.00000 0.0000000 0.0263000 0.0000000 0.0100000 0 0-2 0 0 0",
        "0.0000100  0.0001000 0.0000100 0.0030000 0.0000100 0.0200000",
    ]


@pytest.fixture
def broadening_block_no_lines():
    return []


@pytest.fixture
def fit_config():
    # Create a minimal FitConfig instance
    return FitConfig()


def test_is_header_line():
    assert Card04.is_header_line("BROADENING")
    assert Card04.is_header_line("  BROADENING   ")
    assert not Card04.is_header_line(" BRADENING")
    assert not Card04.is_header_line("")


def test_bad_lines(fit_config):
    with pytest.raises(ValueError):
        Card04.from_lines(["BROADENING PARAMETERS FOLLOW", "INVALID LINE"], fit_config)


def test_bad_fit_config(fit_config, broadening_block3):
    with pytest.raises(ValueError):
        Card04.from_lines(broadening_block3, fit_config="")


def test_from_lines_empty_lines(fit_config):
    with pytest.raises(ValueError):
        Card04.from_lines([], fit_config)


def test_broadening_block1(fit_config, broadening_block1):
    Card04.from_lines(broadening_block1, fit_config)

    broadening_params = fit_config.physics_params.broadening_parameters

    assert broadening_params.crfn == 9.602
    assert broadening_params.temp == 104.309
    assert broadening_params.thick == 0.002335
    assert broadening_params.deltal == 0.024
    assert broadening_params.deltag == -0.020
    assert broadening_params.deltae == 0.088

    assert broadening_params.d_crfn == 1.0
    assert broadening_params.d_temp == 1.0
    assert broadening_params.d_thick == 1.0
    assert broadening_params.d_deltal == 0.1
    assert broadening_params.d_deltag == 0.1
    assert broadening_params.d_deltae is None


def test_broadening_block2(fit_config, broadening_block2):
    Card04.from_lines(broadening_block2, fit_config)

    broadening_params = fit_config.physics_params.broadening_parameters

    assert broadening_params.crfn == 9.540
    assert broadening_params.temp == 0.0
    assert broadening_params.thick == 0.1
    assert broadening_params.deltal == 0.038
    assert broadening_params.deltag == 0.010
    assert broadening_params.deltae == 0.0


def test_broadening_block3(fit_config, broadening_block3):
    Card04.from_lines(broadening_block3, fit_config)

    broadening_params = fit_config.physics_params.broadening_parameters

    assert broadening_params.crfn == 9.45000000
    assert broadening_params.temp == 300.00000
    assert broadening_params.thick == 0.0000000
    assert broadening_params.deltal == 0.0263000
    assert broadening_params.deltag == 0.0000000
    assert broadening_params.deltae == 0.0100000

    assert broadening_params.d_crfn == 0.00001
    assert broadening_params.d_temp == 0.0001
    assert broadening_params.d_thick == 0.0000100
    assert broadening_params.d_deltal == 0.0030000
    assert broadening_params.d_deltag == 0.0000100
    assert broadening_params.d_deltae == 0.02


def test_to_lines_from_lines_round_trip(fit_config, broadening_block1):
    Card04.from_lines(broadening_block1, fit_config)
    lines = Card04.to_lines(fit_config)
    fit_config_new = FitConfig()
    Card04.from_lines(lines, fit_config_new)
    assert fit_config_new.physics_params.broadening_parameters == fit_config.physics_params.broadening_parameters
