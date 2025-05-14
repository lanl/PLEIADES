from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    Plot file control options = [
    ----------------------------
        "EV = UNITS ON ENERGY in plot file",
        "KEV = UNITS ON ENERGy in plot file",
        "MEV = UNITS ON ENERGy in plot file",
    ----------------------------
        "ODF FILE IS WANTED-- XXXXXX.XXX,ZEROth order",
        "ODF FILE IS WANTED-- XXXXXX.XXX,FINAl calcul",
    ----------------------------
        "DO NOT GENERATE PLOT file automatically", *
        "GENERATE PLOT FILE Automatically",
    ----------------------------
        "DO NOT INCLUDE THEORetical uncertainties", *
        "INCLUDE THEORETICAL uncertainties in Plot fi",
    ----------------------------
        "PLOT UNBROADENED CROss sections",
    ----------------------------
    ]
"""


class PlotFileOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # Energy units options (mutually exclusive)
    ev_units_on_energy_in_plot_file: bool = Field(
        default=False,
        description="Energies in plot file are in eV (Default if Emax < 1 keV, Angular distribution plots always use eV)",
    )
    kev_units_on_energy_in_plot_file: bool = Field(
        default=False,
        description="Energies in plot file are in keV (Default if Emax > 1 keV, Angular distribution plots always use eV)",
    )
    mev_units_on_energy_in_plot_file: bool = Field(
        default=False,
        description="Energies in plot file are in MeV (Angular distribution plots always use eV)",
    )

    # ODF file options
    odf_file_is_wanted_zeroth_order: bool = Field(
        default=False,
        description="(Largely obsolete) Specify ODF output filename for zeroth order calculation",
    )
    odf_file_is_wanted_final_calculation: bool = Field(
        default=False,
        description="(Largely obsolete) Specify ODF output filename for final calculation",
    )

    # Plot generation options (mutually exclusive)
    do_not_generate_plot_file_automatically: bool = Field(
        default=True,
        description="Do not automatically create SAMMY.ODF, SAMMY.LST, SAMMY.PLT (Default)",
    )
    generate_plot_file_automatically: bool = Field(
        default=False,
        description="Automatically create SAMMY.ODF (plot file), SAMMY.LST (ASCII), SAMMY.PLT (binary) with results",
    )

    # Theoretical uncertainties options (mutually exclusive)
    do_not_include_theoretical_uncertainties: bool = Field(
        default=True,
        description="Do not include theoretical uncertainties (ΔTi) in plot file (Default)",
    )
    include_theoretical_uncertainties_in_plot_file: bool = Field(
        default=False,
        description="Include theoretical uncertainties (ΔTi from parameter covariance) in plot file",
    )

    # Additional plot options
    plot_unbroadened_cross_sections: bool = Field(
        default=False,
        description="Create SAMMY.UNB (ODF), SAMUNB.DAT (ASCII TWENTY), SAMUNX.DAT (ASCII CSISRS) with unbroadened cross sections",
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        [
            "ev_units_on_energy_in_plot_file",
            "kev_units_on_energy_in_plot_file",
            "mev_units_on_energy_in_plot_file",
        ],
        [
            "do_not_generate_plot_file_automatically",
            "generate_plot_file_automatically",
        ],
        [
            "do_not_include_theoretical_uncertainties",
            "include_theoretical_uncertainties_in_plot_file",
        ],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "PlotFileOptions":
        """Validate mutually exclusive fields."""
        # Check Energy units options (mutually exclusive)
        energy_units_selected = 0
        if self.ev_units_on_energy_in_plot_file:
            energy_units_selected += 1
        if self.kev_units_on_energy_in_plot_file:
            energy_units_selected += 1
        if self.mev_units_on_energy_in_plot_file:
            energy_units_selected += 1

        if energy_units_selected > 1:
            raise ValueError("Only one of EV, KEV, or MEV units can be enabled for plot file energy units")

        # Check Plot generation options (mutually exclusive)
        if self.do_not_generate_plot_file_automatically and self.generate_plot_file_automatically:
            raise ValueError(
                "DO NOT GENERATE PLOT FILE AUTOMATICALLY and GENERATE PLOT FILE AUTOMATICALLY cannot both be enabled"
            )

        # Check Theoretical uncertainties options (mutually exclusive)
        if self.do_not_include_theoretical_uncertainties and self.include_theoretical_uncertainties_in_plot_file:
            raise ValueError(
                "DO NOT INCLUDE THEORETICAL UNCERTAINTIES and INCLUDE THEORETICAL UNCERTAINTIES IN PLOT FILE cannot both be enabled"
            )

        return self

    def get_alphanumeric_commands(self) -> List[str]:
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []
        if self.ev_units_on_energy_in_plot_file:
            commands.append("EV = UNITS ON ENERGY IN PLOT FILE")
        if self.kev_units_on_energy_in_plot_file:
            commands.append("KEV = UNITS ON ENERGY IN PLOT FILE")
        if self.mev_units_on_energy_in_plot_file:
            commands.append("MEV = UNITS ON ENERGY IN PLOT FILE")
        if self.odf_file_is_wanted_zeroth_order:
            commands.append("ODF FILE IS WANTED-- ZEROTH ORDER")
        if self.odf_file_is_wanted_final_calculation:
            commands.append("ODF FILE IS WANTED-- FINAL CALCULATION")
        if self.do_not_generate_plot_file_automatically:
            commands.append("DO NOT GENERATE PLOT FILE AUTOMATICALLY")
        if self.generate_plot_file_automatically:
            commands.append("GENERATE PLOT FILE AUTOMATICALLY")
        if self.do_not_include_theoretical_uncertainties:
            commands.append("DO NOT INCLUDE THEORETICAL UNCERTAINTIES")
        if self.include_theoretical_uncertainties_in_plot_file:
            commands.append("INCLUDE THEORETICAL UNCERTAINTIES IN PLOT FILE")
        if self.plot_unbroadened_cross_sections:
            commands.append("PLOT UNBROADENED CROSS SECTIONS")
        return commands


# Example usage
if __name__ == "__main__":
    try:
        # Example valid configuration
        options = PlotFileOptions(
            ev_units_on_energy_in_plot_file=True,
            generate_plot_file_automatically=True,
            do_not_generate_plot_file_automatically=False,
            include_theoretical_uncertainties_in_plot_file=True,
            do_not_include_theoretical_uncertainties=False,
            plot_unbroadened_cross_sections=True,
        )
        print("Valid configuration:")
        print(options.get_alphanumeric_commands())

        # Example with mutually exclusive error
        options = PlotFileOptions(
            ev_units_on_energy_in_plot_file=True,
            kev_units_on_energy_in_plot_file=True,  # This should fail
        )
    except ValueError as e:
        print(f"Validation error: {e}")
