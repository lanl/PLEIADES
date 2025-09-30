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
    Convert transmission spectra from CSV to SAMMY twenty format.

    This function supports tab-, comma-, and space-separated files, with either two columns
    (energy, transmission) or three columns (energy, transmission, uncertainty).
    If only two columns are present, the uncertainty column will be filled with 0.0.

    Args:
        csv_file: Path to input CSV file with columns: energy_eV, transmission, [uncertainty]
        twenty_file: Path to output SAMMY twenty format file

    File Formats:
        Input CSV (tab, comma, or space separated):
            "energy_eV,transmission,uncertainty\n6.673,0.932,0.272\n"
            or
            "energy_eV\ttransmission\tuncertainty\n6.673\t0.932\t0.272\n"
            or
            "# Energy(eV)  Transmission  Uncertainty\n6.673240e+00 1.003460e+00 7.242967e-03\n"
            or
            "energy_eV,transmission\n6.673,0.932\n"
        Output twenty:
            "        6.6732397079        0.9323834777        0.2727669477\n"

    Example:
        >>> convert_csv_to_sammy_twenty(
        ...     "transmission.txt",
        ...     "transmission.twenty"
        ... )
        >>> convert_csv_to_sammy_twenty(
        ...     "ineuit.csv",
        ...     "ineuit_transmission.twenty"
        ... )
    """
    logger.info(f"Converting {csv_file} to SAMMY twenty format: {twenty_file}")

    data = []

    with open(csv_file, "r") as f:
        lines = f.readlines()

    # Skip header lines (comments starting with # or containing non-numeric first field)
    for line in lines:
        # Strip whitespace and skip empty lines
        line = line.strip()
        if not line:
            continue

        # Skip comment lines
        if line.startswith("#"):
            continue

        # Try to parse the line with different delimiters
        # First try splitting by whitespace (most common for scientific data)
        fields = line.split()

        # If that doesn't give us 2 or 3 fields, try comma
        if len(fields) not in [2, 3]:
            fields = line.split(",")

        # If still not right, try tab
        if len(fields) not in [2, 3]:
            fields = line.split("\t")

        # Skip lines that don't have the right number of fields
        if len(fields) not in [2, 3]:
            # Check if this might be a header line
            try:
                float(fields[0])
            except (ValueError, IndexError):
                continue  # Skip header lines
            logger.warning(f"Skipping line with {len(fields)} fields: {line[:50]}...")
            continue

        # Try to convert to floats
        try:
            numeric_fields = [float(field) for field in fields]
            data.append(numeric_fields)
        except ValueError:
            # This is likely a header line, skip it
            continue

    if not data:
        raise ValueError(f"No valid data found in {csv_file}")

    # Convert data to numpy array of floats
    data = np.array(data, dtype=float)

    # Handle for 2-columns (energy, transmission), and adding zero uncertainty column
    if data.shape[1] == 2:
        data = np.column_stack([data, np.zeros(data.shape[0])])

    # If data is not 2 or 3 columns, raise error
    elif data.shape[1] != 3:
        raise ValueError(f"Expected 2 or 3 columns (energy, transmission, [uncertainty]), got {data.shape[1]}")

    # Check if output directory exists, create if not
    Path(twenty_file).parent.mkdir(parents=True, exist_ok=True)

    # Write to SAMMY twenty format (fixed-width columns)
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
