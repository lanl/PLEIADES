#!/usr/bin/env python
import re
from typing import List

from pydantic import BaseModel

from pleiades.nuclear.models import RadiusParameters
from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

# Regex patterns for keywords
radius_keywords = [r"radius\s*=", r"radii\s*=", r"effective\s+radius", r"true\s+radius"]

# Line two pattern for effective and true radii, with optional flags
line_two_pattern = re.compile(
    r"^\s*(?:" + "|".join(radius_keywords) + r")\s*"
    r"([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)(?:[,\s]+([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?))?"
    r"(?:.*?flags?\s*=?\s*([YNyn10\-3, ]+))?",
    re.IGNORECASE,
)

# Line six pattern for flags, with optional comma-separated values
line_six_pattern = re.compile(r"flags?\s*=?\s*([YNyn10\-3, ]+)", re.IGNORECASE)

# Line seven pattern for groups and channels of each radius
line_seven_pattern = re.compile(r"^\s*group\s*=\s*(\d+|all)\s+chan(?:nels)?\s*=\s*([0-9,\s]+)", re.IGNORECASE)


def parse_flag_values(flag_str, n=2):
    """Parse up to n flag values from a string, return as list of int/str."""
    if not flag_str:
        return [None] * n
    # Split by comma or whitespace
    parts = [s.strip() for s in re.split(r"[,\s]+", flag_str) if s.strip()]

    # Map to canonical values
    def canonical(val):
        if val.upper() in ("Y", "1"):
            return 1
        if val.upper() in ("N", "0"):
            return 0
        if val == "-1":
            return -1
        if val == "3":
            return 3
        return val  # fallback

    flags = [canonical(p) for p in parts]
    # Pad or truncate to n
    if len(flags) == 1:
        # If only one flag, for eff; true is fixed (0), unless eff is -1
        if flags[0] == -1:
            return [-1, -1]
        return [flags[0], 0]
    return (flags + [0] * n)[:n]


class Card07a(BaseModel):
    """
    Class representing the Card 7a format for radii parameters in the SAMMY parameter file.
    This class is used to extract radii information based on a key-word format
    """

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if the first 5 characters of the line are 'ISOTO'
        """
        # Check if the line starts with
        # "RADII" or "CHANN" or "KEY-WORD"
        return (
            line.strip().upper().startswith("RADII") or line.strip().upper().startswith("CHANN") or "KEY-WORD" in line
        )

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

        radius_params_list = []  # List to hold parsed radius parameters

        line_index = 0  # Index for iterating through lines

        # Parse lines into a list of RadiusParameters
        while line_index < len(lines):
            line = lines[line_index]

            # Look for lines matching the radius pattern (line 2)
            radii_match = line_two_pattern.match(line)

            # If a match is found, parse the effective and true radii (along with flags if present)
            if radii_match:
                eff = float(radii_match.group(1))
                true = float(radii_match.group(2)) if radii_match.group(2) else eff
                # Try to get flags from same line
                flag_str = radii_match.group(3)

                # If no flags found, try to get from next line
                if not flag_str:
                    if line_index + 1 < len(lines):
                        flag_match = line_six_pattern.match(lines[line_index + 1])
                        if flag_match:
                            flag_str = flag_match.group(1)

                flag_eff, flag_true = parse_flag_values(flag_str)

                # Parse group and channel assignments for this radii entry
                groups_and_channels = []
                j = line_index + 1
                while j < len(lines):
                    group_match = line_seven_pattern.match(lines[j])
                    if group_match:
                        group = group_match.group(1)
                        if group.lower() == "all":
                            group = "all"
                        else:
                            group = int(group)
                        # Parse channels as list of ints
                        chans = [int(c) for c in re.split(r"[,\s]+", group_match.group(2)) if c.strip()]
                        groups_and_channels.append((group, chans))
                        j += 1
                    else:
                        break

                spin_groups = []  # List to hold spin groups
                channels = []  # List to hold channels
                channel_mode = 0  # Default channel mode
                if groups_and_channels:
                    for group, chans in groups_and_channels:
                        if group == "all":
                            spin_groups = None
                            channels = None
                            channel_mode = 0
                            break
                        spin_groups.append(group)
                        if chans and len(chans) > 0:
                            channels.extend(chans)
                    if channels:
                        channel_mode = 1
                    else:
                        channel_mode = 0
                else:
                    spin_groups = None
                    channels = None
                    channel_mode = 0

                rp = RadiusParameters(
                    effective_radius=eff,
                    true_radius=true,
                    channel_mode=channel_mode,
                    vary_effective=flag_eff,
                    vary_true=flag_true,
                    spin_groups=spin_groups,
                    channels=channels if channel_mode == 1 else None,
                )
                radius_params_list.append(rp)
                line_index = j
            else:
                line_index += 1

        # --- Check if there are multiple isotopes in the fit_config object ---
        multiple_isotopes = False

        # if there are multiple isotopes then check if spin groups of the isotopes match the spin groups of the radius parameters
        if len(fit_config.nuclear_params.isotopes) > 1:
            multiple_isotopes = True

        # Loop through the isotopes to assign or append the radius parameters based on matching spin groups
        if multiple_isotopes:
            for isotope in fit_config.nuclear_params.isotopes:
                logger.info(f"Isotope: {isotope.isotope_information.name}, Spin Groups: {isotope.spin_groups}")

                # Assign matching radius parameters to each isotope
                matching_radii = []
                for radius_param in radius_params_list:
                    if radius_param.spin_groups:
                        # If any spin group in radius_param matches any in isotope
                        if any(sg in isotope.spin_groups for sg in radius_param.spin_groups):
                            matching_radii.append(radius_param)
                    else:
                        # If spin_groups is None, treat as global (assign to all)
                        matching_radii.append(radius_param)
                if matching_radii:
                    isotope.radius_parameters = matching_radii
                    logger.info(
                        f"Assigned {len(matching_radii)} RadiusParameters to Isotope: {isotope.isotope_information.name}"
                    )

        # If no isotopes in fit_config, assign to a default isotope
        if not multiple_isotopes:
            default_isotope = fit_config.nuclear_params.isotopes[0]
            default_isotope.radius_parameters = radius_params_list
            logger.debug(
                f"Assigned {len(radius_params_list)} RadiusParameters to Default Isotope: {default_isotope.isotope_information.name}"
            )
