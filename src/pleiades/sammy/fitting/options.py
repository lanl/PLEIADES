"""
This module defines the FitOptions class for configuring SAMMY fits.

SAMMY is a nuclear physics code that requires different configuration options.
The FitOptions class encapsulates these options and provides factory methods
for different modes of operation.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

# Import all alphanumerics classes from the central module
from pleiades.sammy.alphanumerics import (
    AngularDistributionOptions,
    AveragesOptions,
    BayesSolutionOptions,
    BroadeningOptions,
    CovarianceMatrixOptions,
    CovarianceMatrixOutputOptions,
    CrossSectionOptions,
    ENDFOptions,
    ExperimentalDataInputOptions,
    LPTOutputOptions,
    MultipleScatteringCorrectionsOptions,
    PCovarianceMatrixInOptions,
    PhysicalConstantsOptions,
    PlotFileOptions,
    QuantumNumbersOptions,
    RMatrixOptions,
    SpecialAnalysisOptions,
    URROptions,
)


class FitOptions(BaseModel):
    """Container for all fit options with SAMMY based on alphanumerics modules.

    This class uses the actual alphanumerics classes that implement validation,
    mutual exclusivity enforcement, and command generation.

    Attributes:
        r_matrix: Options for the R-matrix formalism
        quantum_numbers: Options for spin group and quantum numbers
        experimental_data: Options for data format
        broadening: Options for broadening calculations
        endf: Options for ENDF file usage
        bayes_solution: Options for Bayes fitting
        lpt_output: Options for LPT file output
        angular_distribution: Options for angular distributions
        averages: Options for energy averages
        data_covariance: Options for data covariance
        p_covariance_in: Options for parameter covariance input
        p_covariance_out: Options for parameter covariance output
        multiple_scattering: Options for multiple scattering corrections
        cross_section: Options for cross section calculations
        physical_constants: Options for physical constants
        plot_file: Options for plot file generation
        special_analysis: Options for special analysis
        urr: Options for unresolved resonance region
    """

    r_matrix: RMatrixOptions = Field(
        default_factory=RMatrixOptions, description="Options for R-matrix approximation and general calculations"
    )

    quantum_numbers: QuantumNumbersOptions = Field(
        default_factory=QuantumNumbersOptions, description="Options for spin group and quantum numbers parameters"
    )

    experimental_data: ExperimentalDataInputOptions = Field(
        default_factory=ExperimentalDataInputOptions, description="Options for experimental data format"
    )

    broadening: BroadeningOptions = Field(
        default_factory=BroadeningOptions, description="Options for broadening calculations"
    )

    endf: ENDFOptions = Field(default_factory=ENDFOptions, description="Options for ENDF file usage")

    bayes_solution: BayesSolutionOptions = Field(
        default_factory=BayesSolutionOptions, description="Options for Bayes fitting"
    )

    lpt_output: LPTOutputOptions = Field(default_factory=LPTOutputOptions, description="Options for LPT file output")

    angular_distribution: Optional[AngularDistributionOptions] = Field(
        default=None, description="Options for angular distributions"
    )

    averages: Optional[AveragesOptions] = Field(default=None, description="Options for energy averages")

    data_covariance: Optional[CovarianceMatrixOptions] = Field(
        default=None, description="Options for data covariance matrix"
    )

    p_covariance_in: Optional[PCovarianceMatrixInOptions] = Field(
        default=None, description="Options for parameter covariance matrix input"
    )

    p_covariance_out: Optional[CovarianceMatrixOutputOptions] = Field(
        default=None, description="Options for parameter covariance matrix output"
    )

    multiple_scattering: Optional[MultipleScatteringCorrectionsOptions] = Field(
        default=None, description="Options for multiple scattering corrections"
    )

    cross_section: Optional[CrossSectionOptions] = Field(
        default=None, description="Options for cross section calculations"
    )

    physical_constants: Optional[PhysicalConstantsOptions] = Field(
        default=None, description="Options for physical constants"
    )

    plot_file: Optional[PlotFileOptions] = Field(default=None, description="Options for plot file generation")

    special_analysis: Optional[SpecialAnalysisOptions] = Field(default=None, description="Options for special analysis")

    urr: Optional[URROptions] = Field(default=None, description="Options for unresolved resonance region")

    def get_alphanumeric_commands(self) -> List[str]:
        """Generate all SAMMY alphanumeric commands from constituent options.

        Returns:
            List[str]: List of all alphanumeric commands for SAMMY INP file
        """
        commands = []

        commands.extend(self.r_matrix.get_alphanumeric_commands())
        commands.extend(self.quantum_numbers.get_alphanumeric_commands())
        commands.extend(self.experimental_data.get_alphanumeric_commands())
        commands.extend(self.broadening.get_alphanumeric_commands())
        commands.extend(self.endf.get_alphanumeric_commands())
        commands.extend(self.bayes_solution.get_alphanumeric_commands())
        commands.extend(self.lpt_output.get_alphanumeric_commands())

        if self.angular_distribution:
            commands.extend(self.angular_distribution.get_alphanumeric_commands())
        if self.averages:
            commands.extend(self.averages.get_alphanumeric_commands())
        if self.data_covariance:
            commands.extend(self.data_covariance.get_alphanumeric_commands())
        if self.p_covariance_in:
            commands.extend(self.p_covariance_in.get_alphanumeric_commands())
        if self.p_covariance_out:
            commands.extend(self.p_covariance_out.get_alphanumeric_commands())
        if self.multiple_scattering:
            commands.extend(self.multiple_scattering.get_alphanumeric_commands())
        if self.cross_section:
            commands.extend(self.cross_section.get_alphanumeric_commands())
        if self.physical_constants:
            commands.extend(self.physical_constants.get_alphanumeric_commands())
        if self.plot_file:
            commands.extend(self.plot_file.get_alphanumeric_commands())
        if self.special_analysis:
            commands.extend(self.special_analysis.get_alphanumeric_commands())
        if self.urr:
            commands.extend(self.urr.get_alphanumeric_commands())

        return commands

    @classmethod
    def from_endf_config(cls) -> "FitOptions":
        """Create a FitOptions instance configured for ENDF extraction.

        ENDF mode is used for extracting resonance information from ENDF files
        without Bayesian fitting.

        Mandatory fields:
        - UID 12: PUT QUANTUM NUMBERS into parameter file
        - UID 15: INPUT IS ENDF/B FILE 2
        - UID 37: DATA ARE ENDF/B FILE
        - UID 103: DO NOT SOLVE BAYES Equations

        Optional field:
        - UID 16: USE ENERGY RANGE FROm endf/b file 2

        Returns:
            FitOptions: Instance configured for ENDF extraction
        """
        # Create with default options
        options = cls()

        # Configure for ENDF mode with mandatory fields
        options.quantum_numbers = QuantumNumbersOptions(put_quantum_numbers_into_parameter_file=True)
        options.endf = ENDFOptions(
            input_is_endf_file_2=True,
            use_energy_range_from_endf_file_2=True,  # Optional field
        )
        options.experimental_data = ExperimentalDataInputOptions(data_are_endf_b_file=True)
        options.bayes_solution = BayesSolutionOptions(
            solve_bayes_equations=False,  # Set solve_bayes_equations to False
            do_not_solve_bayes_equations=True,  # Explicitly set the opposite flag to generate the command
        )

        return options

    @classmethod
    def from_fitting_config(cls) -> "FitOptions":
        """Create a FitOptions instance configured for Bayesian fitting.

        Fitting mode is used for customized Bayesian fitting of nuclear data.

        Mandatory fields:
        - UID 2: REICH-MOORE FORMALISm is wanted
        - UID 10: KEY-WORD PARTICLE-PAir definitions are given
        - UID 11: QUANTUM NUMBERS ARE in parameter file
        - UID 34: USE TWENTY SIGNIFICAnt digits
        - UID 61: BROADENING IS NOT WAnted (or 60 is wanted)
        - UID 102: SOLVE BAYES EQUATIONs
        - UID 133: CHI SQUARED IS WANTEd

        Optional fields depend on specific use case.

        Returns:
            FitOptions: Instance configured for Bayesian fitting
        """
        # Create with default options
        options = cls()

        # Configure for Fitting mode with mandatory fields
        options.r_matrix = RMatrixOptions(reich_moore=True)
        options.quantum_numbers = QuantumNumbersOptions(
            keyword_particle_pair_definitions=True, quantum_numbers_in_parameter_file=True
        )
        options.experimental_data = ExperimentalDataInputOptions(use_twenty_significant_digits=True)
        options.broadening = BroadeningOptions(broadening_is_wanted=True)
        options.bayes_solution = BayesSolutionOptions(solve_bayes_equations=True)
        options.lpt_output = LPTOutputOptions(chi_squared_is_wanted=True)

        return options

    @classmethod
    def from_multi_isotope_config(cls) -> "FitOptions":
        """Create a FitOptions instance configured for multi-isotope JSON mode fitting.

        Multi-isotope mode combines ENDF extraction and Bayesian fitting in a single step
        using JSON configuration files for multiple isotopes.

        Key features for multi-isotope mode (following SAMMY expert recommendations):
        - REICH-MOORE FORMALISM IS WANTED
        - USE NEW SPIN GROUP Format
        - USE TWENTY SIGNIFICANT DIGITS
        - BROADENING IS WANTED
        - INPUT IS ENDF/B FILE 2
        - SOLVE BAYES EQUATIONS
        - CHI SQUARED IS WANTED

        Note: Removed unnecessary alphanumerics per expert recommendation to avoid
        undocumented cross-firing between alphanumeric commands in SAMMY.

        Returns:
            FitOptions: Instance configured for multi-isotope JSON mode fitting
        """
        # Create with ONLY the essential options - exclude problematic categories entirely
        return cls(
            r_matrix=RMatrixOptions(reich_moore=True),
            quantum_numbers=QuantumNumbersOptions(new_spin_group_format=True),
            endf=ENDFOptions(input_is_endf_file_2=True),
            experimental_data=ExperimentalDataInputOptions(
                use_twenty_significant_digits=True,
                data_in_original_multi_style_format=False,
                do_not_divide_data_into_regions=False,
            ),
            broadening=BroadeningOptions(broadening_is_wanted=True),
            bayes_solution=BayesSolutionOptions(
                solve_bayes_equations=True,
                let_sammy_choose_which_inversion_scheme_to_use=False,
            ),
            lpt_output=LPTOutputOptions(
                chi_squared_is_wanted=True,
                do_not_print_any_input_parameters=False,
                do_not_print_input_data=False,
                do_not_print_theoretical_values=False,
                do_not_print_partial_derivatives=False,
                do_not_suppress_any_intermediate_printout=True,
                do_not_use_short_format_for_output=False,
                do_not_print_reduced_widths=False,
                do_not_print_debug_info=False,
                do_not_print_weighted_residuals=False,
                do_not_print_bayes_weighted_residuals=False,
                do_not_print_phase_shifts=False,
            ),
            plot_file=PlotFileOptions(
                generate_plot_file_automatically=True,
                do_not_generate_plot_file_automatically=False,
                ev_units_on_energy_in_plot_file=True,  # Following expert recommendation
            ),
        )

    @classmethod
    def from_custom_config(cls, **kwargs) -> "FitOptions":
        """Create a FitOptions instance with custom settings.

        Custom mode is for advanced users who need granular control over all options.

        Args:
            **kwargs: Keyword arguments for specific alphanumerics options

        Returns:
            FitOptions: Instance with custom configuration
        """
        return cls(**kwargs)
