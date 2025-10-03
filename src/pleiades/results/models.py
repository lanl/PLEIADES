from typing import List

from pydantic import BaseModel, Field


class AbundanceInfo(BaseModel):
    """Container for isotope abundance information, such as isotope name, abundance, and uncertainty.
    Attributes:
        isotope_name (str): Name of the isotope.
        abundance (float): Abundance of the isotope.
        uncertainty (float): Uncertainty in the abundance.
    """

    isotope_name: str = Field(..., description="Name of the isotope")
    abundance: float = Field(..., description="Abundance of the isotope")
    uncertainty: float = Field(..., description="Uncertainty in the abundance")


class BackgroundInfo(BaseModel):
    # TODO: Add attributes and methods for background information
    ...


class NormalizationInfo(BaseModel):
    # TODO: Add attributes and methods for normalization information
    ...


class PixelInfo(BaseModel):
    position: List[float] = Field(..., description="x,y,z coordinates")
    isotope_info: List[AbundanceInfo] = Field(default_factory=list)
    background: List[BackgroundInfo] = Field(default_factory=list)
    normalization: List[NormalizationInfo] = Field(default_factory=list)
    temperature: List[float] = Field(default_factory=list)


class ResultsMap(BaseModel):
    """Container for results map data.

    Attributes:
        results_map (List[PixelInfo]): List of pixel information containing isotope and background data.
    """

    results_map: List[PixelInfo] = Field(default_factory=list)
