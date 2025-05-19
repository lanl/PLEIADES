"""Unit tests for SAMMY parameter file - Card 10 (isotopes and abundances) classes."""

import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.par10_isotopes import Card10


@pytest.fixture
def standard_format_lines_silicon():
    return [
        "ISOTOPIC MASSES AND ABUNDANCES FOLLOW",
        " 27.976929 1.0000000  .9200    1 1 2 3 4 5 6 7",
        " 28.976496  .0467000  .0500    1 8 91011121314151617",
        " 29.973772  .0310000  .0200    11819202122",
        " 16.000000 1.0000000  .0100000 023242526272829",
    ]


@pytest.fixture
def extended_format_lines_ta181_U235_u238():
    return [
        "ISOTOPIC ABUNDANCES FOLLOW",
        "   180.948       0.2      0.02    1    1    2    3    4    5    6    7    8   -1",
        "    9   10   11   12   13   14   15   16   17   18   19   20   21   22   23   -1",
        "   24   25   26   27   28   29   30   31   32   33   34   35   36   37   38   -1",
        "   39   40   41   42   43   44   45   46   47   48",
        "   235.044       0.2     0.025    1   49   50   51   52   53   54   55   56   -1",
        "   57   58   59   60   61   62   63   64   65   66   67   68   69   70   71   -1",
        "   72   73   74   75   76   77   78   79   80   81   82   83   84   85   86   -1",
        "   87   88   89   90   91   92   93   94   95   96",
        "   238.051       0.4      0.04    1   97   98   99  100  101",
    ]


@pytest.fixture
def standard_format_lines_tr102():
    return [
        "ISOTOPIC ABUNDANCES FOLLOW",
        "   64.9278       0.3      0.03 1 1 2 3 4 5 6                                    ",
        "   59.9308      0.25     0.025 1 7 8 9101112131415                              ",
        "   244.064       0.2      0.02 116                                              ",
        "   87.9051       0.4      0.04 117181920212223                                  ",
    ]


@pytest.fixture
def mixed_format_lines_ta181_u238():
    return [
        "ISOTOPIC ABUNDANCES                                                             ",
        "   180.948       0.2      0.02 1 1 2 3 4 5 6 7 8 91011121314151617181920212223-1",
        "   24   25   26   27   28   29   30   31   32   33   34   35   36   37   38   -1",
        "   39   40   41   42   43   44   45   46   47   48                              ",
        "   238.051       0.4      0.04 14950515253        ",
    ]


@pytest.fixture
def mixed_format_lines_ta181():
    return [
        "ISOTOPIC ABUNDANCES                                                             ",
        "   180.948         1         0 0 1 2 3 4 5 6 7 8 91011121314151617181920212223-1",
        "   24   25   26   27   28   29   30   31   32   33   34   35   36   37   38   -1",
        "   39   40   41   42   43   44   45   46   47   48                               ",
    ]


def test_standard_format_silicon(standard_format_lines_silicon):
    fit_config = FitConfig()
    Card10.from_lines(standard_format_lines_silicon, fit_config)
    isotopes = fit_config.nuclear_params.isotopes
    assert len(isotopes) == 4
    masses = [round(iso.isotope_information.mass_data.atomic_mass, 6) for iso in isotopes]
    assert 27.976929 in masses
    assert 28.976496 in masses
    assert 29.973772 in masses
    assert 16.0 in masses
    # Check abundances
    abundances = [iso.abundance for iso in isotopes]
    assert pytest.approx(1.0) in abundances
    assert pytest.approx(0.0467, rel=1e-3) in abundances


def test_extended_format_ta181_U235_u238(extended_format_lines_ta181_U235_u238):
    fit_config = FitConfig()
    Card10.from_lines(extended_format_lines_ta181_U235_u238, fit_config)
    isotopes = fit_config.nuclear_params.isotopes
    assert len(isotopes) == 3
    masses = [round(iso.isotope_information.mass_data.atomic_mass, 3) for iso in isotopes]
    assert 180.948 in masses
    assert 235.044 in masses
    assert 238.051 in masses


def test_standard_format_tr102(standard_format_lines_tr102):
    fit_config = FitConfig()
    Card10.from_lines(standard_format_lines_tr102, fit_config)
    isotopes = fit_config.nuclear_params.isotopes
    assert len(isotopes) == 4
    masses = [round(iso.isotope_information.mass_data.atomic_mass, 4) for iso in isotopes]
    assert 64.9278 in masses
    assert 59.9308 in masses
    assert 244.064 in masses
    assert 87.9051 in masses


def test_mixed_format_ta181_u238(mixed_format_lines_ta181_u238):
    fit_config = FitConfig()
    Card10.from_lines(mixed_format_lines_ta181_u238, fit_config)
    isotopes = fit_config.nuclear_params.isotopes
    assert len(isotopes) == 2
    masses = [round(iso.isotope_information.mass_data.atomic_mass, 3) for iso in isotopes]
    assert 180.948 in masses
    assert 238.051 in masses


def test_invalid_header_raises():
    lines = ["INVALID HEADER", " 27.976929 1.0000000  .9200    1 1 2 3 4 5 6 7"]
    fit_config = FitConfig()
    with pytest.raises(ValueError):
        Card10.from_lines(lines, fit_config)
