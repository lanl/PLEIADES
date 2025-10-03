#!/usr/bin/env python
"""Oak Ridge Resolution Function parameters (Card Set 9)."""

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, model_validator

from pleiades.utils.helper import VaryFlag, format_float, format_vary, safe_parse

# Constants for header identifiers
CARD_9_HEADER = "ORRES"


class ModeratorType(Enum):
    """Type of moderator used"""

    WATER = "WATER"
    TANTALUM = "TANTA"


class DetectorType(Enum):
    """Type of detector used"""

    LITHIUM = "LITHI"
    NE110 = "NE110"


# Format definitions for fixed-width fields
FORMAT_BURST = {
    "burst": slice(10, 20),  # Burst width value
    "flag_burst": slice(6, 7),  # Flag to vary burst
    "d_burst": slice(20, 30),  # Uncertainty on burst
}

FORMAT_WATER = {
    "flag_watr0": slice(6, 7),  # Flag for WATR0
    "flag_watr1": slice(7, 8),  # Flag for WATR1
    "flag_watr2": slice(8, 9),  # Flag for WATR2
    "dof": slice(9, 10),  # Degrees of freedom
    "watr0": slice(10, 20),  # Constant term
    "watr1": slice(20, 30),  # Linear term
    "watr2": slice(30, 40),  # Quadratic term
    "d_watr0": slice(10, 20),  # Uncertainty on WATR0
    "d_watr1": slice(20, 30),  # Uncertainty on WATR1
    "d_watr2": slice(30, 40),  # Uncertainty on WATR2
}

FORMAT_TANTA = {
    # First line
    "flag_tanta": slice(6, 7),  # Flag for TANTA
    "tanta": slice(10, 20),  # Main parameter
    "d_tanta": slice(20, 30),  # Uncertainty on TANTA
    # Second line
    "flag_x1": slice(6, 7),  # Flag for X1
    "flag_x2": slice(7, 8),  # Flag for X2
    "flag_x3": slice(8, 9),  # Flag for X3
    "flag_x0": slice(9, 10),  # Flag for X0
    "x1": slice(10, 20),  # x'1 parameter
    "x2": slice(20, 30),  # x'2 parameter
    "x3": slice(30, 40),  # x'3 parameter
    "x0": slice(40, 50),  # x'0 parameter
    # Third line - uncertainties
    "d_x1": slice(10, 20),  # Uncertainty on X1
    "d_x2": slice(20, 30),  # Uncertainty on X2
    "d_x3": slice(30, 40),  # Uncertainty on X3
    "d_x0": slice(40, 50),  # Uncertainty on X0
    # Fourth line - beta/alpha
    "flag_beta": slice(6, 7),  # Flag for beta
    "flag_alpha": slice(7, 8),  # Flag for alpha
    "beta": slice(10, 20),  # Beta parameter
    "alpha": slice(20, 30),  # Alpha parameter
    # Fifth line - uncertainties
    "d_beta": slice(10, 20),  # Uncertainty on beta
    "d_alpha": slice(20, 30),  # Uncertainty on alpha
}

FORMAT_LITHI = {
    "flag_d": slice(6, 7),  # Flag for d
    "flag_f": slice(7, 8),  # Flag for f
    "flag_g": slice(8, 9),  # Flag for g
    "d": slice(10, 20),  # d parameter
    "f": slice(20, 30),  # f parameter
    "g": slice(30, 40),  # g parameter
    "d_d": slice(10, 20),  # Uncertainty on d
    "d_f": slice(20, 30),  # Uncertainty on f
    "d_g": slice(30, 40),  # Uncertainty on g
}

FORMAT_NE110 = {
    "flag_delta": slice(6, 7),  # Flag for delta
    "num_points": slice(7, 10),  # Number of E/sigma points
    "delta": slice(10, 20),  # Delta parameter
    "d_delta": slice(20, 30),  # Uncertainty on delta
    "density": slice(30, 40),  # Density parameter
    # Format for E/sigma points
    "energy": slice(10, 20),  # Energy value
    "sigma": slice(20, 30),  # Cross section value
}

FORMAT_CHANNEL = {
    "flag_chann": slice(6, 7),  # Flag for channel width
    "ecrnch": slice(10, 20),  # Maximum energy
    "chann": slice(20, 30),  # Channel width
    "d_chann": slice(30, 40),  # Uncertainty on width
}


