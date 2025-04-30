from pydantic import BaseModel, Field
from typing import Optional
from pleiades.nuclear.models import nuclearParameters
from pleiades.experimental.models import PhysicsParameters

class FitResults(BaseModel):
    """
    A container for combined results from nuclear and experimental data
    in SAMMY calculations.
    """
    nuclear_data: nuclearParameters = Field(default_factory=nuclearParameters, description="Nuclear parameters data")
    physics_data: PhysicsParameters = Field(default_factory=PhysicsParameters, description="Experimental physics parameters")
    
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
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize nuclear and physics data with default values
        self.nuclear_data = nuclearParameters()
        self.physics_data = PhysicsParameters()


class RunResults(BaseModel):
    """RunResults is a container for aggregating multiple fit results from a given SAMMY execution.

    Attributes:
        fit_results (list[FitResults]): List of FitResults from multiple fits.
    """
    fit_results: list[FitResults] = Field(default_factory=list, description="List of FitResults from multiple fits.")
    
    def add_fit_result(self, fit_result: FitResults):
        """Add a FitResults object to the list of fit results."""
        self.fit_results.append(fit_result)
        
    def get_single_fit_results(self, index: int) -> FitResults:
        """Retrieve a single fit result from the list."""
        if self.fit_results:
            return self.fit_results[index]
        else:
            raise ValueError("No fit results available.")