from enum import Enum
from pydantic import BaseModel, Field, constr
from pleiades.core.nuclear_params import nuclearParameters
from pleiades.core.physics_params import PhysicsParameters

import pleiades.sammy.fit_options as fit_options 


class DataType(str, Enum):
    TRANSMISSION = "TRANSmission"
    TOTAL_CROSS_SECTION = "TOTAL cross section"
    SCATTERING = "SCATTering"
    ELASTIC = "ELASTic"
    DIFFERENTIAL_ELASTIC = "DIFFErential elastic"
    DIFFERENTIAL_REACTION = "DIFFErentiAL REaction"
    REACTION = "REACTion"
    INELASTIC_SCATTERING = "INELAstic scattering"
    FISSION = "FISSion"
    CAPTURE = "CAPTure"
    SELF_INDICATION = "SELF-indication"
    INTEGRAL = "INTEGral"
    COMBINATION = "COMBInation"

class FitRoutineParameters(BaseModel):
    """Container for fit routine parameters.

    Attributes:
        max_iterations: Maximum number of iterations
        tolerance: Tolerance for chi-squared convergence
        max_cpu_time: Maximum CPU time allowed
        max_wall_time: Maximum wall time allowed
        max_memory: Maximum memory allowed
        max_disk: Maximum disk space allowed
    """

    max_iterations: int = Field(description="Maximum number of iterations")
    i_correlation: int = Field(description="Correlation matrix interval", Default=50)
    endf_mat_num: int = Field(description="ENDF material number", Default=0)


class dataParameters(BaseModel):
    """Container for data parameters.

    Attributes:
        data_file: File containing the data
        data_format: Format of the data
        data_type: Type of the data
        data_units: Units of the data
        data_title: Title of the data
        data_comment: Comment for the data
    """

    data_file: str = Field(description="File containing the data")
    data_format: str = Field(description="Format of the data")
    data_type: DataType = Field(description="Type of the data")
    data_units: str = Field(description="Units of the data")
    data_title: str = Field(description="Title of the data")
    data_comment: str = Field(description="Comment for the data")

class FitParameters(BaseModel):
    """Container for fit parameters including nuclear and physics parameters.

    Attributes:
        nuclear_params (nuclearParameters): Nuclear parameters used in SAMMY calculations.
        physics_params (PhysicsParameters): Physics parameters including energy, normalization, and broadening.
    """

    fit_title: str = Field(description="Title of fitting run", default="SAMMY Fit")
    tolerance: float = Field(description="Tolerance for chi-squared convergence")
    max_cpu_time: float = Field(description="Maximum CPU time allowed")
    max_wall_time: float = Field(description="Maximum wall time allowed")
    max_memory: float = Field(description="Maximum memory allowed")
    max_disk: float = Field(description="Maximum disk space allowed")

    data_params: dataParameters = Field(description="Data parameters used in SAMMY calculations")
    fit_routine_params: FitRoutineParameters = Field(description="Fit routine parameters used in SAMMY calculations")
    
    nuclear_params: nuclearParameters = Field(description="Nuclear parameters used in SAMMY calculations")
    physics_params: PhysicsParameters = Field(description="Physics parameters used in SAMMY calculations")

    # fitting parameters and routines to be used. 
    options_and_routines: fit_options.FitOptions = Field(description="Fit options used in SAMMY calculations")