# Individual parameter models for each section
class BurstParameters(BaseModel):
    """Burst width parameters.

    This models the BURST section of ORRES card that specifies:
    - Burst width in nanoseconds
    - Flag indicating whether to vary/PUP the parameter
    - Optional uncertainty on the burst width
    """

    burst: float = Field(description="Full width at half max of burst (ns)")
    flag_burst: VaryFlag = Field(default=VaryFlag.NO, description="Flag to vary burst width")
    d_burst: Optional[float] = Field(None, description="Uncertainty on burst width (ns)")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "BurstParameters":
        """Parse burst parameters from input lines.

        Args:
            lines: List of lines containing burst parameters

        Returns:
            BurstParameters object

        Raises:
            ValueError: If required data missing or invalid format
        """
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        # Parse main line
        line = f"{lines[0]:<30}"  # Pad to minimum width

        params = {}

        # Parse burst width
        burst = safe_parse(line[FORMAT_BURST["burst"]])
        if burst is not None:
            params["burst"] = burst

        # Parse vary flag
        flag_val = line[FORMAT_BURST["flag_burst"]].strip() or "0"
        try:
            params["flag_burst"] = VaryFlag(int(flag_val))
        except (ValueError, TypeError):
            params["flag_burst"] = VaryFlag.NO

        # Parse uncertainty if present
        d_burst = safe_parse(line[FORMAT_BURST["d_burst"]])
        if d_burst is not None:
            params["d_burst"] = d_burst

        return cls(**params)

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines.

        Returns:
            List containing the formatted parameter line
        """
        # Format main parameters using helper functions
        parts = [
            "BURST".ljust(5),  # Section identifier
            " ",  # Spacing
            format_vary(self.flag_burst),
            "   ",  # Additional spacing
            format_float(self.burst, width=10),
            format_float(self.d_burst, width=10) if self.d_burst is not None else "",
        ]

        return ["".join(parts)]


class WaterParameters(BaseModel):
    """Water moderator parameters for the ORRES card.

    Contains parameters for mean free path coefficients:
    - Constant term (WATR0)
    - Linear term (WATR1)
    - Quadratic term (WATR2)
    - Degrees of freedom for chi-squared distribution
    - Vary flags and uncertainties for each parameter
    """

    watr0: float = Field(default=3.614, description="Constant term in mean free path expression (mm)")
    watr1: float = Field(default=-0.089, description="Linear term in mean free path expression (mm)")
    watr2: float = Field(default=0.037, description="Quadratic term in mean free path expression (mm)")
    dof: int = Field(default=4, description="Degrees of freedom for chi-squared distribution", ge=1)

    flag_watr0: VaryFlag = Field(default=VaryFlag.NO)
    flag_watr1: VaryFlag = Field(default=VaryFlag.NO)
    flag_watr2: VaryFlag = Field(default=VaryFlag.NO)

    d_watr0: Optional[float] = Field(None, description="Uncertainty on WATR0")
    d_watr1: Optional[float] = Field(None, description="Uncertainty on WATR1")
    d_watr2: Optional[float] = Field(None, description="Uncertainty on WATR2")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "WaterParameters":
        """Parse water moderator parameters from input lines."""
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<40}"  # Main parameters line
        params = {}

        # Parse main parameters
        for param in ["watr0", "watr1", "watr2"]:
            value = safe_parse(line[FORMAT_WATER[param]])
            if value is not None:
                params[param] = value

        # Parse flags
        for flag in ["flag_watr0", "flag_watr1", "flag_watr2"]:
            value = line[FORMAT_WATER[flag]].strip() or "0"
            try:
                params[flag] = VaryFlag(int(value))
            except (ValueError, TypeError):
                params[flag] = VaryFlag.NO

        # Parse degrees of freedom
        dof = safe_parse(line[FORMAT_WATER["dof"]], as_int=True)
        if dof is not None and dof > 0:
            params["dof"] = dof

        # Parse uncertainties if present
        if len(lines) > 1 and lines[1].strip():
            unc_line = f"{lines[1]:<40}"

            for param in ["d_watr0", "d_watr1", "d_watr2"]:
                value = safe_parse(unc_line[FORMAT_WATER[param]])
                if value is not None:
                    params[param] = value

        return cls(**params)

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines."""
        lines = []

        # Main parameters line
        main_parts = [
            "WATER".ljust(5),
            " ",
            format_vary(self.flag_watr0),
            format_vary(self.flag_watr1),
            format_vary(self.flag_watr2),
            str(self.dof),
            format_float(self.watr0, width=10),
            format_float(self.watr1, width=10),
            format_float(self.watr2, width=10),
        ]
        lines.append("".join(main_parts))

        # Add uncertainties line if any uncertainties present
        if any(getattr(self, f"d_{param}") is not None for param in ["watr0", "watr1", "watr2"]):
            unc_parts = [
                format_float(getattr(self, f"d_{param}", 0.0), width=10) for param in ["watr0", "watr1", "watr2"]
            ]
            # pad the first 10 characters
            unc_parts = [" " * 10] + unc_parts
            lines.append("".join(unc_parts))

        return lines


