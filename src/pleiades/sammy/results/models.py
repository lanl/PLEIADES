from pydantic import BaseModel, Field
from pleiades.nuclear.models import nuclearParameters
from pleiades.experimental.models import PhysicsParameters

class FitResults(BaseModel):
    """
    A container for combined results from nuclear and experimental data
    in SAMMY calculations.
    """
    nuclear_data: nuclearParameters = Field(..., description="Nuclear parameters data")
    physics_data: PhysicsParameters = Field(..., description="Experimental physics parameters")
    
class RunResults(BaseModel):
    """RunResults is a container for aggregating multiple fit results from a given SAMMY execution.

    Attributes:
        fit_results (list[FitResults]): List of FitResults from multiple fits.
    """
    fit_results: list[FitResults] = Field(..., description="List of FitResults from multiple fits.")