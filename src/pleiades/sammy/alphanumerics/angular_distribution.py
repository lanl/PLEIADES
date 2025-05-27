from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    Angular distribution options = [
    ----------------------------
        "USE LABORATORY CROSS sections",
        "USE CENTER-OF-MASS Cross sections", *
    ----------------------------
        "PREPARE LEGENDRE COEfficients in endf format",
        "OMIT FINITE SIZE CORrections",
        "INCIDENT NEUTRON ATTenuation is included",
        "APPROXIMATE SCATTEREd neutron attenuation",
        "ANGLE-AVERAGE FOR DIfferential cross section",
    ----------------------------
    ]
"""


class AngularDistributionOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # Reference frame options (mutually exclusive)
    use_laboratory_cross_sections: bool = Field(
        default=False,
        description="For angle-differential data, output cross sections in laboratory frame",
    )
    use_center_of_mass_cross_sections: bool = Field(
        default=True,
        description="For angle-differential data, output cross sections in center-of-mass frame (Default)",
    )

    # Additional angular distribution options
    prepare_legendre_coefficients_in_endf_format: bool = Field(
        default=False,
        description="Generate SAMMY.N04 with ENDF File-4 Legendre coefficients for elastic angular distributions",
    )
    omit_finite_size_corrections: bool = Field(
        default=False,
        description="Do not include finite size corrections for angular distributions",
    )
    incident_neutron_attenuation_is_included: bool = Field(
        default=False,
        description="Include incident neutron attenuation for angular distributions",
    )
    approximate_scattered_neutron_attenuation: bool = Field(
        default=False,
        description="Include approximate scattered neutron attenuation for angular distributions",
    )
    angle_average_for_differential_cross_section: bool = Field(
        default=False,
        description="Perform angle averaging for differential cross sections using quadratic interpolation",
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        [
            "use_laboratory_cross_sections",
            "use_center_of_mass_cross_sections",
        ],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "AngularDistributionOptions":
        """Validate mutually exclusive fields and ensure exactly one frame option is selected."""
        # Check reference frame options (mutually exclusive and exactly one must be True)
        if self.use_laboratory_cross_sections == self.use_center_of_mass_cross_sections:
            raise ValueError(
                "Exactly one of USE LABORATORY CROSS SECTIONS or USE CENTER-OF-MASS CROSS SECTIONS must be enabled"
            )

        return self

    def get_alphanumeric_commands(self) -> List[str]:
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.use_laboratory_cross_sections:
            commands.append("USE LABORATORY CROSS SECTIONS")
        if self.use_center_of_mass_cross_sections:
            commands.append("USE CENTER-OF-MASS CROSS SECTIONS")
        if self.prepare_legendre_coefficients_in_endf_format:
            commands.append("PREPARE LEGENDRE COEFFICIENTS IN ENDF FORMAT")
        if self.omit_finite_size_corrections:
            commands.append("OMIT FINITE SIZE CORRECTIONS")
        if self.incident_neutron_attenuation_is_included:
            commands.append("INCIDENT NEUTRON ATTENUATION IS INCLUDED")
        if self.approximate_scattered_neutron_attenuation:
            commands.append("APPROXIMATE SCATTERED NEUTRON ATTENUATION")
        if self.angle_average_for_differential_cross_section:
            commands.append("ANGLE-AVERAGE FOR DIFFERENTIAL CROSS SECTION")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        # Example valid configuration - default
        options = AngularDistributionOptions()
        print("Default configuration:")
        print(options.get_alphanumeric_commands())

        # Example valid configuration - custom
        options = AngularDistributionOptions(
            use_laboratory_cross_sections=True,
            use_center_of_mass_cross_sections=False,
            prepare_legendre_coefficients_in_endf_format=True,
            omit_finite_size_corrections=True,
        )
        print("Custom configuration:")
        print(options.get_alphanumeric_commands())

        # Example with mutually exclusive error
        options = AngularDistributionOptions(
            use_laboratory_cross_sections=True,
            use_center_of_mass_cross_sections=True,  # This should fail
        )
    except ValueError as e:
        print(f"Validation error: {e}")
