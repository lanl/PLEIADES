"""Tests for pleiades.workflows.resonance module."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pleiades.workflows.models import ManifestData, WorkflowType
from pleiades.workflows.resonance import (
    _get_isotope_composition,
    extract_manifest,
    validate_dataset,
)


class TestValidateDataset:
    """Tests for validate_dataset function."""

    def test_nonexistent_path(self, tmp_path):
        """Validation should fail for nonexistent path."""
        result = validate_dataset(tmp_path / "nonexistent")
        assert not result.valid
        assert len(result.errors) == 1
        assert "does not exist" in result.errors[0].message

    def test_file_not_directory(self, tmp_path):
        """Validation should fail if path is a file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = validate_dataset(test_file)
        assert not result.valid
        assert "not a directory" in result.errors[0].message

    def test_empty_directory(self, tmp_path):
        """Validation should fail for empty directory."""
        result = validate_dataset(tmp_path)
        assert not result.valid
        assert not result.can_run_full_workflow
        assert not result.can_run_simplified_workflow

    def test_simplified_workflow_valid(self, tmp_path):
        """Dataset with SAMMY files should support simplified workflow."""
        sammy_dir = tmp_path / "sammy_data"
        sammy_dir.mkdir()

        # Create SAMMY input files
        (sammy_dir / "ex012a.inp").write_text("SAMMY input")
        (sammy_dir / "ex012a.par").write_text("SAMMY params")
        (sammy_dir / "ex012a.dat").write_text("SAMMY data")

        result = validate_dataset(tmp_path)
        assert result.valid
        assert result.can_run_simplified_workflow
        assert not result.can_run_full_workflow
        assert result.recommended_workflow == WorkflowType.SIMPLIFIED
        assert result.has_sammy_files

    def test_simplified_workflow_missing_par(self, tmp_path):
        """Missing .par file should be an error."""
        sammy_dir = tmp_path / "sammy_data"
        sammy_dir.mkdir()

        (sammy_dir / "ex012a.inp").write_text("SAMMY input")
        (sammy_dir / "ex012a.dat").write_text("SAMMY data")

        result = validate_dataset(tmp_path)
        assert not result.valid
        assert any("Missing parameter file" in e.message for e in result.errors)

    def test_full_workflow_valid(self, tmp_path):
        """Dataset with imaging data should support full workflow."""
        (tmp_path / "raw").mkdir()
        (tmp_path / "open_beam").mkdir()

        result = validate_dataset(tmp_path)
        assert result.valid
        assert result.can_run_full_workflow
        assert not result.can_run_simplified_workflow
        assert result.recommended_workflow == WorkflowType.FULL
        assert result.has_raw_data
        assert result.has_open_beam

    def test_full_workflow_missing_open_beam(self, tmp_path):
        """Missing open_beam makes full workflow unavailable (invalid dataset)."""
        (tmp_path / "raw").mkdir()

        result = validate_dataset(tmp_path)
        # Dataset is invalid because full workflow needs both raw and open_beam
        # and no simplified workflow is available either
        assert not result.valid
        assert result.has_raw_data
        assert not result.has_open_beam
        assert not result.can_run_full_workflow
        # Should have warning about missing open_beam
        assert any("Open beam directory" in w.message for w in result.warnings)

    def test_manifest_detection(self, tmp_path):
        """Manifest file should be detected."""
        (tmp_path / "sammy_data").mkdir()
        (tmp_path / "sammy_data" / "test.inp").write_text("input")
        (tmp_path / "sammy_data" / "test.par").write_text("params")
        (tmp_path / "sammy_data" / "test.dat").write_text("data")

        # Create manifest
        manifest_content = """---
name: test_dataset
description: Test
tool: pleiades
physics: nri
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
---
# Instructions
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = validate_dataset(tmp_path)
        assert result.valid
        assert result.has_manifest

    def test_both_workflow_types_available(self, tmp_path):
        """Dataset with both imaging data and SAMMY files should prefer full workflow."""
        # Create imaging data
        (tmp_path / "raw").mkdir()
        (tmp_path / "open_beam").mkdir()

        # Create SAMMY files
        sammy_dir = tmp_path / "sammy_data"
        sammy_dir.mkdir()
        (sammy_dir / "test.inp").write_text("input")
        (sammy_dir / "test.par").write_text("params")
        (sammy_dir / "test.dat").write_text("data")

        result = validate_dataset(tmp_path)
        assert result.valid
        assert result.can_run_full_workflow
        assert result.can_run_simplified_workflow
        assert result.recommended_workflow == WorkflowType.FULL


class TestExtractManifest:
    """Tests for extract_manifest function."""

    def test_no_manifest(self, tmp_path):
        """Should return None if no manifest found."""
        result = extract_manifest(tmp_path)
        assert result is None

    def test_valid_manifest(self, tmp_path):
        """Should parse valid manifest."""
        manifest_content = """---
