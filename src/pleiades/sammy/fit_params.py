from enum import Enum
from pydantic import BaseModel, Field, constr
from pleiades.core.nuclear_params import nuclearParameters
from pleiades.core.physics_params import PhysicsParameters
from pleiades.sammy.data.options import dataParameters
from pleiades.sammy.fit_options import FitOptions

class FitParameters(BaseModel):
    """Container for fit parameters including nuclear and physics parameters.

    Attributes:
        nuclear_params (nuclearParameters): Nuclear parameters used in SAMMY calculations.
        physics_params (PhysicsParameters): Physics parameters including energy, normalization, and broadening.
    """

    fit_title: str = Field(description="Title of fitting run", default="SAMMY Fit")
    tolerance: float = Field(description="Tolerance for chi-squared convergence")
    max_iterations: int = Field(description="Maximum number of iterations", default=1)
    i_correlation: int = Field(description="Correlation matrix interval", default=50)
    max_cpu_time: float = Field(description="Maximum CPU time allowed")
    max_wall_time: float = Field(description="Maximum wall time allowed")
    max_memory: float = Field(description="Maximum memory allowed")
    max_disk: float = Field(description="Maximum disk space allowed")

    nuclear_params: nuclearParameters = Field(description="Nuclear parameters used in SAMMY calculations")
    physics_params: PhysicsParameters = Field(description="Physics parameters used in SAMMY calculations")
    data_params: dataParameters = Field(description="Data parameters used in SAMMY calculations")
    options_and_routines: FitOptions = Field(description="Fit options used in SAMMY calculations")