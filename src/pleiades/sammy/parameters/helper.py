#!/usr/bin/env python
"""Helper functions for parameter file handling."""

import re
from enum import Enum
from typing import Optional


class VaryFlag(Enum):
    NO = 0
    YES = 1
    PUP = 3  # propagated uncertainty parameter
    USE_FROM_PARFILE = -1  # do not vary, use value from parfile
    USE_FROM_OTHERS = -2  # do not vary, use value from other sources (INP, COV, etc.)


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

    # Subtract 5 characters for "E+xx" (scientific notation exponent)
    # The rest is for the significant digits (1 before the dot and decimals)
    max_decimals = max(0, width - 6)  # At least room for "0.E+00"

    # Create a format string with dynamic precision
    format_str = f"{{:.{max_decimals}E}}"
    formatted = format_str.format(value)

    # Ensure the string fits the width
    if len(formatted) > width:
        raise ValueError(f"Cannot format value {value} to fit in {width} characters.")

    # Align to the left if required
    return f"{formatted:<{width}}"


def format_vary(value: VaryFlag) -> str:
    """Helper to format vary flags with proper spacing"""
    if value == VaryFlag.NO:
        return "0"
    if value == VaryFlag.YES:
        return "1"
    if value == VaryFlag.PUP:
        return "3"
    if value == VaryFlag.USE_FROM_PARFILE:
        return "-1"
    if value == VaryFlag.USE_FROM_OTHERS:
        return "-2"
    raise ValueError(f"Unsupported vary flag: {value}")


def parse_keyword_pairs_to_dict(text: str) -> dict:
    """
    Parse an ASCII text into a dictionary of keyword-value pairs.

    Parameters:
        text (str): The input text with keyword-value pairs.

    Returns:
        dict: A dictionary with keywords as keys and parsed values.
    """
    data = {}

    # Regex to match key=value pairs
    # (\w+): captures the keyword
    # \s*=\s*: matches the equal sign with optional spaces around it
    # ([^=\n]+?): captures the value until the next keyword or end of line
    # (?=\s+\w+\s*=|$): lookahead to match the next keyword or end of line
    pattern = r"(\w+)\s*=\s*([^=\n]+?)(?=\s+\w+\s*=|$)"

    for line in text.splitlines():
        # Skip empty lines
        if not line.strip():
            continue

        # Find all key-value pairs in the line
        matches = re.findall(pattern, line)

        for key, value in matches:
            # Process the value
            value = value.strip()
            if " " in value:
                # Convert space-separated numbers to a list of float or int
                items = value.split()
                parsed_value = [float(item) if "." in item else int(item) if item.isdigit() else item for item in items]
            else:
                # Single value, convert to int or float if possible
                if value.isdigit():
                    parsed_value = int(value)
                else:
                    parsed_value = float(value) if "." in value else value

            data[key] = parsed_value

    return data
