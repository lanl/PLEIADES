#!/usr/bin/env python
"""Manages access to nuclear data files packaged with PLEIADES."""

import functools
import io
import logging
import re
import zipfile
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional, Set

import requests

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData

logger = logging.getLogger(__name__)


class NuclearDataManager:
    
    def clear_cache(self) -> None:
        """Clear the file cache and force reinitialization."""
        self._cached_files.clear()
        self._initialize_cache()

    def download_endf_resonance_file(self, isotope: IsotopeInfo, library: str, output_dir: str = ".") -> Path:
        """
        Download and extract resonance parameter section from ENDF library ZIP.

        Args:
            isotope: IsotopeInfo instance with atomic_number, element, mass_number, material_number.
            library: ENDF library version string (e.g., "ENDF-B-VIII.1")
            output_dir: Directory to write the .par output file

        Returns:
            Path to the saved resonance parameter file
        """
        z = f"{isotope.atomic_number:03d}"
        element = isotope.element.capitalize()
        a = isotope.mass_number
        mat = isotope.material_number

        if mat is None:
            mat = self.get_mat_number(isotope)
            if mat is None:
                raise ValueError(f"Cannot determine MAT number for {isotope}")

        filename = f"n_{z}-{element}-{a}_{mat}.zip"
        url = f"https://www-nds.iaea.org/public/download-endf/{library}/n/{filename}"

        logger.info(f"Downloading ENDF data from {url}")
        response = requests.get(url)
        response.raise_for_status()

        output_name = f"{z}-{element}-{a}.{library.replace('ENDF-', '')}.par"
        output_path = Path(output_dir) / output_name

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith((".endf", ".txt", ".dat")):
                    with zip_ref.open(file) as f:
                        content = f.read().decode("utf-8")

                    # Extract only resonance-related lines
                    resonance_lines = [line for line in content.splitlines() if line[70:72].strip() in {"2", "32", "34"}]

                    output_path.write_text("\n".join(resonance_lines))
                    logger.info(f"Resonance parameters written to {output_path}")
                    return output_path

        raise FileNotFoundError("No suitable ENDF file found inside the ZIP.")
