#!/usr/bin/env python
"""Core physical quantity models with validation."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Annotated

from pleiades.nuclear.isotopes.models import IsotopeInfo, IsotopeMassData
from pleiades.utils.helper import VaryFlag
from pleiades.utils.logger import loguru_logger

NonNegativeFloat = Annotated[float, Field(ge=0)]
PositiveFloat = Annotated[float, Field(gt=0)]

logger = loguru_logger.bind(name=__name__)


class DataRetrievalMethod(str, Enum):
    """Enumeration of methods to retrieve nuclear data."""

    DIRECT = "DIRECT"  # Direct download of complete ENDF files
    API = "API"  # API-based retrieval of specific sections (resonance data only)


class EndfLibrary(str, Enum):
    """Enumeration of ENDF library versions."""

    ENDF_B_VIII_1 = "ENDF-B-VIII.1"
    ENDF_B_VIII_0 = "ENDF-B-VIII.0"
    JEFF_3_3 = "JEFF-3.3"
    JENDL_5 = "JENDL-5"
    CENDL_3_2 = "CENDL-3.2"
    TENDL_2021 = "TENDL-2021"


class EndfFilenamePattern(str, Enum):
    """Filename patterns for different ENDF libraries."""

    MAT_FIRST = "n_{mat}_{z_nozero}-{element}-{a}.zip"  # Format for VIII.0
    ELEMENT_FIRST = "n_{z}-{element}-{a}_{mat}.zip"  # Format for VIII.1 and others


# Mapping of library versions to their filename patterns
LIBRARY_FILENAME_PATTERNS = {
    EndfLibrary.ENDF_B_VIII_0: EndfFilenamePattern.MAT_FIRST,
    EndfLibrary.ENDF_B_VIII_1: EndfFilenamePattern.ELEMENT_FIRST,
    EndfLibrary.JEFF_3_3: EndfFilenamePattern.ELEMENT_FIRST,
    EndfLibrary.JENDL_5: EndfFilenamePattern.ELEMENT_FIRST,
    EndfLibrary.CENDL_3_2: EndfFilenamePattern.ELEMENT_FIRST,
    EndfLibrary.TENDL_2021: EndfFilenamePattern.ELEMENT_FIRST,
}


class ParticlePair(BaseModel):
    """Container for information about a pair of particles used in nuclear calculations.
    Attributes:
        name (str): Name of the particle pair (e.g., 'n+U235' for neutron + Uranium-235).
        name_a (str): Name of particle A (e.g., 'neutron').
        name_b (str): Name of particle B (e.g., 'U-238').
        parity_a (int): Parity of particle A; relevant if spin is zero and parity is negative.
        parity_b (int): Parity of particle B; relevant if spin is zero and parity is negative.
        charge_a (int): Atomic number of particle A (e.g., 0 for neutron).
        charge_b (int): Atomic number of particle B (e.g., 92 for Uranium).
        mass_a (float): Mass of particle A in atomic mass units (default is neutron mass).
        mass_b (float): Mass of particle B in atomic mass units.
        spin_a (float): Spin of particle A (default is 0.5 for neutron).
        spin_b (float): Spin of particle B (default is 0 for Uranium-238).
        calculate_penetrabilities (bool): Whether to calculate penetrabilities for nuclear reactions.
        calculate_shifts (bool): Whether to calculate shifts for nuclear reactions.
        effective_radius (float): Effective radius for channels of this particle pair (in fermi).
        true_radius (float): True radius for channels of this particle pair (in fermi).
    """

    name: str = Field(default="n+", description="Name of the particle pair (e.g., 'n+U235' for neutron)")
    name_a: str = Field(default="neutron", description="Name of particle A (e.g., 'neutron' for neutron)")
    name_b: str = Field(default="UNK-000", description="Name of particle B (e.g., 'U-238' for Uranium-238)")
    parity_a: int = Field(
        default=1,
        description="Parity of particle A; needed only if the spin of particle A is zero and the parity is negative (e.g., 1 for neutron)",
    )
    parity_b: int = Field(
        default=1,
        description="Parity of particle B; needed only if the spin of particle B is zero and the parity is negative (e.g., 1 for Uranium-238)",
    )
    charge_a: int = Field(default=0, description="Atomic number of particle A (e.g., 0 for neutron)")
    charge_b: int = Field(default=0, description="Atomic number of particle B (e.g., 92 for Uranium)")
    mass_a: float = Field(
        default=1.00866491578, description="Mass of particle A in atomic mass units (default is neutron mass)"
    )
    mass_b: float = Field(default=0.0, description="Mass of particle B in atomic mass units (default is 0)")
    spin_a: float = Field(default=0.5, description="Spin of particle A (default is 0.5 for neutron)")
    spin_b: float = Field(default=0.0, description="Spin of particle B (default is 0 for Uranium-238)")
    calculate_penetrabilities: bool = Field(
        default=False, description="Whether to calculate penetrabilities for nuclear reactions"
    )
    calculate_shifts: bool = Field(default=False, description="Whether to calculate shifts for nuclear reactions")
    q_value: Optional[float] = Field(
        default=None, description="Q value for the reaction (optional, can be set to actual Q value)"
    )
    threshold: Optional[float] = Field(
        default=None, description="Threshold energy for the reaction (optional, can be set to actual threshold)"
    )

    def __str__(self):
        """Print the particle pair information in a formatted table."""
        headers = ["Parameter", "Value"]
        rows = [
            ["Name", self.name],
            ["Name A", self.name_a],
            ["Name B", self.name_b],
            ["Parity A", self.parity_a],
            ["Parity B", self.parity_b],
            ["Charge A", self.charge_a],
            ["Charge B", self.charge_b],
            ["Mass A (amu)", self.mass_a],
            ["Mass B (amu)", self.mass_b],
            ["Spin A", self.spin_a],
            ["Spin B", self.spin_b],
            ["Q-Value (MeV)", self.q_value],
            ["Threshold (MeV)", self.threshold],
            ["Calculate Penetrabilities", self.calculate_penetrabilities],
            ["Calculate Shifts", self.calculate_shifts],
        ]
        # Calculate column widths
        col_widths = [
            max(len(str(cell)) for cell in [header] + [row[i] for row in rows]) for i, header in enumerate(headers)
        ]
        # Build table
        lines = []
        header_line = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
        sep_line = " | ".join("-" * col_widths[i] for i in range(len(headers)))
        lines.append(header_line)
        lines.append(sep_line)
        for row in rows:
            lines.append(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))
        return "\n".join(lines)

    # Need to make sure that the q_value and threshold are not both set at the same time
    @model_validator(mode="after")
    def validate_q_or_threshold(self) -> "ParticlePair":
        """Validate that both q_value and threshold are not set at the same time.

        Returns:
            ParticlePair: Self if validation passes

        Raises:
            ValueError: If both q_value and threshold are set
        """
        if self.q_value is not None and self.threshold is not None:
            logger.error("Both q_value and threshold cannot be set at the same time")
            raise ValueError("Both q_value and threshold cannot be set at the same time")
        return self


class SpinGroupChannelInfo(BaseModel):
    """Container for channel information within a given spin group.
       Mainly used in SpinGroups to store information about each channel.

    Attributes:
        channel_number (int): Channel number associated with this spin group
        particle_pair_name (str): Name of the particle pair (e.g., 'n+U235'). Should match ParticlePair.name
        exclude_channel (int): Whether to exclude this channel from calculations (1: exclude, 0: include)
        orbital_angular_momentum (Optional[int]): Orbital angular momentum of the channel (default is None)
        channel_spin (Optional[float]): Spin of the channel (default is None)
        boundary_condition (Optional[str]): Boundary condition for the channel (default is None)
        effective_radius (Optional[float]): Effective radius for the channel (in fermi, default is None)
        true_radius (Optional[float]): True radius for the channel (in fermi, default is None)

    """

    channel_number: int = Field(description="Channel number associated with this spin group")
    particle_pair_name: str = Field(
        description="Name of the particle pair (e.g., 'n+U235'). Should match ParticlePair.name"
    )
    exclude_channel: int = Field(
        description="Whether to exclude this channel from calculations (1: exclude, 0: include)"
    )
    orbital_angular_momentum: Optional[int] = Field(
        default=None, description="Orbital angular momentum of the channel (default is None)"
    )
    channel_spin: Optional[float] = Field(default=None, description="Spin of the channel (default is None)")
    boundary_condition: Optional[str] = Field(
        default=None, description="Boundary condition for the channel (default is None)"
    )
    effective_radius: Optional[float] = Field(
        default=None, description="Effective radius for the channel (in fermi, default is None)"
    )
    true_radius: Optional[float] = Field(
        default=None, description="True radius for the channel (in fermi, default is None)"
    )

    # Define a print method for debugging
    def __str__(self) -> str:
        return (
            f"Channel Number: {self.channel_number}\n"
            f"Particle Pair Name: {self.particle_pair_name}\n"
            f"Exclude Channel: {self.exclude_channel}\n"
            f"Orbital Angular Momentum: {self.orbital_angular_momentum}\n"
            f"Channel Spin: {self.channel_spin}\n"
            f"Boundary Condition: {self.boundary_condition}\n"
            f"Effective Radius: {self.effective_radius}\n"
            f"True Radius: {self.true_radius}\n"
        )


class SpinGroups(BaseModel):
    """Container for all the needed information on a given spin group.

    Attributes:
        spin_group_number (int): Spin group number
        excluded (bool): Whether the spin group is excluded from calculations
        number_of_entry_channels (int): Number of entry channels for this spin group
        number_of_exit_channels (int): Number of exit channels for this spin group
        spin (float): Spin of the spin group (integer or half-integer). Positive of even parity, negative of odd parity.
        Abundance (float): Abundance of the spin group (dimensionless)
        ground_state_spin (float): Ground state spin of the spin group (integer or half-integer)
        channel_info (List[SpinGroupChannelInfo]): List of channel information for the spin group.

    """

    spin_group_number: int = Field(
        default=0, description="Spin group number (positive for even parity, negative for odd parity)"
    )
    excluded: bool = Field(default=False, description="Whether the spin group is excluded from calculations")
    number_of_entry_channels: int = Field(default=0, description="Number of entry channels for this spin group")
    number_of_exit_channels: int = Field(default=0, description="Number of exit channels for this spin group")
    spin: float = Field(default=0.0, description="Spin of the spin group (integer or half-integer)")
    abundance: float = Field(default=0.0, description="Abundance of the spin group (dimensionless)")
    ground_state_spin: float = Field(
        default=0.0, description="Ground state spin of the spin group (integer or half-integer)"
    )
    channel_info: List[SpinGroupChannelInfo] = Field(
        default_factory=list, description="List of channel information for the spin group"
    )

    def __str__(self) -> str:
        headers = [
            "Spin Group",
            "Excluded",
            "Entry Channels",
            "Exit Channels",
            "Spin",
            "Abundance",
            "Ground State Spin",
        ]
        # Define column widths
        col_widths = [10, 8, 14, 13, 6, 9, 17]
        header_fmt = " | ".join(f"{{:<{w}}}" for w in col_widths)
        row_fmt = " | ".join(f"{{:<{w}}}" for w in col_widths)

        table = []
        table.append(header_fmt.format(*headers))
        table.append("=+=".join("=" * w for w in col_widths))

        # Spin group info row
        row = [
            str(self.spin_group_number),
            str(self.excluded),
            str(self.number_of_entry_channels),
            str(self.number_of_exit_channels),
            f"{self.spin:.2f}",
            f"{self.abundance:.2f}",
            f"{self.ground_state_spin:.2f}",
        ]
        table.append(row_fmt.format(*row))

        # Channel info rows
        if self.channel_info:
            channel_headers = ["Channel #", "Pair Name", "Exclude", "L", "Spin", "BC", "R_eff", "R_true"]
            channel_col_widths = [10, 12, 8, 4, 6, 6, 8, 8]
            channel_header_fmt = "    " + " | ".join(f"{{:<{w}}}" for w in channel_col_widths)
            channel_row_fmt = "    " + " | ".join(f"{{:<{w}}}" for w in channel_col_widths)
            table.append(channel_header_fmt.format(*channel_headers))
            table.append("    " + "-+-".join("-" * w for w in channel_col_widths))
            for ch in self.channel_info:
                ch_row = [
                    str(ch.channel_number),
                    str(ch.particle_pair_name),
                    str(ch.exclude_channel),
                    str(ch.orbital_angular_momentum) if ch.orbital_angular_momentum is not None else "",
                    str(ch.channel_spin) if ch.channel_spin is not None else "",
                    str(ch.boundary_condition) if ch.boundary_condition is not None else "",
                    str(ch.effective_radius) if ch.effective_radius is not None else "",
                    str(ch.true_radius) if ch.true_radius is not None else "",
                ]
                table.append(channel_row_fmt.format(*ch_row))

        return "\n".join(table)


class SpinGroupChannels(BaseModel):
    """Container for a spin group and its associated channels.

    This class represents the mapping between a spin group number and the
    list of channels that belong to that group.

    Attributes:
        group_number (int): The spin group number (must be positive)
        channels (List[int]): List of channel numbers for this spin group
    """

    group_number: int = Field(description="Spin group number", gt=0)
    channels: List[int] = Field(description="List of channel numbers for this spin group")

    @field_validator("channels")
    def validate_channels(cls, v: List[int]) -> List[int]:
        """Validate channel numbers.

        Args:
            v: List of channel numbers

        Returns:
            List[int]: Validated channel numbers

        Raises:
            ValueError: If any channel number is invalid
        """
        for channel in v:
            if channel <= 0:
                raise ValueError(f"Channel numbers must be positive, got {channel}")
        return v

    def __str__(self) -> str:
        """Return a string representation of the spin group and channels."""
        channels_str = ", ".join(map(str, self.channels))
        return f"Group= {self.group_number:2d}   Chan= {channels_str}"


class RadiusParameters(BaseModel):
    """Container for nuclear radius parameters of isotopes used in SAMMY calculations.

    This class represents a set of radius parameters that define both the potential
    scattering radius and the radius used for penetrabilities and shift calculations.
    These parameters can be applied globally or to specific spin groups and channels.

    Attributes:
        effective_radius (float):
            The radius (in Fermi) used for potential scattering calculations.

        true_radius (float):
            The radius (in Fermi) used for penetrabilities and shift calculations.
            Special values:
            - If 0: Uses the CRFN value from input file/card set 4
            - If negative: Absolute value represents mass ratio to neutron (AWRI),
              radius calculated as 1.23(AWRI)^1/3 + 0.8 (ENDF formula)

        channel_mode (int):
            Determines how channels are specified:
            - 0: Parameters apply to all channels
            - 1: Parameters apply only to specified channels in channels list

        vary_effective (VaryFlag):
            Flag indicating how effective radius should be treated:
            - NO (0): Parameter is held fixed
            - YES (1): Parameter is varied in fitting
            - PUP (3): Parameter is treated as a propagated uncertainty parameter

        vary_true (VaryFlag):
            Flag indicating how true radius should be treated:
            - USE_FROM_EFFECTIVE (-1): Treated as identical to effective_radius
            - NO (0): Parameter is held fixed
            - YES (1): Parameter is varied independently
            - PUP (3): Parameter is treated as a propagated uncertainty parameter

        spin_groups (List[SpinGroupChannels]):
            List of spin group and channel mappings that use these radius parameters.
            Each entry contains a group number and its associated channels.
            Group numbers > 500 indicate omitted resonances.

        channels (Optional[List[int]]):
            List of channel numbers when channel_mode=1.
            When channel_mode=0, this should be None.

    Note:
        This class supports the three different input formats specified in SAMMY:
        - Default format (card set 7) for <99 spin groups
        - Alternate format for >99 spin groups
        - Keyword-based format
        However, internally it maintains a consistent representation regardless
        of input format.
    """

    effective_radius: Optional[float] = Field(default=None, description="Radius for potential scattering (Fermi)", ge=0)
    true_radius: Optional[float] = Field(default=None, description="Radius for penetrabilities and shifts (Fermi)")
    channel_mode: Optional[int] = Field(
        default=None,
        description="Channel specification mode (0: all channels, 1: specific channels)",
        ge=0,
        le=1,
    )
    vary_effective: Optional[VaryFlag] = Field(default=None, description="Flag for varying effective radius")
    vary_true: Optional[VaryFlag] = Field(default=None, description="Flag for varying true radius")
    spin_groups: Optional[List[SpinGroupChannels]] = Field(
        default=None,
        description="List of spin group and channel mappings",
    )
    channels: Optional[List[int]] = Field(
        default=None, description="List of channel numbers (required when channel_mode=1)"
    )

    @field_validator("spin_groups")
    def validate_spin_groups(cls, v: Optional[List[SpinGroupChannels]]) -> Optional[List[SpinGroupChannels]]:
        """Validate spin groups and their channels.

        Args:
            v: List of SpinGroupChannels objects

        Returns:
            Optional[List[SpinGroupChannels]]: Validated spin groups

        Raises:
            ValueError: If any spin group or channel data is invalid
        """
        if v is None:
            return v

        for spin_group in v:
            # Values > 500 are valid but indicate omitted resonances
            # We allow them but might want to warn the user
            if spin_group.group_number > 500:
                print(f"Warning: Spin group {spin_group.group_number} > 500 indicates omitted resonances")

        return v

    @field_validator("vary_true")
    def validate_vary_true(cls, v: VaryFlag) -> VaryFlag:
        """Validate vary_true flag has valid values.

        For true radius, we allow an additional special value -1 (USE_FROM_PARFILE)

        Args:
            v: Vary flag value

        Returns:
            VaryFlag: Validated flag value

        Raises:
            ValueError: If flag value is invalid
        """
        allowed_values = [
            VaryFlag.USE_FROM_PARFILE,  # -1
            VaryFlag.NO,  # 0
            VaryFlag.YES,  # 1
            VaryFlag.PUP,  # 3
        ]
        if v not in allowed_values:
            raise ValueError(f"vary_true must be one of {allowed_values}, got {v}")
        return v

    @model_validator(mode="after")
    def validate_channels(self) -> "RadiusParameters":
        """Validate channel specifications.

        Ensures that:
        1. If channel_mode=1, channels must be provided
        2. If channel_mode=0, channels should be None

        Returns:
            RadiusParameters: Self if validation passes

        Raises:
            ValueError: If channel specifications are invalid
        """
        if self.channel_mode == 1 and not self.channels:
            raise ValueError("When channel_mode=1, channels must be provided")
        if self.channel_mode == 0 and self.channels is not None:
            raise ValueError("When channel_mode=0, channels must be None")
        return self

    @model_validator(mode="after")
    def validate_true_radius_consistency(self) -> "RadiusParameters":
        """Validate consistency between true_radius and vary_true.

        Ensures that:
        1. If vary_true is USE_FROM_PARFILE, true_radius matches effective_radius
        2. If true_radius is 0, vary_true cannot be USE_FROM_PARFILE
        3. If true_radius is negative, it represents AWRI and vary_true cannot be USE_FROM_PARFILE

        Returns:
            RadiusParameters: Self if validation passes

        Raises:
            ValueError: If radius specifications are inconsistent
        """
        if self.vary_true == VaryFlag.USE_FROM_PARFILE:
            if self.true_radius != self.effective_radius:
                logger.error(f"True radius {self.true_radius} does not match effective radius {self.effective_radius}")
                raise ValueError("When vary_true is USE_FROM_PARFILE (-1), true_radius must match effective_radius")

        # Special cases for true_radius
        if self.true_radius is not None:
            if self.true_radius == 0:
                if self.vary_true == VaryFlag.USE_FROM_PARFILE:
                    logger.error("When true_radius=0 (use CRFN value), vary_true cannot be USE_FROM_PARFILE (-1)")
                    raise ValueError("When true_radius=0 (use CRFN value), vary_true cannot be USE_FROM_PARFILE (-1)")

            if self.true_radius < 0:
                if self.vary_true == VaryFlag.USE_FROM_PARFILE:
                    logger.error(
                        "When true_radius is negative (AWRI specification), vary_true cannot be USE_FROM_PARFILE (-1)"
                    )
                    raise ValueError(
                        "When true_radius is negative (AWRI specification), vary_true cannot be USE_FROM_PARFILE (-1)"
                    )

        return self

    # Define a print method for debugging
    def __str__(self) -> str:
        """Return a text table representation of the RadiusParameters object with aligned columns."""
        headers = ["Parameter", "Value"]
        rows = [
            ["Effective Radius (F)", self.effective_radius],
            ["True Radius (F)", self.true_radius],
            ["Channel Mode", self.channel_mode],
            ["Vary Effective", self.vary_effective],
            ["Vary True", self.vary_true],
            ["Spin Groups", self.spin_groups],
            ["Channels", self.channels],
        ]
        col_widths = [
            max(len(str(cell)) for cell in [header] + [row[i] for row in rows]) for i, header in enumerate(headers)
        ]
        lines = []
        header_line = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
        sep_line = " | ".join("-" * col_widths[i] for i in range(len(headers)))
        lines.append(header_line)
        lines.append(sep_line)
        for row in rows:
            lines.append(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))
        return "\n".join(lines)


class ResonanceEntry(BaseModel):
    """This class handles the parameters for a single resonance entry.

    Attributes:
        resonance_energy: Resonance energy Eλ (eV)
        capture_width: Capture width Γγ (milli-eV)

        channel1_width: Particle width for channel 1 (milli-eV)
        channel2_width: Particle width for channel 2 (milli-eV)
        channel3_width: Particle width for channel 3 (milli-eV)
        NOTE:   If any particle width Γ is negative, SAMMY uses abs(Γ)
                for the width and set the associated amplitude γ to be negative.

        vary_energy:    Flag indicating if resonance energy is varied
        vary_capture_width: Flag indicating if capture width is varied
        vary_channel1: Flag indicating if channel 1 width is varied
        vary_channel2: Flag indicating if channel 2 width is varied
        vary_channel3: Flag indicating if channel 3 width is varied
        NOTE:   0 = no, 1 = yes, 3 = PUP (PUP = Partially Unknown Parameter)

        igroup: Quantum numbers group number (or spin_groups)
        NOTE:   If IGROUP is negative or greater than 50, this resonance will be
                omitted from the calculation.

        x_value: Special value used to detect multi-line entries (unsupported)

    """

    resonance_energy: float = Field(description="Resonance energy Eλ (eV)")
    capture_width: float = Field(description="Capture width Γγ (milli-eV)")
    channel1_width: Optional[float] = Field(None, description="Particle width for channel 1 (milli-eV)")
    channel2_width: Optional[float] = Field(None, description="Particle width for channel 2 (milli-eV)")
    channel3_width: Optional[float] = Field(None, description="Particle width for channel 3 (milli-eV)")
    vary_energy: VaryFlag = Field(default=VaryFlag.NO)
    vary_capture_width: VaryFlag = Field(default=VaryFlag.NO)
    vary_channel1: VaryFlag = Field(default=VaryFlag.NO)
    vary_channel2: VaryFlag = Field(default=VaryFlag.NO)
    vary_channel3: VaryFlag = Field(default=VaryFlag.NO)
    igroup: int = Field(description="Quantum numbers group number")

    # Define print method for debugging
    def __str__(self) -> str:
        # Print as a horizontal table (one row, no headers), aligned columns
        def flag_to_str(flag):
            # Print 'yes' for VaryFlag.YES, 'no' otherwise
            try:
                return "yes" if str(flag).endswith("YES") else "no"
            except Exception:
                return str(flag)

        values = [
            self.resonance_energy,
            self.capture_width,
            self.channel1_width,
            self.channel2_width,
            self.channel3_width,
            flag_to_str(self.vary_energy),
            flag_to_str(self.vary_capture_width),
            flag_to_str(self.vary_channel1),
            flag_to_str(self.vary_channel2),
            flag_to_str(self.vary_channel3),
            self.igroup,
        ]
        # Define column widths for alignment (wider for large numbers and flags)
        col_widths = [12, 12, 14, 8, 8, 4, 4, 4, 4, 4, 3]
        formatted = []
        for v, w in zip(values, col_widths):
            if isinstance(v, float):
                formatted.append(f"{v:>{w}.4f}" if v is not None else f"{'None':>{w}}")
            else:
                formatted.append(f"{str(v):>{w}}")
        return "|".join(formatted)


class IsotopeParameters(BaseModel):
    """Container for a single isotope's parameters which include.
        mass,
        abundance, uncertainty, treatment flag, and associated
    spin groups.

    Attributes:
        IsotopeInformation (Optional[IsotopeInfo]): Information about the isotope
        abundance (float): Fractional abundance (dimensionless)
        uncertainty (Optional[float]): Uncertainty on abundance (dimensionless)
        flag (VaryFlag): Treatment flag for abundance (-2=use input, 0=fixed, 1=vary, 3=PUP)
        spin_groups (List[int]): List of spin group numbers (negative values indicate omitted resonances)
        resonances (List[ResonanceEntry]): List of resonance entries
        radius_parameters (List[RadiusParameters]): List of radius parameters

    """

    particle_pairs: Optional[List[ParticlePair]] = Field(
        default_factory=list, description="List of reaction channel particle pairs (e.g. n+U235 or fission+fission)"
    )
    isotope_information: Optional[IsotopeInfo] = Field(default=None, description="Isotope information")
    abundance: Optional[float] = Field(default=None, description="Fractional abundance")
    uncertainty: Optional[float] = Field(default=None, description="Uncertainty on abundance")
    vary_abundance: Optional[VaryFlag] = Field(default=None, description="Treatment flag for varying abundance")
    endf_library: Optional[EndfLibrary] = Field(
        default=EndfLibrary.ENDF_B_VIII_0, description="ENDF library associated with the isotope"
    )
    spin_groups: Optional[List[SpinGroups]] = Field(default_factory=list, description="List of spin group objects")
    resonances: Optional[List[ResonanceEntry]] = Field(default_factory=list, description="List of resonance entries")
    radius_parameters: Optional[List[RadiusParameters]] = Field(
        default_factory=list, description="List of radius parameters"
    )

    @model_validator(mode="after")
    def validate_groups(self) -> "IsotopeParameters":
        """Validate spin group constraints.

        Validates:
        - Group numbers are non-zero
        - Negative groups only used to indicate omitted resonances
        - Group numbers are within valid range for format

        Returns:
            IsotopeParameters: Self if validation passes

        Raises:
            ValueError: If spin group validation fails
        """
        max_standard = 99  # Maximum group number for standard format

        for group in self.spin_groups:
            if group.spin_group_number == 0:
                logger.error("Spin group number cannot be 0")
                raise ValueError("Spin group number cannot be 0")

            # Check if we need extended format
            if abs(group.spin_group_number) > max_standard:
                logger.error(f"Group number {group.spin_group_number} requires extended format")

        return self

    @model_validator(mode="after")
    def validate_resonances(self) -> "IsotopeParameters":
        """Validate that resonance igroups match spin groups.

        Validates:
        - Each resonance igroup is in the list of spin groups

        Returns:
            IsotopeParameters: Self if validation passes

        Raises:
            ValueError: If resonance igroup validation fails
        """
        # Extract spin group numbers from SpinGroups objects
        spin_group_numbers = [group.spin_group_number for group in self.spin_groups]

        for resonance in self.resonances:
            if resonance.igroup not in spin_group_numbers:
                logger.error(f"Resonance igroup {resonance.igroup} not in spin groups {spin_group_numbers}")
                raise ValueError(f"Resonance igroup {resonance.igroup} not in spin groups {spin_group_numbers}")

        return self

    @model_validator(mode="after")
    def validate_radius_parameters(self) -> "IsotopeParameters":
        """Validate that radius parameter spin groups match isotope spin groups.

        Validates:
        - Each spin group in radius parameters is in the list of isotope spin groups

        Returns:
            IsotopeParameters: Self if validation passes

        Raises:
            ValueError: If radius parameter spin group validation fails
        """
        # Extract spin group numbers from SpinGroups objects
        isotope_spin_group_numbers = [group.spin_group_number for group in self.spin_groups]

        for radius in self.radius_parameters:
            if radius.spin_groups:  # Check if spin_groups is not None
                for spin_group_channel in radius.spin_groups:
                    if spin_group_channel.group_number not in isotope_spin_group_numbers:
                        logger.error(
                            f"Radius parameter spin group {spin_group_channel.group_number} not in isotope spin groups {isotope_spin_group_numbers}"
                        )
                        raise ValueError(
                            f"Radius parameter spin group {spin_group_channel.group_number} not in isotope spin groups {isotope_spin_group_numbers}"
                        )

        return self

    def print_resonances(self) -> str:
        """Print the resonance entries in a formatted table."""
        headers = ["Resonance Energy (eV)", "Capture Width (meV)", "Channel 1 Width (meV)", "Igroup"]
        rows = [
            [
                resonance.resonance_energy,
                resonance.capture_width,
                resonance.channel1_width,
                resonance.igroup,
            ]
            for resonance in self.resonances
        ]
        # Calculate column widths
        col_widths = [
            max(len(str(cell)) for cell in [header] + [row[i] for row in rows]) for i, header in enumerate(headers)
        ]
        # Build table
        lines = []
        header_line = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
        sep_line = " | ".join("-" * col_widths[i] for i in range(len(headers)))
        lines.append(header_line)
        lines.append(sep_line)
        for row in rows:
            lines.append(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))
        return "\n".join(lines)

    def append_particle_pair(self, particle_pair: ParticlePair):
        """Append a particle pair to the list of particle pairs, if no particle pairs exist then create a new list.
        This method is used to add a new particle pair to the isotope parameters.

        Args:
            particle_pair (ParticlePair): The particle pair to append
        """
        if not self.particle_pairs:
            self.particle_pairs = []
        self.particle_pairs.append(particle_pair)
        logger.info(f"Particle pair {particle_pair.name} appended to isotope {self.isotope_information.name}")

    def append_spin_group(self, spin_group: SpinGroups):
        """Append a spin group to the list of spin groups, if no spin groups exist then create a new list.
        This method is used to add a new spin group to the isotope parameters.

        Args:
            spin_group (SpinGroups): The spin group to append
        """
        if not self.spin_groups:
            self.spin_groups = []
        self.spin_groups.append(spin_group)
        logger.info(f"Spin group {spin_group.spin_group_number} appended to isotope {self.isotope_information.name}")

    def __str__(self) -> str:
        """
        Return a text table representation of the IsotopeParameters object.
        """
        headers = ["Parameter", "Value"]
        rows = [
            ["Isotope Name", self.isotope_information.name],
            ["Mass (amu)", self.isotope_information.mass_data.atomic_mass],
            ["Spin", self.isotope_information.spin],
            ["Abundance", self.abundance],
            ["Uncertainty", self.uncertainty],
            ["Vary Abundance", self.vary_abundance],
            ["ENDF Library", self.endf_library],
            ["Num of Spin Groups", len(self.spin_groups)],
            ["Num of Particle Pairs", len(self.particle_pairs)],
            ["Num of Resonances", len(self.resonances)],
            ["Num of Radius Parameters", len(self.radius_parameters)],
        ]
        # Calculate column widths
        col_widths = [
            max(len(str(cell)) for cell in [header] + [row[i] for row in rows]) for i, header in enumerate(headers)
        ]
        # Build table
        lines = []
        header_line = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
        sep_line = "-" * (col_widths[0]) + "-+-" + "-" * (col_widths[1])
        lines.append(header_line)
        lines.append(sep_line)
        for row in rows:
            lines.append(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))
        return "\n".join(lines)


class nuclearParameters(BaseModel):
    """Container for nuclear parameters used in SAMMY calculations.

    Attributes:
        particle (IsotopeInfo): Incoming particle information (default is a neutron)
        isotopes (List[IsotopeParameters]): List of isotope parameters

    """

    particle: IsotopeInfo = Field(
        default=IsotopeInfo(
            name="n", atomic_number=1, mass_data=IsotopeMassData(atomic_mass=1.00866491578), spin=0.5, mass_number=1
        ),
        description="Default particle information (neutron)",
    )
    isotopes: List[IsotopeParameters] = Field(default_factory=list, description="List of isotope parameters")

    @model_validator(mode="after")
    def validate_isotopes(self) -> "nuclearParameters":
        """Validate isotope parameters.

        Validates:
        - Each isotope has a unique mass
        - Each isotope has a unique abundance
        """

        # Check for duplicate isotope names in isotopeInfo
        names = [iso.isotope_information.name for iso in self.isotopes]

        if len(names) != len(set(names)):
            logger.error("Duplicate isotope names found")
            raise ValueError("Duplicate isotope names found")

        # Check for duplicate masses
        masses = [iso.isotope_information.mass_data.atomic_mass for iso in self.isotopes]
        if len(masses) != len(set(masses)):
            logger.error("Duplicate masses found")
            raise ValueError("Duplicate masses found")

        return self

    def append_isotope(self, isotope: IsotopeParameters):
        """Append an isotope to the list of isotopes.

        Args:
            isotope (IsotopeParameters): The isotope to append
        """
        self.isotopes.append(isotope)
        logger.info(f"Isotope {isotope.isotope_information.name} appended to nuclear parameters")


# example usage
if __name__ == "__main__":
    # Example usage of RadiusParameters
    radius_params = RadiusParameters(
        effective_radius=1.0,
        true_radius=1.0,
        channel_mode=0,
        vary_effective=VaryFlag.YES,
        vary_true=VaryFlag.YES,
        spin_groups=[1, 2, 3],
    )

    # Example usage of ResonanceEntry
    resonance_entry = ResonanceEntry(
        resonance_energy=1.0,
        capture_width=1.0,
        channel1_width=1.0,
        channel2_width=1.0,
        channel3_width=1.0,
        vary_energy=VaryFlag.YES,
        vary_capture_width=VaryFlag.YES,
        vary_channel1=VaryFlag.YES,
        vary_channel2=VaryFlag.YES,
        vary_channel3=VaryFlag.YES,
        igroup=1,
    )

    # Example usage of IsotopeParameters
    isotope_params = IsotopeParameters(
        isotope_name="U-238",
        mass=238.0,
        abundance=0.992745,
        uncertainty=0.001,
        flag=VaryFlag.YES,
        spin_groups=[1, 2, 3],
        resonances=[resonance_entry],
        radius_parameters=[radius_params],
    )

    # Example usage of nuclearParameters
    nuclear_params = nuclearParameters(
        isotopes=[isotope_params],
    )

    print(nuclear_params)
