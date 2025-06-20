import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.inp10_spingroups import Card10p2


@pytest.fixture
def spin_group_block1():
    return [
        "SPIN GROUPS",
        "  1      1    1  0.5 1.0000000",
        "    1  Inc Chan    0  0.5",
        "    2  PPair #2    2  1.5",
        "  2      1    1 -0.5 1.0000000",
        "    1  Inc Chan    1  0.5",
        "    2  PPair #4    1  0.5",
        "  3      1    1 -1.5 1.0000000",
        "    1  Inc Chan    1  0.5",
        "    2  PPair #4    1  0.5",
        "  4      1    2  1.5 1.0000000",
        "    1  Inc Chan    2  0.5",
        "    2  PPair #4    2  0.5",
        "    3  PPair #2    0  1.5",
        "  5      1    2  2.5 1.0000000",
        "    1  Inc Chan    2  0.5",
        "    2  PPair #4    2  0.5",
        "    3  PPair #2    0  2.5",
        "  6      1    2 -2.5 1.0000000",
        "    1  Inc Chan    3  0.5",
        "    2  PPair #4    3  0.5",
        "    3  PPair #2    1  2.5",
        "  7      1    2 -3.5 1.0000000",
        "    1  Inc Chan    3  0.5",
        "    2  PPair #4    3  0.5",
        "    3  PPair #2    1  2.5",
        "  8      1    0  0.0 0.0467000",
        "    1  Inc Ch#1    0  0.0",
        "  9      1    0  1.0 0.0467000",
        "    1  Inc Ch#1    0  1.0",
        " 10      1    0 -1.0 0.0467000",
        "    1  Inc Ch#1    1  0.0",
        " 11      1    0 -0.0 0.0467000",
        "    1  Inc Ch#1    1  1.0",
        " 12      1    0 -1.0 0.0467000",
        "    1  Inc Ch#1    1  1.0",
        " 13      1    0 -2.0 0.0467000",
        "    1  Inc Ch#1    1  1.0",
        " 14      1    0  2.0 0.0467000",
        "    1  Inc Ch#1    2  0.0",
        " 15      1    0  1.0 0.0467000",
        "    1  Inc Ch#1    2  1.0",
        " 16      1    0  2.0 0.0467000",
        "    1  Inc Ch#1    2  1.0",
        " 17      1    0  3.0 0.0467000",
        "    1  Inc Ch#1    2  1.0",
        " 18      1    0  0.5 0.0310000",
        "    1  Inc Ch#2    0  0.5",
        " 19      1    0 -0.5 0.0310000",
        "    1  Inc Ch#2    1  0.5",
        " 20      1    0 -1.5 0.0310000",
        "    1  Inc Ch#2    1  0.5",
        " 21      1    0  1.5 0.0310000",
        "    1  Inc Ch#2    2  0.5",
        " 22      1    0  2.5 0.0310000",
        "    1  Inc Ch#2    2  0.5",
        " 23 X    1    0  0.5 1.0000000",
        "    1  Inc Ch#3    0  0.5",
        " 24 X    1    0 -0.5 1.0000000",
        "    1  Inc Ch#3    1  0.5",
        " 25 X    1    0 -1.5 1.0000000",
        "    1  Inc Ch#3    1  0.5",
        " 26 X    1    0  1.5 1.0000000",
        "    1  Inc Ch#3    2  0.5",
        " 27 X    1    0  2.5 1.0000000",
        "    1  Inc Ch#3    2  0.5",
        " 28 X    1    0 -2.5 1.0000000",
        "    1  Inc Ch#3    3  0.5",
        " 29 X    1    0 -3.5 1.0000000",
        "    1  Inc Ch#3    3  0.5",
        ""
    ]


@pytest.fixture
def spin_group_block2():
    return [
        "SPIN GROUP INFORMATION",
        "  1      1    2  0.5 1.0000000",
        "    1    PPair1    0       0.5            9.42848000 8.42304405",
        "    2    PPair2    0         0            9.42848000 8.42304405",
        "    3    PPair2    0         0            9.42848000 8.42304405",
        "  2      1    0 -0.5 1.0000000",
        "    1    PPair1    1       0.5            9.42848000 8.42304405",
        "  3      1    0 -1.5 1.0000000",
        "    1    PPair1    1       0.5            9.42848000 8.42304405",
        "  4      1    0  1.5 1.0000000",
        "    1    PPair1    2       0.5            9.42848000 8.42304405",
        "  5      1    0  2.5 1.0000000",
        "    1    PPair1    2       0.5            9.42848000 8.42304405",
        ""
    ]


@pytest.fixture
def spin_group_block3():
    return [
        "SPIN GROUPS",
        "  1      1    0  0.5 1.0000000",
        "    1  Inc Chan    0  0.5",
        "    2  Inc Chan    0  0.5",
        "  2      1    0 -0.5 1.0000000",
        "    1  Inc Chan    1  0.5",
        "  3      1    0 -1.5 1.0000000",
        "    1  Inc Chan    1  0.5",
        "  4      1    0  1.5 1.0000000",
        "    1  Inc Chan    2  0.5",
        "  5      1    0  2.5 1.0000000",
        "    1  Inc Chan    2  0.5",
        "  6      1    0  0.5 0.0001000",
        "    1  Inc Ch#1    0  0.5",
        ""
    ]
    
@pytest.fixture
def spin_group_no_lines():
    """Fixture for a spin group block with no lines."""
    return []


@pytest.fixture
def fit_config():
    # Create a minimal FitConfig instance
    return FitConfig()

def test_spin_group_block1(fit_config, spin_group_block1):
    """ Read and parse a spin group block 1"""

    # Parse the lines from spin_group_block1 into the FitConfig
    Card10p2.from_lines(spin_group_block1, fit_config)    
    
    # Check if there are 29 spin groups
    assert len(fit_config.spin_groups) == 29
    
    