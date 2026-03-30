"""Tests for pleiades.workflows.models module."""

import math
from pathlib import Path

import pytest

from pleiades.workflows.models import (
    FitQuality,
    ManifestData,
    MaterialProperties,
    ResonanceResult,
    ValidationIssue,
    ValidationResult,
    WorkflowType,
)


class TestFitQuality:
    """Tests for FitQuality enum."""

    def test_from_chi_squared_excellent(self):
        """Chi² < 1.2 should be excellent."""
        assert FitQuality.from_chi_squared(0.9) == FitQuality.EXCELLENT
        assert FitQuality.from_chi_squared(1.1) == FitQuality.EXCELLENT

    def test_from_chi_squared_good(self):
        """1.2 <= Chi² < 2.0 should be good."""
        assert FitQuality.from_chi_squared(1.2) == FitQuality.GOOD
        assert FitQuality.from_chi_squared(1.5) == FitQuality.GOOD
        assert FitQuality.from_chi_squared(1.99) == FitQuality.GOOD

    def test_from_chi_squared_acceptable(self):
        """2.0 <= Chi² < 5.0 should be acceptable."""
        assert FitQuality.from_chi_squared(2.0) == FitQuality.ACCEPTABLE
        assert FitQuality.from_chi_squared(3.5) == FitQuality.ACCEPTABLE
        assert FitQuality.from_chi_squared(4.99) == FitQuality.ACCEPTABLE

    def test_from_chi_squared_poor(self):
        """Chi² >= 5.0 should be poor."""
        assert FitQuality.from_chi_squared(5.0) == FitQuality.POOR
        assert FitQuality.from_chi_squared(10.0) == FitQuality.POOR

    def test_from_chi_squared_invalid_negative(self):
        """Negative chi-squared should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid reduced chi-squared"):
            FitQuality.from_chi_squared(-1.0)

    def test_from_chi_squared_invalid_nan(self):
        """NaN chi-squared should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid reduced chi-squared"):
            FitQuality.from_chi_squared(math.nan)

    def test_from_chi_squared_invalid_infinity(self):
        """Infinite chi-squared should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid reduced chi-squared"):
            FitQuality.from_chi_squared(math.inf)


class TestWorkflowType:
    """Tests for WorkflowType enum."""

    def test_workflow_type_values(self):
        """WorkflowType should have expected values."""
        assert WorkflowType.FULL.value == "full"
        assert WorkflowType.SIMPLIFIED.value == "simplified"


class TestMaterialProperties:
    """Tests for MaterialProperties model."""

    def test_create_with_required_fields(self):
        """MaterialProperties should require density and atomic mass."""
        mp = MaterialProperties(
            density_g_cm3=19.3,
            atomic_mass_amu=196.97,
        )
        assert mp.density_g_cm3 == 19.3
        assert mp.atomic_mass_amu == 196.97
        assert mp.temperature_k is None

    def test_create_with_all_fields(self):
        """MaterialProperties should accept optional temperature."""
        mp = MaterialProperties(
            density_g_cm3=19.3,
            atomic_mass_amu=196.97,
            temperature_k=293.6,
        )
        assert mp.temperature_k == 293.6

    def test_missing_required_field_raises(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            MaterialProperties(density_g_cm3=19.3)

    def test_negative_density_raises(self):
        """Negative density should raise ValidationError."""
        with pytest.raises(Exception, match="must be positive"):
            MaterialProperties(density_g_cm3=-1.0, atomic_mass_amu=196.97)

    def test_zero_density_raises(self):
        """Zero density should raise ValidationError."""
        with pytest.raises(Exception, match="must be positive"):
            MaterialProperties(density_g_cm3=0.0, atomic_mass_amu=196.97)

    def test_negative_atomic_mass_raises(self):
        """Negative atomic mass should raise ValidationError."""
        with pytest.raises(Exception, match="must be positive"):
            MaterialProperties(density_g_cm3=19.3, atomic_mass_amu=-10.0)

    def test_negative_temperature_raises(self):
        """Negative temperature should raise ValidationError."""
        with pytest.raises(Exception, match="must be positive"):
            MaterialProperties(density_g_cm3=19.3, atomic_mass_amu=196.97, temperature_k=-100.0)


class TestValidationIssue:
    """Tests for ValidationIssue model."""

    def test_create_error(self):
        """ValidationIssue should accept error severity."""
        issue = ValidationIssue(
            severity="error",
            message="Missing raw data directory",
            path=Path("/data/raw"),
        )
        assert issue.severity == "error"
        assert "raw data" in issue.message
        assert issue.path == Path("/data/raw")

    def test_create_warning(self):
        """ValidationIssue should accept warning severity."""
        issue = ValidationIssue(
            severity="warning",
            message="Open beam directory not found",
        )
        assert issue.severity == "warning"
        assert issue.path is None


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_dataset(self):
        """ValidationResult for valid dataset."""
        result = ValidationResult(
            valid=True,
            dataset_path=Path("/data/sample"),
            can_run_simplified_workflow=True,
            recommended_workflow=WorkflowType.SIMPLIFIED,
            has_sammy_files=True,
        )
        assert result.valid
        assert result.can_run_simplified_workflow
        assert result.recommended_workflow == WorkflowType.SIMPLIFIED

    def test_invalid_dataset_with_errors(self):
        """ValidationResult should track errors."""
        result = ValidationResult(
            valid=False,
            dataset_path=Path("/data/sample"),
            issues=[
                ValidationIssue(severity="error", message="No data found"),
                ValidationIssue(severity="warning", message="Missing metadata"),
            ],
        )
        assert not result.valid
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_errors_property(self):
        """errors property should filter to error-level issues."""
        result = ValidationResult(
            valid=False,
            dataset_path=Path("/data/sample"),
            issues=[
                ValidationIssue(severity="error", message="Error 1"),
                ValidationIssue(severity="error", message="Error 2"),
                ValidationIssue(severity="warning", message="Warning 1"),
            ],
        )
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


class TestResonanceResult:
    """Tests for ResonanceResult model."""

    def test_successful_result(self):
        """ResonanceResult for successful analysis."""
        result = ResonanceResult(
            success=True,
            workflow_type=WorkflowType.SIMPLIFIED,
            primary_isotope="Au-197",
            isotopes_analyzed=["Au-197"],
            chi_squared=125.5,
            reduced_chi_squared=1.05,
            degrees_of_freedom=120,
            fit_quality=FitQuality.EXCELLENT,
            number_density=0.00123,
            temperature_k=293.6,
            output_dir=Path("/data/output"),
            lpt_file=Path("/data/output/SAMMY.LPT"),
            lst_file=Path("/data/output/SAMMY.LST"),
            runtime_seconds=5.2,
        )
        assert result.success
        assert result.primary_isotope == "Au-197"
        assert result.fit_quality == FitQuality.EXCELLENT
        assert result.error_message is None

    def test_failed_result(self):
        """ResonanceResult for failed analysis."""
        result = ResonanceResult(
            success=False,
            workflow_type=WorkflowType.SIMPLIFIED,
            primary_isotope="Au-197",
            error_message="SAMMY execution failed",
            error_step="sammy_execution",
        )
        assert not result.success
        assert result.error_message == "SAMMY execution failed"
        assert result.error_step == "sammy_execution"
        assert result.reduced_chi_squared is None


class TestManifestData:
    """Tests for ManifestData model."""

    def test_create_minimal(self):
        """ManifestData with only required fields."""
        manifest = ManifestData(
            name="test_dataset",
            description="Test dataset for unit tests",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
        )
        assert manifest.name == "test_dataset"
        assert manifest.isotope is None
        assert manifest.material_properties is None

    def test_create_full(self):
        """ManifestData with all fields."""
        manifest = ManifestData(
            name="Au197_sample",
            description="Gold-197 calibration sample",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            facility="SNS",
            beamline="VENUS",
            detector="MCP",
            sample_id="Au197-001",
            isotope="Au-197",
            material_properties=MaterialProperties(
                density_g_cm3=19.3,
                atomic_mass_amu=196.97,
            ),
            body="# Analysis Instructions\n\nRun fitting with default parameters.",
        )
        assert manifest.isotope == "Au-197"
        assert manifest.material_properties.density_g_cm3 == 19.3
        assert "Analysis Instructions" in manifest.body

    def test_default_use_natural_abundance(self):
        """ManifestData should default to using natural abundance."""
        manifest = ManifestData(
            name="test_dataset",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
        )
        assert manifest.use_natural_abundance is True
        assert manifest.enrichment is None

    def test_enriched_sample_configuration(self):
        """ManifestData should support enriched sample configuration."""
        enrichment_data = {"U-235": 0.90, "U-238": 0.10}
        manifest = ManifestData(
            name="enriched_U235",
            description="Enriched uranium sample",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="U-235",
            use_natural_abundance=False,
            enrichment=enrichment_data,
        )
        assert manifest.use_natural_abundance is False
        assert manifest.enrichment == enrichment_data
        assert manifest.enrichment["U-235"] == 0.90

    def test_enrichment_without_flag_defaults_to_natural(self):
        """Enrichment dict alone doesn't change use_natural_abundance default."""
        manifest = ManifestData(
            name="test",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            enrichment={"Hf-177": 0.95, "Hf-178": 0.05},
        )
        # Enrichment provided but flag still True - user must explicitly set False
        assert manifest.use_natural_abundance is True

    def test_enrichment_values_should_be_fractions(self):
        """Enrichment values should be fractions (0-1), not percentages."""
        # This is a design constraint - values should be fractions for consistency
        # with IsotopeManager.get_natural_composition()
        manifest = ManifestData(
            name="test",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            use_natural_abundance=False,
            enrichment={"Pu-239": 0.94, "Pu-240": 0.06},
        )
        # Verify enrichment values sum to 1.0 (fractions, not percentages)
        total = sum(manifest.enrichment.values())
        assert abs(total - 1.0) < 0.01

    def test_enrichment_sum_not_1_raises(self):
        """Enrichment values that don't sum to 1.0 should raise validation error."""
        with pytest.raises(Exception, match="sum to approximately 1.0"):
            ManifestData(
                name="test",
                description="Test",
                version="1.0.0",
                created="2024-01-01T00:00:00Z",
                enrichment={"U-235": 0.95, "U-238": 0.95},  # Sums to 1.9
            )

    def test_negative_enrichment_values_raises(self):
        """Negative enrichment values should raise validation error."""
        with pytest.raises(Exception, match="cannot be negative"):
            ManifestData(
                name="test",
                description="Test",
                version="1.0.0",
                created="2024-01-01T00:00:00Z",
                enrichment={"U-235": -0.5, "U-238": 1.5},
            )

    def test_enrichment_exceeds_1_raises(self):
        """Enrichment values exceeding 1.0 should raise validation error."""
        with pytest.raises(Exception, match="exceeds 1.0"):
            ManifestData(
                name="test",
                description="Test",
                version="1.0.0",
                created="2024-01-01T00:00:00Z",
                enrichment={"U-235": 1.5, "U-238": 0.0},
            )

    def test_invalid_isotope_key_format_raises(self):
        """Malformed isotope keys in enrichment should raise validation error."""
        with pytest.raises(Exception, match="Invalid isotope key"):
            ManifestData(
                name="test",
                description="Test",
                version="1.0.0",
                created="2024-01-01T00:00:00Z",
                enrichment={"Uranium-235": 1.0},  # Full element name instead of symbol
            )

    def test_invalid_isotope_format_raises(self):
        """Isotope keys without mass number should raise validation error."""
        with pytest.raises(Exception, match="Invalid isotope key"):
            ManifestData(
                name="test",
                description="Test",
                version="1.0.0",
                created="2024-01-01T00:00:00Z",
                enrichment={"U": 1.0},  # Missing mass number
            )
