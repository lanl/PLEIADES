from typing import Optional

from pydantic import BaseModel, Field

from pleiades.experimental.models import PhysicsParameters
from pleiades.nuclear.models import nuclearParameters
from pleiades.sammy.data.options import sammyData
from pleiades.sammy.fitting.options import FitOptions


class FitConfig(BaseModel):
    """Container for fit parameters including nuclear and physics parameters.

    Attributes:
        nuclear_params (nuclearParameters): Nuclear parameters used in SAMMY calculations.
        physics_params (PhysicsParameters): Physics parameters including energy, normalization, and broadening.
    """

    fit_title: str = Field(description="Title of fitting run", default="SAMMY Fit")
    tolerance: Optional[float] = Field(default=None, description="Tolerance for chi-squared convergence")
    max_iterations: int = Field(description="Maximum number of iterations", default=1)
    i_correlation: int = Field(description="Correlation matrix interval", default=50)
    max_cpu_time: Optional[float] = Field(default=None, description="Maximum CPU time allowed")
    max_wall_time: Optional[float] = Field(default=None, description="Maximum wall time allowed")
    max_memory: Optional[float] = Field(default=None, description="Maximum memory allowed")
    max_disk: Optional[float] = Field(default=None, description="Maximum disk space allowed")

    nuclear_params: nuclearParameters = Field(
        default_factory=nuclearParameters, description="Nuclear parameters used in SAMMY calculations"
    )
    physics_params: PhysicsParameters = Field(
        default_factory=PhysicsParameters, description="Physics parameters used in SAMMY calculations"
    )
    data_params: sammyData = Field(default_factory=sammyData, description="Data parameters used in SAMMY calculations")
    options_and_routines: FitOptions = Field(
        default_factory=FitOptions, description="Fit options used in SAMMY calculations"
    )


# example usage
if __name__ == "__main__":
    example_config = FitConfig(
        fit_title="Example SAMMY Fit",
        tolerance=1e-5,
        max_iterations=100,
        i_correlation=10,
        max_cpu_time=3600.0,
        max_wall_time=7200.0,
        max_memory=8.0,
        max_disk=100.0,
        nuclear_params=nuclearParameters(),
        physics_params=PhysicsParameters(),
        data_params=sammyData(),
        options_and_routines=FitOptions(),
    )

    print(example_config)
