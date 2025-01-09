#!/usr/bin/env python
"""Helper functions for parameter file handling."""

from enum import Enum
from typing import Optional


class VaryFlag(Enum):
    NO = 0
    YES = 1
    PUP = 3  # propagated uncertainty parameter


def safe_parse(s: str, as_int: bool = False) -> Optional[float]:
    """Helper function to safely parse numeric values

    Args:
        s: String to parse
        as_int: Flag to parse as integer (default: False)

    Returns:
        Parsed value or None if parsing failed
    """
    s = s.strip()
    if not s:
        return None
    try:
        if as_int:
            return int(s)
        return float(s)
    except ValueError:
        return None


def format_float(value: Optional[float], width: int = 11) -> str:
    """Helper to format float values in fixed width with proper spacing"""
    if value is None:
        return " " * width
    # Format with proper scientific notation and alignment
    return f"{value:<{width}.4E}"


def format_vary(value: VaryFlag) -> str:
    """Helper to format vary flags with proper spacing"""
    if value == VaryFlag.NO:
        return "0"
    return "1"
