from typing import List, Optional

from pydantic import BaseModel, Field

from pleiades.experimental.models import PhysicsParameters
from pleiades.nuclear.models import nuclearParameters
from pleiades.sammy.data.options import LstData


class Chi2Results(BaseModel):
    """
    Container for chi-squared values and related statistics.
    """

    chi2_values: List[float] = Field(default_factory=list, description="List of chi-squared values")
    dof: Optional[int] = Field(default=None, description="Degrees of freedom")
    reduced_chi2: Optional[float] = Field(default=None, description="Reduced chi-squared value")

    def add_chi2(self, value: float):
        self.chi2_values.append(value)

    def calculate_reduced_chi2(self):
        if self.dof and self.dof > 0 and self.chi2_values:
            self.reduced_chi2 = sum(self.chi2_values) / self.dof


class FitResults(BaseModel):
    """
    A container for combined results from nuclear and experimental data
    in SAMMY calculations.
    """

    nuclear_data: nuclearParameters = Field(default_factory=nuclearParameters, description="Nuclear parameters data")
    physics_data: PhysicsParameters = Field(
        default_factory=PhysicsParameters, description="Experimental physics parameters"
    )
    chi2_results: Chi2Results = Field(default_factory=Chi2Results, description="Chi-squared results")

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

    def get_chi2_results(self) -> Chi2Results:
        """Retrieve the current chi-squared results."""
        return self.chi2_results

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize nuclear and physics data with default values
        self.nuclear_data = nuclearParameters()
        self.physics_data = PhysicsParameters()
        self.chi2_results = Chi2Results()


class RunResults(BaseModel):
    """RunResults is a container for aggregating multiple fit results from a given SAMMY execution.

    Attributes:
        fit_results (list[FitResults]): List of FitResults from multiple fits.
    """

    fit_results: list[FitResults] = Field(default_factory=list, description="List of FitResults from multiple fits.")
    data: LstData = Field(default_factory=LstData, description="Container for LST data loaded from a SAMMY .LST file.")

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize the list of fit results
        self.fit_results = []
        # Initialize the data container
        self.data = LstData()

    def add_fit_result(self, fit_result: FitResults):
        """Add a FitResults object to the list of fit results."""
        self.fit_results.append(fit_result)
