"""Test suite for pleiades.mcp.tools module.

Tests cover MCP tool wrappers that expose workflow functions.

These tests define the expected API for Issue #168 (MCP prototype tools).
They are written BEFORE implementation (TDD) to guide development.

Tests verify:
- Tool registration via @mcp_tool decorator
- Input handling (string paths vs Path objects)
- Output format (JSON-serializable dicts)
- Integration with workflow functions
- Error handling and graceful degradation
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestToolRegistration:
    """Test that tools are registered via @mcp_tool decorator."""

    @classmethod
    def setup_class(cls):
        """Ensure tools module is imported (registers tools once for all tests)."""
        import pleiades.mcp.tools as _tools_module  # Import for side-effect (registration)

        del _tools_module  # Not used after import

    def test_validate_resonance_dataset_is_registered(self):
        """validate_resonance_dataset should be registered with decorator."""
        from pleiades.mcp.decorators import get_registered_tools

        tools = get_registered_tools()
        assert "validate_resonance_dataset" in tools

    def test_extract_resonance_manifest_is_registered(self):
        """extract_resonance_manifest should be registered with decorator."""
        from pleiades.mcp.decorators import get_registered_tools

        tools = get_registered_tools()
        assert "extract_resonance_manifest" in tools

    def test_analyze_resonance_is_registered(self):
        """analyze_resonance should be registered with decorator."""
        from pleiades.mcp.decorators import get_registered_tools

        tools = get_registered_tools()
        assert "analyze_resonance" in tools

    def test_all_tools_have_descriptions(self):
        """All registered tools should have descriptions."""
        from pleiades.mcp.decorators import get_registered_tools

        tools = get_registered_tools()

        for tool_name in ["validate_resonance_dataset", "extract_resonance_manifest", "analyze_resonance"]:
            assert tool_name in tools
            assert tools[tool_name]["description"]
            assert len(tools[tool_name]["description"]) > 0

    def test_tools_have_parameter_descriptions(self):
        """Tools should have parameter descriptions for better UX."""
        from pleiades.mcp.decorators import get_registered_tools

        tools = get_registered_tools()

        # validate_resonance_dataset should document dataset_path
        validate_tool = tools["validate_resonance_dataset"]
        if validate_tool.get("parameter_descriptions"):
            assert "dataset_path" in validate_tool["parameter_descriptions"]

        # extract_resonance_manifest should document dataset_path
        extract_tool = tools["extract_resonance_manifest"]
        if extract_tool.get("parameter_descriptions"):
            assert "dataset_path" in extract_tool["parameter_descriptions"]

        # analyze_resonance should document dataset_path
        analyze_tool = tools["analyze_resonance"]
        if analyze_tool.get("parameter_descriptions"):
            assert "dataset_path" in analyze_tool["parameter_descriptions"]


class TestValidateResonanceDatasetInput:
    """Test input handling for validate_resonance_dataset."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_accepts_string_path(self):
        """Tool should accept string paths (MCP convention)."""
        from pleiades.mcp.tools import validate_resonance_dataset

        # Mock the workflow function
        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = True
            mock_result.dataset_path = Path("/fake/path")
            mock_result.model_dump.return_value = {"valid": True}
            mock_validate.return_value = mock_result

            result = validate_resonance_dataset("/fake/path")

            # Should have called workflow with string converted to Path
            assert mock_validate.called
            # Result should be a dict
            assert isinstance(result, dict)

    def test_accepts_absolute_path(self):
        """Tool should accept absolute paths."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = True
            mock_result.dataset_path = Path("/absolute/path")
            mock_result.model_dump.return_value = {"valid": True}
            mock_validate.return_value = mock_result

            result = validate_resonance_dataset("/absolute/path/to/dataset")

            assert mock_validate.called
            assert isinstance(result, dict)

    def test_accepts_relative_path(self):
        """Tool should accept relative paths."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = True
            mock_result.dataset_path = Path("relative/path")
            mock_result.model_dump.return_value = {"valid": True}
            mock_validate.return_value = mock_result

            result = validate_resonance_dataset("relative/path")

            assert mock_validate.called
            assert isinstance(result, dict)

    def test_handles_nonexistent_path_gracefully(self):
        """Tool should handle non-existent paths without raising exceptions."""
        from pleiades.mcp.tools import validate_resonance_dataset

        # Real workflow returns ValidationResult with valid=False for missing paths
        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = False
            mock_result.dataset_path = Path("/nonexistent")
            mock_result.model_dump.return_value = {"valid": False, "issues": []}
            mock_validate.return_value = mock_result

            # Should not raise - should return error result
            result = validate_resonance_dataset("/nonexistent/path")

            assert isinstance(result, dict)
            assert "status" in result
            # Error results should have status='error' or success=False


