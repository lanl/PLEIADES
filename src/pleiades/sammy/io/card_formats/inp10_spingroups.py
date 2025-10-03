#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
from pleiades.nuclear.models import IsotopeParameters, SpinGroupChannelInfo, SpinGroups
from pleiades.sammy.fitting.config import FitConfig
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

        # SPIN_GROUP: first 3 are digits, 4th is blank, 5th is blank or X
        if len(s) >= 5 and s[0:3].strip().isdigit() and s[3] == " " and (s[4] == " " or s[4].upper() == "X"):
            return "SPIN_GROUP"
        # CHANNEL: first 2 blank, next 3 digits, next 2 blank
        if len(s) >= 7 and s[0:2] == "  " and s[2:5].strip().isdigit() and s[5:7] == "  ":
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
                logger.warning(f"Line {idx} does not match expected format: {line.strip()}")
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
                        excluded = 0
                    number_of_entry_channels = int(line[7:10].strip())
                    number_of_exit_channels = int(line[12:15].strip())
                    spin = float(line[15:20].strip())
                    abundance = float(line[20:30].strip())

                except Exception as e:
                    logger.error(
                        f"Failed to parse spin group line: |{line}| ("
                        f"spin_group_number='{line[0:3].strip()}', "
                        f"excluded='{line[4:5].strip()}', "
                        f"number_of_entry_channels='{line[7:10].strip()}', "
                        f"number_of_exit_channels='{line[12:15].strip()}', "
                        f"spin='{line[15:20].strip()}', "
                        f"abundance='{line[20:30].strip()}') ({e})"
                    )
                    raise ValueError(f"Failed to parse spin group line: {line.strip()} ({e})")

                # Parse all channel info lines for this spin group
                channel_info_list = []
                idx += 1

                while idx < len(lines):
                    ch_line = lines[idx]

                    line_type = cls.get_line_type(ch_line)

                    if line_type != "CHANNEL":
                        break

                    try:
                        channel_number = int(ch_line[2:5].strip()) if ch_line[2:5].strip() != "" else None
                        particle_pair_name = ch_line[7:15].strip() if ch_line[7:15].strip() != "" else "IDK"
                        if ch_line[17:18].strip().upper() == "X":
                            exclude_channel = 1
                        elif ch_line[17:18].strip() == "":
                            exclude_channel = 0
                        else:
                            exclude_channel = 0
                        orbital_angular_momentum = (
                            int(ch_line[18:20].strip()) if ch_line[18:20].strip().isdigit() else None
                        )
                        channel_spin = float(ch_line[20:30].strip()) if ch_line[20:30].strip() != "" else None
                        boundary_condition = float(ch_line[30:40].strip()) if ch_line[30:40].strip() != "" else None
                        effective_radius = float(ch_line[40:50].strip()) if ch_line[40:50].strip() != "" else None
                        true_radius = float(ch_line[50:60].strip()) if ch_line[50:60].strip() != "" else None

                    except Exception as e:
                        logger.error(f"Failed to parse channel line: {ch_line.strip()} ({e})")
                        raise ValueError(f"Failed to parse channel line: {ch_line.strip()} ({e})")

                    channel_info_list.append(
                        SpinGroupChannelInfo(
                            channel_number=channel_number,
                            particle_pair_name=particle_pair_name,
                            exclude_channel=exclude_channel,
                            channel_spin=channel_spin,
                            orbital_angular_momentum=orbital_angular_momentum,
                            boundary_condition=boundary_condition,
                            effective_radius=effective_radius,
                            true_radius=true_radius,
                        )
                    )

                    # move to the next channel line
                    idx += 1

                spin_group = SpinGroups(
                    spin_group_number=spin_group_number,
                    excluded=excluded,
                    number_of_entry_channels=number_of_entry_channels,
                    number_of_exit_channels=number_of_exit_channels,
                    spin=spin,
                    abundance=abundance,
                    channel_info=channel_info_list,
                )

            # if isotopes exist, loop through the isotopes, then the existing spin groups to find a match
            if fit_config.nuclear_params.isotopes:
                isotope_spin_group_match = False

                for isotope in fit_config.nuclear_params.isotopes:
                    if not hasattr(isotope, "spin_groups") or isotope.spin_groups is None:
                        isotope.spin_groups = []

                    # Check if the spin group already exists
                    for existing_sg in isotope.spin_groups:
                        if existing_sg.spin_group_number == spin_group.spin_group_number:
                            # Update the existing spin group
                            existing_sg.excluded = spin_group.excluded
                            existing_sg.number_of_entry_channels = spin_group.number_of_entry_channels
                            existing_sg.number_of_exit_channels = spin_group.number_of_exit_channels
                            existing_sg.spin = spin_group.spin
                            existing_sg.abundance = spin_group.abundance
                            existing_sg.channel_info.extend(spin_group.channel_info)
                            isotope_spin_group_match = True
                            break

                    # found matching spin group so break out of isotope for loop
                    if isotope_spin_group_match:
                        break

                    # If no matching spin group is found, create a new one
                    if not isotope_spin_group_match:
                        isotope.spin_groups.append(spin_group)
                        logger.warning(
                            f"Attaching spin group {spin_group.spin_group_number} to isotope {isotope.isotope_information.name}"
                        )

            else:
                logger.warning("No isotopes found in fit_config to attach spin groups. Creating UNKN isotope")

                fit_config.nuclear_params.isotopes.append(
                    IsotopeParameters(
                        isotope_information=IsotopeInfo(
                            name="UNKN",
                            mass_data=IsotopeMassData(atomic_mass=0),
                        )
                    )
                )
                logger.warning(
                    f"Attaching spin group {spin_group.spin_group_number} to isotope {fit_config.nuclear_params.isotopes[0].isotope_information.name}"
                )
                fit_config.nuclear_params.isotopes[0].append_spin_group(spin_group)

    @classmethod
    def to_lines(cls, fit_config: FitConfig) -> List[str]:
        # create header line
        lines = ["SPIN GROUPS"]

        # if fit_config is none or not an instance of FitConfig, raise an error
        if fit_config is None or not isinstance(fit_config, FitConfig):
            message = "fit_config must be an instance of FitConfig"
            logger.error(message)
            raise ValueError(message)

        # if no isotopes are present, return empty lines
        if not fit_config.nuclear_params.isotopes:
            logger.warning("No isotopes found in fit_config, returning empty lines")
            return lines

        # Iterate over isotopes and their spin groups
        for isotope in fit_config.nuclear_params.isotopes:
            for spin_group in isotope.spin_groups:
                line = f"{spin_group.spin_group_number:3d} {'X' if spin_group.excluded else ' '}"
                line += f"{spin_group.number_of_entry_channels:3d} {spin_group.number_of_exit_channels:3d} "
                line += f"{spin_group.spin:5.2f} {spin_group.abundance:10.4f}"
                lines.append(line)
                for channel in spin_group.channel_info:
                    channel_line = f"  {channel.channel_number:3d} {channel.particle_pair_name:<8} "
                    channel_line += "X" if channel.exclude_channel else " "
                    channel_line += (
                        f"{channel.orbital_angular_momentum:2d} "
                        if channel.orbital_angular_momentum is not None
                        else "   "
                    )
                    channel_line += f"{channel.channel_spin:5.2f} " if channel.channel_spin is not None else "      "
                    channel_line += (
                        f"{channel.boundary_condition:10.4f} " if channel.boundary_condition is not None else " " * 11
                    )
                    channel_line += (
                        f"{channel.effective_radius:10.4f} " if channel.effective_radius is not None else " " * 11
                    )
                    channel_line += f"{channel.true_radius:10.4f}" if channel.true_radius is not None else " " * 10
                    lines.append(channel_line)

        lines.append("")
        return lines
