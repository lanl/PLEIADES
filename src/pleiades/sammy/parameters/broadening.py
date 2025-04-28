#!/usr/bin/env python
"""Data class for card 04::broadening parameters."""

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from pleiades.utils.helper import VaryFlag, format_float, format_vary, safe_parse
from pleiades.utils.logger import loguru_logger

# Format definitions for fixed-width fields
# Each numeric field follows a 9+1 pattern:
#   - 9 characters for the actual data (e.g. "1.2340E+00")
#   - 1 character for space separator
# This maintains human readability while ensuring fixed-width alignment


FORMAT_MAIN = {
    "crfn": slice(0, 10),  # Matching radius (F)
    "temp": slice(10, 20),  # Effective temperature (K)
    "thick": slice(20, 30),  # Sample thickness (atoms/barn)
    "deltal": slice(30, 40),  # Spread in flight-path length (m)
    "deltag": slice(40, 50),  # Gaussian resolution width (μs)
    "deltae": slice(50, 60),  # e-folding width of exponential resolution (μs)
    "flag_crfn": slice(60, 62),  # Flag for CRFN
    "flag_temp": slice(62, 64),  # Flag for TEMP
    "flag_thick": slice(64, 66),  # Flag for THICK
    "flag_deltal": slice(66, 68),  # Flag for DELTAL
    "flag_deltag": slice(68, 70),  # Flag for DELTAG
    "flag_deltae": slice(70, 72),  # Flag for DELTAE
}

FORMAT_UNCERTAINTY = {
    "d_crfn": slice(0, 10),  # Uncertainty on CRFN
    "d_temp": slice(10, 20),  # Uncertainty on TEMP
    "d_thick": slice(20, 30),  # Uncertainty on THICK
    "d_deltal": slice(30, 40),  # Uncertainty on DELTAL
    "d_deltag": slice(40, 50),  # Uncertainty on DELTAG
    "d_deltae": slice(50, 60),  # Uncertainty on DELTAE
}

FORMAT_GAUSSIAN = {
    "deltc1": slice(0, 10),  # Width of Gaussian, constant in energy (eV)
    "deltc2": slice(10, 20),  # Width of Gaussian, linear in energy (unitless)
    "flag_deltc1": slice(60, 62),  # Flag for DELTC1
    "flag_deltc2": slice(62, 64),  # Flag for DELTC2
}

FORMAT_GAUSSIAN_UNC = {
    "d_deltc1": slice(0, 10),  # Uncertainty on DELTC1
    "d_deltc2": slice(10, 20),  # Uncertainty on DELTC2
}

CARD_4_HEADER = "BROADening parameters may be varied"


