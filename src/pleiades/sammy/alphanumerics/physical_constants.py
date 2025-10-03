from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    Physical constants control options = [
    ----------------------------
        "USE ENDF VALUES FOR constants", *
        "USE 1995 ENDF-102 COnstant values",
        "USE SAMMY-K1 DEFAULTs for constants",
    ----------------------------
    ]
"""


class PhysicalConstantsOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # Physical constants options (mutually exclusive)
    use_endf_values_for_constants: bool = Field(
        default=True,
        description="Use physical constants from 1999 ENDF-102 (Default)",
    )
    use_1995_endf_102_constant_values: bool = Field(
        default=False,
        description="Use physical constants from 1995 ENDF-102",
    )
    use_sammy_k1_defaults_for_constants: bool = Field(
        default=False,
        description="Use physical constants from SAMMY version K1 (for comparison only)",
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        [
            "use_endf_values_for_constants",
            "use_1995_endf_102_constant_values",
            "use_sammy_k1_defaults_for_constants",
        ],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "PhysicalConstantsOptions":
        """Validate mutually exclusive fields and ensure at least one option is True."""
        # Count how many options are enabled
        options_enabled = 0
        if self.use_endf_values_for_constants:
            options_enabled += 1
        if self.use_1995_endf_102_constant_values:
            options_enabled += 1
        if self.use_sammy_k1_defaults_for_constants:
            options_enabled += 1

        # Check that exactly one option is enabled
        if options_enabled == 0:
            raise ValueError("At least one physical constants option must be enabled")
        if options_enabled > 1:
            raise ValueError(
                "Only one physical constants option can be enabled: "
                "USE ENDF VALUES FOR CONSTANTS, USE 1995 ENDF-102 CONSTANT VALUES, "
                "or USE SAMMY-K1 DEFAULTS FOR CONSTANTS"
            )

        return self

    def get_alphanumeric_commands(self) -> List[str]:
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.use_endf_values_for_constants:
            commands.append("USE ENDF VALUES FOR CONSTANTS")
        if self.use_1995_endf_102_constant_values:
            commands.append("USE 1995 ENDF-102 CONSTANT VALUES")
        if self.use_sammy_k1_defaults_for_constants:
            commands.append("USE SAMMY-K1 DEFAULTS FOR CONSTANTS")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        # Example valid configuration - default
        options = PhysicalConstantsOptions()
        print("Default configuration:")
        print(options.get_alphanumeric_commands())

        # Example valid configuration - ENDF 1995
        options = PhysicalConstantsOptions(
            use_endf_values_for_constants=False,
            use_1995_endf_102_constant_values=True,
        )
        print("ENDF 1995 configuration:")
        print(options.get_alphanumeric_commands())

        # Example with mutually exclusive error
        options = PhysicalConstantsOptions(
            use_endf_values_for_constants=True,
            use_1995_endf_102_constant_values=True,  # This should fail
        )
    except ValueError as e:
        print(f"Validation error: {e}")
