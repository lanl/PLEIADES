#!/usr/bin/env python
import pytest

from pleiades.sammy.parameters.orres import (
    BurstParameters,
    LithiumParameters,
    TantalumParameters,
    VaryFlag,
    WaterParameters,
)


@pytest.fixture
def basic_burst_input():
    # Column:   1----5-7--10--------20--------30
    return ["BURST 1   12.345    0.123"]


@pytest.fixture
def burst_no_uncertainty():
    # Column:   1----5-7--10--------20
    return ["BURST 0   45.678"]


@pytest.fixture
def burst_with_pup():
    # Column:   1----5-7--10--------20--------30
    return ["BURST 3   98.765    0.246"]


def test_parse_basic_burst(basic_burst_input):
    params = BurstParameters.from_lines(basic_burst_input)
    assert params.burst == pytest.approx(12.345)
    assert params.flag_burst == VaryFlag.YES
    assert params.d_burst == pytest.approx(0.123)


def test_parse_burst_no_uncertainty(burst_no_uncertainty):
    params = BurstParameters.from_lines(burst_no_uncertainty)
    assert params.burst == pytest.approx(45.678)
    assert params.flag_burst == VaryFlag.NO
    assert params.d_burst is None


def test_parse_burst_pup(burst_with_pup):
    params = BurstParameters.from_lines(burst_with_pup)
    assert params.burst == pytest.approx(98.765)
    assert params.flag_burst == VaryFlag.PUP
    assert params.d_burst == pytest.approx(0.246)


def test_format_burst(basic_burst_input):
    params = BurstParameters.from_lines(basic_burst_input)
    print(params)
    lines = params.to_lines()
    assert len(lines) == 1
    # Verify exact format preservation
    params_round_trip = BurstParameters.from_lines(lines)
    assert params_round_trip == params


@pytest.fixture
def basic_water_input():
    # Col:    1----5-7-8-9-10-------20-------30-------40
    return ["WATER 11143.614     -0.089    0.037", "          0.001     0.002     0.003"]


@pytest.fixture
def water_no_uncertainty():
    return ["WATER 00043.614     -0.089    0.037"]


@pytest.fixture
def water_with_pup():
    return ["WATER 33343.614     -0.089    0.037"]


def test_parse_basic_water(basic_water_input):
    params = WaterParameters.from_lines(basic_water_input)
    assert params.watr0 == pytest.approx(3.614)
    assert params.watr1 == pytest.approx(-0.089)
    assert params.watr2 == pytest.approx(0.037)
    assert params.flag_watr0 == VaryFlag.YES
    assert params.flag_watr1 == VaryFlag.YES
    assert params.flag_watr2 == VaryFlag.YES
    assert params.d_watr0 == pytest.approx(0.001)
    assert params.d_watr1 == pytest.approx(0.002)
    assert params.d_watr2 == pytest.approx(0.003)


def test_water_no_uncertainty(water_no_uncertainty):
    params = WaterParameters.from_lines(water_no_uncertainty)
    assert params.watr0 == pytest.approx(3.614)
    assert params.flag_watr0 == VaryFlag.NO
    assert params.d_watr0 is None


def test_water_round_trip(basic_water_input):
    params = WaterParameters.from_lines(basic_water_input)
    lines = params.to_lines()

    params_rt = WaterParameters.from_lines(lines)

    assert params_rt == params


@pytest.fixture
def basic_tanta_input():
    # Col:    1----5-7--10--------20--------30
    return [
        "TANTA 1   1.234     0.123",  # Main parameter
        "      1110 2.345     3.456     4.567     5.678",  # Position params
        "          0.234     0.345     0.456     0.567",  # Position uncertainties
        "      10   7.890     8.901",  # Shape params
        "          0.789     0.890",
    ]  # Shape uncertainties


@pytest.fixture
def tanta_no_uncertainty():
    return ["TANTA 0   1.234", "      0000 2.345     3.456     4.567     5.678", "      00   7.890     8.901"]


def test_parse_basic_tanta(basic_tanta_input):
    params = TantalumParameters.from_lines(basic_tanta_input)

    assert params.tanta == pytest.approx(1.234)
    assert params.flag_tanta == VaryFlag.YES
    assert params.d_tanta == pytest.approx(0.123)

    assert params.x1 == pytest.approx(2.345)
    assert params.flag_x1 == VaryFlag.YES
    assert params.d_x1 == pytest.approx(0.234)

    assert params.beta == pytest.approx(7.890)
    assert params.flag_beta == VaryFlag.YES
    assert params.d_beta == pytest.approx(0.789)


def test_tanta_no_uncertainty(tanta_no_uncertainty):
    params = TantalumParameters.from_lines(tanta_no_uncertainty)

    assert params.tanta == pytest.approx(1.234)
    assert params.flag_tanta == VaryFlag.NO
    assert params.d_tanta is None


def test_tanta_round_trip(basic_tanta_input):
    params = TantalumParameters.from_lines(basic_tanta_input)
    lines = params.to_lines()
    params_rt = TantalumParameters.from_lines(lines)
    assert params_rt == params


def test_tanta_invalid_input():
    with pytest.raises(ValueError):
        TantalumParameters.from_lines([])  # Empty input


@pytest.fixture
def basic_lithi_input():
    # Col:    1----5-7-8-9-10-------20-------30-------40
    return ["LITHI 111 1.234     2.345     3.456", "          0.123     0.234     0.345"]


@pytest.fixture
def lithi_no_uncertainty():
    return ["LITHI 000 1.234     2.345     3.456"]


def test_parse_basic_lithi(basic_lithi_input):
    params = LithiumParameters.from_lines(basic_lithi_input)
    assert params.d == pytest.approx(1.234)
    assert params.f == pytest.approx(2.345)
    assert params.g == pytest.approx(3.456)
    assert params.flag_d == VaryFlag.YES
    assert params.d_d == pytest.approx(0.123)


def test_lithi_no_uncertainty(lithi_no_uncertainty):
    params = LithiumParameters.from_lines(lithi_no_uncertainty)
    assert params.d == pytest.approx(1.234)
    assert params.flag_d == VaryFlag.NO
    assert params.d_d is None


def test_lithi_round_trip(basic_lithi_input):
    params = LithiumParameters.from_lines(basic_lithi_input)
    lines = params.to_lines()

    for pos, line in enumerate(lines):
        print(f"{pos:>2}: {line}")

    params_rt = LithiumParameters.from_lines(lines)
    assert params_rt == params


if __name__ == "__main__":
    pytest.main(["-v", __file__])
