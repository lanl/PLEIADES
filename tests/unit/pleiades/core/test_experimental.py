import pytest
from pydantic import ValidationError

from pleiades.core.experimental import (
    BroadeningParameters,
    EnergyParameters,
    NormalizationParameters,
    PhysicsParameters,
    UserResolutionParameters,
)
from pleiades.utils.helper import VaryFlag


def test_energy_parameters():
    params = EnergyParameters(
        min_energy=0.1,
        max_energy=10.0,
        number_of_energy_points=100,
        number_of_extra_points=5,
        number_of_small_res_points=2,
    )
    assert params.min_energy == 0.1
    assert params.max_energy == 10.0
    assert params.number_of_energy_points == 100
    assert params.number_of_extra_points == 5
    assert params.number_of_small_res_points == 2


def test_normalization_parameters():
    params = NormalizationParameters(
        anorm=1.0,
        backa=0.1,
        backb=0.01,
        backc=0.001,
        backd=0.0001,
        backf=0.00001,
        d_anorm=0.1,
        d_backa=0.01,
        d_backb=0.001,
        d_backc=0.0001,
        d_backd=0.00001,
        d_backf=0.000001,
        flag_anorm=VaryFlag.YES,
        flag_backa=VaryFlag.YES,
        flag_backb=VaryFlag.NO,
        flag_backc=VaryFlag.NO,
        flag_backd=VaryFlag.NO,
        flag_backf=VaryFlag.NO,
    )
    assert params.anorm == 1.0
    assert params.backa == 0.1
    assert params.backb == 0.01
    assert params.backc == 0.001
    assert params.backd == 0.0001
    assert params.backf == 0.00001
    assert params.d_anorm == 0.1
    assert params.d_backa == 0.01
    assert params.d_backb == 0.001
    assert params.d_backc == 0.0001
    assert params.d_backd == 0.00001
    assert params.d_backf == 0.000001
    assert params.flag_anorm == VaryFlag.YES
    assert params.flag_backa == VaryFlag.YES
    assert params.flag_backb == VaryFlag.NO
    assert params.flag_backc == VaryFlag.NO
    assert params.flag_backd == VaryFlag.NO
    assert params.flag_backf == VaryFlag.NO


def test_broadening_parameters():
    params = BroadeningParameters(
        crfn=1.0,
        temp=300.0,
        thick=0.1,
        deltal=0.01,
        deltag=0.001,
        deltae=0.0001,
        d_crfn=0.1,
        d_temp=10.0,
        d_thick=0.01,
        d_deltal=0.001,
        d_deltag=0.0001,
        d_deltae=0.00001,
        deltc1=0.1,
        deltc2=0.01,
        d_deltc1=0.001,
        d_deltc2=0.0001,
        flag_crfn=VaryFlag.YES,
        flag_temp=VaryFlag.YES,
        flag_thick=VaryFlag.NO,
        flag_deltal=VaryFlag.NO,
        flag_deltag=VaryFlag.NO,
        flag_deltae=VaryFlag.NO,
        flag_deltc1=VaryFlag.YES,
        flag_deltc2=VaryFlag.YES,
    )
    assert params.crfn == 1.0
    assert params.temp == 300.0
    assert params.thick == 0.1
    assert params.deltal == 0.01
    assert params.deltag == 0.001
    assert params.deltae == 0.0001
    assert params.d_crfn == 0.1
    assert params.d_temp == 10.0
    assert params.d_thick == 0.01
    assert params.d_deltal == 0.001
    assert params.d_deltag == 0.0001
    assert params.d_deltae == 0.00001
    assert params.deltc1 == 0.1
    assert params.deltc2 == 0.01
    assert params.d_deltc1 == 0.001
    assert params.d_deltc2 == 0.0001
    assert params.flag_crfn == VaryFlag.YES
    assert params.flag_temp == VaryFlag.YES
    assert params.flag_thick == VaryFlag.NO
    assert params.flag_deltal == VaryFlag.NO
    assert params.flag_deltag == VaryFlag.NO
    assert params.flag_deltae == VaryFlag.NO
    assert params.flag_deltc1 == VaryFlag.YES
    assert params.flag_deltc2 == VaryFlag.YES

    with pytest.raises(ValidationError):
        BroadeningParameters(crfn=1.0, temp=300.0, thick=0.1, deltal=0.01, deltag=0.001, deltae=0.0001, deltc1=0.1)


