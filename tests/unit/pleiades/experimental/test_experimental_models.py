import pytest

from pleiades.experimental.models import (
    BroadeningParameters,
    EnergyParameters,
    NormalizationParameters,
    PhysicsParameters,
    UserResolutionParameters,
)
from pleiades.utils.helper import VaryFlag


def test_energy_parameters_initialization():
    """Test initialization of EnergyParameters."""
    params = EnergyParameters(
        min_energy=0.1,
        max_energy=10.0,
        number_of_energy_points=1000,
        number_of_extra_points=10,
        number_of_small_res_points=5,
    )
    assert params.min_energy == 0.1
    assert params.max_energy == 10.0
    assert params.number_of_energy_points == 1000
    assert params.number_of_extra_points == 10
    assert params.number_of_small_res_points == 5


def test_normalization_parameters_initialization():
    """Test initialization of NormalizationParameters."""
    params = NormalizationParameters(
        anorm=1.0,
        backa=0.1,
        backb=0.2,
        backc=0.3,
        backd=0.4,
        backf=0.5,
        d_anorm=0.01,
        d_backa=0.02,
        flag_anorm=VaryFlag.YES,
    )
    assert params.anorm == 1.0
    assert params.backa == 0.1
    assert params.d_anorm == 0.01
    assert params.flag_anorm == VaryFlag.YES


def test_broadening_parameters_initialization():
    """Test initialization of BroadeningParameters."""
    params = BroadeningParameters(
        crfn=1.0,
        temp=300.0,
        thick=0.1,
        deltal=0.01,
        deltag=0.02,
        deltae=0.03,
        deltc1=0.001,
        deltc2=0.002,
        flag_deltc1=VaryFlag.YES,
        flag_deltc2=VaryFlag.NO,
    )
    assert params.crfn == 1.0
    assert params.temp == 300.0
    assert params.deltc1 == 0.001
    assert params.flag_deltc1 == VaryFlag.YES


def test_broadening_parameters_validation():
    """Test validation of Gaussian parameters in BroadeningParameters."""
    with pytest.raises(ValueError, match="Both DELTC1 and DELTC2 must be present if either is present"):
        BroadeningParameters(
            crfn=1.0,
            temp=300.0,
            thick=0.1,
            deltal=0.01,
            deltag=0.02,
            deltae=0.03,
            deltc1=0.001,  # Only DELTC1 is present
        )


def test_user_resolution_parameters_initialization():
    """Test initialization of UserResolutionParameters."""
    params = UserResolutionParameters(
        type=UserResolutionParameters.UserDefinedResolutionType.USER,
        burst_width=10.0,
        burst_flag=VaryFlag.YES,
        channel_energies=[1.0, 2.0, 3.0],
        channel_widths=[0.1, 0.2, 0.3],
    )
    assert params.type == UserResolutionParameters.UserDefinedResolutionType.USER
    assert params.burst_width == 10.0
    assert params.channel_energies == [1.0, 2.0, 3.0]
    assert params.channel_widths == [0.1, 0.2, 0.3]


def test_physics_parameters_initialization():
    """Test initialization of PhysicsParameters."""
    energy_params = EnergyParameters(
        min_energy=0.1,
        max_energy=10.0,
        number_of_energy_points=1000,
    )
    normalization_params = NormalizationParameters(
        anorm=1.0,
        backa=0.1,
        backb=0.2,
        backc=0.3,
        backd=0.4,
        backf=0.5,
    )
    broadening_params = BroadeningParameters(
        crfn=1.0,
        temp=300.0,
        thick=0.1,
        deltal=0.01,
        deltag=0.02,
        deltae=0.03,
    )
    user_resolution_params = UserResolutionParameters(
        type=UserResolutionParameters.UserDefinedResolutionType.USER,
        burst_width=10.0,
    )

    params = PhysicsParameters(
        energy_parameters=energy_params,
        normalization_parameters=normalization_params,
        broadening_parameters=broadening_params,
        user_resolution_parameters=user_resolution_params,
    )
    assert params.energy_parameters.min_energy == 0.1
    assert params.normalization_parameters.anorm == 1.0
    assert params.broadening_parameters.crfn == 1.0
    assert params.user_resolution_parameters.burst_width == 10.0
