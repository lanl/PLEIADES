from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    Averaging options = [
    ----------------------------
        "AVERAGE OVER ENERGY Ranges",
        "GROUP AVERAGE OVER Energy ranges",
        "ENERGY AVERAGE USING constant flux",
    ----------------------------
        "MAXWELLIAN-AVERAGED capture cross sections",
        "CALCULATE MAXWELLIAN averages after reconstr",
        "MAKE NO CORRECTIONS to theoretical values",
        "ADD CROSS SECTIONS From endf/b file 3",
        "PRINT AVERAGED SENSItivities for endf parame",
    ----------------------------
    ]
"""


class AveragesOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # Average type options (mutually exclusive)
    average_over_energy_ranges: bool = Field(
        default=False,
        description="Produce energy-averaged experimental and theoretical values (histogram-based, use with caution for theoretical)",
    )
    group_average_over_energy_ranges: bool = Field(
        default=False,
        description="Produce Bondarenko-weighted multigroup cross sections",
    )
    energy_average_using_constant_flux: bool = Field(
        default=False,
        description="Produce unweighted energy average of theoretical cross sections (constant flux)",
    )

    # Maxwellian average options
    maxwellian_averaged_capture_cross_sections: bool = Field(
        default=False,
        description="Generate stellar (Maxwellian) averaged capture cross sections",
    )
    calculate_maxwellian_averages_after_reconstruction: bool = Field(
        default=False,
        description="Calculate stellar averages using an energy grid reconstructed by SAMMY (NJOY method)",
    )

    # Additional averaging options
    make_no_corrections_to_theoretical_values: bool = Field(
        default=False,
        description="Do not perform Doppler/resolution broadening or apply normalization/backgrounds before averaging",
    )
    add_cross_sections_from_endf_b_file_3: bool = Field(
        default=False,
        description="For stellar averages, add smooth cross sections from an ENDF File 3 to resolved resonance calculation",
    )
    print_averaged_sensitivities_for_endf_parameters: bool = Field(
        default=False,
        description="Output SAMAVG.COV, SAMSEN.DAT, SAMMY.LLL, SAMMY.MGS for multigroup averages",
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        [
            "average_over_energy_ranges",
            "group_average_over_energy_ranges",
            "energy_average_using_constant_flux",
        ],
    ]

    @model_validator(mode="after")
    def validate_dependencies(self) -> "AveragesOptions":
        """Validate logical dependencies between options."""
        # Check mutual exclusivity of average types
        average_types_selected = 0
        if self.average_over_energy_ranges:
            average_types_selected += 1
        if self.group_average_over_energy_ranges:
            average_types_selected += 1
        if self.energy_average_using_constant_flux:
            average_types_selected += 1

        if average_types_selected > 1:
            raise ValueError(
                "Only one of AVERAGE OVER ENERGY RANGES, GROUP AVERAGE OVER ENERGY RANGES, "
                "or ENERGY AVERAGE USING CONSTANT FLUX can be enabled"
            )

        # Check if make_no_corrections_to_theoretical_values requires an average type
        if self.make_no_corrections_to_theoretical_values:
            if not (
                self.average_over_energy_ranges
                or self.group_average_over_energy_ranges
                or self.energy_average_using_constant_flux
            ):
                raise ValueError(
                    "MAKE NO CORRECTIONS TO THEORETICAL VALUES requires one of the average types to be enabled"
                )

        # Check if add_cross_sections_from_endf_b_file_3 requires a Maxwellian option
        if self.add_cross_sections_from_endf_b_file_3:
            if not (
                self.maxwellian_averaged_capture_cross_sections
                or self.calculate_maxwellian_averages_after_reconstruction
            ):
                raise ValueError(
                    "ADD CROSS SECTIONS FROM ENDF/B FILE 3 requires MAXWELLIAN-AVERAGED CAPTURE CROSS SECTIONS "
                    "or CALCULATE MAXWELLIAN AVERAGES AFTER RECONSTRUCTION to be enabled"
                )

        return self

    def get_alphanumeric_commands(self) -> List[str]:
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.average_over_energy_ranges:
            commands.append("AVERAGE OVER ENERGY RANGES")
        if self.group_average_over_energy_ranges:
            commands.append("GROUP AVERAGE OVER ENERGY RANGES")
        if self.energy_average_using_constant_flux:
            commands.append("ENERGY AVERAGE USING CONSTANT FLUX")
        if self.maxwellian_averaged_capture_cross_sections:
            commands.append("MAXWELLIAN-AVERAGED CAPTURE CROSS SECTIONS")
        if self.calculate_maxwellian_averages_after_reconstruction:
            commands.append("CALCULATE MAXWELLIAN AVERAGES AFTER RECONSTRUCTION")
        if self.make_no_corrections_to_theoretical_values:
            commands.append("MAKE NO CORRECTIONS TO THEORETICAL VALUES")
        if self.add_cross_sections_from_endf_b_file_3:
            commands.append("ADD CROSS SECTIONS FROM ENDF/B FILE 3")
        if self.print_averaged_sensitivities_for_endf_parameters:
            commands.append("PRINT AVERAGED SENSITIVITIES FOR ENDF PARAMETERS")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        # Example valid configuration
        options = AveragesOptions(
            average_over_energy_ranges=True,
            make_no_corrections_to_theoretical_values=True,
            print_averaged_sensitivities_for_endf_parameters=True,
        )
        print("Valid configuration:")
        print(options.get_alphanumeric_commands())

        # Example with mutually exclusive error
        options = AveragesOptions(
            average_over_energy_ranges=True,
            group_average_over_energy_ranges=True,  # This should fail
        )
    except ValueError as e:
        print(f"Validation error: {e}")