name: Au197_sample
description: Gold calibration sample
tool: pleiades
physics: nri
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
facility: SNS
beamline: VENUS
isotope: Au-197
---
# Analysis Instructions

Run with default parameters.
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.name == "Au197_sample"
        assert result.isotope == "Au-197"
        assert result.facility == "SNS"
        assert "Analysis Instructions" in result.body

    def test_manifest_with_material_properties(self, tmp_path):
        """Should parse material_properties from manifest."""
        manifest_content = """---
name: test
description: Test
tool: pleiades
physics: nri
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
material_properties:
  density_g_cm3: 19.3
  atomic_mass_amu: 196.97
  temperature_k: 293.6
---
Body content
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.material_properties is not None
        assert result.material_properties.density_g_cm3 == 19.3
        assert result.material_properties.atomic_mass_amu == 196.97
        assert result.material_properties.temperature_k == 293.6

    def test_invalid_manifest_format(self, tmp_path):
        """Should raise ValueError for invalid format."""
        (tmp_path / "manifest_intermediate.md").write_text("No frontmatter here")

        with pytest.raises(ValueError, match="missing YAML frontmatter"):
            extract_manifest(tmp_path)

    def test_alternate_manifest_names(self, tmp_path):
        """Should find manifest with alternate names."""
        manifest_content = """---
name: test
description: Test
tool: pleiades
physics: nri
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
---
Body
"""
        # Test smcp_manifest.md
        (tmp_path / "smcp_manifest.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.name == "test"

    def test_manifest_with_horizontal_rule_in_body(self, tmp_path):
        """Should handle markdown body containing --- (horizontal rule)."""
        manifest_content = """---
name: test
description: Test with horizontal rule
tool: pleiades
physics: nri
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
---
# Section 1

Some content here.

---

# Section 2

More content after horizontal rule.

---

Final section.
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.name == "test"
        # Body should contain the horizontal rules
        assert "---" in result.body
        assert "Section 1" in result.body
        assert "Section 2" in result.body
        assert "Final section" in result.body


