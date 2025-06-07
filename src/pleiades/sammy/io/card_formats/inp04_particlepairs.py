#!/usr/bin/env python
import re
from typing import Dict, List

from pydantic import BaseModel

from pleiades.nuclear.models import ParticlePair
from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class Card04(BaseModel):
    @staticmethod
    def is_header_line(line: str) -> bool:
        return line.strip().upper().startswith("PARTICLE PAIR DEFINITIONS")

    @staticmethod
    def normalize_keywords(line: str) -> str:
        # Use regex for robust, case-insensitive, and space-tolerant replacements
        replacements = [
            (r"(?i)\bName\s*=\s*", "NAME="),
            (r"(?i)Particle a\s*=\s*", "PA="),
            (r"(?i)Particle b\s*=\s*", "PB="),
            (r"(?i)Za\s*=\s*", "ZA="),
            (r"(?i)Zb\s*=\s*", "ZB="),
            (r"(?i)Pent\s*=\s*", "PENT="),
            (r"(?i)Shift\s*=\s*", "SHIFT="),
            (r"(?i)Sa\s*=\s*", "SA="),
            (r"(?i)Sb\s*=\s*", "SB="),
            (r"(?i)Ma\s*=\s*", "MA="),
            (r"(?i)Mb\s*=\s*", "MB="),
            (r"(?i)Q-?Value\s*=\s*", "Q="),
        ]
        for pattern, replacement in replacements:
            line = re.sub(pattern, replacement, line)
        return line

    @staticmethod
    def is_fixed_format_line(line: str) -> bool:
        # A basic check: fixed format lines often have particle names and numbers in fixed columns
        return len(line) > 40 and "=" not in line

    @staticmethod
    def parse_fixed_format_line(line: str) -> Dict[str, str]:
        return {
            "NAME": line[0:8].strip(),
            "PA": line[8:10].strip(),
            "PB": line[10:12].strip(),
            "ZA": line[12:15].strip(),
            "ZB": line[15:18].strip(),
            "PENT": line[18:19].strip(),
            "SHIFT": line[19:20].strip(),
            "SA": line[20:25].strip(),
            "SB": line[25:30].strip(),
            "MA": line[30:40].strip(),
            "MB": line[40:50].strip(),
            "Q": line[50:60].strip(),
            "RE": line[60:70].strip(),
            "RT": line[70:80].strip(),
        }

    @staticmethod
    def parse_key_value_line(line):
        # Improved regex: value can include spaces, up to next key or end of line
        matches = re.findall(r"(\w+)=\s*([^=]+?)(?=\s+\w+=|$)", line)
        return {k.upper(): v.strip() for k, v in matches}

    @classmethod
    def from_lines(cls, lines: List[str], fit_config: FitConfig = None) -> None:
        """Parse a complete Card 4 from lines.
        Args:
            lines: List of input lines including header and blank terminator
            fit_config: FitConfig object to read particle pairs into.
        """
        if not lines or not cls.is_header_line(lines[0]):
            raise ValueError("Missing or invalid Card 4 header")

        particle_pairs = []
        current_block = {}

        # Determine format based on second non-blank line
        format_type = None
        for line in lines[1:]:
            if line.strip():
                format_type = "fixed" if cls.is_fixed_format_line(line) else "keyword"
                break

        # Count the number of '=' in the line and process each keyword pair
        if format_type == "keyword":
            for line in lines[1:]:
                if line.strip() == "":
                    continue
                norm_line = cls.normalize_keywords(line)
                eq_count = norm_line.count("=")
                if eq_count == 0:
                    continue
                # Split and process each key-value pair
                pairs = re.findall(r"(\w+)=\s*([^=]+?)(?=\s+\w+=|$)", norm_line)
                for k, v in pairs:
                    current_block[k.upper()] = v.strip()

                # If a new NAME= is found, treat as new block
                if "NAME" in [k.upper() for k, _ in pairs]:
                    if current_block and all(k in current_block for k in ("NAME", "PA", "PB")):
                        particle_pairs.append(cls._build_particle_pair(current_block))
                    current_block = {}

        elif format_type == "fixed":
            for line in lines[1:]:
                if line.strip():
                    kv = cls.parse_fixed_format_line(line)
                    particle_pairs.append(cls._build_particle_pair(kv))

        # If no valid format was determined, raise an error
        else:
            logger.error("Unable to determine format (keyword or fixed) for Card 4.")
            raise ValueError("Unable to determine format (keyword or fixed) for Card 4.")

        print(f"Found {len(particle_pairs)} particle pairs in Card 4.")
        print("Particle pairs:", particle_pairs)

        # If fit_config is None, create a new FitConfig instance
        if fit_config is None:
            fit_config = FitConfig()

        # if fit_config is not None, ensure it is an instance of FitConfig
        elif not isinstance(fit_config, FitConfig):
            raise ValueError("fit_config must be an instance of FitConfig")

        # add the particle pairs info to the fit_config
        for pair in particle_pairs:
            add_flag = False
            for isotope in fit_config.nuclear_params.isotopes:
                # calculate the mass differences for Ma and Mb with the isotope
                ma_diff = (
                    abs(isotope.isotope_information.mass_data.atomic_mass - pair.mass_a)
                    if isotope.isotope_information.mass_data
                    else "unknown"
                )
                mb_diff = (
                    abs(isotope.isotope_information.mass_data.atomic_mass - pair.mass_b)
                    if isotope.isotope_information.mass_data
                    else "unknown"
                )

                if ma_diff != "unknown" and ma_diff < 0.01:
                    add_flag = True
                    logger.info(f"Pair name set for isotope {isotope.isotope_information.name}: {pair.name}")
                elif mb_diff != "unknown" and mb_diff < 0.01:
                    add_flag = True
                    logger.info(f"Pair name set for isotope {isotope.isotope_information.name}: {pair.name}")

                if add_flag:
                    isotope.append_particle_pair(pair)

    @staticmethod
    def _build_particle_pair(kv: Dict[str, str]) -> ParticlePair:
        return ParticlePair(
            name=kv.get("NAME", ""),
            name_a=kv.get("PA", ""),
            name_b=kv.get("PB", ""),
            mass_a=float(kv.get("MA", 0)),
            mass_b=float(kv.get("MB", 0)),
            spin_a=float(kv.get("SA", 0)),
            spin_b=float(kv.get("SB", 0)),
            charge_a=int(kv.get("ZA", 0)),
            charge_b=int(kv.get("ZB", 0)),
            calculate_penetrabilities=kv.get("PENT", "0") in ("1", "YES"),
            calculate_shifts=kv.get("SHIFT", "0") in ("1", "YES"),
            # The following fields use defaults from the model, but you can map more if needed:
            # parity_a, parity_b, calculate_phase_shifts, effective_radius, true_radius
        )

    @staticmethod
    def to_lines(fit_config: FitConfig) -> List[str]:
        """Convert the particle pairs to lines for Card 4 in keyword format."""
        lines = ["PARTICLE PAIR DEFINITIONS"]
        for isotope in fit_config.nuclear_params.isotopes:
            for pair in isotope.particle_pairs:
                lines.append(f"Name={pair.name:<12} Particle a={pair.name_a:<12} Particle b={pair.name_b:<12}")
                lines.append(
                    f"     Za={pair.charge_a:<3}        Zb={pair.charge_b:<3}         Pent={int(pair.calculate_penetrabilities):<1}     Shift={int(pair.calculate_shifts):<1}"
                )
                lines.append(
                    f"     Sa={pair.spin_a:6.1f}     Sb={pair.spin_b:7.1f}     Ma={pair.mass_a:15.12f}     Mb={pair.mass_b:15.12f}"
                )
        lines.append("")
        return lines
