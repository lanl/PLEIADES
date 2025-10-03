from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

        Multiple scattering corrections
        Define how the multiple-scattering corrections are to proceed
        multiple_scattering_corrections_options = [
        ----------------------------
        *   ["DO NOT INCLUDE SELF-shielding multiple-scattering corrections","NO SELF-SHIELDING ANd multiple-scattering corrections"],
            ["USE SELF SHIELDING Only no scattering","SELF SHIELD","INCLUDE ONLY SELF SHielding and not Multiple scattering"],
            ["USE SINGLE SCATTERINg plus self shielding","SINGLE"],
            ["INCLUDE DOUBLE SCATTering corrections","USE MULTIPLE SCATTERing plus single scattering","DOUBLE","MULTIPLE"],
        ----------------------------
            ["INFINITE SLAB","NO FINITE-SIZE CORREctions to single scattering"],
        *   ["FINITE SLAB","FINITE SIZE CORRECTIons to single scattering"],
        ----------------------------
        *   "MAKE NEW FILE WITH Edge effects",
            "FILE WITH EDGE EFFECts already exists",
        ----------------------------
            "MAKE PLOT FILE OF MUltiple scattering pieces",
        ----------------------------
            ["NORMALIZE AS CROSS Section rather than yield","CROSS SECTION"],
            ["NORMALIZE AS YIELD Rather than cross section","YIELD"],
            "NORMALIZE AS (1-E)SIgma",
        ----------------------------
            "PRINT MULTIPLE SCATTering corrections",
            ["PREPARE INPUT FOR MOnte carlo simulation","MONTE CARLO"],
            "Y2 VALUES ARE TABULAted",
        ----------------------------
            "USE QUADRATIC INTERPolation for y1",
            "USE LINEAR INTERPOLAtion for y1",
        ----------------------------
            ["VERSION 7.0.0 FOR Multiple scattering","V7"],
        ----------------------------
            "DO NOT CALCULATE Y0"
        ]

