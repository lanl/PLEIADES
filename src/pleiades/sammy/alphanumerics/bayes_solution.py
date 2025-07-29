from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

"""
    These notes are taken from the SAMMY manual.
    -   * denotes a default options
    -   Mutually exclusive options are grouped together starting with -------------- and ending with -------------
    -   options can be written out multiple ways indicated with ["Default","Alternate 1","Alternate 2"]

    -   Bayes solution options
    -   Define details of the fitting procedure
        bayes_solution_options = [
            ----------------------------
            *   "SOLVE BAYES EQUATIONs",
                "DO NOT SOLVE BAYES Equations",
            ----------------------------
            *   "LET SAMMY CHOOSE WHIch inversion scheme to use",
                "USE (N+V) INVERSION scheme" or "NPV",
                "USE (I+Q) INVERSION scheme" or "IPQ",
                "USE (M+W) INVERSION scheme" or "MPW",
            ----------------------------
                "USE LEAST SQUARES TO define prior parameter covariance matrix",
            ----------------------------
                "TAKE BABY STEPS WITH least-squares method",
            ----------------------------
                "REMEMBER ORIGINAL PArameter values",
            ----------------------------
                "USE REMEMBERED ORIGInal parameter values"
            ----------------------------
            ]
"""


class BayesSolutionOptions(BaseModel):
    model_config = ConfigDict(validate_default=True)

    # Bayes equation solving options
    solve_bayes_equations: bool = Field(default=True, description="SOLVE BAYES EQUATIONs")
    do_not_solve_bayes_equations: bool = Field(default=False, description="DO NOT SOLVE BAYES Equations")

    # Inversion scheme options
    let_sammy_choose_which_inversion_scheme_to_use: bool = Field(
        default=True, description="LET SAMMY CHOOSE WHIch inversion scheme to use"
    )
    use_npv_inversion_scheme: bool = Field(default=False, description="USE (N+V) INVERSION scheme")
    use_ipq_inversion_scheme: bool = Field(default=False, description="USE (I+Q) INVERSION scheme")
    use_mpw_inversion_scheme: bool = Field(default=False, description="USE (M+W) INVERSION scheme")

    # Special fitting options
    use_least_squares_to_define_prior_parameter_covariance_matrix: bool = Field(
        default=False, description="USE LEAST SQUARES TO define prior parameter covariance matrix"
    )
    take_baby_steps_with_least_squares_method: bool = Field(
        default=False, description="TAKE BABY STEPS WITH least-squares method"
    )
    remember_original_parameter_values: bool = Field(default=False, description="REMEMBER ORIGINAL PArameter values")
    use_remembered_original_parameter_values: bool = Field(
        default=False, description="USE REMEMBERED ORIGInal parameter values"
    )

    # Mutually exclusive groups
    mutually_exclusive_groups: List[List[str]] = [
        # Group 1: Bayes equation solving options
        ["solve_bayes_equations", "do_not_solve_bayes_equations"],
        # Group 2: Inversion scheme options
        [
            "let_sammy_choose_which_inversion_scheme_to_use",
            "use_npv_inversion_scheme",
            "use_ipq_inversion_scheme",
            "use_mpw_inversion_scheme",
        ],
        # Single-option groups
        ["use_least_squares_to_define_prior_parameter_covariance_matrix"],
        ["take_baby_steps_with_least_squares_method"],
        ["remember_original_parameter_values"],
        ["use_remembered_original_parameter_values"],
    ]

    @model_validator(mode="after")
    def enforce_exclusivity(self) -> "BayesSolutionOptions":
        """
        Validate mutually exclusive fields - only one option from each group can be True.
        If a user explicitly sets an option, it overrides any default in the same group.
        """
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

        # Bayes equation solving options
        if self.solve_bayes_equations:
            commands.append("SOLVE BAYES EQUATIONS")
        if self.do_not_solve_bayes_equations:
            commands.append("DO NOT SOLVE BAYES EQUATIONS")

        # Inversion scheme options
        if self.let_sammy_choose_which_inversion_scheme_to_use:
            commands.append("LET SAMMY CHOOSE WHICH INVERSION SCHEME TO USE")
        if self.use_npv_inversion_scheme:
            commands.append("USE (N+V) INVERSION SCHEME")
        if self.use_ipq_inversion_scheme:
            commands.append("USE (I+Q) INVERSION SCHEME")
        if self.use_mpw_inversion_scheme:
            commands.append("USE (M+W) INVERSION SCHEME")

        # Special fitting options
        if self.use_least_squares_to_define_prior_parameter_covariance_matrix:
            commands.append("USE LEAST SQUARES TO DEFINE PRIOR PARAMETER COVARIANCE MATRIX")
        if self.take_baby_steps_with_least_squares_method:
            commands.append("TAKE BABY STEPS WITH LEAST-SQUARES METHOD")
        if self.remember_original_parameter_values:
            commands.append("REMEMBER ORIGINAL PARAMETER VALUES")
        if self.use_remembered_original_parameter_values:
            commands.append("USE REMEMBERED ORIGINAL PARAMETER VALUES")

        return commands


# Example usage
if __name__ == "__main__":
    try:
        options = BayesSolutionOptions(
            solve_bayes_equations=True,
            let_sammy_choose_which_inversion_scheme_to_use=True,
            use_least_squares_to_define_prior_parameter_covariance_matrix=True,
            take_baby_steps_with_least_squares_method=True,
            remember_original_parameter_values=True,
            use_remembered_original_parameter_values=True,
        )
    except ValueError as e:
        print(e)
