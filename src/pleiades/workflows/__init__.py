"""PLEIADES high-level workflow APIs.

This module provides simple, high-level functions for common PLEIADES
operations. These functions orchestrate multiple lower-level APIs to
perform complete analysis workflows.

Example:
    >>> from pleiades.workflows import validate_dataset, analyze_resonance
    >>>
    >>> # Validate dataset before analysis
    >>> validation = validate_dataset("/path/to/dataset")
    >>> if validation.valid:
    ...     print(f"Dataset ready for {validation.recommended_workflow.value} workflow")
    ...
    >>> # Run analysis
    >>> result = analyze_resonance("/path/to/dataset")
    >>> if result.success:
    ...     print(f"Chi²/dof: {result.reduced_chi_squared:.3f}")
    ...     print(f"Fit quality: {result.fit_quality.value}")
"""

from __future__ import annotations

from pleiades.workflows.models import (
    FitQuality,
    ManifestData,
    MaterialProperties,
    ResonanceResult,
    ValidationIssue,
    ValidationResult,
    WorkflowType,
)
from pleiades.workflows.resonance import (
    analyze_resonance,
    extract_manifest,
    validate_dataset,
)

__all__ = [
    # Main workflow functions
    "analyze_resonance",
    "validate_dataset",
    "extract_manifest",
    # Result models
    "ResonanceResult",
    "ValidationResult",
    "ValidationIssue",
    "ManifestData",
    "MaterialProperties",
    # Enums
    "WorkflowType",
    "FitQuality",
]