class TantalumParameters(BaseModel):
    """Tantalum target parameters for ORRES card."""

    # Main parameter
    tanta: float = Field(description="η' parameter (mm⁻¹)")
    flag_tanta: VaryFlag = Field(default=VaryFlag.NO)
    d_tanta: Optional[float] = Field(None, description="Uncertainty on TANTA")

    # Position parameters
    x0: float = Field(description="x'₀ parameter (mm)")
    x1: float = Field(description="x'₁ parameter (mm)")
    x2: float = Field(description="x'₂ parameter (mm)")
    x3: float = Field(description="x'₃ parameter (mm)")

    flag_x0: VaryFlag = Field(default=VaryFlag.NO)
    flag_x1: VaryFlag = Field(default=VaryFlag.NO)
    flag_x2: VaryFlag = Field(default=VaryFlag.NO)
    flag_x3: VaryFlag = Field(default=VaryFlag.NO)

    d_x0: Optional[float] = Field(None)
    d_x1: Optional[float] = Field(None)
    d_x2: Optional[float] = Field(None)
    d_x3: Optional[float] = Field(None)

    # Shape parameters
    beta: float = Field(description="β' parameter (mm⁻¹)")
    alpha: float = Field(description="α' parameter (dimensionless)")

    flag_beta: VaryFlag = Field(default=VaryFlag.NO)
    flag_alpha: VaryFlag = Field(default=VaryFlag.NO)

    d_beta: Optional[float] = Field(None)
    d_alpha: Optional[float] = Field(None)

    @classmethod
    def from_lines(cls, lines: List[str]) -> "TantalumParameters":
        """Parse parameters from input lines."""
        if len(lines) < 3:
            raise ValueError("Insufficient lines - require main params, position params, and shape params")

        params = {}

        # First line - main parameter
        line1 = f"{lines[0]:<30}"
        params["tanta"] = safe_parse(line1[FORMAT_TANTA["tanta"]])
        params["flag_tanta"] = VaryFlag(int(line1[FORMAT_TANTA["flag_tanta"]].strip() or "0"))
        if d_tanta := safe_parse(line1[FORMAT_TANTA["d_tanta"]]):
            params["d_tanta"] = d_tanta

        # Second line - position parameters
        line2 = f"{lines[1]:<50}"
        for x in ["x0", "x1", "x2", "x3"]:
            params[x] = safe_parse(line2[FORMAT_TANTA[x]])
            flag_val = line2[FORMAT_TANTA[f"flag_{x}"]].strip() or "0"
            params[f"flag_{x}"] = VaryFlag(int(flag_val))

        # Third line - optional position uncertainties
        if len(lines) > 2 and not lines[2].strip().startswith(" " * 6):
            line3 = f"{lines[2]:<50}"
            for x in ["x0", "x1", "x2", "x3"]:
                if d_x := safe_parse(line3[FORMAT_TANTA[f"d_{x}"]]):
                    params[f"d_{x}"] = d_x

        # Shape parameters - required
        shape_line_idx = 2 if len(lines) == 3 or lines[2].strip().startswith(" " * 6) else 3
        if shape_line_idx >= len(lines):
            raise ValueError("Missing required shape parameters line")

        line4 = f"{lines[shape_line_idx]:<30}"
        params["beta"] = safe_parse(line4[FORMAT_TANTA["beta"]])
        params["alpha"] = safe_parse(line4[FORMAT_TANTA["alpha"]])
        params["flag_beta"] = VaryFlag(int(line4[FORMAT_TANTA["flag_beta"]].strip() or "0"))
        params["flag_alpha"] = VaryFlag(int(line4[FORMAT_TANTA["flag_alpha"]].strip() or "0"))

        # Shape uncertainties - optional
        if shape_line_idx + 1 < len(lines):
            line5 = f"{lines[shape_line_idx + 1]:<30}"
            if d_beta := safe_parse(line5[FORMAT_TANTA["d_beta"]]):
                params["d_beta"] = d_beta
            if d_alpha := safe_parse(line5[FORMAT_TANTA["d_alpha"]]):
                params["d_alpha"] = d_alpha

        return cls(**params)

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines."""
        lines = []

        # Main parameter line
        line1 = [
            "TANTA".ljust(5),
            " ",
            format_vary(self.flag_tanta),
            "   ",
            format_float(self.tanta, width=10),
            format_float(self.d_tanta, width=10) if self.d_tanta else "",
        ]
        lines.append("".join(line1))

        # Position parameters
        line2 = [
            " " * 6,
            format_vary(self.flag_x1),
            format_vary(self.flag_x2),
            format_vary(self.flag_x3),
            format_vary(self.flag_x0),
            format_float(self.x1, width=10),
            format_float(self.x2, width=10),
            format_float(self.x3, width=10),
            format_float(self.x0, width=10),
        ]
        lines.append("".join(line2))

        # Position uncertainties
        line3 = [
            " " * 10,
            format_float(self.d_x1, width=10),
            format_float(self.d_x2, width=10),
            format_float(self.d_x3, width=10),
            format_float(self.d_x0, width=10),
        ]
        lines.append("".join(line3))

        # Shape parameters
        line4 = [
            " " * 6,
            format_vary(self.flag_beta),
            format_vary(self.flag_alpha),
            "   ",
            format_float(self.beta, width=10),
            format_float(self.alpha, width=10),
        ]
        lines.append("".join(line4))

        # Shape uncertainties
        line5 = [" " * 10, format_float(self.d_beta, width=10), format_float(self.d_alpha, width=10)]
        lines.append("".join(line5))

        return lines


class LithiumParameters(BaseModel):
    """Lithium glass detector parameters."""

    d: float = Field(description="d parameter (nsec)")
    f: float = Field(description="f parameter (nsec⁻¹)")
    g: float = Field(description="g parameter (dimensionless)")

    flag_d: VaryFlag = Field(default=VaryFlag.NO)
    flag_f: VaryFlag = Field(default=VaryFlag.NO)
    flag_g: VaryFlag = Field(default=VaryFlag.NO)

    d_d: Optional[float] = Field(None, description="Uncertainty on d")
    d_f: Optional[float] = Field(None, description="Uncertainty on f")
    d_g: Optional[float] = Field(None, description="Uncertainty on g")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "LithiumParameters":
        """Parse lithium detector parameters from input lines."""
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        # Parse main line
        line = f"{lines[0]:<40}"
        params = {}

        # Parse main parameters
        for param in ["d", "f", "g"]:
            value = safe_parse(line[FORMAT_LITHI[param]])
            if value is not None:
                params[param] = value

        # Parse flags
        for flag in ["flag_d", "flag_f", "flag_g"]:
            value = line[FORMAT_LITHI[flag]].strip() or "0"
            try:
                params[flag] = VaryFlag(int(value))
            except (ValueError, TypeError):
                params[flag] = VaryFlag.NO

        # Parse uncertainties if present
        if len(lines) > 1 and lines[1].strip():
            unc_line = f"{lines[1]:<40}"
            for param in ["d_d", "d_f", "d_g"]:
                value = safe_parse(unc_line[FORMAT_LITHI[param]])
                if value is not None:
                    params[param] = value

        return cls(**params)

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines."""
        lines = []

        # Main parameters line
        main_parts = [
            "LITHI".ljust(5),
            " ",
            format_vary(self.flag_d),
            format_vary(self.flag_f),
            format_vary(self.flag_g),
            " ",
            format_float(self.d, width=10),
            format_float(self.f, width=10),
            format_float(self.g, width=10),
        ]
        lines.append("".join(main_parts))

        # Add uncertainties line if any present
        if any(getattr(self, f"d_{param}") is not None for param in ["d", "f", "g"]):
            unc_parts = [
                format_float(self.d_d, width=10),
                format_float(self.d_f, width=10),
                format_float(self.d_g, width=9),
            ]
            # pad the first 10 characters
            unc_parts = [" " * 10] + unc_parts
            lines.append("".join(unc_parts))

        return lines