class TestValidateResonanceDatasetOutput:
    """Test output format for validate_resonance_dataset."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_returns_json_serializable_dict(self):
        """Tool should return JSON-serializable dict."""
        import json

        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = True
            mock_result.dataset_path = Path("/fake")
            mock_result.model_dump.return_value = {"valid": True, "dataset_path": "/fake"}
            mock_validate.return_value = mock_result

            result = validate_resonance_dataset("/fake/path")

            # Should be JSON-serializable
            json_str = json.dumps(result)
            assert isinstance(json_str, str)

    def test_includes_status_field(self):
        """Result should include status field (success/error)."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = True
            mock_result.dataset_path = Path("/fake")
            mock_result.model_dump.return_value = {"valid": True}
            mock_validate.return_value = mock_result

            result = validate_resonance_dataset("/fake/path")

            # Should have status field
            assert "status" in result
            assert result["status"] in ["success", "error"]

    def test_success_result_has_data_field(self):
        """Successful result should include data field with validation results."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_validation = MagicMock()
            mock_validation.valid = True
            mock_validation.dataset_path = Path("/fake")
            mock_validation.can_run_full_workflow = False
            mock_validation.can_run_simplified_workflow = True
            mock_validation.model_dump.return_value = {
                "valid": True,
                "dataset_path": "/fake",
                "can_run_full_workflow": False,
                "can_run_simplified_workflow": True,
            }
            mock_validate.return_value = mock_validation

            result = validate_resonance_dataset("/fake/path")

            assert result["status"] == "success"
            assert "data" in result
            assert isinstance(result["data"], dict)
            assert result["data"]["valid"] is True

    def test_error_result_has_error_field(self):
        """Error result should include error message."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            # Simulate workflow raising exception
            mock_validate.side_effect = ValueError("Invalid dataset")

            result = validate_resonance_dataset("/fake/path")

            assert result["status"] == "error"
            assert "error" in result
            assert "Invalid dataset" in result["error"]

    def test_converts_path_objects_to_strings(self):
        """Path objects in result should be converted to strings for JSON."""
        import json

        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = True
            mock_result.dataset_path = Path("/fake/path")
            mock_result.model_dump.return_value = {
                "valid": True,
                "dataset_path": "/fake/path",  # Already converted
            }
            mock_validate.return_value = mock_result

            result = validate_resonance_dataset("/fake/path")

            # Should be JSON-serializable (no Path objects)
            json_str = json.dumps(result)
            assert isinstance(json_str, str)

            # Verify dataset_path is a string
            if "data" in result and "dataset_path" in result["data"]:
                assert isinstance(result["data"]["dataset_path"], str)


class TestExtractResonanceManifestInput:
    """Test input handling for extract_resonance_manifest."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_accepts_string_path(self):
        """Tool should accept string paths."""
        from pleiades.mcp.tools import extract_resonance_manifest

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            mock_extract.return_value = None

            result = extract_resonance_manifest("/fake/path")

            assert mock_extract.called
            assert isinstance(result, dict)

    def test_handles_missing_manifest_gracefully(self):
        """Tool should handle missing manifest without raising exceptions."""
        from pleiades.mcp.tools import extract_resonance_manifest

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            # Workflow returns None for missing manifest
            mock_extract.return_value = None

            result = extract_resonance_manifest("/fake/path")

            assert isinstance(result, dict)
            assert "status" in result


class TestExtractResonanceManifestOutput:
    """Test output format for extract_resonance_manifest."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_returns_json_serializable_dict(self):
        """Tool should return JSON-serializable dict."""
        import json

        from pleiades.mcp.tools import extract_resonance_manifest

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            mock_manifest = MagicMock()
            mock_manifest.model_dump.return_value = {
                "name": "test",
                "description": "test dataset",
                "version": "1.0.0",
                "created": "2024-01-01T00:00:00",
            }
            mock_extract.return_value = mock_manifest

            result = extract_resonance_manifest("/fake/path")

            # Should be JSON-serializable
            json_str = json.dumps(result)
            assert isinstance(json_str, str)

    def test_success_result_has_manifest_data(self):
        """Successful result should include manifest data."""
        from pleiades.mcp.tools import extract_resonance_manifest

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            mock_manifest = MagicMock()
            mock_manifest.model_dump.return_value = {
                "name": "Au197_sample",
                "description": "Gold sample",
                "version": "1.0.0",
                "created": "2024-01-01T00:00:00",
                "isotope": "Au-197",
            }
            mock_extract.return_value = mock_manifest

            result = extract_resonance_manifest("/fake/path")

            assert result["status"] == "success"
            assert "data" in result
            assert result["data"]["name"] == "Au197_sample"
            assert result["data"]["isotope"] == "Au-197"

    def test_missing_manifest_returns_error(self):
        """Missing manifest should return error status."""
        from pleiades.mcp.tools import extract_resonance_manifest

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            # Workflow returns None when no manifest found
            mock_extract.return_value = None

            result = extract_resonance_manifest("/fake/path")

            assert result["status"] == "error"
            assert "error" in result

    def test_invalid_manifest_returns_error(self):
        """Invalid manifest should return error result."""
        from pleiades.mcp.tools import extract_resonance_manifest

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            # Workflow raises ValueError for invalid manifest
            mock_extract.side_effect = ValueError("Invalid manifest format")

            result = extract_resonance_manifest("/fake/path")

            assert result["status"] == "error"
            assert "error" in result
            assert "Invalid manifest" in result["error"]


