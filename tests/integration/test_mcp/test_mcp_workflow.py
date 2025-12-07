"""Integration tests for MCP workflow.

Tests end-to-end MCP tool functionality with real dataset processing.
Some tests require Docker backend and are skipped if unavailable.
"""

import json

import pytest


class TestValidateWorkflow:
    """Test validate_resonance_dataset tool end-to-end."""

    def test_validates_sample_dataset(self, sample_dataset):
        """Should successfully validate a well-formed dataset."""
        from pleiades.mcp.tools import validate_resonance_dataset

        result = validate_resonance_dataset(str(sample_dataset))

        assert result["status"] == "success"
        assert "data" in result
        # Validation result should include key fields
        assert isinstance(result["data"], dict)

    def test_validates_nonexistent_path(self):
        """Should handle nonexistent path gracefully."""
        from pleiades.mcp.tools import validate_resonance_dataset

        result = validate_resonance_dataset("/nonexistent/path/to/dataset")

        # Should return result (not crash) - either error or validation failure
        assert "status" in result
        assert isinstance(result, dict)

    def test_result_is_json_serializable(self, sample_dataset):
        """Validation result should be fully JSON-serializable."""
        from pleiades.mcp.tools import validate_resonance_dataset

        result = validate_resonance_dataset(str(sample_dataset))

        # Should not raise
        json_str = json.dumps(result)
        parsed = json.loads(json_str)

        assert parsed["status"] == result["status"]


class TestExtractManifestWorkflow:
    """Test extract_resonance_manifest tool end-to-end."""

    def test_extracts_manifest_from_sample(self, sample_dataset):
        """Should extract manifest from valid dataset."""
        from pleiades.mcp.tools import extract_resonance_manifest

        result = extract_resonance_manifest(str(sample_dataset))

        assert result["status"] == "success"
        assert result["data"]["name"] == "integration_test_dataset"
        assert result["data"]["isotope"] == "Si-28"
        assert result["data"]["material_properties"]["density_g_cm3"] == 2.33

    def test_handles_missing_manifest(self, sample_dataset_no_manifest):
        """Should return error for missing manifest."""
        from pleiades.mcp.tools import extract_resonance_manifest

        result = extract_resonance_manifest(str(sample_dataset_no_manifest))

        assert result["status"] == "error"
        assert "No manifest found" in result["error"]

    def test_handles_invalid_manifest(self, sample_dataset_invalid_manifest):
        """Should return error for invalid manifest format."""
        from pleiades.mcp.tools import extract_resonance_manifest

        result = extract_resonance_manifest(str(sample_dataset_invalid_manifest))

        assert result["status"] == "error"
        # Should indicate format error
        assert "error" in result

    def test_manifest_result_is_json_serializable(self, sample_dataset):
        """Manifest result should be fully JSON-serializable."""
        from pleiades.mcp.tools import extract_resonance_manifest

        result = extract_resonance_manifest(str(sample_dataset))

        # datetime and other types should be converted
        json_str = json.dumps(result)
        parsed = json.loads(json_str)

        assert parsed["status"] == "success"
        assert parsed["data"]["created"] == "2024-06-15T10:00:00"


