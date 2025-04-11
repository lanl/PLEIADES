import pytest

from pleiades.experimental.models import PhysicsParameters
from pleiades.nuclear.models import nuclearParameters
from pleiades.sammy.data.options import dataParameters
from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.fitting.options import (
    BroadeningTypeOptions,
    DataFormatOptions,
    FitOptions,
    QuantumNumbersOptions,
    RMatrixOptions,
    SpinGroupOptions,
)


def test_fit_config_defaults():
    """Test the default values of FitConfig."""
    nuclear_params = nuclearParameters()
    physics_params = PhysicsParameters()
    data_params = dataParameters()
    options_and_routines = FitOptions()

    config = FitConfig(
        nuclear_params=nuclear_params, physics_params=physics_params, data_params=data_params, options_and_routines=options_and_routines
    )

    assert config.fit_title == "SAMMY Fit"
    assert config.tolerance is None
    assert config.max_iterations == 1
    assert config.i_correlation == 50
    assert config.max_cpu_time is None
    assert config.max_wall_time is None
    assert config.max_memory is None
    assert config.max_disk is None
    assert config.nuclear_params == nuclear_params
    assert config.physics_params == physics_params
    assert config.data_params == data_params
    assert config.options_and_routines == options_and_routines


def test_fit_config_custom_values():
    """Test custom values of FitConfig."""
    nuclear_params = nuclearParameters()
    physics_params = PhysicsParameters()
    data_params = dataParameters(
        data_file="custom.dat",
        data_type="CAPTURE",
        energy_units="keV",
        cross_section_units="millibarn",
        data_title="Custom Data",
        data_comment="This is a custom data set.",
    )
    options_and_routines = FitOptions(
        RMatrix=RMatrixOptions.ORIGINAL_REICH_MOORE,
        SpinGroupFormat=SpinGroupOptions.PARTICLE_PAIR_DEFINITION,
        QuantumNumbers=QuantumNumbersOptions.PUT_Q_NUMBERS_IN_PARAM_FILE,
        input_is_endf_b_file_2=True,
        DataFormat=DataFormatOptions.DATA_IN_ENDF_FORMAT,
        ImplementBroadeningOption=True,
        BroadeningType=BroadeningTypeOptions.FREE_GAS_MODEL,
        SolveBayesEquation=True,
    )

    config = FitConfig(
        fit_title="Custom Fit",
        tolerance=0.01,
        max_iterations=10,
        i_correlation=100,
        max_cpu_time=3600,
        max_wall_time=7200,
        max_memory=16,
        max_disk=100,
        nuclear_params=nuclear_params,
        physics_params=physics_params,
        data_params=data_params,
        options_and_routines=options_and_routines,
    )

    assert config.fit_title == "Custom Fit"
    assert config.tolerance == 0.01
    assert config.max_iterations == 10
    assert config.i_correlation == 100
    assert config.max_cpu_time == 3600
    assert config.max_wall_time == 7200
    assert config.max_memory == 16
    assert config.max_disk == 100
    assert config.nuclear_params == nuclear_params
    assert config.physics_params == physics_params
    assert config.data_params == data_params
    assert config.options_and_routines == options_and_routines


if __name__ == "__main__":
    pytest.main()
