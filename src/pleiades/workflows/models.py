"""Pydantic models for PLEIADES workflow results.

This module defines structured result types for workflow operations,
enabling type-safe results and consistent output formatting.
"""

from __future__ import annotations

import math
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkflowType(str, Enum):
    """Type of resonance analysis workflow."""

    FULL = "full"
    SIMPLIFIED = "simplified"


class FitQuality(str, Enum):
    """Quality assessment of SAMMY fit."""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"

    @classmethod
    def from_chi_squared(cls, reduced_chi_sq: float) -> FitQuality:
        """Determine fit quality from reduced chi-squared value.

        Args:
            reduced_chi_sq: Reduced chi-squared value (must be non-negative and finite).

        Returns:
            FitQuality enum value based on the chi-squared value.

        Raises:
            ValueError: If reduced_chi_sq is negative, NaN, or infinite.
        """
        if not math.isfinite(reduced_chi_sq) or reduced_chi_sq < 0:
            raise ValueError(f"Invalid reduced chi-squared value: {reduced_chi_sq}")
        if reduced_chi_sq < 1.2:
            return cls.EXCELLENT
        elif reduced_chi_sq < 2.0:
            return cls.GOOD
        elif reduced_chi_sq < 5.0:
            return cls.ACCEPTABLE
        else:
            return cls.POOR