class CrossSectionPoint(BaseModel):
    """Single energy/cross-section point for NE110 detector."""

    energy: float = Field(description="Maximum energy (eV)")
    sigma: float = Field(description="Total cross section (barns)")


class NE110Parameters(BaseModel):
    """NE110 detector parameters."""

    delta: float = Field(description="δ parameter (mm)")
    flag_delta: VaryFlag = Field(default=VaryFlag.NO)
    d_delta: Optional[float] = Field(None, description="Uncertainty on δ")
    density: float = Field(default=0.0047, description="Number of molecules per mm.b")
    cross_sections: Optional[List[CrossSectionPoint]] = Field(None)

    @classmethod
    def from_lines(cls, lines: List[str]) -> "NE110Parameters":
        """Parse NE110 detector parameters from input lines."""
        if not lines or not lines[0].strip():
            raise ValueError("No valid parameter line provided")

        line = f"{lines[0]:<40}"
        params = {}

        # Parse main parameters
        params["delta"] = safe_parse(line[FORMAT_NE110["delta"]])
        params["flag_delta"] = VaryFlag(int(line[FORMAT_NE110["flag_delta"]].strip() or "0"))

        if d_delta := safe_parse(line[FORMAT_NE110["d_delta"]]):
            params["d_delta"] = d_delta

        if density := safe_parse(line[FORMAT_NE110["density"]]):
            params["density"] = density

        # Parse number of cross section points
        num_points = safe_parse(line[FORMAT_NE110["num_points"]], as_int=True)

        # Parse cross section data if present
        if num_points and num_points > 0 and len(lines) > 1:
            cross_sections = []
            for line in lines[1 : num_points + 1]:
                line = f"{line:<30}"
                energy = safe_parse(line[FORMAT_NE110["energy"]])
                sigma = safe_parse(line[FORMAT_NE110["sigma"]])
                if energy is not None and sigma is not None:
                    cross_sections.append(CrossSectionPoint(energy=energy, sigma=sigma))
            if cross_sections:
                params["cross_sections"] = cross_sections

        return cls(**params)

    def to_lines(self) -> List[str]:
        """Convert parameters to fixed-width format lines."""
        lines = []

        # Main parameters
        main_parts = [
            "NE110".ljust(5),
            " ",
            format_vary(self.flag_delta),
            str(len(self.cross_sections or [])).rjust(3),
            format_float(self.delta, width=10),
            format_float(self.d_delta, width=10),
            format_float(self.density, width=10),
        ]
        lines.append("".join(main_parts))

        # Cross section points
        if self.cross_sections:
            for point in self.cross_sections:
                lines.append(
                    "".join([" " * 10, format_float(point.energy, width=10), format_float(point.sigma, width=10)])
                )

        return lines