class TestAnalyzeWorkflow:
    """Test analyze_resonance tool end-to-end."""

    def test_handles_incomplete_dataset(self, sample_dataset):
        """Should handle dataset without full SAMMY setup."""
        from pleiades.mcp.tools import analyze_resonance

        # Dataset has manifest but no SAMMY files
        result = analyze_resonance(str(sample_dataset))

        # Should return error (missing required files) or partial result
        assert "status" in result
        assert isinstance(result, dict)

    def test_handles_nonexistent_path(self):
        """Should handle nonexistent path gracefully."""
        from pleiades.mcp.tools import analyze_resonance

        result = analyze_resonance("/nonexistent/path")

        # Should return a result (not crash) - may be success with validation failure
        # or error depending on how the workflow handles missing paths
        assert "status" in result
        assert isinstance(result, dict)

    def test_backend_parameter_accepted(self, sample_dataset):
        """Should accept backend parameter."""
        from pleiades.mcp.tools import analyze_resonance

        # Should not crash with different backend values
        result = analyze_resonance(str(sample_dataset), backend="auto")
        assert "status" in result

    def test_result_is_json_serializable(self, sample_dataset):
        """Analysis result should be JSON-serializable."""
        from pleiades.mcp.tools import analyze_resonance

        result = analyze_resonance(str(sample_dataset))

        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestFullWorkflowPipeline:
    """Test complete validate -> manifest -> analyze pipeline."""

    def test_pipeline_with_sample_dataset(self, sample_dataset):
        """Test complete workflow pipeline."""
        from pleiades.mcp.tools import (
            analyze_resonance,
            extract_resonance_manifest,
            validate_resonance_dataset,
        )

        # Step 1: Validate
        validation = validate_resonance_dataset(str(sample_dataset))
        assert validation["status"] == "success"

        # Step 2: Extract manifest
        manifest = extract_resonance_manifest(str(sample_dataset))
        assert manifest["status"] == "success"
        assert manifest["data"]["name"] == "integration_test_dataset"

        # Step 3: Analyze (will fail due to missing SAMMY files, but shouldn't crash)
        analysis = analyze_resonance(str(sample_dataset))
        assert "status" in analysis

    def test_pipeline_stops_on_validation_failure(self, sample_dataset_no_manifest):
        """Pipeline should handle validation/manifest failures."""
        from pleiades.mcp.tools import extract_resonance_manifest, validate_resonance_dataset

        # Validate passes (directory exists)
        validation = validate_resonance_dataset(str(sample_dataset_no_manifest))
        assert "status" in validation

        # Manifest extraction fails
        manifest = extract_resonance_manifest(str(sample_dataset_no_manifest))
        assert manifest["status"] == "error"


class TestDockerBackendIntegration:
    """Integration tests requiring Docker backend.

    These tests are skipped if Docker is not available.
    """

    @pytest.mark.skipif(
        not __import__("shutil").which("docker"),
        reason="Docker executable not available",
    )
    def test_analyze_with_docker_backend(self, sample_dataset):
        """Test analyze_resonance with explicit docker backend."""
        from pleiades.mcp.tools import analyze_resonance

        # Run analysis with docker backend
        # Will fail gracefully if SAMMY Docker image not available
        result = analyze_resonance(str(sample_dataset), backend="docker")

        # Should return a valid result structure (success or error)
        assert "status" in result
        assert isinstance(result, dict)


class TestErrorRecovery:
    """Test error recovery and graceful degradation."""

    def test_recovers_from_permission_error(self, tmp_path):
        """Should handle permission errors gracefully."""
        from pleiades.mcp.tools import validate_resonance_dataset

        # Create restricted directory
        restricted = tmp_path / "restricted"
        restricted.mkdir()
        restricted.chmod(0o000)

        try:
            result = validate_resonance_dataset(str(restricted))

            # Should return error, not crash
            assert "status" in result
        finally:
            restricted.chmod(0o755)  # Restore for cleanup

    def test_handles_empty_directory(self, tmp_path):
        """Should handle empty directory."""
        from pleiades.mcp.tools import validate_resonance_dataset

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = validate_resonance_dataset(str(empty_dir))

        assert "status" in result

    def test_handles_file_instead_of_directory(self, tmp_path):
        """Should handle file path instead of directory."""
        from pleiades.mcp.tools import validate_resonance_dataset

        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        result = validate_resonance_dataset(str(file_path))

        # Should handle gracefully
        assert "status" in result


class TestResultStructure:
    """Test that all results follow consistent structure."""

    def test_success_result_structure(self, sample_dataset):
        """Success results should have status='success' and 'data' field."""
        from pleiades.mcp.tools import extract_resonance_manifest

        result = extract_resonance_manifest(str(sample_dataset))

        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], dict)

    def test_error_result_structure(self, sample_dataset_no_manifest):
        """Error results should have status='error' and 'error' field."""
        from pleiades.mcp.tools import extract_resonance_manifest

        result = extract_resonance_manifest(str(sample_dataset_no_manifest))

        assert result["status"] == "error"
        assert "error" in result
        assert isinstance(result["error"], str)

    def test_all_tools_return_dict(self, sample_dataset):
        """All tools should return dict type."""
        from pleiades.mcp.tools import (
            analyze_resonance,
            extract_resonance_manifest,
            validate_resonance_dataset,
        )

        assert isinstance(validate_resonance_dataset(str(sample_dataset)), dict)
        assert isinstance(extract_resonance_manifest(str(sample_dataset)), dict)
        assert isinstance(analyze_resonance(str(sample_dataset)), dict)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
