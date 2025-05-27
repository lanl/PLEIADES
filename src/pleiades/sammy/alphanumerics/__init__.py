"""
SAMMY Alphanumeric Options Module.

This module implements the various alphanumeric command options for SAMMY.
These modules provide Pydantic models for validating and generating SAMMY alphanumeric commands.
"""

# Angular Distribution Options (UIDs 53-59)
# For angle-differential data, reference frame and calculation options
from pleiades.sammy.alphanumerics.angular_distribution import AngularDistributionOptions

# Averages Options (UIDs 159-166)
# Energy averages, group averages, and Maxwellian-averaged options
from pleiades.sammy.alphanumerics.averages import AveragesOptions

# Bayes Solution Options (UIDs 102-110)
# Control the Bayes equation solving methods and inversion schemes
from pleiades.sammy.alphanumerics.bayes_solution import BayesSolutionOptions

# Broadening Options (UIDs 60-82)
# Controls Doppler and resolution broadening options
from pleiades.sammy.alphanumerics.broadening import BroadeningOptions

# Covariance Matrix Data Options (UIDs 41-52)
# Options for handling data covariance matrices
from pleiades.sammy.alphanumerics.covariance_matrix_data import CovarianceMatrixOptions

# Cross Section Options (UIDs 199-210)
# Control cross section calculation options
from pleiades.sammy.alphanumerics.cross_section import CrossSectionOptions

# ENDF Options (UIDs 15-16, 142-148)
# Options for ENDF file input and output
from pleiades.sammy.alphanumerics.endf import ENDFOptions

# Experimental Data Input Options (UIDs 32-40)
# Control format and processing of experimental data
from pleiades.sammy.alphanumerics.experimental_data_input import ExperimentalDataInputOptions

# Quantum Numbers Options (UIDs 7-14)
# Control spin group and particle-pair definitions
from pleiades.sammy.alphanumerics.input_quantum_numbers import QuantumNumbersOptions

# LPT Output Options (UIDs 111-141)
# Control printing and output options in SAMMY.LPT file
from pleiades.sammy.alphanumerics.lpt import LPTOutputOptions

# Multiple Scattering Corrections Options (UIDs 83-101)
# Control self-shielding and multiple-scattering corrections
from pleiades.sammy.alphanumerics.multiple_scattering_corrections import MultipleScatteringCorrectionsOptions

# P-Covariance Matrix Input Options (UIDs 18-28)
# Control parameter covariance matrix input
from pleiades.sammy.alphanumerics.p_covariance_matrix_in import CovarianceMatrixOptions as PCovarianceMatrixInOptions

# P-Covariance Matrix Output Options (UIDs 29-31)
# Control parameter covariance matrix output
from pleiades.sammy.alphanumerics.p_covariance_matrix_out import CovarianceMatrixOutputOptions

# Physical Constants Options (UIDs 167-169)
# Control which set of physical constants to use
from pleiades.sammy.alphanumerics.physical_constants import PhysicalConstantsOptions

# Plot File Options (UIDs 149-158)
# Control generation and format of plot files
from pleiades.sammy.alphanumerics.plot_file import PlotFileOptions

# R-Matrix Options (UIDs 2-6)
# Control R-Matrix formalism settings
from pleiades.sammy.alphanumerics.r_matrix import RMatrixOptions

# Special Analysis Options (UIDs 170-190)
# Control special analysis modes and output options
from pleiades.sammy.alphanumerics.special_analysis import SpecialAnalysisOptions

# Unresolved Resonance Region Options (UIDs 1, 191-198)
# Control options for unresolved resonance region analysis
from pleiades.sammy.alphanumerics.urr import URROptions

__all__ = [
    "AngularDistributionOptions",
    "AveragesOptions",
    "BayesSolutionOptions",
    "BroadeningOptions",
    "CovarianceMatrixOptions",
    "CrossSectionOptions",
    "ENDFOptions",
    "ExperimentalDataInputOptions",
    "QuantumNumbersOptions",
    "LPTOutputOptions",
    "MultipleScatteringCorrectionsOptions",
    "PCovarianceMatrixInOptions",
    "CovarianceMatrixOutputOptions",
    "PhysicalConstantsOptions",
    "PlotFileOptions",
    "RMatrixOptions",
    "SpecialAnalysisOptions",
    "URROptions",
]
