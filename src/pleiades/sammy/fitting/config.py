from pydantic import BaseModel, Field

from pleiades.experimental.parameters import PhysicsParameters
from pleiades.nuclear.parameters import nuclearParameters
from pleiades.sammy.data.options import dataParameters
from pleiades.sammy.fitting.options import FitOptions


class FitConfig(BaseModel):
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
        data_params=dataParameters(),
        options_and_routines=FitOptions(),
    )

    print(example_config)
