#!/usr/bin/env python
"""
Card Set 3 (Physical Constants) for SAMMY INP files.

This module provides the Card03 class for parsing and generating the physical
constants line in SAMMY input files. This card appears after the element information
and defines temperature, flight path, and resolution parameters.

Format specification (Card Set 3 - Physical Constants):
    The line contains five floating-point values with variable spacing:
    - TEMP: Temperature (K)
    - FPL: Flight path length (m)
    - DELTAL: Spread in flight-path length (m)
    - DELTAG: Gaussian resolution width (μs)
    - DELTAE: e-folding width of exponential resolution (μs)

Example:
          300.  200.0000  0.182233       0.0  0.002518
"""

from typing import List

from pydantic import BaseModel, Field

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class PhysicalConstants(BaseModel):
    """Pydantic model for physical constants in Card Set 3.

    Attributes:
        temperature: Temperature in Kelvin
        flight_path_length: Flight path length in meters
        delta_l: Spread in flight-path length in meters
        delta_g: Gaussian resolution width in microseconds
        delta_e: e-folding width of exponential resolution in microseconds
    """

    temperature: float = Field(..., description="Temperature (K)", gt=0)
    flight_path_length: float = Field(..., description="Flight path length (m)", gt=0)
    delta_l: float = Field(default=0.0, description="Spread in flight-path length (m)", ge=0)
    delta_g: float = Field(default=0.0, description="Gaussian resolution width (μs)", ge=0)
    delta_e: float = Field(default=0.0, description="e-folding width of exponential resolution (μs)", ge=0)


class Card03(BaseModel):
    """
    Class representing Card Set 3 (physical constants) in SAMMY INP files.

    This card defines temperature, flight path, and resolution parameters for the analysis.
    """

    @classmethod
    def from_lines(cls, lines: List[str]) -> PhysicalConstants:
        """Parse physical constants from Card Set 3 line.

        Args:
            lines: List of input lines (expects single line for Card 3)

        Returns:
            PhysicalConstants: Parsed physical constants

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            message = "No valid Card 3 line provided"
            logger.error(message)
            raise ValueError(message)

        line = lines[0].strip()
        fields = line.split()

        if len(fields) < 2:
            message = f"Card 3 line must have at least 2 fields (TEMP, FPL), got {len(fields)}"
            logger.error(message)
            raise ValueError(message)

        try:
            temperature = float(fields[0])
            flight_path_length = float(fields[1])
            delta_l = float(fields[2]) if len(fields) > 2 else 0.0
            delta_g = float(fields[3]) if len(fields) > 3 else 0.0
            delta_e = float(fields[4]) if len(fields) > 4 else 0.0
        except (ValueError, IndexError) as e:
            message = f"Failed to parse Card 3 line: {e}"
            logger.error(message)
            raise ValueError(message)

        return PhysicalConstants(
            temperature=temperature,
            flight_path_length=flight_path_length,
            delta_l=delta_l,
            delta_g=delta_g,
            delta_e=delta_e,
        )

    @classmethod
    def to_lines(cls, constants: PhysicalConstants) -> List[str]:
        """Convert physical constants to Card Set 3 formatted line.

        Args:
            constants: PhysicalConstants object containing parameter data

        Returns:
            List containing single formatted line for Card Set 3
        """
        if not isinstance(constants, PhysicalConstants):
            message = "constants must be an instance of PhysicalConstants"
            logger.error(message)
            raise ValueError(message)

        line = (
            f"    {constants.temperature:5.1f}    "
            f"{constants.flight_path_length:8.4f}  "
            f"{constants.delta_l:8.6f}       "
            f"{constants.delta_g:3.1f}  "
            f"{constants.delta_e:8.6f}"
        )

        return [line]