class ChannelParameters(BaseModel):
    """Channel width parameters."""

    ecrnch: float = Field(description="Maximum energy for this channel width (eV)")
    chann: float = Field(description="Channel width (ns)")
    d_chann: Optional[float] = Field(None, description="Uncertainty on channel width")
    flag_chann: VaryFlag = Field(default=VaryFlag.NO)

    @classmethod
    def from_lines(cls, lines: List[str]) -> List["ChannelParameters"]:
        """Parse multiple channel parameter entries.

        Returns list since multiple channel definitions can exist."""
        if not lines:
            raise ValueError("No channel parameter lines provided")

        channels = []
        for line in lines:
            if not line.strip():
                continue

            line = f"{line:<40}"
            params = {}

            params["ecrnch"] = safe_parse(line[FORMAT_CHANNEL["ecrnch"]])
            params["chann"] = safe_parse(line[FORMAT_CHANNEL["chann"]])

            if d_chann := safe_parse(line[FORMAT_CHANNEL["d_chann"]]):
                params["d_chann"] = d_chann

            flag_val = line[FORMAT_CHANNEL["flag_chann"]].strip() or "0"
            params["flag_chann"] = VaryFlag(int(flag_val))

            channels.append(cls(**params))

        return channels

    def to_lines(self) -> List[str]:
        """Convert single channel parameter to fixed-width format."""
        parts = [
            "CHANN".ljust(5),
            " ",
            format_vary(self.flag_chann),
            "   ",
            format_float(self.ecrnch, width=10),
            format_float(self.chann, width=10),
            format_float(self.d_chann, width=10) if self.d_chann else "",
        ]
        return ["".join(parts)]


