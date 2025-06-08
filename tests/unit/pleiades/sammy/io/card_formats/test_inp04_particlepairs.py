# Copyright 2024, PLEIADES Project
import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.inp04_particlepairs import Card04


@pytest.fixture
def particle_pair_block1():
    return [
        "PARTICLE PAIR DEFINITIONS",
        "Name=PPair1       Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=73         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5     Ma=   1.008664915780000     Mb= 180.948029999999989",
        "",
    ]


@pytest.fixture
def particle_pair_block2():
    return [
        "PARTICLE PAIR DEFINITIONS",
        "Name=PPair1       ",
        "     Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=73         ",
        "     Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5    ",
        "      Ma=   1.008664915780000     Mb= 180.948029999999989",
        "Name=PPair2       ",
        "     Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=92         ",
        "     Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   0.0     ",
        "     Ma=   1.008664915780000     Mb= 238.050972113574687",
        "Name=PPair3       ",
        "     Particle a=fission       Particle b=fission ",
        "     Za= 0        Zb= 0         ",
        "     Pent=0     Shift=0",
        "     Sa=  0.0     Sb=   0.0     ",
        "     Ma=   0.000000000000000     Mb=   0.000000000000000",
        "",
    ]


@pytest.fixture
def particle_pair_block3():
    return [
        "PARTICLE PAIR DEFINITIONS",
        "Name=PPair1       Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=73         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5     Ma=   1.008664915780000     Mb= 180.948029999999989",
        "Name=PPair2       Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=92         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5     Ma=   1.008664915780000     Mb= 235.043940266651362",
        "Name=PPair3       Particle a=fission       Particle b=fission ",
        "     Za= 0        Zb= 0         Pent=0     Shift=0",
        "     Sa=  0.0     Sb=   0.0     Ma=   0.000000000000000     Mb=   0.000000000000000",
        "Name=PPair4       Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=92         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   0.0     Ma=   1.008664915780000     Mb= 238.050972113574687",
        "Name=PPair5       Particle a=fission       Particle b=fission ",
        "     Za= 0        Zb= 0         Pent=0     Shift=0",
        "     Sa=  0.0     Sb=   0.0     Ma=   0.000000000000000     Mb=   0.000000000000000",
        "",
    ]


@pytest.fixture
def particle_pair_block4():
    return [
        "PARTICLE PAIR DEFINITIONS",
        "Name=PPair1       ",
        "     Particle a=neutron       ",
        "     Particle b=Other   ",
        "     Za= 0        ",
        "     Zb=29         ",
        "     Pent=1     ",
        "     Shift=0",
        "     Sa=  0.5     ",
        "     Sb=  -1.5     ",
        "     Ma=   1.008664915780000     ",
        "     Mb=  64.927790888706070",
        "Name=PPair2       ",
        "     Particle a=neutron       ",
        "     Particle b=Other   ",
        "     Za= 0        ",
        "     Zb=28         ",
        "     Pent=1     ",
        "     Shift=0",
        "     Sa=  0.5     ",
        "     Sb=   0.0     ",
        "     Ma=   1.008664915780000     ",
        "     Mb=  59.930834635984482",
        "Name=PPair3       ",
        "     Particle a=neutron       ",
        "     Particle b=Other   ",
        "     Za= 0        ",
        "     Zb=94         ",
        "     Pent=1     ",
        "     Shift=0",
        "     Sa=  0.5     ",
        "     Sb=   0.0     ",
        "     Ma=   1.008664915780000     ",
        "     Mb= 244.063623676539294",
        "Name=PPair4       ",
        "     Particle a=fission       ",
        "     Particle b=fission ",
        "     Za= 0        ",
        "     Zb= 0         ",
        "     Pent=0     ",
        "     Shift=0",
        "     Sa=  0.0     ",
        "     Sb=   0.0     ",
        "     Ma=   0.000000000000000     ",
        "     Mb=   0.000000000000000",
        "Name=PPair5       ",
        "     Particle a=neutron       ",
        "     Particle b=Other   ",
        "     Za= 0        ",
        "     Zb=38         ",
        "     Pent=1     ",
        "     Shift=0",
        "     Sa=  0.5     ",
        "     Sb=   0.0    ",
        "     Ma=   1.008664915780000     ",
        "     Mb=  87.905611396088261",
        "",
    ]


@pytest.fixture
def fit_config():
    # Create a minimal FitConfig instance
    return FitConfig()


# Simple parametrized test to run keyword parsing and multiline field tests on all fixtures
@pytest.mark.parametrize(
    "block_fixture",
    [
        "particle_pair_block1",
        "particle_pair_block2",
        "particle_pair_block3",
        "particle_pair_block4",
    ],
)
def test_keyword_and_multiline_on_all_blocks(block_fixture, fit_config, request):
    lines = request.getfixturevalue(block_fixture)
    Card04.from_lines(lines, fit_config)
    # Access particle pairs through isotopes (FitConfig.nuclear_params.isotopes is a list of IsotopeParameters)
    found = []
    for iso in fit_config.nuclear_params.isotopes:
        if hasattr(iso, "particle_pairs") and iso.particle_pairs:
            found.extend(iso.particle_pairs)
    assert found, f"No particle pairs parsed for {block_fixture}"
    # Check that all pairs have required fields
    for pair in found:
        assert pair.name
        assert pair.name_a
        assert pair.name_b
        assert pair.mass_a is not None
        assert pair.mass_b is not None
        assert pair.charge_a is not None
        assert pair.charge_b is not None
        assert pair.spin_a is not None
        assert pair.spin_b is not None


