#!/usr/bin/env python
"""
Sample Density for SAMMY INP files.

This module provides the Card03Density class for parsing and generating the sample
density line in SAMMY input files. This line appears after the physical constants
and defines the material density and number density.

Format specification (Sample Density):
    The line contains two floating-point values:
    - Density: Material density (g/cm³)
    - Number density: Number density (atoms/barn-cm)

Example:
       4.20000  0.347162
"""

from typing import List

from pydantic import BaseModel, Field

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class SampleDensity(BaseModel):
    """Pydantic model for sample density parameters.

    Attributes:
        density: Material density in g/cm³
        number_density: Number density in atoms/barn-cm
    """

    density: float = Field(..., description="Material density (g/cm³)", gt=0)
    number_density: float = Field(..., description="Number density (atoms/barn-cm)", gt=0)


class Card03Density(BaseModel):
    """
    Class representing sample density line in SAMMY INP files.

    This line defines the material density and number density for the sample.
    """

    @classmethod
    def from_lines(cls, lines: List[str]) -> SampleDensity:
        """Parse sample density from density line.

        Args:
            lines: List of input lines (expects single line)

        Returns:
            SampleDensity: Parsed sample density parameters

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            message = "No valid density line provided"
            logger.error(message)
            raise ValueError(message)

        line = lines[0].strip()
        fields = line.split()

        if len(fields) < 2:
            message = f"Density line must have 2 fields (density, number_density), got {len(fields)}"
            logger.error(message)
            raise ValueError(message)

        try:
            density = float(fields[0])
            number_density = float(fields[1])
        except (ValueError, IndexError) as e:
            message = f"Failed to parse density line: {e}"
            logger.error(message)
            raise ValueError(message)

        return SampleDensity(
            density=density,
            number_density=number_density,
        )

    @classmethod
    def to_lines(cls, sample_density: SampleDensity) -> List[str]:
        """Convert sample density to formatted line.

        Args:
            sample_density: SampleDensity object containing density data

        Returns:
            List containing single formatted line
        """
        if not isinstance(sample_density, SampleDensity):
            message = "sample_density must be an instance of SampleDensity"
            logger.error(message)
            raise ValueError(message)

        line = f"  {sample_density.density:8.6f} {sample_density.number_density:.6e}"

        return [line]
