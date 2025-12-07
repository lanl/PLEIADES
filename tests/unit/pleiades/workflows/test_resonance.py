"""Tests for pleiades.workflows.resonance module."""

from unittest.mock import MagicMock, patch

import pytest

from pleiades.workflows.models import WorkflowType
from pleiades.workflows.resonance import (
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
        """Dataset with both imaging data and SAMMY files should prefer simplified."""
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
        # Should prefer simplified since full is not yet implemented
        assert result.recommended_workflow == WorkflowType.SIMPLIFIED


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
