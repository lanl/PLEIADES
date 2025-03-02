from pydantic import BaseModel, Field, model_validator

"""
# Parameters output control for parameter covariance matrix
# Define the method of output for the parameter covariance matrix
output_covariance_matrix_options = [
    --------------
    ["WRITE CORRELATIONS Into compact format","PUT CORRELATIONS INTo compact format"],
    ["WRITE COVARIANCES INto compact format","PUT COVARIANCES INTO compact format"],
    "PUT COVARIANCE MATRIx into endf file 32"
    --------------
    ]
"""

class CovarianceMatrixOutputOptions(BaseModel):
    """Model to enforce mutually exclusive selection of output covariance matrix options using boolean flags."""
    
    # Boolean flags for mutual exclusivity
    write_correlations_into_compact_format: bool = Field(default=False, description="Write correlations into compact format")
    put_correlations_into_compact_format: bool = Field(default=False, description="Put correlations into compact format")
    write_covariances_into_compact_format: bool = Field(default=False, description="Write covariances into compact format")
    put_covariances_into_compact_format: bool = Field(default=False, description="Put covariances into compact format")
    put_covariance_matrix_into_endf_file_32: bool = Field(default=False, description="Put covariance matrix into ENDF file 32")

    def get_alphanumeric_commands(self):
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.write_correlations_into_compact_format:
            commands.append("WRITE CORRELATIONS INTO COMPACT FORMAT")
        if self.put_correlations_into_compact_format:
            commands.append("PUT CORRELATIONS INTO COMPACT FORMAT")
        if self.write_covariances_into_compact_format:
            commands.append("WRITE COVARIANCES INTO COMPACT FORMAT")
        if self.put_covariances_into_compact_format:
            commands.append("PUT COVARIANCES INTO COMPACT FORMAT")
        if self.put_covariance_matrix_into_endf_file_32:
            commands.append("PUT COVARIANCE MATRIX INTO ENDF FILE 32")
        return commands

    @model_validator(mode='after')
    def check_exclusivity(cls, values):
        """Ensure that only one option is selected using boolean flags."""
        mutually_exclusive_groups = [
            ["write_correlations_into_compact_format", "put_correlations_into_compact_format","write_covariances_into_compact_format", "put_covariances_into_compact_format","put_covariance_matrix_into_endf_file_32"],
        ]

        for group in mutually_exclusive_groups:
            selected_flags = [key for key in group if getattr(values, key)]
            if len(selected_flags) > 1:
                raise ValueError(f"Only one option can be selected from the group: {selected_flags}")

        return values