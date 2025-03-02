from pydantic import BaseModel, Field
from typing import ClassVar

"""
    These notes are taken from the SAMMY manual. 
    -  * denotes a default options
    - Mutually exclusive options are grouped together starting with ------ and ending with ------
    - options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]
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
    """Model to enforce mutually exclusive selection of multiple scattering corrections options using boolean flags."""
    
    # Boolean flags for mutual exclusivity
    do_not_include_self_shielding: bool = Field(default=True, description="DO NOT INCLUDE SELF-shielding multiple-scattering corrections")
    use_self_shielding_only: bool = Field(default=False, description="USE SELF SHIELDING Only no scattering")
    use_single_scattering_plus_self_shielding: bool = Field(default=False, description="USE SINGLE SCATTERINg plus self shielding")
    include_double_scattering_corrections: bool = Field(default=False, description="INCLUDE DOUBLE SCATTering corrections")
    infinite_slab: bool = Field(default=False, description="INFINITE SLAB")
    finite_slab: bool = Field(default=True, description="FINITE SLAB")
    make_new_file_with_edge_effects: bool = Field(default=True, description="MAKE NEW FILE WITH Edge effects")
    file_with_edge_effects_already_exists: bool = Field(default=False, description="FILE WITH EDGE EFFECts already exists")
    make_plot_file_of_multiple_scattering_pieces: bool = Field(default=False, description="MAKE PLOT FILE OF MUltiple scattering pieces")
    normalize_as_cross_section: bool = Field(default=False, description="NORMALIZE AS CROSS Section rather than yield")
    normalize_as_yield: bool = Field(default=False, description="NORMALIZE AS YIELD Rather than cross section")
    normalize_as_1_minus_e_sigma: bool = Field(default=False, description="NORMALIZE AS (1-E)SIgma")
    print_multiple_scattering_corrections: bool = Field(default=False, description="PRINT MULTIPLE SCATTering corrections")
    prepare_input_for_monte_carlo_simulation: bool = Field(default=False, description="PREPARE INPUT FOR MOnte carlo simulation")
    y2_values_are_tabulated: bool = Field(default=False, description="Y2 VALUES ARE TABULAted")
    use_quadratic_interpolation_for_y1: bool = Field(default=False, description="USE QUADRATIC INTERPolation for y1")
    use_linear_interpolation_for_y1: bool = Field(default=False, description="USE LINEAR INTERPOLAtion for y1")
    version_7_for_multiple_scattering: bool = Field(default=False, description="VERSION 7.0.0 FOR Multiple scattering")
    do_not_calculate_y0: bool = Field(default=False, description="DO NOT CALCULATE Y0")

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: ClassVar[list[list[str]]] = [
        ["do_not_include_self_shielding", "use_self_shielding_only", "use_single_scattering_plus_self_shielding", "include_double_scattering_corrections"],
        ["infinite_slab", "finite_slab"],
        ["make_new_file_with_edge_effects", "file_with_edge_effects_already_exists"],
        ["normalize_as_cross_section", "normalize_as_yield", "normalize_as_1_minus_e_sigma"],
        ["use_quadratic_interpolation_for_y1", "use_linear_interpolation_for_y1"]
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
                        self.__dict__[option] = False
        self.__dict__[name] = value

    def get_alphanumeric_commands(self):
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.do_not_include_self_shielding:
            commands.append("DO NOT INCLUDE SELF-shielding multiple-scattering corrections")
        if self.use_self_shielding_only:
            commands.append("USE SELF SHIELDING Only no scattering")
        if self.use_single_scattering_plus_self_shielding:
            commands.append("USE SINGLE SCATTERINg plus self shielding")
        if self.include_double_scattering_corrections:
            commands.append("INCLUDE DOUBLE SCATTering corrections")
        if self.infinite_slab:
            commands.append("INFINITE SLAB")
        if self.finite_slab:
            commands.append("FINITE SLAB")
        if self.make_new_file_with_edge_effects:
            commands.append("MAKE NEW FILE WITH Edge effects")
        if self.file_with_edge_effects_already_exists:
            commands.append("FILE WITH EDGE EFFECts already exists")
        if self.make_plot_file_of_multiple_scattering_pieces:
            commands.append("MAKE PLOT FILE OF MUltiple scattering pieces")
        if self.normalize_as_cross_section:
            commands.append("NORMALIZE AS CROSS Section rather than yield")
        if self.normalize_as_yield:
            commands.append("NORMALIZE AS YIELD Rather than cross section")
        if self.normalize_as_1_minus_e_sigma:
            commands.append("NORMALIZE AS (1-E)SIgma")
        if self.print_multiple_scattering_corrections:
            commands.append("PRINT MULTIPLE SCATTering corrections")
        if self.prepare_input_for_monte_carlo_simulation:
            commands.append("PREPARE INPUT FOR MOnte carlo simulation")
        if self.y2_values_are_tabulated:
            commands.append("Y2 VALUES ARE TABULAted")
        if self.use_quadratic_interpolation_for_y1:
            commands.append("USE QUADRATIC INTERPolation for y1")
        if self.use_linear_interpolation_for_y1:
            commands.append("USE LINEAR INTERPOLAtion for y1")
        if self.version_7_for_multiple_scattering:
            commands.append("VERSION 7.0.0 FOR Multiple scattering")
        if self.do_not_calculate_y0:
            commands.append("DO NOT CALCULATE Y0")
        return commands

    def check_exclusivity(self):
        """Ensure that only one multiple scattering corrections option is selected using boolean flags."""
        for group in self.mutually_exclusive_groups:
            selected_flags = [key for key in group if getattr(self, key)]
            if len(selected_flags) > 1:
                raise ValueError(f"Only one option can be selected from the group: {selected_flags}")

# Example usage
try:
    options = MultipleScatteringCorrectionsOptions(
        do_not_include_self_shielding=True,
        use_self_shielding_only=True  # This will automatically switch off do_not_include_self_shielding
    )
except ValueError as e:
    print(e)