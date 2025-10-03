from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with ------ and ending with ------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    Special Analysis Options (UIDs 170-190) = [
    ----------------------------
        "RECONSTRUCT CROSS SECTION FROM RESONANCE PARAMETERS",
        "ARTIFICIAL ENERGY GRID IS NEEDED",
        "RELEVANT PARAMETERS ARE CHOSEN VIA UNCERTAINTIES",
        "CROSS SECTION COVARIANCE MATRIX IS WANTED",
        "INITIAL UNCERTAINTY MULTIPLIER = value",
        "FINAL UNCERTAINTY MULTIPLIER = value",
        "E-DEPENDENT INITIAL UNCERTAINTY MULTIPLIER",
        "SUMMED STRENGTH FUNCTION IS WANTED",
        "GENERATE PARTIAL DERIVATIVES ONLY",
        "GENERATE SPIN GROUP CROSS SECTIONS",
        "REFORMULATE DATA FOR IMPLICIT DATA COVARIANCE",
        "COMPARE EXPERIMENT TO THEORY",
    ----------------------------
        "GENERATE Y AND W MATRICES",
        "READ Y AND W MATRICES",
    ----------------------------
        "STOP abc n",
        "WRITE CALCULATED CROSS SECTIONS INTO ASCII",
    ----------------------------
        "UNIFORM ENERGY GRID",
        "UNIFORM VELOCITY GRID",
        "UNIFORM TIME GRID",
    ----------------------------
        "CREATE PUBLISHABLE LIST OF PARAMETERS",
        "DO NOT TEST FOR EIGENVALUES",
    ----------------------------
    ]
