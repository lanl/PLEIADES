from typing import Optional

from pydantic import BaseModel, Field

from pleiades.experimental.models import PhysicsParameters
from pleiades.nuclear.isotopes.manager import IsotopeManager
from pleiades.nuclear.models import nuclearParameters
from pleiades.sammy.data.options import SammyData
from pleiades.sammy.fitting.options import FitOptions
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


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
    data_params: SammyData = Field(default_factory=SammyData, description="Data parameters used in SAMMY calculations")
    options_and_routines: FitOptions = Field(
        default_factory=FitOptions, description="Fit options used in SAMMY calculations"
    )

    def append_isotope_from_string(self, isotope_string: str) -> None:
        isotope_info = IsotopeManager().get_isotope_parameters_from_isotope_string(isotope_string)

        if isotope_info:
            logger.info(f"Appending Isotope {isotope_string} to isotope list in nuclear parameters.")
            self.nuclear_params.isotopes.append(isotope_info)
        else:
            logger.error(f"Could not append Isotope {isotope_string}.")
