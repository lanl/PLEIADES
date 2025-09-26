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


def check_pseudo_scientific(val: str) -> float:
    """Check for pseudo scientific notation sometimes found in SAMMY files.

    Args:
        val (str): The input string potentially containing pseudo scientific notation.

    Returns:
        str: The fixed string with proper scientific notation.

    Examples:

    """
    import re

    s = str(val).strip()
    # Case 1: 5.00000.-5 or -1.23.+4 (dot before sign)
    m = re.match(r"^([+-]?\d*\.?\d+)\.(\+|\-)(\d+)$", s)
    if m:
        s_fixed = f"{m.group(1)}e{m.group(2)}{m.group(3)}"
        try:
            return float(s_fixed)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert pseudo-scientific string '{val}' to float (fixed: '{s_fixed}')")
    # Case 2: 5.00000-5 or -1.23+4 (no dot before sign, no E)
    m2 = re.match(r"^([+-]?\d*\.?\d+)([+-]\d+)$", s)
    if m2:
        s_fixed = f"{m2.group(1)}e{m2.group(2)}"
        try:
            return float(s_fixed)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert pseudo-scientific string '{val}' to float (fixed: '{s_fixed}')")
    # Case 3: already valid scientific notation or normal float
    try:
        return float(s)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert string '{val}' to float. Original error: {e}")


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

    # If it fits, return the formatted scientific notation
    if len(formatted) <= width:
        return f"{formatted:<{width}}"

    # Fall back to standard float format
    max_decimals_f = max(0, width - len(f"{int(value):d}") - 2)  # Leave room for "-" and "."
    format_str_float = f"{{:.{max_decimals_f}f}}"
    formatted_float = format_str_float.format(value)

    # Ensure the fallback fits
    if len(formatted_float) > width:
        raise ValueError(f"Cannot format value {value} to fit in {width} characters.")

    return f"{formatted_float:<{width}}"


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

    Args:
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