def test_user_resolution_parameters():
    params = UserResolutionParameters(
        burst_width=10.0,
        burst_uncertainty=1.0,
        burst_flag=VaryFlag.YES,
        channel_energies=[1.0, 2.0, 3.0],
        channel_widths=[0.1, 0.2, 0.3],
        channel_uncertainties=[0.01, 0.02, 0.03],
        channel_flags=[VaryFlag.YES, VaryFlag.NO, VaryFlag.YES],
        filenames=["file1.dat", "file2.dat"],
    )
    assert params.burst_width == 10.0
    assert params.burst_uncertainty == 1.0
    assert params.burst_flag == VaryFlag.YES
    assert params.channel_energies == [1.0, 2.0, 3.0]
    assert params.channel_widths == [0.1, 0.2, 0.3]
    assert params.channel_uncertainties == [0.01, 0.02, 0.03]
    assert params.channel_flags == [VaryFlag.YES, VaryFlag.NO, VaryFlag.YES]
    assert params.filenames == ["file1.dat", "file2.dat"]


def test_physics_parameters():
    energy_params = EnergyParameters(
        min_energy=0.1,
        max_energy=10.0,
        number_of_energy_points=100,
        number_of_extra_points=5,
        number_of_small_res_points=2,
    )
    normalization_params = NormalizationParameters(
        anorm=1.0,
        backa=0.1,
        backb=0.01,
        backc=0.001,
        backd=0.0001,
        backf=0.00001,
        d_anorm=0.1,
        d_backa=0.01,
        d_backb=0.001,
        d_backc=0.0001,
        d_backd=0.00001,
        d_backf=0.000001,
        flag_anorm=VaryFlag.YES,
        flag_backa=VaryFlag.YES,
        flag_backb=VaryFlag.NO,
        flag_backc=VaryFlag.NO,
        flag_backd=VaryFlag.NO,
        flag_backf=VaryFlag.NO,
    )
    broadening_params = BroadeningParameters(
        crfn=1.0,
        temp=300.0,
        thick=0.1,
        deltal=0.01,
        deltag=0.001,
        deltae=0.0001,
        d_crfn=0.1,
        d_temp=10.0,
        d_thick=0.01,
        d_deltal=0.001,
        d_deltag=0.0001,
        d_deltae=0.00001,
        deltc1=0.1,
        deltc2=0.01,
        d_deltc1=0.001,
        d_deltc2=0.0001,
        flag_crfn=VaryFlag.YES,
        flag_temp=VaryFlag.YES,
        flag_thick=VaryFlag.NO,
        flag_deltal=VaryFlag.NO,
        flag_deltag=VaryFlag.NO,
        flag_deltae=VaryFlag.NO,
        flag_deltc1=VaryFlag.YES,
        flag_deltc2=VaryFlag.YES,
    )
    user_resolution_params = UserResolutionParameters(
        burst_width=10.0,
        burst_uncertainty=1.0,
        burst_flag=VaryFlag.YES,
        channel_energies=[1.0, 2.0, 3.0],
        channel_widths=[0.1, 0.2, 0.3],
        channel_uncertainties=[0.01, 0.02, 0.03],
        channel_flags=[VaryFlag.YES, VaryFlag.NO, VaryFlag.YES],
        filenames=["file1.dat", "file2.dat"],
    )
    params = PhysicsParameters(
        energy_parameters=energy_params,
        normalization_parameters=normalization_params,
        broadening_parameters=broadening_params,
        user_resolution_parameters=user_resolution_params,
    )
    assert params.energy_parameters == energy_params
    assert params.normalization_parameters == normalization_params
    assert params.broadening_parameters == broadening_params
    assert params.user_resolution_parameters == user_resolution_params
