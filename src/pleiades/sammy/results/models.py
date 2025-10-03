from typing import Optional

from pydantic import BaseModel, Field

from pleiades.experimental.models import PhysicsParameters
from pleiades.nuclear.models import nuclearParameters
from pleiades.sammy.data.options import SammyData


class ChiSquaredResults(BaseModel):
    """
    Container for chi-squared values and related statistics.
    """

    chi_squared: Optional[float] = Field(default=None, description="Chi-squared value")
    dof: Optional[int] = Field(default=None, description="Number of data points")
    reduced_chi_squared: Optional[float] = Field(default=None, description="Reduced chi-squared value")


class FitResults(BaseModel):
    """
    A container for combined results from nuclear and experimental data
    in SAMMY calculations.
    """

    nuclear_data: nuclearParameters = Field(default_factory=nuclearParameters, description="Nuclear parameters data")
    physics_data: PhysicsParameters = Field(
        default_factory=PhysicsParameters, description="Experimental physics parameters"
    )
    chi_squared_results: ChiSquaredResults = Field(default_factory=ChiSquaredResults, description="Chi-squared results")

    def update_nuclear_data(self, new_data: nuclearParameters):
        """Update the nuclear data with new parameters."""
        self.nuclear_data = new_data

    def update_physics_data(self, new_data: PhysicsParameters):
        """Update the physics data with new parameters."""
        self.physics_data = new_data

    def get_physics_data(self) -> PhysicsParameters:
        """Retrieve the current physics data."""
        return self.physics_data

    def get_nuclear_data(self) -> nuclearParameters:
        """Retrieve the current nuclear data."""
        return self.nuclear_data

    def get_chi_squared_results(self) -> ChiSquaredResults:
        """Retrieve the current chi-squared results."""
        return self.chi_squared_results


class RunResults(BaseModel):
    """RunResults is a container for aggregating multiple fit results from a given SAMMY execution.

    Attributes:
        fit_results (list[FitResults]): List of FitResults from multiple fits.
    """

    fit_results: list[FitResults] = Field(default_factory=list, description="List of FitResults from multiple fits.")
    data: SammyData = Field(
        default_factory=SammyData, description="Container for LST data loaded from a SAMMY .LST file."
    )

    def add_fit_result(self, fit_result: FitResults):
        """Add a FitResults object to the list of fit results."""
        self.fit_results.append(fit_result)
