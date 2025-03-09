from enum import Enum
from pydantic import BaseModel, Field
"""
This module defines various enumerations and a data model for configuring fit options in the SAMMY code.
SAMMY is a software tool used for the analysis of neutron-induced reactions, particularly in the context of 
resonance parameter evaluation. The enumerations represent different configuration options available in SAMMY, 
while the `FitOptions` class serves as a container for these options, providing a structured way to manage 
and validate the configuration settings.

Enumerations:
- `RMatrixOptions`: Options for the R-matrix formalism used in the calculations.
- `SpinGroupOptions`: Options for parameter input related to spin groups.
- `QuantumNumbersOptions`: Options for handling quantum numbers in parameter files.
- `DataFormatOptions`: Options for the format of the input data.
- `BroadeningTypeOptions`: Options for the type of broadening model to be used.
- `PrintInputOptions`: Options for printing input data and parameters.

Classes:
- `FitOptions`: A Pydantic data model that encapsulates all the fit options for SAMMY, ensuring that the 
    configuration is well-defined and validated.

Usage:
This module is intended to be used as part of the SAMMY codebase, where it provides a clear and structured 
way to manage the various configuration options required for running SAMMY simulations.
"""


""" Fit options for SAMMY """


class RMatrixOptions(str, Enum):
    REICH_MOORE_FORMALISM = "REICH-MOORE FORMALISM"
    ORIGINAL_REICH_MOORE = "ORIGINAL REICH-MOORE"
    MULTILEVEL_BREITWIGNER = "MULTILEVEL BREITWIGNER"
    SINGLE_LEVEL_BREITWIGNER = "SINGLE LEVEL BREITWIGNER"
    REDUCED_WIDTH_AMPLITUDES = "REDUCED WIDTH AMPLITUDES"

class SpinGroupOptions(str, Enum):
    """Parameter input options."""
    USE_NEW_SPIN_GROUP = "USE NEW SPIN GROUP"
    PARTICLE_PAIR_DEFINITION = "PARTICLE PAIR DEFINITION"
    KEY_WORD_PARTICLE_PAIR = "KEY WORD PARTICLE PAIR"

class QuantumNumbersOptions(str, Enum):
    """Quantum numbers options."""
    Q_NUMBERS_IN_PARAM_FILE = "QUANTUM NUMBERS ARE IN PARAMETER FILE"
    PUT_Q_NUMBERS_IN_PARAM_FILE = "PUT QUANTUM NUMBERS INTO PARAMETER FILE"


class DataFormatOptions(str,Enum):
    """ Data format options """
    DATA_IN_ORIGINAL_MULTI_FORMAT = "DATA IN ORIGINAL MULTI-FORMAT"
    DATA_IN_CSISRS_FORMAT = "DATA IN CSISRS FORMAT"
    DATA_IN_TWENTY_FORMAT = "DATA IN TWENTY FORMAT"
    DATA_IN_STANDARD_FORMAT = "DATA IN STANDARD FORMAT"
    DATA_IN_ODF_FORMAT = "DATA IN ODF FORMAT"
    DATA_IN_ENDF_FORMAT = "DATA IN ENDF FORMAT"

class BroadeningTypeOptions(str, Enum):
    FREE_GAS_MODEL = "FREE GAS MODEL"
    LEAL_HWANG_DOPPLER_MODEL = "LEAL-HWANG DOPPLER MODEL"
    HIGH_ENERGY_GAUSSIAN = "HIGH ENERGY GAUSSIAN"
    CRYSTAL_LATTICE_MODEL = "CRYSTAL LATTICE MODEL"

class PrintInputOptions(str, Enum):
    DO_NOT_PRINT_ANY_INPUT = "DO NOT PRINT ANY INPUT"
    PRINT_ALL_INPUT = "PRINT ALL INPUT"
    PRINT_VARIED_INPUT = "PRINT VARIED INPUT"


# a class to hold all the fit options
class FitOptions(BaseModel):
    """Container for fit options with SAMMY"""
    RMatrix: RMatrixOptions = Field(description="R-matrix option for the calculation", default=RMatrixOptions.REICH_MOORE_FORMALISM)
    SpinGroupFormat: SpinGroupOptions = Field(description="Parameter input options", default=SpinGroupOptions.USE_NEW_SPIN_GROUP)
    QuantumNumbers: QuantumNumbersOptions = Field(description="Quantum numbers options", default=QuantumNumbersOptions.Q_NUMBERS_IN_PARAM_FILE)
    input_is_endf_b_file_2: bool = Field(description="Indicates if the input is ENDF/B FILE 2", default=False)
    DataFormat: DataFormatOptions = Field(description="Data format options", default=DataFormatOptions.DATA_IN_ORIGINAL_MULTI_FORMAT)
    ImplementBroadeningOption: bool = Field(description="option to implement Broadening", default=False)
    BroadeningType: BroadeningTypeOptions = Field(description="Broadening type options", default=BroadeningTypeOptions.FREE_GAS_MODEL)
    SolveBayesEquation: bool = Field(description="option to solve Bayes equation", default=False)
    PrintInputDataInLPT: bool = Field(description="option to print input data in LPT", default=False)
    PrintInputParamsInLPT: PrintInputOptions = Field(description="option to print input parameters in LPT", default=PrintInputOptions.DO_NOT_PRINT_ANY_INPUT)



# Example usage of FitOptions
def main():
    # Create an instance of FitOptions with default values
    default_fit_options = FitOptions()
    print("Default FitOptions:")
    print(default_fit_options.json(indent=4))

    # Create an instance of FitOptions with custom values
    custom_fit_options = FitOptions(
        RMatrix=RMatrixOptions.MULTILEVEL_BREITWIGNER,
        SpinGroupFormat=SpinGroupOptions.PARTICLE_PAIR_DEFINITION,
        QuantumNumbers=QuantumNumbersOptions.PUT_Q_NUMBERS_IN_PARAM_FILE,
        input_is_endf_b_file_2=True,
        DataFormat=DataFormatOptions.DATA_IN_ENDF_FORMAT,
        ImplementBroadeningOption=True,
        BroadeningType=BroadeningTypeOptions.LEAL_HWANG_DOPPLER_MODEL,
        SolveBayesEquation=True,
        PrintInputDataInLPT=True,
        PrintInputParamsInLPT=PrintInputOptions.PRINT_ALL_INPUT
    )
    print("\nCustom FitOptions:")
    print(custom_fit_options.json(indent=4))

if __name__ == "__main__":
    main()