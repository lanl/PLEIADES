"""Unit tests for SAMMY parameter file - Card 1 (resonances) classes."""

import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.par01_resonances import Card01


@pytest.fixture
def resonance_block1():
    return [
        "RESONANCES are listed next",
        "-3661600.00 158770.000 3698500.+3  0.0000               0 0 1 0   1",
        "-873730.000 1025.30000 101.510000  0.0000               0 0 1 0   1",
        "-365290.000 1000.00000 30.4060000  0.0000               0 0 0 0   1",
        "-63159.0000 1000.00000 46.8940000  0.0000               0 0 0 0   1",
        "-48801.0000 1000.00000 9.24960000  0.0000               0 0 0 0   1",
        "31739.99805 1000.00000 15.6670000  0.0000     0.0000    0 0 0 0 0 5",
        "55676.96094 1580.30000 653310.000  0.0000               0 0 0 0   1",
        "67732.84375 2500.00000 2658.90000  0.0000               0 0 0 0   3",
        "70800.00781 1000.00000 29.6170000  0.0000     0.0000    0 0 0 0 0 5",
        "86797.35938 2500.00000 726.180000  0.0000               0 0 0 0   3",
        "181617.5000 5600.00000 34894000.0  0.0000               0 0 0 0   1",
        "298700.0000 1000.00000 9886.00000  0.0000     0.0000    0 0 0 0 0 5",
        "301310.8125 3600.00000 2354.80000  0.0000               0 0 0 0   1",
        "354588.6875 1000.00000 14460.0000  0.0000     0.0000    0 0 0 0 0 5",
        "399675.9375 660.000000 813.610000  0.0000               0 0 0 0   3",
        "532659.8750 2500.00000 532810.000  0.0000               0 0 0 0   3",
        "565576.8750 2900.00000 10953000.0  0.0000               0 0 0 0   3",
        "587165.7500 8800.00000 199160.000  0.0000               0 0 0 0   2",
        "590290.1250 3600.00000 523660.000  0.0000               0 0 0 0   1",
        "602467.3125 3400.00000 50491.0000  0.0000     0.0000    0 0 0 0 0 4",
        "714043.4375 2500.00000 1216.50000  0.0000               0 0 0 0   3",
        "771711.9375 1000.00000 53139.0000  0.0000     0.0000    0 0 0 0 0 5",
        "812491.6250 9700.00000 30100000.0  0.0000               0 0 0 0   3",
        "845233.8750 2000.00000 397910.000  0.0000     0.0000    0 0 0 0 0 4",
        "872305.8125 1300.00000 32140.0000  0.0000     0.0000    0 0 0 0 0 5",
    ]


@pytest.fixture
def resonance_block2():
    return [
        "RESONANCES are listed next",
        "-61367.0000 2000.00000 43910000.0                       1 0 1     1 5000.00000",
        "-4400.00000 1400.00000 819820.000                       1 0 1     1 2000.00000",
        "13317.00000 790.000000 7425.10000                       1 0 1     2 2.00000000",
        "13637.00000 490.000000 1073.10000                       1 0 1     3 3.00000000",
        "15310.00000 970.000000 1332100.00                       1 0 1     1 30.0000000",
        "20024.00000 370.000000 1388.50000                       0 0 0     2",
        "21144.00000 460.000000 2116.00000                       0 0 0     3",
        "26643.00000 720.000000 1462.50000                       0 0 0     3",
        "32268.00000 1000.00000 300.000000                       0 0 0     3",
        "32397.00000 1620.00000 17612.0000                       0 0 0     2",
        "34242.00000 740.000000 800.000000                       0 0 0     3",
        "36133.00000 1720.00000 17782.0000                       1 0 1     1 5.00000000",
        "39552.00000 1350.00000 550.000000                       0 0 0     4",
        "47901.00000 810.000000 4517.10000                       0 0 0     3",
        "51906.00000 1500.00000 400.000000                       0 0 0     5",
        "52226.00000 1230.00000 1000.00000                       0 0 0     4",
        "58700.00000 640.000000 800.000000                       0 0 1     3",
        "60149.00000 440.000000 16460.0000                       0 0 1     3",
        "61790.00000 1870.00000 17229.0000                       0 0 0     2",
        "63295.00000 3500.00000 3711000.00                       1 0 1     1 50.0000000",
    ]


@pytest.fixture
def resonance_block_bad():
    return ["RESONANCES are listed next", "1.0 2.0 3.0 4.0 5.0 6.0 7.0 8.0 9.0 10.0 11.0 12.0 13.0 14.0 15.0 16.0"]


@pytest.fixture
def resonance_block_empty():
    return []


@pytest.fixture
def fit_config():
    # Create a minimal FitConfig instance
    return FitConfig()


def test_is_header_line():
    assert Card01.is_header_line("RESONANCES")
    assert Card01.is_header_line("  RESONANCES   ")
    assert not Card01.is_header_line("NOT A HEADER")
    assert not Card01.is_header_line("")


def test_from_lines_empty_lines(fit_config):
    with pytest.raises(ValueError):
        Card01.from_lines([], fit_config)


def test_from_lines_bad_fit_config(resonance_block1):
    with pytest.raises(ValueError):
        Card01.from_lines(resonance_block1, fit_config=None)
    with pytest.raises(ValueError):
        Card01.from_lines(resonance_block1, fit_config="not_a_fit_config")


def test_resonance_block1(fit_config, resonance_block1):
    Card01.from_lines(resonance_block1, fit_config)

    # Check that an isotope "UNKN" was created
    assert fit_config.nuclear_params.isotopes
    assert len(fit_config.nuclear_params.isotopes) == 1
    assert fit_config.nuclear_params.isotopes[0].isotope_information.name == "UNKN"

    # check that resonances were appended to the isotope
    assert fit_config.nuclear_params.isotopes[0].resonances
    assert len(fit_config.nuclear_params.isotopes[0].resonances) == 25


def test_resonance_block2(fit_config, resonance_block2):
    Card01.from_lines(resonance_block2, fit_config)

    # Check that an isotope "UNKN" was created
    assert fit_config.nuclear_params.isotopes
    assert len(fit_config.nuclear_params.isotopes) == 1
    assert fit_config.nuclear_params.isotopes[0].isotope_information.name == "UNKN"

    # check that resonances were appended to the isotope
    assert fit_config.nuclear_params.isotopes[0].resonances
    assert len(fit_config.nuclear_params.isotopes[0].resonances) == 20
