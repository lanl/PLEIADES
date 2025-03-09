from enum import Enum
from pydantic import BaseModel, Field
import pint

# Create a unit registry
ureg = pint.UnitRegistry()

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
    energy_units: pint.Quantity = Field(description="Units of energy", default=ureg.eV)
    cross_section_units: pint.Quantity = Field(description="Units of cross-section", default=ureg.barn)
    data_title: str = Field(description="Title of the data", default=None)
    data_comment: str = Field(description="Comment for the data", default=None)

    def convert_energy_units(self, value, from_units, to_units):
        """Convert energy value from specified units to specified units."""
        energy = value * ureg(from_units)
        converted_energy = energy.to(to_units)
        return converted_energy.magnitude
        
    def convert_cross_section_units(self, value, from_units, to_units):
        """Convert cross-section value from specified units to specified units."""
        cross_section = value * ureg(from_units)
        converted_cross_section = cross_section.to(to_units)
        return converted_cross_section.magnitude

# Example usage
if __name__ == "__main__":
    params = dataParameters()
    energy_in_keV = params.convert_energy_units(1000, 'eV', 'keV')
    cross_section_in_cm2 = params.convert_cross_section_units(1, 'barn', 'cm^2')
    print(f"1000 eV is equal to {energy_in_keV} keV")
    print(f"1 barn is equal to {cross_section_in_cm2} cm^2")