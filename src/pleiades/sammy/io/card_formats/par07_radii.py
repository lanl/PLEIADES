#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class Card07(BaseModel):
    """
    Class representing the Card 7 format for radii parameters in the SAMMY parameter file.
    This class is used to extract radii information based on a default format.
    """

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

        # Not currently supporting the default format for Card 7
        # Raise an error if the default format is not supported
        message = "Default format for Card 7 is not supported"
        logger.error(message)
        raise ValueError(message)