class TestAnalyzeResonanceInput:
    """Test input handling for analyze_resonance."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_accepts_string_path(self):
        """Tool should accept string paths."""
        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.model_dump.return_value = {"success": True}
            mock_analyze.return_value = mock_result

            result = analyze_resonance("/fake/path")

            assert mock_analyze.called
            assert isinstance(result, dict)

    def test_passes_backend_parameter(self):
        """Tool should pass backend parameter to workflow."""
        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.model_dump.return_value = {"success": True}
            mock_analyze.return_value = mock_result

            analyze_resonance("/fake/path", backend="docker")

            # Verify backend was passed
            call_kwargs = mock_analyze.call_args[1]
            assert call_kwargs["backend"] == "docker"

    def test_backend_defaults_to_auto(self):
        """Tool should default backend to 'auto'."""
        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.model_dump.return_value = {"success": True}
            mock_analyze.return_value = mock_result

            analyze_resonance("/fake/path")

            call_kwargs = mock_analyze.call_args[1]
            assert call_kwargs["backend"] == "auto"


class TestAnalyzeResonanceOutput:
    """Test output format for analyze_resonance."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_returns_json_serializable_dict(self):
        """Tool should return JSON-serializable dict."""
        import json

        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.chi_squared = 1.5
            mock_result.reduced_chi_squared = 1.2
            mock_result.model_dump.return_value = {
                "success": True,
                "chi_squared": 1.5,
                "reduced_chi_squared": 1.2,
            }
            mock_analyze.return_value = mock_result

            result = analyze_resonance("/fake/path")

            # Should be JSON-serializable
            json_str = json.dumps(result)
            assert isinstance(json_str, str)

    def test_success_result_has_analysis_data(self):
        """Successful result should include analysis data."""
        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.chi_squared = 1.5
            mock_result.reduced_chi_squared = 1.2
            mock_result.primary_isotope = "Au-197"
            mock_result.model_dump.return_value = {
                "success": True,
                "chi_squared": 1.5,
                "reduced_chi_squared": 1.2,
                "primary_isotope": "Au-197",
            }
            mock_analyze.return_value = mock_result

            result = analyze_resonance("/fake/path")

            assert result["status"] == "success"
            assert "data" in result
            assert result["data"]["success"] is True
            assert result["data"]["primary_isotope"] == "Au-197"

    def test_failed_analysis_returns_error(self):
        """Failed analysis should return error status."""
        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error_message = "SAMMY execution failed"
            mock_result.model_dump.return_value = {
                "success": False,
                "error_message": "SAMMY execution failed",
            }
            mock_analyze.return_value = mock_result

            result = analyze_resonance("/fake/path")

            # Could be success status with success=False in data
            # OR error status with error message
            # Both are valid designs - test accepts either
            assert "status" in result
            if result["status"] == "success":
                assert result["data"]["success"] is False
            else:
                assert result["status"] == "error"

    def test_exception_returns_error(self):
        """Workflow exception should return error result."""
        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_analyze.side_effect = RuntimeError("SAMMY not available")

            result = analyze_resonance("/fake/path")

            assert result["status"] == "error"
            assert "error" in result
            assert "SAMMY not available" in result["error"]

    def test_converts_path_objects_to_strings(self):
        """Path objects in result should be converted to strings."""
        import json

        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.output_dir = Path("/fake/output")
            mock_result.model_dump.return_value = {
                "success": True,
                "output_dir": "/fake/output",  # Already converted
            }
            mock_analyze.return_value = mock_result

            result = analyze_resonance("/fake/path")

            # Should be JSON-serializable
            json_str = json.dumps(result)
            assert isinstance(json_str, str)


