from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, field_validator

from pleiades.nuclear.manager import NuclearDataManager
from pleiades.nuclear.models import IsotopeIdentifier

from pleiades.utils.helper import VaryFlag
from pleiades.utils.logger import Logger

logger = Logger(__name__)


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

        spin_groups (List[int]):
            List of spin group numbers that use these radius parameters.
            Values > 500 indicate omitted resonances.

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

    effective_radius: float = Field(description="Radius for potential scattering (Fermi)", ge=0)
    true_radius: float = Field(description="Radius for penetrabilities and shifts (Fermi)")
    channel_mode: int = Field(
        description="Channel specification mode (0: all channels, 1: specific channels)",
        ge=0,  # Greater than or equal to 0
        le=1,  # Less than or equal to 1
    )
    vary_effective: VaryFlag = Field(default=VaryFlag.NO, description="Flag for varying effective radius")
    vary_true: VaryFlag = Field(default=VaryFlag.NO, description="Flag for varying true radius")
    spin_groups: Optional[List[int]] = Field(
        description="List of spin group numbers",
    )
    channels: Optional[List[int]] = Field(default=None, description="List of channel numbers (required when channel_mode=1)")

    @field_validator("spin_groups")
    def validate_spin_groups(cls, v: List[int]) -> List[int]:
        """Validate spin group numbers.

        Args:
            v: List of spin group numbers

        Returns:
            List[int]: Validated spin group numbers

        Raises:
            ValueError: If any spin group number is invalid
        """
        for group in v:
            if group <= 0:
                raise ValueError(f"Spin group numbers must be positive, got {group}")

            # Values > 500 are valid but indicate omitted resonances
            # We allow them but might want to warn the user
            if group > 500:
                print(f"Warning: Spin group {group} > 500 indicates omitted resonances")

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
        if self.true_radius == 0:
            if self.vary_true == VaryFlag.USE_FROM_PARFILE:
                logger.error("When true_radius=0 (use CRFN value), vary_true cannot be USE_FROM_PARFILE (-1)")
                raise ValueError("When true_radius=0 (use CRFN value), vary_true cannot be USE_FROM_PARFILE (-1)")

        if self.true_radius < 0:
            if self.vary_true == VaryFlag.USE_FROM_PARFILE:
                logger.error("When true_radius is negative (AWRI specification), vary_true cannot be USE_FROM_PARFILE (-1)")
                raise ValueError("When true_radius is negative (AWRI specification), vary_true cannot be USE_FROM_PARFILE (-1)")

        return self


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


class IsotopeParameters(BaseModel):
    """Container for a single isotope's parameters which include.
        mass, 
        abundance, uncertainty, treatment flag, and associated
    spin groups.

    Attributes:
        mass (float): Atomic mass in atomic mass units (amu)
        abundance (float): Fractional abundance (dimensionless)
        uncertainty (Optional[float]): Uncertainty on abundance (dimensionless)
        flag (VaryFlag): Treatment flag for abundance (-2=use input, 0=fixed, 1=vary, 3=PUP)
        spin_groups (List[int]): List of spin group numbers (negative values indicate omitted resonances)
        resonances (List[ResonanceEntry]): List of resonance entries
        radius_parameters (List[RadiusParameters]): List of radius parameters

    """

    isotope_name: str = Field(description="Isotope name")
    mass: float = Field(description="Atomic mass in amu", gt=0)
    abundance: float = Field(description="Fractional abundance", ge=0)
    uncertainty: Optional[float] = Field(None, description="Uncertainty on abundance")
    flag: Optional[VaryFlag] = Field(default=None, description="Treatment flag for abundance")
    spin_groups: Optional[List[int]] = Field(default=None, description="Spin group numbers")
    resonances: Optional[List[ResonanceEntry]] = Field(default=None, description="List of resonance entries")
    radius_parameters: Optional[List[RadiusParameters]] = Field(default=None, description="List of radius parameters")
    
    @classmethod
    def from_name(cls, isotope_name: str) -> "IsotopeParameters":
        """Create an IsotopeParameters object from isotope name.

        Args:
            isotope_name: Isotope name (e.g., "U-238")

        Returns:
            IsotopeParameters: IsotopeParameters object with isotope name
        """
        # Convert to uppercase
        isotope_name = isotope_name.upper()
        
        # Create an instance of NuclearDataManager
        manager = NuclearDataManager()
        
        # Convert isotope_name to IsotopeIdentifier
        isotope_identifier = IsotopeIdentifier.from_string(isotope_name)
        
       # Get mass data from the manager
        mass_data = manager.get_mass_data(isotope_identifier)
        mass = mass_data.atomic_mass if mass_data else None
        
        # Get abundance data from the manager
        isotope_info = manager.get_isotope_info(isotope_identifier)
        abundance = isotope_info.abundance if isotope_info else None
        
        

        return cls(
            isotope_name=isotope_name,
            mass=mass,
            abundance=abundance,
            uncertainty=None,  # Default value
            flag=None,  # Default value
            spin_groups=[],  # Default value
            resonances=[],  # Default value
            radius_parameters=[]  # Default value
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
        where_am_i = "IsotopeParameters.validate_groups()"
        max_standard = 99  # Maximum group number for standard format

        for group in self.spin_groups:
            if group == 0:
                logger.info(f"{where_am_i}:Spin group number cannot be 0")
                raise ValueError("Spin group number cannot be 0")

            # Check if we need extended format
            if abs(group) > max_standard:
                logger.info(f"{where_am_i}:Group number {group} requires extended format")

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
        where_am_i = "IsotopeParameters.validate_resonances()"

        for resonance in self.resonances:
            if resonance.igroup not in self.spin_groups:
                logger.info(f"{where_am_i}:Resonance igroup {resonance.igroup} not in spin groups {self.spin_groups}")
                raise ValueError(f"Resonance igroup {resonance.igroup} not in spin groups {self.spin_groups}")

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
        where_am_i = "IsotopeParameters.validate_radius_parameters()"

        for radius in self.radius_parameters:
            for group in radius.spin_groups:
                if group not in self.spin_groups:
                    logger.info(f"{where_am_i}:Radius parameter spin group {group} not in isotope spin groups {self.spin_groups}")
                    raise ValueError(f"Radius parameter spin group {group} not in isotope spin groups {self.spin_groups}")

        return self
    
class nuclearParameters(BaseModel):
    """Container for nuclear parameters used in SAMMY calculations.

    Attributes:
        isotopes (List[IsotopeParameters]): List of isotope parameters

    """

    isotopes: List[IsotopeParameters] = Field(default_factory=list, description="List of isotope parameters")

    @model_validator(mode="after")
    def validate_isotopes(self) -> "nuclearParameters":
        """Validate isotope parameters.

        Validates:
        - Each isotope has a unique mass
        - Each isotope has a unique abundance   
        """
        where_am_i = "nuclear_params.validate_isotopes()"

        # Check for duplicate isotope names
        names = [iso.isotope_name for iso in self.isotopes]
        if len(names) != len(set(names)):
            logger.info(f"{where_am_i}:Duplicate isotope names found")
            raise ValueError("Duplicate isotope names found")

        # Check for duplicate masses
        masses = [iso.mass for iso in self.isotopes]
        if len(masses) != len(set(masses)):
            logger.info(f"{where_am_i}:Duplicate masses found")
            raise ValueError("Duplicate masses found")


        return self
    
    
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