#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class Card10p2(BaseModel):
    """Model for the INP10 card format (spin groups)."""

    @staticmethod
    def is_header_line(line: str) -> bool:
        return line.strip().upper().startswith("SPIN GROUPS")

    @classmethod
    def from_lines(cls, lines: List[str], fit_config: FitConfig = None) -> None:
        """Parse INP10 card lines and update the fit configuration."""
        if not fit_config:
            raise ValueError("FitConfig must be provided to parse INP10 card.")
