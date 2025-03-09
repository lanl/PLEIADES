from enum import Enum
from pydantic import BaseModel, Field

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
        data_units: Units of the data
        data_title: Title of the data
        data_comment: Comment for the data
    """

    data_file: str = Field(description="File containing the data", default=None)
    data_type: DataTypeOptions = Field(description="Type of the data", default=DataTypeOptions.TRANSMISSION)
    data_units: str = Field(description="Units of the data")
    energy_units: str = Field(description="Units of energy", default="eV")
    cross_section_units: str = Field(description="Units of cross-section", default="barns")
    data_title: str = Field(description="Title of the data", default=None)
    data_comment: str = Field(description="Comment for the data", default=None)