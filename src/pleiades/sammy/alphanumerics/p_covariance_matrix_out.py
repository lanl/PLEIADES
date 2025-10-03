from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

        Parameters output control for parameter covariance matrix
        Define the method of output for the parameter covariance matrix
        output_covariance_matrix_options = [
        ----------------------------
            ["WRITE CORRELATIONS Into compact format","PUT CORRELATIONS INTo compact format"],
            ["WRITE COVARIANCES INto compact format","PUT COVARIANCES INTO compact format"],
            "PUT COVARIANCE MATRIx into endf file 32"
        ----------------------------
        ]
"""


class CovarianceMatrixOutputOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    write_correlations_into_compact_format: bool = Field(
        default=False, description="WRITE CORRELATIONS Into compact format"
    )
    put_correlations_into_compact_format: bool = Field(
        default=False, description="PUT CORRELATIONS INTo compact format"
    )
    write_covariances_into_compact_format: bool = Field(
        default=False, description="WRITE COVARIANCES INto compact format"
    )
    put_covariances_into_compact_format: bool = Field(default=False, description="PUT COVARIANCES INTO compact format")
    put_covariance_matrix_into_endf_file_32: bool = Field(
        default=False, description="PUT COVARIANCE MATRIx into endf file 32"
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        [
            "write_correlations_into_compact_format",
            "put_correlations_into_compact_format",
            "write_covariances_into_compact_format",
            "put_covariances_into_compact_format",
            "put_covariance_matrix_into_endf_file_32",
        ]
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "CovarianceMatrixOutputOptions":
        for group in self.mutually_exclusive_groups:
            true_fields = [f for f in group if getattr(self, f)]
            if not true_fields:
                continue

            user_true = [f for f in true_fields if f in self.model_fields_set]
            default_true = [f for f in true_fields if f not in self.model_fields_set]

            # If >1 user-specified in same group => error
            if len(user_true) > 1:
                raise ValueError(
                    f"Multiple user-specified fields {user_true} are True in group {group}. Only one allowed."
                )

            # If exactly 1 user-specified => turn off all defaults in that group
            if len(user_true) == 1:
                for f in default_true:
                    setattr(self, f, False)
                continue

            # If all True fields are defaults, and more than 1 => error
            if len(default_true) > 1:
                raise ValueError(f"Multiple default fields {default_true} are True in group {group}. Only one allowed.")
        return self

    def get_alphanumeric_commands(self) -> List[str]:
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


# Example usage
if __name__ == "__main__":
    try:
        options = CovarianceMatrixOutputOptions(
            write_correlations_into_compact_format=True,
            put_correlations_into_compact_format=True,  # This should raise a ValueError
        )
    except ValueError as e:
        print(e)