"""


class SpecialAnalysisOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # UID 170
    reconstruct_cross_section: bool = Field(
        default=False,
        description="Automatically choose energy grid and evaluate total, elastic, capture, "
        "fission cross sections (NJOY method). (No experimental grid needed).",
    )

    # UID 171
    artificial_energy_grid: bool = Field(
        default=False,
        description="Automatically choose auxiliary grid based on NEPNTS, EMIN, EMAX "
        "(uniform in velocity space), then add points for structure. (No experimental grid needed).",
    )

    # UID 172
    relevant_parameters_via_uncertainty: bool = Field(
        default=False,
        description="Solve Bayes' once, choose relevant R-matrix parameters based on uncertainty ratio, "
        "create SAMMY.REL with only relevant parameters flagged.",
    )

    # UID 173
    cross_section_covariance_matrix: bool = Field(
        default=False,
        description="Calculate and print point-wise cross section covariance matrix to SAMMY.LPT "
        "and SAMCOV.PUB. (No-Bayes run).",
    )

    # UID 174
    initial_uncertainty_multiplier: Optional[float] = Field(
        default=None,
        description="Multiply all prior parameter uncertainties by the specified value.",
    )

    # UID 175
    final_uncertainty_multiplier: Optional[float] = Field(
        default=None,
        description="Multiply all output parameter uncertainties by the specified value. (Discouraged).",
    )

    # UID 176
    e_dependent_initial_uncertainty: bool = Field(
        default=False,
        description="Multiply prior parameter uncertainties by an energy- and spin-group-dependent "
        "multiplier from EDU file.",
    )

    # UID 177
    summed_strength_function: bool = Field(
        default=False,
        description="Evaluate and print summed strength function and its covariance matrix. "
        "COVariance file needed as input.",
    )

    # UID 178
    generate_partial_derivatives_only: bool = Field(
        default=False,
        description="Assume all and only resonance parameters are varied, do not solve Bayes', "
        "write partial derivatives of theory to SAMMY.PDS.",
    )

    # UID 179
    generate_spin_group_cross_sections: bool = Field(
        default=False,
        description="Output ODF file with unbroadened total cross section and contributions "
        "from each spin group on auxiliary grid.",
    )

    # UID 180
    reformulate_data_for_idc: bool = Field(
        default=False,
        description="Create SAMMY.DA2 (corrected data), SAMMY.IDC (norm/bkgd info), "
        "SAMMY.PA2 (params w/o norm/bkgd) for IDC use.",
    )

    # UID 181
    compare_experiment_to_theory: bool = Field(
        default=False,
        description="Output SAM53.DAT for SAMCPR to compare SAMMY calculations with other "
        '"experimental" data (e.g., from another code).',
    )

    # UID 182 and 183 (mutually exclusive)
    generate_y_and_w_matrices: bool = Field(
        default=False,
        description="For M+W simultaneous fit, generate Yi and Wi sub-matrices for the current "
        "dataset and store in SAMMY.YWY.",
    )

    read_y_and_w_matrices: bool = Field(
        default=False,
        description="For M+W simultaneous fit, read Yi and Wi sub-matrices from files (specified "
        "in interactive input) and solve Bayes'.",
    )

    # UID 184
    stop_command: Optional[str] = Field(
        default=None,
        description="Cease execution prior to nth occurrence of segment `abc`. Format: 'abc n'. "
        "(Debug/Monte Carlo prep).",
    )

    # UID 185
    write_calculated_cross_sections: bool = Field(
        default=False,
        description="Write energies and theoretical values to SAMTHE.DAT (2F20.10 format).",
    )

    # UID 186, 187, 188 (mutually exclusive)
    uniform_energy_grid: bool = Field(
        default=False,
        description='Create an "experimental" energy grid of NEPNTS points uniformly spaced in '
        "energy E. (Testing only, no-Bayes runs).",
    )

    uniform_velocity_grid: bool = Field(
        default=False,
        description='Create an "experimental" energy grid of NEPNTS points uniformly spaced in '
        "velocity (sqrt(E)). (Testing only, no-Bayes runs).",
    )

    uniform_time_grid: bool = Field(
        default=False,
        description='Create an "experimental" energy grid of NEPNTS points uniformly spaced in '
        "time (1/sqrt(E)). (Testing only, no-Bayes runs).",
    )

    # UID 189
    create_publishable_list: bool = Field(
        default=False,
        description="Create SAMMY.PUB file with resonance parameters and uncertainties, "
        "tab-separated for spreadsheets.",
    )

    # UID 190
    do_not_test_for_eigenvalues: bool = Field(
        default=False,
        description="Do not test if parameter covariance matrix is positive-definite.",
    )

    # Define mutually exclusive groups as a class attribute
    mutually_exclusive_groups: List[List[str]] = [
        [
            "generate_y_and_w_matrices",
            "read_y_and_w_matrices",
        ],
        [
            "uniform_energy_grid",
            "uniform_velocity_grid",
            "uniform_time_grid",
        ],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "SpecialAnalysisOptions":
        """Validate mutually exclusive fields."""
        # Y and W matrices options are mutually exclusive
        if self.generate_y_and_w_matrices and self.read_y_and_w_matrices:
            raise ValueError("GENERATE Y AND W MATRICES and READ Y AND W MATRICES cannot both be enabled")

        # Uniform grid options are mutually exclusive
        grid_options = [
            self.uniform_energy_grid,
            self.uniform_velocity_grid,
            self.uniform_time_grid,
        ]
        if sum(grid_options) > 1:
            raise ValueError(
                "Only one of UNIFORM ENERGY GRID, UNIFORM VELOCITY GRID, or UNIFORM TIME GRID can be enabled"
            )

        return self

    def get_alphanumeric_commands(self) -> List[str]:
        """Return the list of alphanumeric commands based on the selected options."""
        commands = []

        # UID 170
        if self.reconstruct_cross_section:
            commands.append("RECONSTRUCT CROSS SECTION FROM RESONANCE PARAMETERS")

        # UID 171
        if self.artificial_energy_grid:
            commands.append("ARTIFICIAL ENERGY GRID IS NEEDED")

        # UID 172
        if self.relevant_parameters_via_uncertainty:
            commands.append("RELEVANT PARAMETERS ARE CHOSEN VIA UNCERTAINTIES")

        # UID 173
        if self.cross_section_covariance_matrix:
            commands.append("CROSS SECTION COVARIANCE MATRIX IS WANTED")

        # UID 174
        if self.initial_uncertainty_multiplier is not None:
            commands.append(f"INITIAL UNCERTAINTY MULTIPLIER = {self.initial_uncertainty_multiplier}")

        # UID 175
        if self.final_uncertainty_multiplier is not None:
            commands.append(f"FINAL UNCERTAINTY MULTIPLIER = {self.final_uncertainty_multiplier}")

        # UID 176
        if self.e_dependent_initial_uncertainty:
            commands.append("E-DEPENDENT INITIAL UNCERTAINTY MULTIPLIER")

        # UID 177
        if self.summed_strength_function:
            commands.append("SUMMED STRENGTH FUNCTION IS WANTED")

        # UID 178
        if self.generate_partial_derivatives_only:
            commands.append("GENERATE PARTIAL DERIVATIVES ONLY")

        # UID 179
        if self.generate_spin_group_cross_sections:
            commands.append("GENERATE SPIN GROUP CROSS SECTIONS")

        # UID 180
        if self.reformulate_data_for_idc:
            commands.append("REFORMULATE DATA FOR IMPLICIT DATA COVARIANCE")

        # UID 181
        if self.compare_experiment_to_theory:
            commands.append("COMPARE EXPERIMENT TO THEORY")

        # UID 182
        if self.generate_y_and_w_matrices:
            commands.append("GENERATE Y AND W MATRICES")

        # UID 183
        if self.read_y_and_w_matrices:
            commands.append("READ Y AND W MATRICES")

        # UID 184
        if self.stop_command:
            commands.append(f"STOP {self.stop_command}")

        # UID 185
        if self.write_calculated_cross_sections:
            commands.append("WRITE CALCULATED CROSS SECTIONS INTO ASCII")

        # UID 186
        if self.uniform_energy_grid:
            commands.append("UNIFORM ENERGY GRID")

        # UID 187
        if self.uniform_velocity_grid:
            commands.append("UNIFORM VELOCITY GRID")

        # UID 188
        if self.uniform_time_grid:
            commands.append("UNIFORM TIME GRID")

        # UID 189
        if self.create_publishable_list:
            commands.append("CREATE PUBLISHABLE LIST OF PARAMETERS")

        # UID 190
        if self.do_not_test_for_eigenvalues:
            commands.append("DO NOT TEST FOR EIGENVALUES")

        return commands


# Example usage
if __name__ == "__main__":
    try:
        # Example valid configuration
        options = SpecialAnalysisOptions(
            reconstruct_cross_section=True,
            cross_section_covariance_matrix=True,
            initial_uncertainty_multiplier=1.5,
            summed_strength_function=True,
            create_publishable_list=True,
        )
        print("Valid configuration:")
        print(options.get_alphanumeric_commands())

        # Example with mutually exclusive error
        options = SpecialAnalysisOptions(
            generate_y_and_w_matrices=True,
            read_y_and_w_matrices=True,  # This should fail
        )
    except ValueError as e:
        print(f"Validation error: {e}")