class MaterialProperties(BaseModel):
    """Material properties for resonance analysis."""

    density_g_cm3: float = Field(..., description="Material density in g/cm³")
    atomic_mass_amu: float = Field(..., description="Atomic mass in amu")
    temperature_k: float | None = Field(None, description="Sample temperature in Kelvin")

    @field_validator("density_g_cm3", "atomic_mass_amu")
    @classmethod
    def validate_positive(cls, v: float, info) -> float:
        """Validate that physical properties are positive."""
        if v <= 0:
            raise ValueError(f"{info.field_name} must be positive, got {v}")
        return v

    @field_validator("temperature_k")
    @classmethod
    def validate_temperature(cls, v: float | None) -> float | None:
        """Validate that temperature is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError(f"temperature_k must be positive, got {v}")
        return v


class IsotopeResult(BaseModel):
    """Results for a single isotope in the analysis."""

    isotope: str = Field(..., description="Isotope identifier (e.g., 'Au-197')")
    abundance: float = Field(..., description="Fitted abundance fraction")
    abundance_uncertainty: float | None = Field(None, description="Uncertainty in abundance")


class ResonanceResult(BaseModel):
    """Complete results from resonance analysis workflow.

    This model captures all outputs from a successful resonance analysis,
    including fit quality metrics, physical parameters, and output file paths.
    """

    success: bool = Field(..., description="Whether the analysis completed successfully")
    workflow_type: WorkflowType = Field(..., description="Type of workflow executed")

    # Primary isotope info
    primary_isotope: str = Field(..., description="Primary isotope analyzed")
    isotopes_analyzed: list[str] = Field(default_factory=list, description="All isotopes in analysis")

    # Fit results
    chi_squared: float | None = Field(None, description="Chi-squared value")
    reduced_chi_squared: float | None = Field(None, description="Reduced chi-squared (chi²/dof)")
    degrees_of_freedom: int | None = Field(None, description="Degrees of freedom")
    fit_quality: FitQuality | None = Field(None, description="Qualitative fit assessment")

    # Physical parameters (fitted)
    number_density: float | None = Field(None, description="Number density (atoms/barn-cm)")
    temperature_k: float | None = Field(None, description="Effective temperature (K)")

    # Isotope-specific results (for multi-isotope analysis)
    isotope_results: list[IsotopeResult] = Field(default_factory=list, description="Per-isotope fit results")

    # Output paths
    output_dir: Path | None = Field(None, description="SAMMY output directory")
    lpt_file: Path | None = Field(None, description="SAMMY .LPT log file")
    lst_file: Path | None = Field(None, description="SAMMY .LST listing file")
    par_file: Path | None = Field(None, description="Updated .PAR parameter file")
    plot_file: Path | None = Field(None, description="Generated fit plot")

    # Error info (if success=False)
    error_message: str | None = Field(None, description="Error message if analysis failed")
    error_step: str | None = Field(None, description="Workflow step where error occurred")

    # Workflow metadata
    runtime_seconds: float | None = Field(None, description="Total execution time")
    workflow_steps: dict[str, str] = Field(default_factory=dict, description="Status of each workflow step")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ValidationIssue(BaseModel):
    """Single validation issue found in dataset."""

    severity: Literal["error", "warning"] = Field(..., description="Issue severity")
    message: str = Field(..., description="Description of the issue")
    path: Path | None = Field(None, description="Path related to the issue")


class ValidationResult(BaseModel):
    """Results from dataset validation.

    Validates that a dataset has the required structure and files
    for resonance analysis.
    """

    valid: bool = Field(..., description="Whether the dataset is valid for analysis")
    dataset_path: Path = Field(..., description="Path to the validated dataset")

    # Detected workflow type
    can_run_full_workflow: bool = Field(False, description="Dataset supports full imaging workflow")
    can_run_simplified_workflow: bool = Field(False, description="Dataset has pre-existing SAMMY files")
    recommended_workflow: WorkflowType | None = Field(None, description="Recommended workflow type")

    # Dataset contents
    has_raw_data: bool = Field(False, description="Has raw imaging data")
    has_open_beam: bool = Field(False, description="Has open beam normalization data")
    has_metadata: bool = Field(False, description="Has NeXus metadata")
    has_sammy_files: bool = Field(False, description="Has pre-existing SAMMY files")
    has_manifest: bool = Field(False, description="Has sMCP manifest file")

    # Validation issues
    issues: list[ValidationIssue] = Field(default_factory=list, description="All validation issues found")

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == "warning"]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ManifestData(BaseModel):
    """Parsed manifest data from dataset.

    Structured representation of the sMCP manifest frontmatter
    and processing instructions.
    """

    name: str = Field(..., description="Unique dataset identifier")
    description: str = Field(..., description="Human-readable description")
    version: str = Field(..., description="Manifest version (semver)")
    created: str = Field(..., description="ISO-8601 creation timestamp")

    # Experiment metadata
    facility: str | None = Field(None, description="Facility identifier (e.g., 'SNS')")
    beamline: str | None = Field(None, description="Beamline name (e.g., 'VENUS')")
    detector: str | None = Field(None, description="Detector type")
    sample_id: str | None = Field(None, description="Sample identifier")

    # Analysis parameters
    isotope: str | None = Field(None, description="Primary isotope (e.g., 'Au-197')")
    material_properties: MaterialProperties | None = Field(None, description="Material physical properties")

    # Isotope composition settings (Issue #204)
    use_natural_abundance: bool = Field(
        True,
        description="If True, use natural abundance from isotopes.info. If False, use custom enrichment values.",
    )
    enrichment: dict[str, float] | None = Field(
        None,
        description="Custom isotope composition for enriched samples. "
        "Keys are isotope strings (e.g., 'U-235'), values are fractions (0-1). "
        "Only used when use_natural_abundance=False.",
    )

    # Explicit isotope list (Issue #206)
    isotopes: list[str] | None = Field(
        None,
        description="Explicit list of isotopes to analyze (e.g., ['Hf-176', 'Hf-177']). "
        "When set, only these isotopes are included regardless of natural abundance. "
        "Takes priority over both enrichment and natural abundance lookup.",
    )

    @field_validator("isotopes")
    @classmethod
    def validate_isotopes(cls, v: list[str] | None) -> list[str] | None:
        """Validate isotopes list contains valid isotope format strings.

        Checks:
        - All elements are strings
        - All strings match isotope format (Element-MassNumber, e.g., 'Hf-177')
        """
        import re

        if v is None:
            return v

        if not v:  # Empty list is valid
            return v

        # Validate each isotope in the list
        isotope_pattern = re.compile(r"^[A-Z][a-z]?-\d+$")
        for idx, isotope in enumerate(v):
            if not isinstance(isotope, str):
                raise ValueError(f"Invalid isotope at index {idx}: expected string, got {type(isotope).__name__}")
            if not isotope_pattern.match(isotope):
                raise ValueError(
                    f"Invalid isotope format '{isotope}' at index {idx}. "
                    f"Expected format: 'Element-MassNumber' (e.g., 'Hf-177', 'U-235')"
                )

        return v

    @field_validator("enrichment")
    @classmethod
    def validate_enrichment(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        """Validate enrichment dict has valid isotope keys and abundance fractions.

        Checks:
        - All values are in range [0, 1]
        - Values sum to approximately 1.0 (within 1% tolerance)
        - Keys match isotope format (Element-MassNumber)
        """
        import re

        if v is None:
            return v

        if not v:
            return v

        # Validate isotope key format
        isotope_pattern = re.compile(r"^[A-Z][a-z]?-\d+$")
        for key in v.keys():
            if not isotope_pattern.match(key):
                raise ValueError(
                    f"Invalid isotope key '{key}' in enrichment. "
                    f"Expected format: 'Element-MassNumber' (e.g., 'U-235', 'Hf-177')"
                )

        # Validate values are in valid range
        for key, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Enrichment value for '{key}' must be a number, got {type(value).__name__}")
            if value < 0:
                raise ValueError(f"Enrichment value for '{key}' cannot be negative: {value}")
            if value > 1.0:
                raise ValueError(
                    f"Enrichment value for '{key}' exceeds 1.0: {value}. "
                    f"Values should be fractions (0-1), not percentages."
                )

        # Validate sum is approximately 1.0
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Enrichment values must sum to approximately 1.0, got {total:.4f}. Values: {v}")

        return v

    # Raw content
    body: str = Field("", description="Markdown body with processing instructions")
    raw_frontmatter: dict[str, Any] = Field(default_factory=dict, description="Raw YAML frontmatter")