class TestAnalyzeResonance:
    """Tests for analyze_resonance function."""

    def test_invalid_dataset_fails(self, tmp_path):
        """Analysis should fail for invalid dataset."""
        from pleiades.workflows.resonance import analyze_resonance

        result = analyze_resonance(tmp_path / "nonexistent")
        assert not result.success
        assert result.error_step == "validation"

    def test_skip_validation(self, tmp_path):
        """skip_validation should bypass validation check."""
        from pleiades.workflows.resonance import analyze_resonance

        # Empty directory, would fail validation
        result = analyze_resonance(tmp_path, skip_validation=True)
        # Should fail at file discovery, not validation
        assert not result.success
        assert result.error_step == "file_discovery"
        assert "No SAMMY files" in result.error_message

    @patch("pleiades.sammy.results.manager.ResultsManager")
    @patch("pleiades.sammy.factory.SammyFactory")
    def test_simplified_workflow_success(self, mock_factory, mock_results_manager_class, tmp_path):
        """Simplified workflow should succeed with mocked SAMMY."""
        from pleiades.workflows.resonance import analyze_resonance

        # Create SAMMY files
        sammy_dir = tmp_path / "sammy_data"
        sammy_dir.mkdir()
        (sammy_dir / "ex012a.inp").write_text("input")
        (sammy_dir / "ex012a.par").write_text("params")
        (sammy_dir / "ex012a.dat").write_text("data")

        # Create expected SAMMY output files (these are checked before parsing)
        sammy_output = tmp_path / "sammy_output"
        sammy_output.mkdir()
        (sammy_output / "SAMMY.LPT").write_text("log output")
        (sammy_output / "SAMMY.LST").write_text("list output")

        # Mock SAMMY runner
        mock_runner = MagicMock()
        mock_exec_result = MagicMock()
        mock_exec_result.success = True
        mock_runner.execute_sammy.return_value = mock_exec_result
        mock_factory.auto_select.return_value = mock_runner

        # Mock results manager
        mock_fit_result = MagicMock()
        mock_fit_result.chi_squared_results.chi_squared = 125.5
        mock_fit_result.chi_squared_results.reduced_chi_squared = 1.05
        mock_fit_result.chi_squared_results.dof = 120
        mock_fit_result.physics_data.broadening_parameters.temp = 293.6
        mock_fit_result.physics_data.broadening_parameters.thick = 0.00123

        mock_run_results = MagicMock()
        mock_run_results.fit_results = [mock_fit_result]
        mock_results_manager_class.return_value.run_results = mock_run_results

        result = analyze_resonance(tmp_path)

        assert result.success
        assert result.workflow_type == WorkflowType.SIMPLIFIED
        assert result.reduced_chi_squared == 1.05
        assert result.temperature_k == 293.6

    def test_full_workflow_handles_empty_raw_folder(self, tmp_path):
        """Full workflow should handle empty raw folder gracefully."""
        from pleiades.workflows.resonance import analyze_resonance

        # Create imaging data structure with empty folders
        (tmp_path / "raw").mkdir()
        (tmp_path / "open_beam").mkdir()

        result = analyze_resonance(tmp_path)

        assert not result.success
        assert result.workflow_type == WorkflowType.FULL
        # The normalization step should fail because there are no TIFF files
        assert result.error_step == "normalization"
        assert "Normalization failed" in result.error_message or "No files found" in result.error_message

    @patch("pleiades.workflows.resonance._execute_full_workflow")
    @patch("pleiades.workflows.resonance.extract_manifest", return_value=None)
    @patch("pleiades.workflows.resonance.validate_dataset")
    def test_analyze_prefers_full_workflow_when_both_available(
        self,
        mock_validate,
        _mock_extract_manifest,
        mock_execute_full_workflow,
        tmp_path,
    ):
        """When both workflows are valid, analyze_resonance should run the full workflow."""
        from pleiades.workflows.resonance import analyze_resonance

        mock_validate.return_value = SimpleNamespace(
            valid=True,
            can_run_full_workflow=True,
            can_run_simplified_workflow=True,
        )
        sentinel = MagicMock()
        mock_execute_full_workflow.return_value = sentinel

        result = analyze_resonance(tmp_path)

        mock_execute_full_workflow.assert_called_once()
        assert result is sentinel

    @patch("pleiades.workflows.resonance._execute_simplified_workflow")
    @patch("pleiades.workflows.resonance.extract_manifest", return_value=None)
    @patch("pleiades.workflows.resonance.validate_dataset")
    def test_analyze_rejects_isotopes_in_simplified_workflow(
        self,
        mock_validate,
        _mock_extract_manifest,
        mock_execute_simplified_workflow,
        tmp_path,
    ):
        """Supplying isotopes for simplified workflow should return a parameter error."""
        from pleiades.workflows.resonance import analyze_resonance

        mock_validate.return_value = SimpleNamespace(
            valid=True,
            can_run_full_workflow=False,
            can_run_simplified_workflow=True,
        )

        result = analyze_resonance(tmp_path, isotopes=["Hf-177"])

        assert not result.success
        assert result.error_step == "parameter_validation"
        assert "isotopes parameter" in result.error_message
        mock_execute_simplified_workflow.assert_not_called()

    @patch("pleiades.sammy.results.manager.ResultsManager")
    @patch("pleiades.sammy.factory.SammyFactory")
    def test_empty_fit_results_handled(self, mock_factory, mock_results_manager_class, tmp_path):
        """Empty fit_results list should return error, not crash."""
        from pleiades.workflows.resonance import analyze_resonance

        # Create SAMMY files
        sammy_dir = tmp_path / "sammy_data"
        sammy_dir.mkdir()
        (sammy_dir / "ex012a.inp").write_text("input")
        (sammy_dir / "ex012a.par").write_text("params")
        (sammy_dir / "ex012a.dat").write_text("data")

        # Create expected SAMMY output files (these are checked before parsing)
        sammy_output = tmp_path / "sammy_output"
        sammy_output.mkdir()
        (sammy_output / "SAMMY.LPT").write_text("log output")
        (sammy_output / "SAMMY.LST").write_text("list output")

        # Mock SAMMY runner
        mock_runner = MagicMock()
        mock_exec_result = MagicMock()
        mock_exec_result.success = True
        mock_runner.execute_sammy.return_value = mock_exec_result
        mock_factory.auto_select.return_value = mock_runner

        # Mock results manager with EMPTY fit_results
        mock_run_results = MagicMock()
        mock_run_results.fit_results = []  # Empty list
        mock_results_manager_class.return_value.run_results = mock_run_results

        result = analyze_resonance(tmp_path)

        # Should fail gracefully, not crash with IndexError
        assert not result.success
        assert result.error_step == "results_parsing"
        assert "No fit results" in result.error_message


