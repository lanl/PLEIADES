#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.sammy.fitting.config import FitConfig
from pleiades.nuclear.models import SpinGroups, SpinGroupChannelInfo
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class Card10p2(BaseModel):
    """Model for the INP10 card format (spin groups)."""

    @staticmethod
    def is_header_line(line: str) -> bool:
        return line.strip().upper().startswith("SPIN GROUPS")

    @staticmethod
    def get_line_type(line: str):
        """
        Returns:
            "SPIN_GROUP" if the line is a spin group line,
            "CHANNEL" if the line is a channel line,
            None otherwise.
        """
        s = line[:8]
        if (
            len(s) >= 8
            and s[0:3].strip().isdigit()
            and (s[3] == " " or s[3].upper() == "X")
            and s[4:6] == "  "
        ):
            return "SPIN_GROUP"
        if (
            len(s) >= 8
            and s[0:2] == "  "
            and s[2:5].strip().isdigit()
            and s[5:7] == "  "
        ):
            return "CHANNEL"
        return None

    @classmethod
    def from_lines(cls, lines: List[str], fit_config: FitConfig = None) -> None:
        if not lines:
            message = "No lines provided"
            logger.error(message)
            raise ValueError(message)
        if fit_config is None or not isinstance(fit_config, FitConfig):
            message = "fit_config must be an instance of FitConfig"
            logger.error(message)
            raise ValueError(message)

        # Skip header if present
        if cls.is_header_line(lines[0]):
            lines = lines[1:]

        spin_groups = []
        idx = 0

        while idx < len(lines):

            line = lines[idx]
            
            if not line.strip():
                idx += 1
                continue

            line_type = cls.get_line_type(line)
            
            if line_type is None:
                idx += 1
                continue

            if line_type == "SPIN_GROUP":
                # Parse spin group line
                try:
                    spin_group_number = int(line[0:3].strip())
                    if line[4:5].strip().upper() == "X":
                        excluded = 1
                    elif line[4:5].strip() == "":
                        excluded = 0
                    else:
                        raise ValueError(f"Invalid exclusion flag in line: {line.strip()}")
                    number_of_entry_channels = int(line[7:10].strip())
                    number_of_exit_channels = int(line[12:15].strip())
                    spin = float(line[15:20].strip())
                    abundance = float(line[20:30].strip())
                except Exception as e:
                    logger.error(
                        f"Failed to parse spin group line: |{line}| ("
                        f"spin_group_number='{line[0:3].strip()}', "
                        f"number_of_entry_channels='{line[7:10].strip()}', "
                        f"number_of_exit_channels='{line[12:15].strip()}', "
                        f"spin='{line[15:20].strip()}', "
                        f"abundance='{line[20:30].strip()}') ({e})"
                    )
                    raise ValueError(f"Failed to parse spin group line: {line.strip()} ({e})")

                # Parse all channel info lines for this spin group
                channel_info = []
                idx += 1
                while idx < len(lines):
                    ch_line = lines[idx]
                    if cls.get_line_type(ch_line) != "CHANNEL":
                        break
                    try:
                        channel_number = int(ch_line[2:5].strip()) if ch_line[2:5].strip() != "" else None
                        particle_pair_name = ch_line[7:15].strip() if ch_line[7:15].strip() != "" else "UNKNOWN"
                        if ch_line[17:18].strip().upper() == "X":
                            exclude_channel = 1
                        elif ch_line[17:18].strip() == "":
                            exclude_channel = 0
                        else:
                            exclude_channel = 0
                        orbital_angular_momentum = int(ch_line[18:20].strip()) if ch_line[18:20].strip().isdigit() else None
                        channel_spin = float(ch_line[20:30].strip()) if ch_line[20:30].strip() != "" else None
                        en_boundary = float(ch_line[30:40].strip()) if ch_line[30:40].strip() != "" else None
                        effective_radius = float(ch_line[40:50].strip()) if ch_line[40:50].strip() != "" else None
                        true_radius = float(ch_line[50:60].strip()) if ch_line[50:60].strip() != "" else None
                    except Exception as e:
                        logger.error(f"Failed to parse channel line: {ch_line.strip()} ({e})")
                        raise ValueError(f"Failed to parse channel line: {ch_line.strip()} ({e})")
                    channel_info.append(
                        SpinGroupChannelInfo(
                            channel_number=channel_number,
                            particle_pair_name=particle_pair_name,
                            exclude_channel=exclude_channel,
                            channel_spin=channel_spin,
                        )
                    )
                    idx += 1

                spin_group = SpinGroups(
                    spin_group_number=spin_group_number,
                    excluded=excluded,
                    number_of_entry_channels=number_of_entry_channels,
                    number_of_exit_channels=number_of_exit_channels,
                    spin=spin,
                    abundance=abundance,
                    channel_info=channel_info,
                )
                spin_groups.append(spin_group)
            
            # Check to see if the spin group already exists
            
            #TODO Loop through isotopes to match spin group to correct isotope
            if fit_config.nuclear_params.isotopes:
                iso = fit_config.nuclear_params.isotopes[0]
                if not hasattr(iso, "spin_groups") or iso.spin_groups is None:
                    iso.spin_groups = []
                for new_sg in spin_groups:
                    # Try to find an existing spin group with the same number
                    found = False
                    for i, existing_sg in enumerate(iso.spin_groups):
                        if existing_sg.spin_group_number == new_sg.spin_group_number:
                            # Update the existing spin group
                            iso.spin_groups[i] = new_sg
                            found = True
                            break
                    
            else:
                logger.warning("No isotopes found in fit_config to attach spin groups")