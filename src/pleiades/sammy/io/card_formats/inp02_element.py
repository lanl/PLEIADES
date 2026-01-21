#!/usr/bin/env python
"""
Card Set 2 (Element Information) for SAMMY INP files.

This module provides the Card02 class for parsing and generating the element
information line in SAMMY input files. This card appears early in the INP file
and defines the sample element, atomic weight, and energy range.

Format specification (Card Set 2):
    Cols    Format  Variable    Description
    1-10    A       ELMNT       Sample element's name (left-aligned)
    11-20   F       AW          Atomic weight (amu)
    21-30   F       EMIN        Minimum energy for dataset (eV)
    31-40   F       EMAX        Maximum energy (eV)
    41-45   I       NEPNTS      Points in artificial energy grid
    46-50   I       ITMAX       Maximum iterations for Bayes' solution
    51-52   I       ICORR       Correlation threshold x100
    53-55   I       NXTRA       Extra points between experimental points
    56-57   I       IPTDOP      Grid enhancement for Doppler broadening
    59-60   I       IPTWID      Grid enhancement for resonance tails
    61-70   I       IXXCHN      Channel skip or ZA for ENDF output
    71-72   I       NDIGIT      Digits for compact covariance output
    73-74   I       IDROPP      Percent threshold for zeroing covariances
    75-80   I       MATNUM      ENDF material number

Example:
    Si        27.976928 300000.   1800000.
"""

from typing import List

from pydantic import BaseModel, Field

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

# Format specification for Card Set 2
CARD02_FORMAT = {
    "element": slice(0, 10),
    "atomic_weight": slice(10, 20),
    "min_energy": slice(20, 30),
    "max_energy": slice(30, 40),
    "nepnts": slice(40, 45),
    "itmax": slice(45, 50),
    "icorr": slice(50, 52),
    "nxtra": slice(52, 55),
    "iptdop": slice(55, 57),
    "iptwid": slice(58, 60),
    "ixxchn": slice(60, 70),
    "ndigit": slice(70, 72),
    "idropp": slice(72, 74),
    "matnum": slice(74, 80),
}


class ElementInfo(BaseModel):
    """Pydantic model for element information in Card Set 2.

    Attributes:
        element: Sample element's name (up to 10 characters)
        atomic_weight: Atomic weight in amu
        min_energy: Minimum energy for dataset in eV
        max_energy: Maximum energy in eV
        nepnts: Points in artificial energy grid
        itmax: Maximum iterations for Bayes' solution
        icorr: Correlation threshold x100
        nxtra: Extra points between experimental points
        iptdop: Grid enhancement for Doppler broadening
        iptwid: Grid enhancement for resonance tails
        ixxchn: Channel skip or ZA for ENDF output
        ndigit: Digits for compact covariance output
        idropp: Percent threshold for zeroing covariances
        matnum: ENDF material number
    """

    element: str = Field(..., description="Sample element's name", max_length=10)
    atomic_weight: float = Field(..., description="Atomic weight (amu)", gt=0)
    min_energy: float = Field(..., description="Minimum energy (eV)", ge=0)
    max_energy: float = Field(..., description="Maximum energy (eV)", gt=0)
    nepnts: int | None = Field(default=None, description="Points in artificial energy grid")
    itmax: int | None = Field(default=None, description="Maximum iterations for Bayes' solution")
    icorr: int | None = Field(default=None, description="Correlation threshold x100")
    nxtra: int | None = Field(default=None, description="Extra points between experimental points")
    iptdop: int | None = Field(default=None, description="Grid enhancement for Doppler broadening")
    iptwid: int | None = Field(default=None, description="Grid enhancement for resonance tails")
    ixxchn: int | None = Field(default=None, description="Channel skip or ZA for ENDF output")
    ndigit: int | None = Field(default=None, description="Digits for compact covariance output")
    idropp: int | None = Field(default=None, description="Percent threshold for zeroing covariances")
    matnum: int | None = Field(default=None, description="ENDF material number")

    def model_post_init(self, __context) -> None:
        """Validate that max_energy > min_energy."""
        if self.max_energy <= self.min_energy:
            raise ValueError(f"max_energy ({self.max_energy}) must be greater than min_energy ({self.min_energy})")


