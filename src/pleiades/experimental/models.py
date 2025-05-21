from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

# Import VaryFlag from helper module
from pleiades.utils.helper import VaryFlag

# NOTE: Some physics parameters are not supported in the current version of the code


class EnergyParameters(BaseModel):
    """Parameters for energy bounds and sampling

    Args:
        BaseModel (_type_): _description_

    Raises:
        ValueError: _description_
        ValueError: _description_

    Returns:
        _type_: _description_
    """

    min_energy: float = Field(default=0.0, description="Minimum energy for this data set(eV)")
    max_energy: float = Field(default=0.0, description="Maximum energy (eV)")
    number_of_energy_points: int = Field(
        description="Number of points to be used in generating artificial energy grid", default=10001
    )
    number_of_extra_points: int = Field(
        description="Number of extra points to be added between each pair of data points for auxiliary energy grid",
        default=0,
    )
    number_of_small_res_points: int = Field(
        description="Number of points to be added to auxiliary energy grid across small resonances", default=0
    )


class NormalizationParameters(BaseModel):
    """Parameters for normalization and background for one angle.

    Contains:
    - Normalization and background values
    - Their uncertainties (optional)
    - Flags indicating whether each parameter should be varied

    Note on fixed-width format:
    Each numeric field in the file uses a 10-column width with a 9+1 pattern:
    - 9 characters for the actual numeric data (e.g. "1.2340E+00")
    - 1 character for space separator
    """

    # Main parameters
    anorm: float = Field(default=None, description="Normalization (dimensionless)")
    backa: float = Field(default=None, description="Constant background")
    backb: float = Field(default=None, description="Background proportional to 1/E")
    backc: float = Field(default=None, description="Background proportional to √E")
    backd: float = Field(default=None, description="Exponential background coefficient")
    backf: float = Field(default=None, description="Exponential decay constant")

    # Optional uncertainties
    d_anorm: Optional[float] = Field(None, description="Uncertainty on ANORM")
    d_backa: Optional[float] = Field(None, description="Uncertainty on BACKA")
    d_backb: Optional[float] = Field(None, description="Uncertainty on BACKB")
    d_backc: Optional[float] = Field(None, description="Uncertainty on BACKC")
    d_backd: Optional[float] = Field(None, description="Uncertainty on BACKD")
    d_backf: Optional[float] = Field(None, description="Uncertainty on BACKF")

    # Vary flags
    flag_anorm: VaryFlag = Field(default=VaryFlag.NO)
    flag_backa: VaryFlag = Field(default=VaryFlag.NO)
    flag_backb: VaryFlag = Field(default=VaryFlag.NO)
    flag_backc: VaryFlag = Field(default=VaryFlag.NO)
    flag_backd: VaryFlag = Field(default=VaryFlag.NO)
    flag_backf: VaryFlag = Field(default=VaryFlag.NO)

    # Define a print method for the class
    def __str__(self) -> str:
        """Return a text table representation of the NormalizationParameters object."""
        headers = ["Parameter", "Value", "Uncertainty", "Vary"]
        rows = [
            ["Normalization", self.anorm, self.d_anorm, self.flag_anorm],
            ["Const. Background", self.backa, self.d_backa, self.flag_backa],
            ["1/E Background", self.backb, self.d_backb, self.flag_backb],
            ["sqrt(E) Background", self.backc, self.d_backc, self.flag_backc],
            ["Exp. Background", self.backd, self.d_backd, self.flag_backd],
            ["Exp. Decay Const.", self.backf, self.d_backf, self.flag_backf],
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


class BroadeningParameters(BaseModel):
    """Container for a single set of broadening parameters.

    Contains all parameters from a single card set 4 entry including:
    - Main parameters (CRFN, TEMP, etc.)
    - Their uncertainties
    - Additional Gaussian parameters
    - Flags indicating whether each parameter should be varied

    Note on fixed-width format:
    Each numeric field in the file uses a 10-column width with a 9+1 pattern:
    - 9 characters for the actual numeric data (e.g. "1.2340E+00")
    - 1 character for space separator
    This format ensures human readability while maintaining proper fixed-width alignment.
    """

    # Main parameters
    crfn: float = Field(default=None, description="Matching radius (F)")
    temp: float = Field(default=None, description="Effective temperature (K)")
    thick: float = Field(default=None, description="Sample thickness (atoms/barn)")
    deltal: float = Field(default=None, description="Spread in flight-path length (m)")
    deltag: float = Field(default=None, description="Gaussian resolution width (μs)")
    deltae: float = Field(default=None, description="e-folding width of exponential resolution (μs)")

    # Optional uncertainties for main parameters
    d_crfn: Optional[float] = Field(None, description="Uncertainty on CRFN")
    d_temp: Optional[float] = Field(None, description="Uncertainty on TEMP")
    d_thick: Optional[float] = Field(None, description="Uncertainty on THICK")
    d_deltal: Optional[float] = Field(None, description="Uncertainty on DELTAL")
    d_deltag: Optional[float] = Field(None, description="Uncertainty on DELTAG")
    d_deltae: Optional[float] = Field(None, description="Uncertainty on DELTAE")

    # Optional additional Gaussian parameters
    deltc1: Optional[float] = Field(None, description="Width of Gaussian, constant in energy (eV)")
    deltc2: Optional[float] = Field(None, description="Width of Gaussian, linear in energy (unitless)")
    d_deltc1: Optional[float] = Field(None, description="Uncertainty on DELTC1")
    d_deltc2: Optional[float] = Field(None, description="Uncertainty on DELTC2")

    # Vary flags for all parameters
    flag_crfn: VaryFlag = Field(default=VaryFlag.NO)
    flag_temp: VaryFlag = Field(default=VaryFlag.NO)
    flag_thick: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltal: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltag: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltae: VaryFlag = Field(default=VaryFlag.NO)
    flag_deltc1: Optional[VaryFlag] = Field(None)
    flag_deltc2: Optional[VaryFlag] = Field(None)

    @model_validator(mode="after")
    def validate_gaussian_parameters(self) -> "BroadeningParameters":
        """Validate that if any Gaussian parameter is present, both are present."""
        has_deltc1 = self.deltc1 is not None
        has_deltc2 = self.deltc2 is not None
        if has_deltc1 != has_deltc2:
            raise ValueError("Both DELTC1 and DELTC2 must be present if either is present")
        if has_deltc1:
            if self.flag_deltc1 is None or self.flag_deltc2 is None:
                raise ValueError("Flags must be specified for DELTC1 and DELTC2 if present")
        return self

    # define a print method for the class that prints a table
    def __str__(self) -> str:
        """Return a text table representation of the BroadeningParameters object."""
        headers = ["Parameter", "Value", "Uncertainty", "Vary"]
        rows = [
            ["CRFN", self.crfn, self.d_crfn, self.flag_crfn],
            ["TEMP", self.temp, self.d_temp, self.flag_temp],
            ["THICK", self.thick, self.d_thick, self.flag_thick],
            ["DELTAL", self.deltal, self.d_deltal, self.flag_deltal],
            ["DELTAG", self.deltag, self.d_deltag, self.flag_deltag],
            ["DELTAE", self.deltae, self.d_deltae, self.flag_deltae],
            ["DELT1", self.deltc1, self.d_deltc1, self.flag_deltc1],
            ["DELT2", self.deltc2, self.d_deltc2, self.flag_deltc2],
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


class UserResolutionParameters(BaseModel):
    """Container for User-Defined Resolution Function parameters.

    Attributes:
        type: Parameter type identifier (always "USER")
        burst_width: Square burst width value (ns), optional
        burst_uncertainty: Uncertainty on burst width, optional
        burst_flag: Flag for varying burst width
        channel_energies: List of energies for channel widths
        channel_widths: List of channel width values
        channel_uncertainties: List of uncertainties on channel widths
        channel_flags: List of flags for varying channel widths
        filenames: List of data file names
    """

    class UserDefinedResolutionType(str, Enum):
        """Enumeration of user defined resolution types."""

        USER = "USER"  # Header identifier
        BURST = "BURST"
        CHANN = "CHANN"
        FILE = "FILE="

    type: UserDefinedResolutionType = UserDefinedResolutionType.USER
    burst_width: Optional[float] = Field(default=None, description="Square burst width (ns)")
    burst_uncertainty: Optional[float] = Field(default=None, description="Uncertainty on burst width")
    burst_flag: VaryFlag = Field(default=VaryFlag.NO, description="Flag for burst width")
    channel_energies: List[float] = Field(default_factory=list, description="Energies for channels")
    channel_widths: List[float] = Field(default_factory=list, description="Channel width values")
    channel_uncertainties: List[Optional[float]] = Field(default_factory=list, description="Channel uncertainties")
    channel_flags: List[VaryFlag] = Field(default_factory=list, description="Channel flags")
    filenames: List[str] = Field(default_factory=list, description="Resolution function filenames")


class PhysicsParameters(BaseModel):
    """Container for all physics parameters.

    Attributes:
        energy_parameters: Parameters for energy bounds and sampling
        normalization_parameters: Parameters for normalization and background
        broadening_parameters: Parameters for broadening
        user_resolution_parameters: User-defined resolution function parameters
    """

    energy_parameters: EnergyParameters = Field(default_factory=EnergyParameters, description="Energy parameters")
    normalization_parameters: NormalizationParameters = Field(
        default_factory=NormalizationParameters, description="Normalization parameters"
    )
    broadening_parameters: BroadeningParameters = Field(
        default_factory=BroadeningParameters, description="Broadening parameters"
    )
    user_resolution_parameters: UserResolutionParameters = Field(
        default_factory=UserResolutionParameters, description="User-defined resolution function parameters"
    )

    def __init__(self, **data):
        super().__init__(**data)
        self.validate_gaussian_parameters()

    def validate_gaussian_parameters(self) -> None:
        """Validate that if any Gaussian parameter is present, both are present."""
        self.broadening_parameters.validate_gaussian_parameters()
