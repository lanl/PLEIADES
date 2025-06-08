#!/usr/bin/env python
import re
from typing import Dict, List

from pydantic import BaseModel

from pleiades.nuclear.models import IsotopeInfo, IsotopeMassData, IsotopeParameters, ParticlePair
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
            (r"(?i)Particle A\s*=\s*", "PA="),
            (r"(?i)Particle B\s*=\s*", "PB="),
            (r"(?i)Charge_A\s*=\s*", "ZA="),
            (r"(?i)Charge_B\s*=\s*", "ZB="),
            (r"(?i)PEnetrability\s*=\s*", "PENT="),
            (r"(?i)Shift\s*=\s*", "SHIFT="),
            (r"(?i)Spin A\s*=\s*", "SA="),
            (r"(?i)Spin B\s*=\s*", "SB="),
            (r"(?i)Mass A\s*=\s*", "MA="),
            (r"(?i)Mass B\s*=\s*", "MB="),
            # Accept any Q* (Q-value, Q-V, QVAL, Q, etc, case-insensitive, with or without dash/space/underscore)
            (r"(?i)Q[\-_ ]?([A-Za-z]*)\s*=\s*", "Q="),
            # Accept both THreshold and Threshold (case-insensitive)
            (r"(?i)THreshold\s*=\s*", "THRESHOLD="),
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
            # Accumulate lines for each particle pair block, ending on a blank line or a new NAME= line
            particle_lines = []
            for line in lines[1:]:
                if line.strip() == "":
                    # End of a block, process accumulated lines
                    if particle_lines:
                        block = " ".join(particle_lines)
                        norm_block = cls.normalize_keywords(block)
                        # Allow for split key-value pairs across lines (e.g., Name=... on one line, Particle a=... on next)
                        # Find all key-value pairs, even if separated by newlines or extra spaces
                        pairs = re.findall(r"(\w+)=\s*([^=]+?)(?=\s+\w+=|$)", norm_block, re.DOTALL)
                        # Also catch any single key-value at the end
                        if not pairs:
                            m = re.match(r"\s*(\w+)=\s*(.+)", norm_block)
                            if m:
                                pairs = [(m.group(1), m.group(2))]
                        kv = {k.upper(): v.strip() for k, v in pairs}
                        # If PA or PB are missing, try to recover from multi-line split (e.g., Particle a=... on its own line)
                        if "PA" not in kv or "PB" not in kv:
                            # Try to find PA and PB in the original lines
                            for particle_line in particle_lines:
                                lnorm = cls.normalize_keywords(particle_line)
                                if lnorm.strip().startswith("PA="):
                                    kv["PA"] = lnorm.split("=", 1)[1].strip()
                                if lnorm.strip().startswith("PB="):
                                    kv["PB"] = lnorm.split("=", 1)[1].strip()
                        if all(k in kv for k in ("NAME", "PA", "PB")):
                            particle_pairs.append(cls._build_particle_pair(kv))
                        particle_lines = []
                    continue
                # If a new NAME= line and we already have lines, process previous block
                norm_line = cls.normalize_keywords(line)
                if norm_line.strip().startswith("NAME=") and particle_lines:
                    block = " ".join(particle_lines)
                    norm_block = cls.normalize_keywords(block)
                    pairs = re.findall(r"(\w+)=\s*([^=]+?)(?=\s+\w+=|$)", norm_block, re.DOTALL)
                    if not pairs:
                        m = re.match(r"\s*(\w+)=\s*(.+)", norm_block)
                        if m:
                            pairs = [(m.group(1), m.group(2))]
                    kv = {k.upper(): v.strip() for k, v in pairs}
                    if "PA" not in kv or "PB" not in kv:
                        for particle_line in particle_lines:
                            lnorm = cls.normalize_keywords(particle_line)
                            if lnorm.strip().startswith("PA="):
                                kv["PA"] = lnorm.split("=", 1)[1].strip()
                            if lnorm.strip().startswith("PB="):
                                kv["PB"] = lnorm.split("=", 1)[1].strip()
                    if all(k in kv for k in ("NAME", "PA", "PB")):
                        particle_pairs.append(cls._build_particle_pair(kv))
                    particle_lines = []
                particle_lines.append(line)
            # After all lines, process any remaining block
            if particle_lines:
                block = " ".join(particle_lines)
                norm_block = cls.normalize_keywords(block)
                pairs = re.findall(r"(\w+)=\s*([^=]+?)(?=\s+\w+=|$)", norm_block, re.DOTALL)
                if not pairs:
                    m = re.match(r"\s*(\w+)=\s*(.+)", norm_block)
                    if m:
                        pairs = [(m.group(1), m.group(2))]
                kv = {k.upper(): v.strip() for k, v in pairs}
                if "PA" not in kv or "PB" not in kv:
                    for particle_line in particle_lines:
                        lnorm = cls.normalize_keywords(particle_line)
                        if lnorm.strip().startswith("PA="):
                            kv["PA"] = lnorm.split("=", 1)[1].strip()
                        if lnorm.strip().startswith("PB="):
                            kv["PB"] = lnorm.split("=", 1)[1].strip()
                if all(k in kv for k in ("NAME", "PA", "PB")):
                    particle_pairs.append(cls._build_particle_pair(kv))

        elif format_type == "fixed":
            for line in lines[1:]:
                if line.strip():
                    kv = cls.parse_fixed_format_line(line)
                    particle_pairs.append(cls._build_particle_pair(kv))

        # If no valid format was determined, raise an error
        else:
            logger.error("Unable to determine format (keyword or fixed) for Card 4.")
            raise ValueError("Unable to determine format (keyword or fixed) for Card 4.")

        logger.info(f"Found {len(particle_pairs)} particle pairs in Card 4.")

        # If fit_config is None, create a new FitConfig instance
        if fit_config is None:
            fit_config = FitConfig()

        # if fit_config is not None, ensure it is an instance of FitConfig
        elif not isinstance(fit_config, FitConfig):
            raise ValueError("fit_config must be an instance of FitConfig")

        # add the particle pairs info to the fit_config
        if not fit_config.nuclear_params.isotopes or len(fit_config.nuclear_params.isotopes) == 0:
            # Create a dummy isotope UNK-000 and append all particle pairs to it
            unk_isotope = IsotopeParameters(
                isotope_information=IsotopeInfo(
                    name="UNK-000",
                    element="UNK",
                    mass_number=0,
                    atomic_number=0,
                    mass_data=IsotopeMassData(atomic_mass=0.0),
                ),
                particle_pairs=[],
            )
            for pair in particle_pairs:
                if not any(existing_pair.name == pair.name for existing_pair in unk_isotope.particle_pairs):
                    unk_isotope.append_particle_pair(pair)
                    logger.info(f"Pair name set for isotope UNK-000: {pair.name}")
            fit_config.nuclear_params.isotopes.append(unk_isotope)
        else:
            for pair in particle_pairs:
                for isotope in fit_config.nuclear_params.isotopes:
                    if not hasattr(isotope, "particle_pairs"):
                        continue
                    iso_mass = (
                        isotope.isotope_information.mass_data.atomic_mass
                        if isotope.isotope_information.mass_data
                        else None
                    )
                    if iso_mass is None:
                        continue
                    ma_diff = abs(iso_mass - pair.mass_a)
                    mb_diff = abs(iso_mass - pair.mass_b)
                    # Only add if either matches within tolerance
                    if ma_diff < 0.01 or mb_diff < 0.01:
                        # Prevent duplicate particle pairs by name
                        if not any(existing_pair.name == pair.name for existing_pair in isotope.particle_pairs):
                            isotope.append_particle_pair(pair)
                            logger.info(f"Pair name set for isotope {isotope.isotope_information.name}: {pair.name}")

    @staticmethod
    def _build_particle_pair(kv: Dict[str, str]) -> ParticlePair:
        # Handle q_value and threshold as optional floats, treat missing/empty/zero as None
        def parse_optional_float(val):
            if val is None or str(val).strip() == "":
                return None
            try:
                f = float(val)
                if abs(f) < 1e-12:
                    return None
                return f
            except Exception:
                return None

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
            q_value=parse_optional_float(kv.get("Q", None)),
            threshold=parse_optional_float(kv.get("THRESHOLD", None)),
        )

    @staticmethod
    def to_lines(fit_config: FitConfig) -> List[str]:
        """Convert the particle pairs to lines for Card 4 in keyword format, including Q and Threshold if present and nonzero."""
        lines = ["PARTICLE PAIR DEFINITIONS"]
        for isotope in fit_config.nuclear_params.isotopes:
            for pair in isotope.particle_pairs:
                # Always write the first line
                lines.append(f"Name={pair.name:<12} PA={pair.name_a:<12} PB={pair.name_b:<12}")
                # Second line: charges, pent, shift
                lines.append(
                    f"\tZA={int(pair.charge_a):6d}\tZB={int(pair.charge_b):6d}\tPent={int(pair.calculate_penetrabilities):<1}\tShift={int(pair.calculate_shifts):<1}"
                )
                # Third line: spins, masses
                lines.append(
                    f"\tSA={pair.spin_a:6.1f}\tSB={pair.spin_b:6.1f}\tMA={pair.mass_a:15.12f}\tMB={pair.mass_b:15.12f}"
                )
                # Fourth line: Q and Threshold, only if present and nonzero
                qval = pair.q_value if pair.q_value is not None and abs(pair.q_value) > 1e-12 else None
                thresh = pair.threshold if pair.threshold is not None and abs(pair.threshold) > 1e-12 else None
                if qval is not None or thresh is not None:
                    qstr = f"Q={qval:.8f}" if qval is not None else ""
                    tstr = f"Threshold={thresh:.8f}" if thresh is not None else ""
                    # Write both if both present, else just one
                    lines.append(f"\t{qstr}{tstr}")
        lines.append("")
        return lines