class Card02(BaseModel):
    """
    Class representing Card Set 2 (element information) in SAMMY INP files.

    This card defines the sample element, atomic weight, and energy range for the analysis.
    """

    @classmethod
    def from_lines(cls, lines: List[str]) -> ElementInfo:
        """Parse element information from Card Set 2 line.

        Args:
            lines: List of input lines (expects single line for Card 2)

        Returns:
            ElementInfo: Parsed element information

        Raises:
            ValueError: If format is invalid or required values missing
        """
        if not lines or not lines[0].strip():
            message = "No valid Card 2 line provided"
            logger.error(message)
            raise ValueError(message)

        line = lines[0]
        if len(line) < 80:
            line = f"{line:<80}"

        try:
            element = line[CARD02_FORMAT["element"]].strip()
            atomic_weight = float(line[CARD02_FORMAT["atomic_weight"]].strip())
            min_energy = float(line[CARD02_FORMAT["min_energy"]].strip())
            max_energy = float(line[CARD02_FORMAT["max_energy"]].strip())

            def parse_int(value: str) -> int | None:
                stripped = value.strip()
                return int(stripped) if stripped else None

            nepnts = parse_int(line[CARD02_FORMAT["nepnts"]])
            itmax = parse_int(line[CARD02_FORMAT["itmax"]])
            icorr = parse_int(line[CARD02_FORMAT["icorr"]])
            nxtra = parse_int(line[CARD02_FORMAT["nxtra"]])
            iptdop = parse_int(line[CARD02_FORMAT["iptdop"]])
            iptwid = parse_int(line[CARD02_FORMAT["iptwid"]])
            ixxchn = parse_int(line[CARD02_FORMAT["ixxchn"]])
            ndigit = parse_int(line[CARD02_FORMAT["ndigit"]])
            idropp = parse_int(line[CARD02_FORMAT["idropp"]])
            matnum = parse_int(line[CARD02_FORMAT["matnum"]])
        except (ValueError, IndexError) as e:
            message = f"Failed to parse Card 2 line: {e}"
            logger.error(message)
            raise ValueError(message)

        if not element:
            message = "Element name cannot be empty"
            logger.error(message)
            raise ValueError(message)

        return ElementInfo(
            element=element,
            atomic_weight=atomic_weight,
            min_energy=min_energy,
            max_energy=max_energy,
            nepnts=nepnts,
            itmax=itmax,
            icorr=icorr,
            nxtra=nxtra,
            iptdop=iptdop,
            iptwid=iptwid,
            ixxchn=ixxchn,
            ndigit=ndigit,
            idropp=idropp,
            matnum=matnum,
        )

    @classmethod
    def to_lines(cls, element_info: ElementInfo) -> List[str]:
        """Convert element information to Card Set 2 formatted line.

        Args:
            element_info: ElementInfo object containing element data

        Returns:
            List containing single formatted line for Card Set 2
        """
        if not isinstance(element_info, ElementInfo):
            message = "element_info must be an instance of ElementInfo"
            logger.error(message)
            raise ValueError(message)

        line = f"{element_info.element:<10s}{element_info.atomic_weight:10.6f}"

        def format_energy(value: float, fixed_format: str) -> str:
            if value != 0.0 and abs(value) < 1.0e-3:
                return f"{value:10.3E}"
            return format(value, fixed_format)

        line += format_energy(element_info.min_energy, "10.3f") + format_energy(element_info.max_energy, "10.1f")

        extra_fields = (
            element_info.nepnts,
            element_info.itmax,
            element_info.icorr,
            element_info.nxtra,
            element_info.iptdop,
            element_info.iptwid,
            element_info.ixxchn,
            element_info.ndigit,
            element_info.idropp,
            element_info.matnum,
        )

        if any(value is not None for value in extra_fields):

            def fmt_int(value: int | None, width: int) -> str:
                if value is None:
                    return " " * width
                return f"{value:>{width}d}"

            line += (
                f"{fmt_int(element_info.nepnts, 5)}"
                f"{fmt_int(element_info.itmax, 5)}"
                f"{fmt_int(element_info.icorr, 2)}"
                f"{fmt_int(element_info.nxtra, 3)}"
                f"{fmt_int(element_info.iptdop, 2)}"
                f" "
                f"{fmt_int(element_info.iptwid, 2)}"
                f"{fmt_int(element_info.ixxchn, 10)}"
                f"{fmt_int(element_info.ndigit, 2)}"
                f"{fmt_int(element_info.idropp, 2)}"
                f"{fmt_int(element_info.matnum, 6)}"
            )

        return [line]