class TestExtractManifestEnrichment:
    """Tests for enrichment parsing in extract_manifest (Issue #204)."""

    def test_manifest_default_natural_abundance(self, tmp_path):
        """Should default to use_natural_abundance=True."""
        manifest_content = """---
name: test
description: Test
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
isotope: Hf-177
---
Body
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.use_natural_abundance is True
        assert result.enrichment is None

    def test_manifest_enriched_sample(self, tmp_path):
        """Should parse enrichment for enriched samples."""
        manifest_content = """---
name: enriched_u235
description: Enriched uranium sample
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
isotope: U-235
use_natural_abundance: false
enrichment:
  U-235: 0.90
  U-238: 0.10
---
Body
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.use_natural_abundance is False
        assert result.enrichment == {"U-235": 0.90, "U-238": 0.10}


class TestGetIsotopeComposition:
    """Tests for _get_isotope_composition helper (Issue #204)."""

    def test_user_specified_isotopes_equal_weights(self):
        """User-specified isotopes should get equal weights."""
        from pleiades.workflows.resonance import _get_isotope_composition

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=["Hf-177", "Hf-178"],
            manifest=None,
            primary_isotope="Hf-177",
        )

        assert isotopes == ["Hf-177", "Hf-178"]
        assert len(abundances) == 2
        assert all(a == 0.5 for a in abundances)

    def test_enriched_sample_uses_manifest_enrichment(self):
        """Enriched samples should use manifest enrichment values."""
        from pleiades.workflows.models import ManifestData
        from pleiades.workflows.resonance import _get_isotope_composition

        manifest = ManifestData(
            name="test",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="U-235",
            use_natural_abundance=False,
            enrichment={"U-235": 0.90, "U-238": 0.10},
        )

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=None,
            manifest=manifest,
            primary_isotope="U-235",
        )

        assert set(isotopes) == {"U-235", "U-238"}
        # Find U-235's abundance
        u235_idx = isotopes.index("U-235")
        assert abs(abundances[u235_idx] - 0.90) < 0.001

    def test_natural_abundance_from_isotope_manager(self):
        """Natural abundance should come from IsotopeManager."""
        from pleiades.workflows.models import ManifestData
        from pleiades.workflows.resonance import _get_isotope_composition

        manifest = ManifestData(
            name="test",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            use_natural_abundance=True,
        )

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=None,
            manifest=manifest,
            primary_isotope="Hf-177",
        )

        # Should return all 6 natural Hf isotopes
        assert len(isotopes) == 6
        assert "Hf-174" in isotopes
        assert "Hf-180" in isotopes

        # Abundances should sum to ~1.0
        assert abs(sum(abundances) - 1.0) < 0.01

        # Hf-180 should be most abundant (~35%)
        hf180_idx = isotopes.index("Hf-180")
        assert abundances[hf180_idx] > 0.30

    def test_element_only_isotope_uses_natural_abundance(self):
        """Element-only isotope (e.g., 'Hf') should use natural abundance."""
        from pleiades.workflows.resonance import _get_isotope_composition

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=None,
            manifest=None,
            primary_isotope="Hf",
        )

        # Should return all natural Hf isotopes
        assert len(isotopes) == 6
        assert abs(sum(abundances) - 1.0) < 0.01

    def test_element_nat_suffix_uses_natural_abundance(self):
        """Element-nat isotope (e.g., 'Hf-nat') should use natural abundance."""
        from pleiades.workflows.resonance import _get_isotope_composition

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=None,
            manifest=None,
            primary_isotope="Hf-nat",
        )

        # Should return all natural Hf isotopes
        assert len(isotopes) == 6

    def test_single_natural_isotope_element_100_percent_abundance(self):
        """Elements with only one naturally occurring isotope should return that isotope with 100% abundance."""
        from pleiades.workflows.resonance import _get_isotope_composition

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=None,
            manifest=None,
            primary_isotope="Au-197",
        )

        # Gold has only one natural isotope (Au-197)
        assert len(isotopes) == 1
        assert isotopes[0] == "Au-197"
        assert abundances[0] == 1.0

    def test_unknown_element_raises_error(self):
        """Unknown element should raise ValueError."""
        from pleiades.workflows.resonance import _get_isotope_composition

        with pytest.raises(ValueError, match="No natural isotopes found"):
            _get_isotope_composition(
                user_isotopes=None,
                manifest=None,
                primary_isotope="Xx-999",
            )

    def test_empty_primary_isotope_raises(self):
        """Empty primary_isotope should raise ValueError."""
        from pleiades.workflows.resonance import _get_isotope_composition

        with pytest.raises(ValueError, match="cannot be empty"):
            _get_isotope_composition(
                user_isotopes=None,
                manifest=None,
                primary_isotope="",
            )

    def test_malformed_primary_isotope_raises(self):
        """Malformed primary_isotope should raise ValueError."""
        from pleiades.workflows.resonance import _get_isotope_composition

        # Test various malformed formats
        malformed_inputs = [
            "Hf-",  # Trailing dash
            "-177",  # Leading dash
            "177-Hf",  # Reversed format
            "hf177",  # Missing dash
            "123",  # Just numbers
        ]

        for bad_input in malformed_inputs:
            with pytest.raises(ValueError, match="Invalid primary_isotope format"):
                _get_isotope_composition(
                    user_isotopes=None,
                    manifest=None,
                    primary_isotope=bad_input,
                )


