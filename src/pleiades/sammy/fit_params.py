from enum import Enum
from pydantic import BaseModel, Field, constr
from pleiades.core.nuclear_params import nuclearParameters
from pleiades.core.physics_params import PhysicsParameters
from pleiades.sammy.data.options import dataParameters

import pleiades.sammy.fit_options as fit_options 

class DataTypeOptions(str, Enum):
    TRANSMISSION = "TRANSMISSION"
    TOTAL_CROSS_SECTION = "TOTAL CROSS SECTION"
    SCATTERING = "SCATTERING"
    ELASTIC = "ELASTIC"
    DIFFERENTIAL_ELASTIC = "DIFFERENTIAL ELASTIC"
    DIFFERENTIAL_REACTION = "DIFFERENTIAL REACTION"
    REACTION = "REACTION"
    INELASTIC_SCATTERING = "INELASTIC SCATTERING"
    FISSION = "FISSION"
    CAPTURE = "CAPTURE"
    SELF_INDICATION = "SELF INDICATION"
    INTEGRAL = "INTEGRAL"
    COMBINATION = "COMBINATION"

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

    max_iterations: int = Field(description="Maximum number of iterations", default=1)
    i_correlation: int = Field(description="Correlation matrix interval", default=50)
    endf_mat_num: int = Field(description="ENDF material number", default=0)


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