class TestWorkflowIntegration:
    """Test integration with workflow functions."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_validate_dataset_calls_workflow_function(self):
        """validate_resonance_dataset should call workflows.validate_dataset."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = True
            mock_result.model_dump.return_value = {"valid": True}
            mock_validate.return_value = mock_result

            validate_resonance_dataset("/test/path")

            # Should have called the workflow function
            assert mock_validate.called
            # Should have passed the path (as string or Path)
            call_args = mock_validate.call_args[0]
            assert len(call_args) == 1

    def test_extract_manifest_calls_workflow_function(self):
        """extract_resonance_manifest should call workflows.extract_manifest."""
        from pleiades.mcp.tools import extract_resonance_manifest

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            mock_extract.return_value = None

            extract_resonance_manifest("/test/path")

            assert mock_extract.called

    def test_analyze_resonance_calls_workflow_function(self):
        """analyze_resonance should call workflows.analyze_resonance."""
        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.model_dump.return_value = {"success": True}
            mock_analyze.return_value = mock_result

            analyze_resonance("/test/path")

            assert mock_analyze.called

    def test_workflow_result_is_properly_formatted(self):
        """Workflow results should be converted to MCP-friendly format."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            # Create realistic ValidationResult mock
            mock_result = MagicMock()
            mock_result.valid = True
            mock_result.dataset_path = Path("/test")
            mock_result.can_run_full_workflow = False
            mock_result.can_run_simplified_workflow = True
            mock_result.has_manifest = True
            mock_result.model_dump.return_value = {
                "valid": True,
                "dataset_path": "/test",
                "can_run_full_workflow": False,
                "can_run_simplified_workflow": True,
                "has_manifest": True,
            }
            mock_validate.return_value = mock_result

            result = validate_resonance_dataset("/test")

            # Should be properly formatted
            assert "status" in result
            assert "data" in result
            assert isinstance(result["data"], dict)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_validate_dataset_handles_permission_error(self):
        """validate_resonance_dataset should handle permission errors."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_validate.side_effect = PermissionError("Access denied")

            result = validate_resonance_dataset("/restricted/path")

            assert result["status"] == "error"
            assert "error" in result

    def test_extract_manifest_handles_yaml_error(self):
        """extract_resonance_manifest should handle YAML parsing errors."""
        from pleiades.mcp.tools import extract_resonance_manifest

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            mock_extract.side_effect = ValueError("Invalid YAML format")

            result = extract_resonance_manifest("/test/path")

            assert result["status"] == "error"
            assert "error" in result

    def test_analyze_resonance_handles_sammy_error(self):
        """analyze_resonance should handle SAMMY execution errors."""
        from pleiades.mcp.tools import analyze_resonance

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_analyze.side_effect = RuntimeError("SAMMY executable not found")

            result = analyze_resonance("/test/path")

            assert result["status"] == "error"
            assert "error" in result

    def test_empty_path_handled_gracefully(self):
        """Empty path should be handled gracefully."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = False
            mock_result.model_dump.return_value = {"valid": False}
            mock_validate.return_value = mock_result

            result = validate_resonance_dataset("")

            assert isinstance(result, dict)
            assert "status" in result

    def test_none_result_from_workflow_handled(self):
        """None result from workflow should be handled."""
        from pleiades.mcp.tools import extract_resonance_manifest

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            mock_extract.return_value = None

            result = extract_resonance_manifest("/test/path")

            assert isinstance(result, dict)
            assert "status" in result


class TestOutputConsistency:
    """Test consistency of output format across all tools."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_all_tools_return_dict(self):
        """All tools should return dict."""
        from pleiades.mcp.tools import (
            analyze_resonance,
            extract_resonance_manifest,
            validate_resonance_dataset,
        )

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {}
            mock_validate.return_value = mock_result
            result = validate_resonance_dataset("/test")
            assert isinstance(result, dict)

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            mock_extract.return_value = None
            result = extract_resonance_manifest("/test")
            assert isinstance(result, dict)

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {}
            mock_analyze.return_value = mock_result
            result = analyze_resonance("/test")
            assert isinstance(result, dict)

    def test_all_tools_include_status_field(self):
        """All tools should include status field."""
        from pleiades.mcp.tools import (
            analyze_resonance,
            extract_resonance_manifest,
            validate_resonance_dataset,
        )

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {}
            mock_validate.return_value = mock_result
            result = validate_resonance_dataset("/test")
            assert "status" in result

        with patch("pleiades.mcp.tools.workflows.extract_manifest") as mock_extract:
            mock_extract.return_value = None
            result = extract_resonance_manifest("/test")
            assert "status" in result

        with patch("pleiades.mcp.tools.workflows.analyze_resonance") as mock_analyze:
            mock_result = MagicMock()
            mock_result.model_dump.return_value = {}
            mock_analyze.return_value = mock_result
            result = analyze_resonance("/test")
            assert "status" in result

    def test_success_results_have_data_field(self):
        """Successful results should have data field."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_result = MagicMock()
            mock_result.valid = True
            mock_result.model_dump.return_value = {"valid": True}
            mock_validate.return_value = mock_result

            result = validate_resonance_dataset("/test")

            if result["status"] == "success":
                assert "data" in result

    def test_error_results_have_error_field(self):
        """Error results should have error field."""
        from pleiades.mcp.tools import validate_resonance_dataset

        with patch("pleiades.mcp.tools.workflows.validate_dataset") as mock_validate:
            mock_validate.side_effect = ValueError("Test error")

            result = validate_resonance_dataset("/test")

            if result["status"] == "error":
                assert "error" in result


class TestParameterDescriptions:
    """Test that tools have helpful parameter descriptions."""

    def setup_method(self):
        """Ensure tools are registered by reloading if needed."""
        import importlib

        from pleiades.mcp.decorators import get_registered_tools

        # If registry is empty (cleared by previous tests), reload to re-register
        if not get_registered_tools():
            import pleiades.mcp.tools as tools_module

            importlib.reload(tools_module)

    def test_validate_dataset_has_parameter_description(self):
        """validate_resonance_dataset should document its parameters."""
        from pleiades.mcp.decorators import get_registered_tools

        tools = get_registered_tools()
        tool = tools["validate_resonance_dataset"]

        # Parameter descriptions are optional but recommended
        if tool.get("parameter_descriptions"):
            assert "dataset_path" in tool["parameter_descriptions"]

    def test_extract_manifest_has_parameter_description(self):
        """extract_resonance_manifest should document its parameters."""
        from pleiades.mcp.decorators import get_registered_tools

        tools = get_registered_tools()
        tool = tools["extract_resonance_manifest"]

        if tool.get("parameter_descriptions"):
            assert "dataset_path" in tool["parameter_descriptions"]

    def test_analyze_resonance_has_parameter_descriptions(self):
        """analyze_resonance should document its parameters."""
        from pleiades.mcp.decorators import get_registered_tools

        tools = get_registered_tools()
        tool = tools["analyze_resonance"]

        if tool.get("parameter_descriptions"):
            # Should document at least the main parameter
            assert "dataset_path" in tool["parameter_descriptions"]


class TestJsonSerializationEdgeCases:
    """Test _convert_to_json_serializable handles all edge cases."""

    def test_circular_reference_protection(self):
        """Should detect deeply nested structures that exceed depth limit."""
        from pleiades.mcp.tools import _convert_to_json_serializable

        # Create deeply nested structure exceeding _MAX_SERIALIZATION_DEPTH (100)
        deep = {"level": 0}
        current = deep
        for i in range(150):
            current["next"] = {"level": i + 1}
            current = current["next"]

        with pytest.raises(ValueError, match="maximum serialization depth"):
            _convert_to_json_serializable(deep)

    def test_handles_datetime(self):
        """Should convert datetime to ISO format string."""
        import json
        from datetime import datetime

        from pleiades.mcp.tools import _convert_to_json_serializable

        dt = datetime(2024, 6, 15, 12, 30, 45)
        result = _convert_to_json_serializable(dt)

        assert result == "2024-06-15T12:30:45"
        # Verify JSON-serializable
        json.dumps(result)

    def test_handles_date(self):
        """Should convert date to ISO format string."""
        import json
        from datetime import date

        from pleiades.mcp.tools import _convert_to_json_serializable

        d = date(2024, 6, 15)
        result = _convert_to_json_serializable(d)

        assert result == "2024-06-15"
        json.dumps(result)

    def test_handles_time(self):
        """Should convert time to ISO format string."""
        import json
        from datetime import time

        from pleiades.mcp.tools import _convert_to_json_serializable

        t = time(12, 30, 45)
        result = _convert_to_json_serializable(t)

        assert result == "12:30:45"
        json.dumps(result)

    def test_handles_decimal(self):
        """Should convert Decimal to float."""
        import json
        from decimal import Decimal

        from pleiades.mcp.tools import _convert_to_json_serializable

        d = Decimal("3.14159")
        result = _convert_to_json_serializable(d)

        assert isinstance(result, float)
        assert abs(result - 3.14159) < 0.00001
        json.dumps(result)

    def test_handles_bytes(self):
        """Should convert bytes to UTF-8 string."""
        import json

        from pleiades.mcp.tools import _convert_to_json_serializable

        b = b"hello world"
        result = _convert_to_json_serializable(b)

        assert result == "hello world"
        json.dumps(result)

    def test_handles_bytes_with_invalid_utf8(self):
        """Should handle bytes with invalid UTF-8 using replacement."""
        import json

        from pleiades.mcp.tools import _convert_to_json_serializable

        b = b"hello \xff\xfe world"
        result = _convert_to_json_serializable(b)

        assert isinstance(result, str)
        assert "hello" in result
        assert "world" in result
        json.dumps(result)

    def test_handles_set(self):
        """Should convert set to sorted list."""
        import json

        from pleiades.mcp.tools import _convert_to_json_serializable

        s = {3, 1, 2}
        result = _convert_to_json_serializable(s)

        assert isinstance(result, list)
        assert result == [1, 2, 3]
        json.dumps(result)

    def test_handles_frozenset(self):
        """Should convert frozenset to sorted list."""
        import json

        from pleiades.mcp.tools import _convert_to_json_serializable

        fs = frozenset(["c", "a", "b"])
        result = _convert_to_json_serializable(fs)

        assert isinstance(result, list)
        assert result == ["a", "b", "c"]
        json.dumps(result)

    def test_handles_enum(self):
        """Should convert Enum to its value."""
        import json
        from enum import Enum

        from pleiades.mcp.tools import _convert_to_json_serializable

        class Color(Enum):
            RED = "red"
            GREEN = "green"

        result = _convert_to_json_serializable(Color.RED)

        assert result == "red"
        json.dumps(result)

    def test_handles_int_enum(self):
        """Should convert IntEnum to its value."""
        import json
        from enum import IntEnum

        from pleiades.mcp.tools import _convert_to_json_serializable

        class Priority(IntEnum):
            LOW = 1
            HIGH = 2

        result = _convert_to_json_serializable(Priority.HIGH)

        assert result == 2
        json.dumps(result)

    def test_handles_unknown_type_with_fallback(self):
        """Should convert unknown types to string with warning."""
        import json

        from pleiades.mcp.tools import _convert_to_json_serializable

        class CustomClass:
            def __str__(self):
                return "custom_instance"

        obj = CustomClass()
        result = _convert_to_json_serializable(obj)

        assert result == "custom_instance"
        json.dumps(result)

    def test_handles_nested_mixed_types(self):
        """Should handle complex nested structures with mixed types."""
        import json
        from datetime import datetime
        from decimal import Decimal
        from enum import Enum

        from pleiades.mcp.tools import _convert_to_json_serializable

        class Status(Enum):
            ACTIVE = "active"

        data = {
            "timestamp": datetime(2024, 1, 1, 12, 0),
            "values": {1, 2, 3},
            "price": Decimal("99.99"),
            "status": Status.ACTIVE,
            "nested": {
                "path": Path("/test/path"),
                "items": [datetime(2024, 1, 2), b"data"],
            },
        }

        result = _convert_to_json_serializable(data)

        # Verify all types converted
        assert result["timestamp"] == "2024-01-01T12:00:00"
        assert result["values"] == [1, 2, 3]
        assert isinstance(result["price"], float)
        assert result["status"] == "active"
        assert result["nested"]["path"] == "/test/path"
        assert result["nested"]["items"][0] == "2024-01-02T00:00:00"
        assert result["nested"]["items"][1] == "data"

        # Verify entire result is JSON-serializable
        json.dumps(result)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
