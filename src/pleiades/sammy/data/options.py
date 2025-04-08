from enum import Enum

from pydantic import BaseModel, Field

from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions


class DataTypeOptions(str, Enum):
    TRANSMISSION = "TRANSMISSION"
    TOTAL_CROSS_SECTION = "TOTAL CROSS SECTION"
    SCATTERING = "SCATTERING"
    ELASTIC = "ELASTIC"
    DIFFERENTIAL_ELASTIC = "DIFFERENTIAL ELASTIC"
    DIFFERENTIAL_REACTION = "DIFFERENTIAL REACTION"
    REACTION = "REACTION"
    INELASTIC_SCATTERING = "INELASTIC SCATTERING"
    FISSION = "FISSION"
    CAPTURE = "CAPTURE"
    SELF_INDICATION = "SELF INDICATION"
    INTEGRAL = "INTEGRAL"
    COMBINATION = "COMBINATION"


class dataParameters(BaseModel):
    """Container for data parameters.

    Attributes:
        data_file: File containing the data
        data_format: Format of the data
        data_type: Type of the data
        energy_units: Units of energy
        cross_section_units: Units of cross-section
        data_title: Title of the data
        data_comment: Comment for the data
    """

    data_file: str = Field(description="File containing the data", default=None)
    data_type: DataTypeOptions = Field(description="Type of the data", default=DataTypeOptions.TRANSMISSION)
    energy_units: EnergyUnitOptions = Field(description="Units of energy", default=EnergyUnitOptions.eV)
    cross_section_units: CrossSectionUnitOptions = Field(
        description="Units of cross-section", default=CrossSectionUnitOptions.barn
    )
    data_title: str = Field(description="Title of the data", default=None)
    data_comment: str = Field(description="Comment for the data", default=None)