class TestGetSammyRunner:
    """Tests for _get_sammy_runner helper."""

    @patch("pleiades.sammy.factory.SammyFactory")
    def test_auto_backend(self, mock_factory, tmp_path):
        """auto backend should call SammyFactory.auto_select."""
        from pleiades.workflows.resonance import _get_sammy_runner

        working = tmp_path / "work"
        output = tmp_path / "output"

        _get_sammy_runner("auto", working, output)

        mock_factory.auto_select.assert_called_once()

    @patch("pleiades.sammy.factory.SammyFactory")
    def test_specific_backend(self, mock_factory, tmp_path):
        """Specific backend should call SammyFactory.create_runner."""
        from pleiades.workflows.resonance import _get_sammy_runner

        working = tmp_path / "work"
        output = tmp_path / "output"

        _get_sammy_runner("docker", working, output)

        mock_factory.create_runner.assert_called_once_with(
            backend_type="docker",
            working_dir=working,
            output_dir=output,
        )

    @patch("pleiades.sammy.factory.SammyFactory")
    def test_creates_directories(self, mock_factory, tmp_path):
        """Should create working and output directories."""
        from pleiades.workflows.resonance import _get_sammy_runner

        working = tmp_path / "work"
        output = tmp_path / "output"

        _get_sammy_runner("auto", working, output)

        assert working.exists()
        assert output.exists()