class ORRESParameters(BaseModel):
    """Main container for ORRES parameters with validation logic."""

    burst: Optional[BurstParameters] = None
    moderator: Optional[Union[WaterParameters, TantalumParameters]] = None
    detector: Optional[Union[LithiumParameters, NE110Parameters]] = None
    channels: Optional[List[ChannelParameters]] = None

    @model_validator(mode="after")
    def validate_components(self) -> "ORRESParameters":
        """Validate dependencies between components."""
        # Check 0: Channel parameters order
        if self.channels and len(self.channels) > 1:
            prev_energy = float("-inf")
            for channel in self.channels:
                if channel.ecrnch <= prev_energy:
                    raise ValueError("Channel energies must be in increasing order")
                prev_energy = channel.ecrnch

        # Check 1: NE110 cross section data consistency
        if isinstance(self.detector, NE110Parameters) and self.detector.cross_sections:
            prev_energy = float("-inf")
            for point in self.detector.cross_sections:
                if point.energy <= prev_energy:
                    raise ValueError("NE110 cross section energies must be in increasing order")
                prev_energy = point.energy

        return self

    @classmethod
    def parse_orres_parameters(cls, lines: List[str]) -> "ORRESParameters":
        params = {}
        current_section = None
        section_lines = []
        channel_lines = []  # Accumulate channel lines

        # Check data validity
        # NOTE: post model initialization validation does not work as later
        #       one overwrites the previous one.
        has_water_moderator = False
        has_tantalum_moderator = False
        has_lithium_detector = False
        has_ne110_detector = False
        for line in lines:
            if not line:
                continue  # Skip empty lines
            if line.startswith("WATER"):
                has_water_moderator = True
            elif line.startswith("TANTA"):
                has_tantalum_moderator = True
            elif line.startswith("LITHI"):
                has_lithium_detector = True
            elif line.startswith("NE110"):
                has_ne110_detector = True
        # Check for conflicting moderator and detector types
        if has_water_moderator and has_tantalum_moderator:
            raise ValueError("Cannot have both WATER and TANTA moderators")
        if has_lithium_detector and has_ne110_detector:
            raise ValueError("Cannot have both LITHI and NE110 detectors")

        # Process lines
        for line in lines:
            if not line:
                continue

            if line.startswith("CHANN"):
                channel_lines.append(line)
            elif line.startswith(("BURST", "WATER", "TANTA", "LITHI", "NE110")):
                if section_lines:
                    cls._process_section(current_section, section_lines, params)
                current_section = line[:5].lower().strip()
                section_lines = [line]
            else:
                section_lines.append(line)

        # Process final non-channel section
        if section_lines and current_section != "chann":
            cls._process_section(current_section, section_lines, params)

        # Process accumulated channel lines
        if channel_lines:
            params["channels"] = ChannelParameters.from_lines(channel_lines)

        return cls(**params)

    @staticmethod
    def _process_section(section: str, lines: List[str], params: dict):
        """Process lines for a given section."""
        if section == "burst":
            params["burst"] = BurstParameters.from_lines(lines)

        elif section == "water":
            params["moderator"] = WaterParameters.from_lines(lines)

        elif section == "tanta":
            params["moderator"] = TantalumParameters.from_lines(lines)

        elif section == "lithi":
            params["detector"] = LithiumParameters.from_lines(lines)

        elif section == "ne110":
            params["detector"] = NE110Parameters.from_lines(lines)

        elif section == "channel":
            params["channels"] = ChannelParameters.from_lines(lines)

    def to_lines(self) -> List[str]:
        """Convert all parameters to lines."""
        lines = []

        if self.burst:
            lines.extend(self.burst.to_lines())

        if isinstance(self.moderator, WaterParameters):
            lines.extend(self.moderator.to_lines())
        elif isinstance(self.moderator, TantalumParameters):
            lines.extend(self.moderator.to_lines())

        if isinstance(self.detector, LithiumParameters):
            lines.extend(self.detector.to_lines())
        elif isinstance(self.detector, NE110Parameters):
            lines.extend(self.detector.to_lines())

        if self.channels:
            for channel in self.channels:
                lines.extend(channel.to_lines())

        return lines


class ORRESCard(BaseModel):
    """Container for complete ORRES card."""

    parameters: ORRESParameters

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        return line.strip().upper().startswith("ORRES")

    @classmethod
    def from_lines(cls, lines: List[str]) -> "ORRESCard":
        if not lines:
            raise ValueError("No lines provided")

        if not cls.is_header_line(lines[0]):
            raise ValueError(f"Invalid header line: {lines[0]}")

        parameters = ORRESParameters.parse_orres_parameters(lines[1:])
        return cls(parameters=parameters)

    def to_lines(self) -> List[str]:
        lines = ["ORRES"]
        lines.extend(self.parameters.to_lines())
        lines.append("")  # Trailing blank line
        return lines


if __name__ == "__main__":
    print("Refer unit test for usage examples.")
