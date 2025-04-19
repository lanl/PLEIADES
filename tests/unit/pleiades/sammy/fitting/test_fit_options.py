import pytest

from pleiades.sammy.fitting.fit_options import (
    BroadeningTypeOptions,
    DataFormatOptions,
    FitOptions,
    PrintInputOptions,
    QuantumNumbersOptions,
    RMatrixOptions,
    SpinGroupOptions,
)


def test_fit_options_defaults():
    # Create an instance of FitOptions with default values
    fit_options = FitOptions()

    # Check default values
    assert fit_options.RMatrix == RMatrixOptions.REICH_MOORE_FORMALISM
    assert fit_options.SpinGroupFormat == SpinGroupOptions.USE_NEW_SPIN_GROUP
    assert fit_options.QuantumNumbers == QuantumNumbersOptions.Q_NUMBERS_IN_PARAM_FILE
    assert not fit_options.input_is_endf_b_file_2
    assert fit_options.DataFormat == DataFormatOptions.DATA_IN_ORIGINAL_MULTI_FORMAT
    assert not fit_options.ImplementBroadeningOption
    assert fit_options.BroadeningType == BroadeningTypeOptions.FREE_GAS_MODEL
    assert not fit_options.SolveBayesEquation
    assert not fit_options.PrintInputDataInLPT
    assert fit_options.PrintInputParamsInLPT == PrintInputOptions.DO_NOT_PRINT_ANY_INPUT


def test_fit_options_custom_values():
    # Create an instance of FitOptions with custom values
    fit_options = FitOptions(
        RMatrix=RMatrixOptions.ORIGINAL_REICH_MOORE,
        SpinGroupFormat=SpinGroupOptions.PARTICLE_PAIR_DEFINITION,
        QuantumNumbers=QuantumNumbersOptions.PUT_Q_NUMBERS_IN_PARAM_FILE,
        input_is_endf_b_file_2=True,
        DataFormat=DataFormatOptions.DATA_IN_CSISRS_FORMAT,
        ImplementBroadeningOption=True,
        BroadeningType=BroadeningTypeOptions.LEAL_HWANG_DOPPLER_MODEL,
        SolveBayesEquation=True,
        PrintInputDataInLPT=True,
        PrintInputParamsInLPT=PrintInputOptions.PRINT_ALL_INPUT,
    )

    # Check custom values
    assert fit_options.RMatrix == RMatrixOptions.ORIGINAL_REICH_MOORE
    assert fit_options.SpinGroupFormat == SpinGroupOptions.PARTICLE_PAIR_DEFINITION
    assert fit_options.QuantumNumbers == QuantumNumbersOptions.PUT_Q_NUMBERS_IN_PARAM_FILE
    assert fit_options.input_is_endf_b_file_2
    assert fit_options.DataFormat == DataFormatOptions.DATA_IN_CSISRS_FORMAT
    assert fit_options.ImplementBroadeningOption
    assert fit_options.BroadeningType == BroadeningTypeOptions.LEAL_HWANG_DOPPLER_MODEL
    assert fit_options.SolveBayesEquation
    assert fit_options.PrintInputDataInLPT
    assert fit_options.PrintInputParamsInLPT == PrintInputOptions.PRINT_ALL_INPUT


if __name__ == "__main__":
    pytest.main()