class TestManifestDataIsotopesField:
    """Tests for ManifestData.isotopes field (Issue #206)."""

    def test_manifest_data_isotopes_field_accepts_valid_list(self):
        """Valid isotope list should be accepted by ManifestData."""
        manifest = ManifestData(
            name="test",
            description="Test manifest with isotopes list",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            isotopes=["Hf-176", "Hf-177", "Hf-178"],
        )

        assert manifest.isotopes == ["Hf-176", "Hf-177", "Hf-178"]

    def test_manifest_data_isotopes_field_accepts_none(self):
        """None should be valid for isotopes field (no filtering)."""
        manifest = ManifestData(
            name="test",
            description="Test manifest without isotopes",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            isotopes=None,
        )

        assert manifest.isotopes is None

    def test_manifest_data_isotopes_field_accepts_empty_list(self):
        """Empty list should be valid for isotopes field."""
        manifest = ManifestData(
            name="test",
            description="Test manifest with empty isotopes list",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            isotopes=[],
        )

        assert manifest.isotopes == []

    def test_manifest_data_isotopes_field_rejects_invalid_isotope_format(self):
        """Invalid isotope formats should be rejected with validation error."""
        # Test lowercase element symbol
        with pytest.raises(ValueError, match="Invalid isotope format"):
            ManifestData(
                name="test",
                description="Test",
                version="1.0.0",
                created="2024-01-01T00:00:00Z",
                isotope="Hf-177",
                isotopes=["hf-177", "Hf-178"],  # lowercase 'hf' is invalid
            )

        # Test completely invalid format
        with pytest.raises(ValueError, match="Invalid isotope format"):
            ManifestData(
                name="test",
                description="Test",
                version="1.0.0",
                created="2024-01-01T00:00:00Z",
                isotope="Hf-177",
                isotopes=["Hf-177", "invalid"],
            )

        # Test missing hyphen
        with pytest.raises(ValueError, match="Invalid isotope format"):
            ManifestData(
                name="test",
                description="Test",
                version="1.0.0",
                created="2024-01-01T00:00:00Z",
                isotope="Hf-177",
                isotopes=["Hf177"],
            )

    def test_manifest_data_isotopes_field_rejects_non_string_elements(self):
        """Non-string elements in isotopes list should be rejected."""
        with pytest.raises(ValueError):
            ManifestData(
                name="test",
                description="Test",
                version="1.0.0",
                created="2024-01-01T00:00:00Z",
                isotope="Hf-177",
                isotopes=[177, "Hf-177"],  # Integer is invalid
            )


class TestExtractManifestIsotopesList:
    """Tests for extract_manifest parsing of isotopes list (Issue #206)."""

    def test_extract_manifest_parses_isotopes_list(self, tmp_path):
        """YAML with isotopes list should be parsed into ManifestData.isotopes."""
        manifest_content = """---
name: hf_subset
description: Hafnium sample with specific isotopes
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
isotope: Hf-177
isotopes:
  - Hf-176
  - Hf-177
  - Hf-178
---
# Analysis Instructions

Analyze only the specified isotopes.
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.isotopes == ["Hf-176", "Hf-177", "Hf-178"]
        assert result.isotope == "Hf-177"

    def test_extract_manifest_handles_missing_isotopes(self, tmp_path):
        """YAML without isotopes field should result in ManifestData.isotopes=None."""
        manifest_content = """---
name: test
description: Test without isotopes list
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
isotope: Au-197
---
Body content
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.isotopes is None
        assert result.isotope == "Au-197"

    def test_extract_manifest_handles_empty_isotopes_list(self, tmp_path):
        """YAML with empty isotopes list should result in empty list."""
        manifest_content = """---
name: test
description: Test with empty isotopes
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
isotope: Hf-177
isotopes: []
---
Body content
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.isotopes == []

    def test_extract_manifest_isotopes_list_with_enrichment(self, tmp_path):
        """Manifest can have both isotopes list and enrichment (different purposes)."""
        manifest_content = """---
name: enriched_subset
description: Enriched sample analyzing specific isotopes
version: "1.0.0"
created: "2024-01-01T00:00:00Z"
isotope: U-235
use_natural_abundance: false
enrichment:
  U-235: 0.90
  U-238: 0.10
isotopes:
  - U-235