"""


class MultipleScatteringCorrectionsOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    do_not_include_self_shielding: bool = Field(
        default=True, description="DO NOT INCLUDE SELF-shielding multiple-scattering corrections"
    )
    use_self_shielding_only: bool = Field(default=False, description="USE SELF SHIELDING Only no scattering")
    use_single_scattering_plus_self_shielding: bool = Field(
        default=False, description="USE SINGLE SCATTERINg plus self shielding"
    )
    include_double_scattering_corrections: bool = Field(
        default=False, description="INCLUDE DOUBLE SCATTering corrections"
    )
    infinite_slab: bool = Field(default=False, description="INFINITE SLAB")
    finite_slab: bool = Field(default=True, description="FINITE SLAB")
    make_new_file_with_edge_effects: bool = Field(default=True, description="MAKE NEW FILE WITH Edge effects")
    file_with_edge_effects_already_exists: bool = Field(
        default=False, description="FILE WITH EDGE EFFECts already exists"
    )
    make_plot_file_of_multiple_scattering_pieces: bool = Field(
        default=False, description="MAKE PLOT FILE OF MUltiple scattering pieces"
    )
    normalize_as_cross_section: bool = Field(default=False, description="NORMALIZE AS CROSS Section rather than yield")
    normalize_as_yield: bool = Field(default=False, description="NORMALIZE AS YIELD Rather than cross section")
    normalize_as_1_minus_e_sigma: bool = Field(default=False, description="NORMALIZE AS (1-E)SIgma")
    print_multiple_scattering_corrections: bool = Field(
        default=False, description="PRINT MULTIPLE SCATTering corrections"
    )
    prepare_input_for_monte_carlo_simulation: bool = Field(
        default=False, description="PREPARE INPUT FOR MOnte carlo simulation"
    )
    y2_values_are_tabulated: bool = Field(default=False, description="Y2 VALUES ARE TABULAted")
    use_quadratic_interpolation_for_y1: bool = Field(default=False, description="USE QUADRATIC INTERPolation for y1")
    use_linear_interpolation_for_y1: bool = Field(default=False, description="USE LINEAR INTERPOLAtion for y1")
    version_7_for_multiple_scattering: bool = Field(default=False, description="VERSION 7.0.0 FOR Multiple scattering")
    do_not_calculate_y0: bool = Field(default=False, description="DO NOT CALCULATE Y0")

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        [
            "do_not_include_self_shielding",
            "use_self_shielding_only",
            "use_single_scattering_plus_self_shielding",
            "include_double_scattering_corrections",
        ],
        ["infinite_slab", "finite_slab"],
        ["make_new_file_with_edge_effects", "file_with_edge_effects_already_exists"],
        ["make_plot_file_of_multiple_scattering_pieces"],
        ["normalize_as_cross_section", "normalize_as_yield", "normalize_as_1_minus_e_sigma"],
        [
            "print_multiple_scattering_corrections",
            "prepare_input_for_monte_carlo_simulation",
            "y2_values_are_tabulated",
        ],
        ["use_quadratic_interpolation_for_y1", "use_linear_interpolation_for_y1"],
        ["version_7_for_multiple_scattering"],
        ["do_not_calculate_y0"],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "MultipleScatteringCorrectionsOptions":
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
        if self.do_not_include_self_shielding:
            commands.append("DO NOT INCLUDE SELF-SHIELDING MULTIPLE-SCATTERING CORRECTIONS")
        if self.use_self_shielding_only:
            commands.append("USE SELF SHIELDING ONLY NO SCATTERING")
        if self.use_single_scattering_plus_self_shielding:
            commands.append("USE SINGLE SCATTERING PLUS SELF SHIELDING")
        if self.include_double_scattering_corrections:
            commands.append("INCLUDE DOUBLE SCATTERING CORRECTIONS")
        if self.infinite_slab:
            commands.append("INFINITE SLAB")
        if self.finite_slab:
            commands.append("FINITE SLAB")
        if self.make_new_file_with_edge_effects:
            commands.append("MAKE NEW FILE WITH EDGE EFFECTS")
        if self.file_with_edge_effects_already_exists:
            commands.append("FILE WITH EDGE EFFECTS ALREADY EXISTS")
        if self.make_plot_file_of_multiple_scattering_pieces:
            commands.append("MAKE PLOT FILE OF MULTIPLE SCATTERING PIECES")
        if self.normalize_as_cross_section:
            commands.append("NORMALIZE AS CROSS SECTION RATHER THAN YIELD")
        if self.normalize_as_yield:
            commands.append("NORMALIZE AS YIELD RATHER THAN CROSS SECTION")
        if self.normalize_as_1_minus_e_sigma:
            commands.append("NORMALIZE AS (1-E)SIGMA")
        if self.print_multiple_scattering_corrections:
            commands.append("PRINT MULTIPLE SCATTERING CORRECTIONS")
        if self.prepare_input_for_monte_carlo_simulation:
            commands.append("PREPARE INPUT FOR MONTE CARLO SIMULATION")
        if self.y2_values_are_tabulated:
            commands.append("Y2 VALUES ARE TABULATED")
        if self.use_quadratic_interpolation_for_y1:
            commands.append("USE QUADRATIC INTERPOLATION FOR Y1")
        if self.use_linear_interpolation_for_y1:
            commands.append("USE LINEAR INTERPOLATION FOR Y1")
        if self.version_7_for_multiple_scattering:
            commands.append("VERSION 7.0.0 FOR MULTIPLE SCATTERING")
        if self.do_not_calculate_y0:
            commands.append("DO NOT CALCULATE Y0")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        options = MultipleScatteringCorrectionsOptions(
            do_not_include_self_shielding=True,
            use_self_shielding_only=True,  # This should raise a ValueError
        )
    except ValueError as e:
        print(e)
