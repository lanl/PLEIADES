from enum import Enum
from pydantic import BaseModel, Field, root_validator

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
    BroadeningType: BroadeningTypeOptions = Field(description="Broadening type options", default=None)
    SolveBayesEquation: bool = Field(description="option to solve Bayes equation", default=False)
    PrintInputDataInLPT: bool = Field(description="option to print input data in LPT", default=False)
    PrintInputParamsInLPT: PrintInputOptions = Field(description="option to print input parameters in LPT", default=PrintInputOptions.DO_NOT_PRINT_ANY_INPUT)

    # set the default broadening type to FGM if the broadening option is set
    @root_validator(pre=True)
    def set_broadening_type(cls, values):
        if values.get('ImplementBroadeningOption'):
            if 'BroadeningType' not in values or values['BroadeningType'] is None:
                values['BroadeningType'] = BroadeningTypeOptions.FREE_GAS_MODEL
        else:
            values['BroadeningType'] = None
        return values