class BroadeningParameters(BaseModel):
    """Container for a single set of broadening parameters.

    Contains all parameters from a single card set 4 entry including:
    - Main parameters (CRFN, TEMP, etc.)
    - Their uncertainties
    - Additional Gaussian parameters
    - Flags indicating whether each parameter should be varied

    Note on fixed-width format:
    Each numeric field in the file uses a 10-column width with a 9+1 pattern:
    - 9 characters for the actual numeric data (e.g. "1.2340E+00")
    - 1 character for space separator
    This format ensures human readability while maintaining proper fixed-width alignment.
    """

    # Main parameters
    crfn: float = Field(description="Matching radius (F)")
    temp: float = Field(description="Effective temperature (K)")
    thick: float = Field(description="Sample thickness (atoms/barn)")
    deltal: float = Field(description="Spread in flight-path length (m)")
    deltag: float = Field(description="Gaussian resolution width (μs)")
    deltae: float = Field(description="e-folding width of exponential resolution (μs)")

    # Optional uncertainties for main parameters
    d_crfn: Optional[float] = Field(None, description="Uncertainty on CRFN")
    d_temp: Optional[float] = Field(None, description="Uncertainty on TEMP")
    d_thick: Optional[float] = Field(None, description="Uncertainty on THICK")
    d_deltal: Optional[float] = Field(None, description="Uncertainty on DELTAL")
    d_deltag: Optional[float] = Field(None, description="Uncertainty on DELTAG")
    d_deltae: Optional[float] = Field(None, description="Uncertainty on DELTAE")

    # Optional additional Gaussian parameters
    deltc1: Optional[float] = Field(None, description="Width of Gaussian, constant in energy (eV)")
    deltc2: Optional[float] = Field(None, description="Width of Gaussian, linear in energy (unitless)")
    d_deltc1: Optional[float] = Field(None, description="Uncertainty on DELTC1")
    d_deltc2: Optional[float] = Field(None, description="Uncertainty on DELTC2")

    # Vary flags for all parameters
    flag_crfn: VaryFlag = Field(default=VaryFlag.NO)
    flag_temp: VaryFlag = Field(default=VaryFlag.NO)
    flag_thick: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltal: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltag: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltae: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltc1: Optional[VaryFlag] = Field(None)
    flag_deltc2: Optional[VaryFlag] = Field(None)

    @model_validator(mode="after")
    def validate_gaussian_parameters(self) -> "BroadeningParameters":
        """Validate that if any Gaussian parameter is present, both are present."""
        has_deltc1 = self.deltc1 is not None
        has_deltc2 = self.deltc2 is not None
        if has_deltc1 != has_deltc2:
            raise ValueError("Both DELTC1 and DELTC2 must be present if either is present")
        if has_deltc1:
            if self.flag_deltc1 is None or self.flag_deltc2 is None:
                raise ValueError("Flags must be specified for DELTC1 and DELTC2 if present")
        return self

    @classmethod
    def from_lines(cls, lines: List[str]) -> "BroadeningParameters":
        """Parse broadening parameters from a list of fixed-width format lines.

        Args:
            lines: List of input lines (excluding header)

        Returns:
            BroadeningParameters: Parsed parameters

        Raises:
            ValueError: If lines are invalid or required data is missing
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        # Make sure first line is long enough
        main_line = f"{lines[0]:<72}"

        params = {}

        # Parse main parameters
        for field in ["crfn", "temp", "thick", "deltal", "deltag", "deltae"]:
            value = safe_parse(main_line[FORMAT_MAIN[field]])
            if value is not None:
                params[field] = value

        # Parse vary flags
        for field in ["flag_crfn", "flag_temp", "flag_thick", "flag_deltal", "flag_deltag", "flag_deltae"]:
            value = main_line[FORMAT_MAIN[field]].strip() or "0"
            try:
                params[field] = VaryFlag(int(value))
            except (ValueError, TypeError):
                params[field] = VaryFlag.NO

        # Parse uncertainties if present
        if len(lines) > 1 and lines[1].strip():
            unc_line = f"{lines[1]:<60}"
            for field in ["d_crfn", "d_temp", "d_thick", "d_deltal", "d_deltag", "d_deltae"]:
                value = safe_parse(unc_line[FORMAT_UNCERTAINTY[field]])
                if value is not None:
                    params[field] = value

        # Parse additional Gaussian parameters if present
        if len(lines) > 2 and lines[2].strip():
            gaussian_line = f"{lines[2]:<64}"

            # Parse main Gaussian parameters
            for field in ["deltc1", "deltc2"]:
                value = safe_parse(gaussian_line[FORMAT_GAUSSIAN[field]])
                if value is not None:
                    params[field] = value

            # Parse Gaussian flags
            for field in ["flag_deltc1", "flag_deltc2"]:
                value = gaussian_line[FORMAT_GAUSSIAN[field]].strip() or "0"
                try:
                    params[field] = VaryFlag(int(value))
                except (ValueError, TypeError):
                    params[field] = VaryFlag.NO

            # Parse Gaussian uncertainties if present
            if len(lines) > 3 and lines[3].strip():
                gaussian_unc_line = f"{lines[3]:<20}"
                for field in ["d_deltc1", "d_deltc2"]:
                    value = safe_parse(gaussian_unc_line[FORMAT_GAUSSIAN_UNC[field]])
                    if value is not None:
                        params[field] = value

        return cls(**params)

    def to_lines(self) -> List[str]:
        """Convert the parameters to a list of fixed-width format lines.

        Returns:
            List[str]: Lines representing the parameters
        """
        lines = []

        # Format main parameter line
        main_parts = [
            format_float(self.crfn, width=9),
            format_float(self.temp, width=9),
            format_float(self.thick, width=9),
            format_float(self.deltal, width=9),
            format_float(self.deltag, width=9),
            format_float(self.deltae, width=9),
        ]
        main_seg = " ".join(main_parts)
        flag_parts = [
            format_vary(self.flag_crfn),
            format_vary(self.flag_temp),
            format_vary(self.flag_thick),
            format_vary(self.flag_deltal),
            format_vary(self.flag_deltag),
            format_vary(self.flag_deltae),
        ]
        flag_seg = " ".join(flag_parts)
        main_line = f"{main_seg}  {flag_seg}"
        lines.append(main_line)

        # Add uncertainties line if any uncertainties are present
        if any(
            getattr(self, f"d_{param}") is not None for param in ["crfn", "temp", "thick", "deltal", "deltag", "deltae"]
        ):
            unc_parts = [
                format_float(getattr(self, f"d_{param}", 0.0), width=9)
                for param in ["crfn", "temp", "thick", "deltal", "deltag", "deltae"]
            ]
            lines.append(" ".join(unc_parts))

        # Add Gaussian parameters if present
        if self.deltc1 is not None and self.deltc2 is not None:
            gaussian_parts = [
                format_float(self.deltc1, width=9),
                format_float(self.deltc2, width=9),
                " " * 40,  # Padding
                format_vary(self.flag_deltc1),
                format_vary(self.flag_deltc2),
            ]
            lines.append(" ".join(gaussian_parts))

            # Add Gaussian uncertainties if present
            if self.d_deltc1 is not None or self.d_deltc2 is not None:
                gaussian_unc_parts = [
                    format_float(self.d_deltc1 or 0.0, width=9),
                    format_float(self.d_deltc2 or 0.0, width=9),
                ]
                lines.append(" ".join(gaussian_unc_parts))

        return lines


class BroadeningParameterCard(BaseModel):
    """Container for a complete broadening parameter card set (Card Set 4).

    This class handles a complete broadening parameter card set, including:
    - Header line
    - Parameter entries
    - Trailing blank line
    """

    parameters: BroadeningParameters

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if line is a valid header
        """
        return line.strip().upper().startswith("BROAD")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "BroadeningParameterCard":
        """Parse a complete broadening parameter card set from lines.

        Args:
            lines: List of input lines including header

        Returns:
            BroadeningParameterCard: Parsed card set

        Raises:
            ValueError: If no valid header found or invalid format
        """
        if not lines:
            raise ValueError("No lines provided")

        # Validate header
        if not cls.is_header_line(lines[0]):
            raise ValueError(f"Invalid header line: {lines[0]}")

        # Parse parameters (skip header and trailing blank lines)
        content_lines = [line for line in lines[1:] if line.strip()]
        if not content_lines:
            raise ValueError("No parameter lines found")

        parameters = BroadeningParameters.from_lines(content_lines)
        return cls(parameters=parameters)

    def to_lines(self) -> List[str]:
        """Convert the card set to a list of lines.

        Returns:
            List[str]: Lines including header and parameters
        """
        lines = [CARD_4_HEADER]
        lines.extend(self.parameters.to_lines())
        lines.append("")  # Trailing blank line
        return lines


