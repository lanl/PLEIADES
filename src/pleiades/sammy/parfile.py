#!/usr/bin/env python
"""Top level parameter file handler for SAMMY."""

from typing import Optional

from pydantic import BaseModel, Field

from pleiades.sammy.parameters import (
    BroadeningParameterCard,
    DataReductionCard,
    ExternalREntry,
    NormalizationBackgroundCard,
    ORRESCard,
    RadiusCard,
    ResonanceEntry,
    UnusedCorrelatedCard,
)


class SammyParameterFile(BaseModel):
    """Top level parameter file for SAMMY."""

    resonance: ResonanceEntry = Field(description="Resonance parameters")
    fudge: float = Field(0.1, description="Fudge factor", ge=0.0, le=1.0)
    # Add additional optional cards
    external_r: Optional[ExternalREntry] = Field(None, description="External R matrix")
    broadening: Optional[BroadeningParameterCard] = Field(None, description="Broadening parameters")
    unused_correlated: Optional[UnusedCorrelatedCard] = Field(None, description="Unused but correlated variables")
    normalization: Optional[NormalizationBackgroundCard] = Field(None, description="Normalization and background parameters")
    radius: Optional[RadiusCard] = Field(None, description="Radius parameters")
    data_reduction: Optional[DataReductionCard] = Field(None, description="Data reduction parameters")
    orres: Optional[ORRESCard] = Field(None, description="ORRES card parameters")

    @classmethod
    def from_file(cls, file_path):
        """Load a SAMMY parameter file from disk."""
        with open(file_path, "r") as f:
            lines = f.readlines()

        # Parse resonance card
        resonance = ResonanceEntry.from_str(lines[0])

        return cls(resonance=resonance)


if __name__ == "__main__":
    print("TODO: usage example for SAMMY parameter file handling")
