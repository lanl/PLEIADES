#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.experimental.models import NormalizationParameters, PhysicsParameters
from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.helper import VaryFlag
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


FORMAT_MAIN = {
    "anorm": slice(0, 10),  # Normalization
    "backa": slice(10, 20),  # Constant background
    "backb": slice(20, 30),  # Background proportional to 1/E
    "backc": slice(30, 40),  # Background proportional to √E
    "backd": slice(40, 50),  # Exponential background coefficient
    "backf": slice(50, 60),  # Exponential decay constant
    "flag_anorm": slice(60, 62),  # Flag for ANORM
    "flag_backa": slice(62, 64),  # Flag for BACKA
    "flag_backb": slice(64, 66),  # Flag for BACKB
    "flag_backc": slice(66, 68),  # Flag for BACKC
    "flag_backd": slice(68, 70),  # Flag for BACKD
    "flag_backf": slice(70, 72),  # Flag for BACKF
}

FORMAT_UNCERTAINTY = {
    "d_anorm": slice(0, 10),
    "d_backa": slice(10, 20),
    "d_backb": slice(20, 30),
    "d_backc": slice(30, 40),
    "d_backd": slice(40, 50),
    "d_backf": slice(50, 60),
}


class Card06(BaseModel):
    """
    Class representing the Card 6 format for normalization parameters in the SAMMY parameter file.
    This class is used to extract normalization information based on a default format.
    """

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if the first 5 characters of the line are 'ISOTO'
        """

        return line.strip().upper().startswith("NORMA")

    @classmethod
    def from_lines(cls, lines: List[str], fit_config: FitConfig = None) -> None:
        """Parse a complete isotope parameter card set from lines.

        Args:
            lines: List of input lines including header and blank terminator
            FitConfig: FitConfig object to read isotopes into.

        Raises:
            ValueError: If no valid header found or invalid format
        """

        if not lines:
            message = "No lines provided"
            logger.error(message)
            raise ValueError(message)

        # Validate header
        if not cls.is_header_line(lines[0]):
            message = f"Invalid header line: {lines[0]}"
            logger.error(message)
            raise ValueError(message)

        # if fit_config is not an instance of FitConfig, raise an error
        if fit_config is not None and not isinstance(fit_config, FitConfig):
            message = "fit_config must be an instance of FitConfig"
            logger.error(message)
            raise ValueError(message)

        elif fit_config is None:
            fit_config = FitConfig()

        # Ensure fit_config.physics_parameters exists
        if not hasattr(fit_config, "physics_parameters") or fit_config.physics_parameters is None:
            fit_config.physics_parameters = PhysicsParameters()

        # --- Begin parsing ---
        # Card 6 main line is usually the second line (after header)
        main_line = None
        uncertainty_line = None
        for line in lines[1:]:
            if line.strip() == "":
                continue
            if main_line is None:
                main_line = line
            elif uncertainty_line is None:
                uncertainty_line = line
                break

        # Parse main values and flags
        main_kwargs = {}
        if main_line:
            for key, sl in FORMAT_MAIN.items():
                val = main_line[sl].strip()
                if key.startswith("flag_"):
                    # Flags: convert to int or VaryFlag
                    try:
                        main_kwargs[key] = VaryFlag(int(val)) if val else VaryFlag.NO
                    except Exception:
                        main_kwargs[key] = VaryFlag.NO
                else:
                    main_kwargs[key] = float(val) if val else None
        # Parse uncertainties
        if uncertainty_line:
            for key, sl in FORMAT_UNCERTAINTY.items():
                val = uncertainty_line[sl].strip()
                main_kwargs[key] = float(val) if val else None

        norm_params = NormalizationParameters(**main_kwargs)
        fit_config.physics_parameters.normalization_parameters = norm_params
        logger.info("Assigned normalization parameters to fit_config.physics_parameters.normalization_parameters")