if __name__ == "__main__":
    # Enable logging for debugging
    from pleiades.utils.logger import configure_logger

    configure_logger(console_level="DEBUG")
    logger = loguru_logger.bind(name=__name__)

    # Test example with main parameters only
    logger.debug("**Testing main parameters only**")
    main_only_lines = ["1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0"]

    try:
        params = BroadeningParameters.from_lines(main_only_lines)
        logger.debug("Successfully parsed main parameters:")
        logger.debug(f"CRFN: {params.crfn}")
        logger.debug(f"TEMP: {params.temp}")
        logger.debug("Output lines:")
        for line in params.to_lines():
            logger.debug(f"'{line}'")
        logger.debug("")
    except ValueError as e:
        logger.error(f"Failed to parse main parameters: {e}")

    # Test example with uncertainties
    logger.debug("**Testing with uncertainties**")
    with_unc_lines = [
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0",
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02",
    ]

    try:
        params = BroadeningParameters.from_lines(with_unc_lines)
        logger.debug("Successfully parsed parameters with uncertainties:")
        logger.debug(f"CRFN: {params.crfn} ± {params.d_crfn}")
        logger.debug(f"TEMP: {params.temp} ± {params.d_temp}")
        logger.debug("Output lines:")
        for line in params.to_lines():
            logger.debug(f"'{line}'")
        logger.debug("")
    except ValueError as e:
        logger.error(f"Failed to parse parameters with uncertainties: {e}")

    # Test example with Gaussian parameters
    logger.debug("**Testing with Gaussian parameters**")
    full_lines = [
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0",
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02",
        "1.000E-01 2.000E-02                                              1 1",
        "5.000E-03 1.000E-03",
    ]

    try:
        params = BroadeningParameters.from_lines(full_lines)
        logger.debug("Successfully parsed full parameter set:")
        logger.debug(f"DELTC1: {params.deltc1} ± {params.d_deltc1}")
        logger.debug(f"DELTC2: {params.deltc2} ± {params.d_deltc2}")
        logger.debug("Output lines:")
        for line in params.to_lines():
            logger.debug(f"'{line}'")
        logger.debug("")
    except ValueError as e:
        logger.error(f"Failed to parse full parameter set: {e}")

    # Test complete card set
    logger.debug("**Testing complete card set**")
    card_lines = [
        "BROADening parameters may be varied",
        "1.234E+00 2.980E+02 1.500E-01 2.500E-02 1.000E+00 5.000E-01  1 0 1 0 1 0",
        "1.000E-02 1.000E+00 1.000E-03 1.000E-03 1.000E-02 1.000E-02",
        "1.000E-01 2.000E-02                                              1 1",
        "5.000E-03 1.000E-03",
        "",
    ]

    try:
        card = BroadeningParameterCard.from_lines(card_lines)
        logger.debug("Successfully parsed complete card set")
        logger.debug("Output lines:")
        for line in card.to_lines():
            logger.debug(f"'{line}'")
    except ValueError as e:
        logger.error(f"Failed to parse complete card set: {e}")

    # Test error handling
    logger.debug("**Testing Error Handling**")

    # Test invalid header
    try:
        bad_lines = [
            "WRONG header line",
            "1.2340E+00 2.9800E+02 1.5000E-01 2.5000E-02 1.0000E+00 5.0000E-01  1 0 1 0 1 0",
            "",
        ]
        logger.debug("Testing invalid header:")
        BroadeningParameterCard.from_lines(bad_lines)
    except ValueError as e:
        logger.debug(f"Caught expected error for invalid header: {e}")

    # Test invalid Gaussian parameters (missing one)
    try:
        bad_lines = [
            "1.2340E+00 2.9800E+02 1.5000E-01 2.5000E-02 1.0000E+00 5.0000E-01  1 0 1 0 1 0",  ## 11 char instead of 10
            "1.0000E-02 1.0000E+00 1.0000E-03 1.0000E-03 1.0000E-02 1.0000E-02",
            "1.0000E-01                                                     1 1",  # Missing DELTC2
        ]
        BroadeningParameters.from_lines(bad_lines)
    except ValueError as e:
        logger.debug(f"Caught expected error for invalid Gaussian parameters: {e}")
