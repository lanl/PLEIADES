from pydantic import BaseModel, Field, model_validator
from typing import ClassVar

"""
    These notes are taken from the SAMMY manual. 
    - * denotes a default options
    - Mutually exclusive options are grouped together starting with -------------- and ending with -------------
    - options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    # Experimental data input control
    # Define the format for the experimental data
    experimental_data_input_options = [
        --------------
        *"DATA ARE IN ORIGINAL multi-style format",
        ["DATA FORMAT IS ONE Point per line","USE CSISRS FORMAT FOr data","CSISRS"],
        ["USE TWENTY SIGNIFICAnt digits","TWENTY"],
        "DATA ARE IN STANDARD odf format",
        "DATA ARE IN ODF FILE",
        ["DATA ARE ENDF/B FILE","USE ENDF/B ENERGIES and data, with MAT=9999"],
        --------------
        "DIFFERENTIAL DATA ARe in ascii file",
        --------------
        *"DO NOT DIVIDE DATA Into regions",
        "DIVIDE DATA INTO REGions with a fixed number of data points per region"
        --------------
        ]
"""

class ExperimentalDataInputOptions(BaseModel):
    """Model to enforce mutually exclusive selection of experimental data input options using boolean flags."""
    
    # Boolean flags for mutual exclusivity
    data_in_original_multi_style_format: bool = Field(default=True, description="DATA ARE IN ORIGINAL multi-style format")
    data_format_is_one_point_per_line: bool = Field(default=False, description="DATA FORMAT IS ONE Point per line")
    use_csisrs_format_for_data: bool = Field(default=False, description="USE CSISRS FORMAT For data")
    use_twenty_significant_digits: bool = Field(default=False, description="USE TWENTY SIGNIFICANT digits")
    data_are_in_standard_odf_format: bool = Field(default=False, description="DATA ARE IN STANDARD odf format")
    data_are_in_odf_file: bool = Field(default=False, description="DATA ARE IN ODF FILE")
    data_are_endf_b_file: bool = Field(default=False, description="DATA ARE ENDF/B FILE")
    use_endf_b_energies_and_data: bool = Field(default=False, description="USE ENDF/B ENERGIES and data, with MAT=9999")
    differential_data_are_in_ascii_file: bool = Field(default=False, description="DIFFERENTIAL DATA ARE in ascii file")
    do_not_divide_data_into_regions: bool = Field(default=True, description="DO NOT DIVIDE DATA Into regions")
    divide_data_into_regions: bool = Field(default=False, description="DIVIDE DATA INTO REGions with a fixed number of data points per region")

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: ClassVar[list[list[str]]] = [
        ["data_in_original_multi_style_format", "data_format_is_one_point_per_line", "use_csisrs_format_for_data", "use_twenty_significant_digits", "data_are_in_standard_odf_format", "data_are_in_odf_file", "data_are_endf_b_file", "use_endf_b_energies_and_data"],
        ["do_not_divide_data_into_regions", "divide_data_into_regions"]
    ]
    
    def __init__(self, **data):
        super().__init__(**data)
        for name, value in data.items():
            self.__setattr__(name, value)
        self.check_exclusivity()

    def __setattr__(self, name, value):
        """Custom setattr to handle mutually exclusive options."""
        for group in self.mutually_exclusive_groups:
            if name in group and value is True:
                for option in group:
                    if option != name:
                        super().__setattr__(option, False)
        super().__setattr__(name, value)

    def get_alphanumeric_commands(self):
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.data_in_original_multi_style_format:
            commands.append("DATA ARE IN ORIGINAL multi-style format")
        if self.data_format_is_one_point_per_line:
            commands.append("DATA FORMAT IS ONE Point per line")
        if self.use_csisrs_format_for_data:
            commands.append("USE CSISRS FORMAT For data")
        if self.use_twenty_significant_digits:
            commands.append("USE TWENTY SIGNIFICANT digits")
        if self.data_are_in_standard_odf_format:
            commands.append("DATA ARE IN STANDARD odf format")
        if self.data_are_in_odf_file:
            commands.append("DATA ARE IN ODF FILE")
        if self.data_are_endf_b_file:
            commands.append("DATA ARE ENDF/B FILE")
        if self.use_endf_b_energies_and_data:
            commands.append("USE ENDF/B ENERGIES and data, with MAT=9999")
        if self.differential_data_are_in_ascii_file:
            commands.append("DIFFERENTIAL DATA ARE in ascii file")
        if self.do_not_divide_data_into_regions:
            commands.append("DO NOT DIVIDE DATA Into regions")
        if self.divide_data_into_regions:
            commands.append("DIVIDE DATA INTO REGions with a fixed number of data points per region")
        return commands

    def check_exclusivity(self):
        """Ensure that only one experimental data input option is selected using boolean flags."""
        for group in self.mutually_exclusive_groups:
            selected_flags = [key for key in group if getattr(self, key)]
            if len(selected_flags) > 1:
                raise ValueError(f"Only one option can be selected from the group: {selected_flags}")

# Example usage
try:
    options = ExperimentalDataInputOptions(
        data_in_original_multi_style_format=True,
        data_format_is_one_point_per_line=True  # This will automatically switch off data_in_original_multi_style_format
    )
except ValueError as e:
    print(e)