def test_keyword_parsing_simple(fit_config):
    lines = [
        "PARTICLE PAIR DEFINITIONS",
        "Name=Inc Ch#1     Particle a=neutron       Particle b=Other",
        "     Za= 0        Zb= 0         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   0.0     Ma=   1.008664915780000     Mb=  57.935000000000",
        "     Q-value = 92935.45",
        "",
    ]
    Card04.from_lines(lines, fit_config)
    found = [p for iso in fit_config.nuclear_params.isotopes for p in iso.particle_pairs]
    assert found, "No particle pairs parsed"
    pair = found[0]
    assert pair.name == "Inc Ch#1"
    assert pair.q_value == pytest.approx(92935.45)
    assert pair.mass_b == pytest.approx(57.935)
    assert pair.charge_a == 0
    assert pair.charge_b == 0
    assert pair.spin_a == 0.5
    assert pair.spin_b == 0.0
    assert pair.calculate_penetrabilities is True
    assert pair.calculate_shifts is False


def test_multiline_split_fields(fit_config):
    lines = [
        "PARTICLE PAIR DEFINITIONS",
        "Name=PPair1       ",
        "     Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=73         ",
        "     Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5    ",
        "      Ma=   1.008664915780000     Mb= 180.948029999999989",
        "",
    ]
    Card04.from_lines(lines, fit_config)
    found = [p for iso in fit_config.nuclear_params.isotopes for p in iso.particle_pairs]
    assert found, "No particle pairs parsed"
    pair = found[-1]
    assert pair.name == "PPair1"
    assert pair.name_a == "neutron"
    assert pair.name_b == "Other"
    assert pair.mass_b == pytest.approx(180.948029999999989)
    assert pair.charge_b == 73
    assert pair.spin_b == 3.5


def test_multiple_pairs(fit_config):
    lines = [
        "PARTICLE PAIR DEFINITIONS",
        "Name=PPair1       Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=73         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5     Ma=   1.008664915780000     Mb= 180.948029999999989",
        "Name=PPair2       Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=92         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5     Ma=   1.008664915780000     Mb= 235.043940266651362",
        "",
    ]
    Card04.from_lines(lines, fit_config)
    found = [p for iso in fit_config.nuclear_params.isotopes for p in iso.particle_pairs]
    assert len(found) >= 2
    assert found[0].name == "PPair1"
    assert found[1].name == "PPair2"
    assert found[1].mass_b == pytest.approx(235.043940266651362)


def test_qvalue_variants(fit_config):
    lines = [
        "PARTICLE PAIR DEFINITIONS",
        "Name=PPairQ       Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=73         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5     Ma=   1.008664915780000     Mb= 180.948029999999989",
        "     Q-V = 123.45",
        "     QVAL= 543.21",
        "     Q= 999.99",
        "",
    ]
    Card04.from_lines(lines, fit_config)
    found = [p for iso in fit_config.nuclear_params.isotopes for p in iso.particle_pairs]
    # The last Q=... should win if multiple present
    assert found[-1].q_value == pytest.approx(999.99)


def test_threshold(fit_config):
    lines = [
        "PARTICLE PAIR DEFINITIONS",
        "Name=PPairT       Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=73         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5     Ma=   1.008664915780000     Mb= 180.948029999999989",
        "     THreshold = 42.0",
        "",
    ]
    Card04.from_lines(lines, fit_config)
    found = [p for iso in fit_config.nuclear_params.isotopes for p in iso.particle_pairs]
    assert found[-1].threshold == pytest.approx(42.0)


def test_to_lines_roundtrip(fit_config):
    # Test that to_lines produces a string that can be parsed again
    lines = [
        "PARTICLE PAIR DEFINITIONS",
        "Name=PPair1       Particle a=neutron       Particle b=Other   ",
        "     Za= 0        Zb=73         Pent=1     Shift=0",
        "     Sa=  0.5     Sb=   3.5     Ma=   1.008664915780000     Mb= 180.948029999999989",
        "     Q= 123.456",
        "",
    ]
    Card04.from_lines(lines, fit_config)
    # Now convert back to lines
    out_lines = Card04.to_lines(fit_config)
    assert any("Q=" in line for line in out_lines)
    # Parse again
    fit_config2 = fit_config.__class__()
    Card04.from_lines(out_lines, fit_config2)
    found = [p for iso in fit_config2.nuclear_params.isotopes for p in iso.particle_pairs]
    assert found[-1].q_value == pytest.approx(123.456)


def test_particle_pair_blocks_all(block_fixture, expected_count, fit_config, request):
    lines = request.getfixturevalue(block_fixture)
    Card04.from_lines(lines, fit_config)
    found = [p for iso in fit_config.nuclear_params.isotopes for p in iso.particle_pairs]
    assert len(found) == expected_count
    for pair in found:
        assert pair.name
        assert pair.mass_a is not None
        assert pair.mass_b is not None
        assert pair.charge_a is not None
        assert pair.charge_b is not None
        assert pair.spin_a is not None
        assert pair.spin_b is not None