---
Body
"""
        (tmp_path / "manifest_intermediate.md").write_text(manifest_content)

        result = extract_manifest(tmp_path)
        assert result is not None
        assert result.isotopes == ["U-235"]
        assert result.enrichment == {"U-235": 0.90, "U-238": 0.10}


class TestGetIsotopeCompositionWithManifestIsotopes:
    """Tests for _get_isotope_composition with manifest isotopes list (Issue #206)."""

    def test_get_isotope_composition_manifest_isotopes_takes_priority_over_natural(self):
        """When manifest has isotopes list (but no enrichment), use those with equal weights."""
        manifest = ManifestData(
            name="test",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            isotopes=["Hf-176", "Hf-177", "Hf-178"],
            use_natural_abundance=True,  # Natural abundance flag, but isotopes list takes priority
        )

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=None,
            manifest=manifest,
            primary_isotope="Hf-177",
        )

        # Should use manifest isotopes, not all natural Hf isotopes
        assert isotopes == ["Hf-176", "Hf-177", "Hf-178"]
        assert len(abundances) == 3
        # Equal weights for all isotopes
        assert all(abs(a - 1.0 / 3) < 0.001 for a in abundances)

    def test_get_isotope_composition_user_isotopes_takes_priority_over_manifest_isotopes(self):
        """User parameter should trump manifest isotopes list."""
        manifest = ManifestData(
            name="test",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            isotopes=["Hf-176", "Hf-177", "Hf-178"],
        )

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=["Hf-179", "Hf-180"],  # User overrides manifest
            manifest=manifest,
            primary_isotope="Hf-177",
        )

        # Should use user isotopes, not manifest isotopes
        assert isotopes == ["Hf-179", "Hf-180"]
        assert len(abundances) == 2
        assert all(a == 0.5 for a in abundances)

    def test_get_isotope_composition_isotopes_list_takes_priority_over_enrichment(self):
        """When both isotopes list and enrichment are set, isotopes list takes priority (explicit subset selection).

        The isotopes list is a more explicit declaration of which isotopes to include,
        so it takes priority over enrichment which is about abundance values.
        """
        manifest = ManifestData(
            name="test",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="U-235",
            isotopes=["U-235"],  # Manifest specifies ONLY U-235
            use_natural_abundance=False,
            enrichment={"U-235": 0.90, "U-238": 0.10},  # Enrichment has both, but isotopes list wins
        )

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=None,
            manifest=manifest,
            primary_isotope="U-235",
        )

        # Should use isotopes list (only U-235), not enrichment (both U-235 and U-238)
        assert isotopes == ["U-235"]
        assert len(abundances) == 1
        assert abundances[0] == 1.0  # Equal weight for single isotope

    def test_get_isotope_composition_manifest_isotopes_with_equal_weights(self):
        """Verify that manifest isotopes get equal weights (1/n for n isotopes)."""
        # Test with 2 isotopes
        manifest_2 = ManifestData(
            name="test2",
            description="Test with 2 isotopes",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            isotopes=["Hf-177", "Hf-178"],
        )

        isotopes_2, abundances_2 = _get_isotope_composition(
            user_isotopes=None,
            manifest=manifest_2,
            primary_isotope="Hf-177",
        )

        assert len(isotopes_2) == 2
        assert all(abs(a - 0.5) < 0.001 for a in abundances_2)

        # Test with 4 isotopes
        manifest_4 = ManifestData(
            name="test4",
            description="Test with 4 isotopes",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            isotopes=["Hf-176", "Hf-177", "Hf-178", "Hf-179"],
        )

        isotopes_4, abundances_4 = _get_isotope_composition(
            user_isotopes=None,
            manifest=manifest_4,
            primary_isotope="Hf-177",
        )

        assert len(isotopes_4) == 4
        assert all(abs(a - 0.25) < 0.001 for a in abundances_4)

    def test_get_isotope_composition_empty_manifest_isotopes_uses_natural(self):
        """Empty manifest isotopes list should fall back to natural abundance."""
        manifest = ManifestData(
            name="test",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            isotopes=[],  # Empty list should be treated as "not specified"
        )

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=None,
            manifest=manifest,
            primary_isotope="Hf-177",
        )

        # Should fall back to natural abundance (all 6 Hf isotopes)
        assert len(isotopes) == 6
        assert "Hf-174" in isotopes
        assert "Hf-180" in isotopes
        assert abs(sum(abundances) - 1.0) < 0.01

    def test_get_isotope_composition_manifest_isotopes_without_enrichment_flag(self):
        """Manifest isotopes should work regardless of use_natural_abundance flag."""
        # Test with use_natural_abundance=False but no enrichment dict
        manifest = ManifestData(
            name="test",
            description="Test",
            version="1.0.0",
            created="2024-01-01T00:00:00Z",
            isotope="Hf-177",
            isotopes=["Hf-177", "Hf-178"],
            use_natural_abundance=False,  # Flag is False
            enrichment=None,  # But no enrichment dict
        )

        isotopes, abundances = _get_isotope_composition(
            user_isotopes=None,
            manifest=manifest,
            primary_isotope="Hf-177",
        )

        # Should use manifest isotopes since enrichment is None
        assert isotopes == ["Hf-177", "Hf-178"]
        assert all(abs(a - 0.5) < 0.001 for a in abundances)
