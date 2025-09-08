"""
SAMMY data format management utilities.

This module provides functions for converting between different data formats
required by SAMMY, including the twenty-column fixed-width format used for
experimental transmission data.
"""

from pathlib import Path
from typing import Union

import numpy as np

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="sammy_data_manager")


def convert_csv_to_sammy_twenty(csv_file: Union[str, Path], twenty_file: Union[str, Path]) -> None:
    """
    Convert PLEIADES transmission CSV to SAMMY twenty format.

    Converts tab-separated transmission data (energy, transmission, uncertainty)
    to SAMMY's twenty-column fixed-width format required for fitting.

    Args:
        csv_file: Path to input CSV file with columns: energy_eV, transmission, uncertainties
        twenty_file: Path to output SAMMY twenty format file

    File Formats:
        Input CSV: "energy_eV\\ttransmission\\tuncertainties\\n6.673...\\t0.932...\\t0.272...\\n"
        Output twenty: "        6.6732397079        0.9323834777        0.2727669477\\n"

    Example:
        >>> convert_csv_to_sammy_twenty(
        ...     "venus_output/Combined_Runs_8022_8023_8024_8025_8026_8027_transmission.txt",
        ...     "sammy_input/venus_transmission.twenty"
        ... )
    """
    logger.info(f"Converting {csv_file} to SAMMY twenty format: {twenty_file}")

    # Load CSV data (skip header row)
    data = np.loadtxt(csv_file, skiprows=1)

    if data.shape[1] != 3:
        raise ValueError(f"Expected 3 columns (energy, transmission, uncertainty), got {data.shape[1]}")

    # Create output directory if needed
    Path(twenty_file).parent.mkdir(parents=True, exist_ok=True)

    # Write in SAMMY twenty format: 20-character fixed-width columns, right-aligned
    with open(twenty_file, "w") as f:
        for energy, transmission, uncertainty in data:
            f.write(f"{energy:20.10f}{transmission:20.10f}{uncertainty:20.10f}\n")

    logger.info(f"Converted {len(data)} data points to twenty format")


def validate_sammy_twenty_format(twenty_file: Union[str, Path]) -> bool:
    """
    Validate that a file follows SAMMY twenty format requirements.

    Checks that each line has exactly 60 characters (3 columns × 20 chars each)
    and contains valid floating point data.

    Args:
        twenty_file: Path to file to validate

    Returns:
        bool: True if file is valid twenty format

    Example:
        >>> is_valid = validate_sammy_twenty_format("data.twenty")
        >>> print(f"File is valid: {is_valid}")
    """
    try:
        with open(twenty_file, "r") as f:
            for line_num, line in enumerate(f, 1):
                # Remove newline for length check
                line_content = line.rstrip("\n\r")

                # Check line length (60 chars = 3 × 20-char columns)
                if len(line_content) != 60:
                    logger.error(f"Line {line_num}: Expected 60 characters, got {len(line_content)}")
                    return False

                # Try to parse as three floats
                try:
                    energy = float(line_content[0:20])
                    transmission = float(line_content[20:40])
                    uncertainty = float(line_content[40:60])
                except ValueError as e:
                    logger.error(f"Line {line_num}: Could not parse as floats: {e}")
                    return False

        logger.info(f"File {twenty_file} is valid SAMMY twenty format")
        return True

    except Exception as e:
        logger.error(f"Error validating {twenty_file}: {e}")
        return False
