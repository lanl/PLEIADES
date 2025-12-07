"""Test suite for manifest parsing functionality.

Tests cover YAML frontmatter parsing, field validation, and material properties
extraction used by MCP tools for resonance dataset analysis.

These tests verify the manifest parsing exposed through MCP workflows.
"""

import pytest

from pleiades.workflows import extract_manifest


class TestManifestFileDiscovery:
    """Test manifest file discovery with different naming conventions."""

    def test_finds_manifest_intermediate_md(self, tmp_path):
        """Should find manifest_intermediate.md first."""
        manifest_file = tmp_path / "manifest_intermediate.md"
        manifest_file.write_text(
            """---
name: test
description: test dataset
version: 1.0.0
created: 2024-01-01
---
Body content
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.name == "test"

    def test_finds_smcp_manifest_md(self, tmp_path):
        """Should find smcp_manifest.md as second priority."""
        manifest_file = tmp_path / "smcp_manifest.md"
        manifest_file.write_text(
            """---
name: smcp_test
description: test
version: 1.0.0
created: 2024-01-01
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.name == "smcp_test"

    def test_finds_manifest_md(self, tmp_path):
        """Should find manifest.md as third priority."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: plain_manifest
description: test
version: 1.0.0
created: 2024-01-01
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.name == "plain_manifest"

    def test_priority_order(self, tmp_path):
        """Should prefer manifest_intermediate.md over others."""
        # Create all three variants
        (tmp_path / "manifest.md").write_text(
            """---
name: lowest_priority
description: test
version: 1.0.0
created: 2024-01-01
---
Body
"""
        )
        (tmp_path / "smcp_manifest.md").write_text(
            """---
name: medium_priority
description: test
version: 1.0.0
created: 2024-01-01
---
Body
"""
        )
        (tmp_path / "manifest_intermediate.md").write_text(
            """---
name: highest_priority
description: test
version: 1.0.0
created: 2024-01-01
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.name == "highest_priority"

    def test_returns_none_when_no_manifest(self, tmp_path):
        """Should return None when no manifest file exists."""
        result = extract_manifest(tmp_path)

        assert result is None

    def test_handles_string_path(self, tmp_path):
        """Should accept string path in addition to Path object."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: string_path_test
description: test
version: 1.0.0
created: 2024-01-01
---
Body
"""
        )

        result = extract_manifest(str(tmp_path))

        assert result is not None
        assert result.name == "string_path_test"


class TestYamlFrontmatterParsing:
    """Test YAML frontmatter parsing."""

    def test_parses_basic_frontmatter(self, tmp_path):
        """Should parse basic YAML frontmatter correctly."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: Au197_sample
description: Gold-197 resonance dataset
version: 2.1.0
created: 2024-06-15T10:30:00
facility: SNS
beamline: VENUS
---
# Sample Analysis

This is the body content.
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.name == "Au197_sample"
        assert result.description == "Gold-197 resonance dataset"
        assert result.version == "2.1.0"
        assert result.facility == "SNS"
        assert result.beamline == "VENUS"

    def test_handles_multiline_description(self, tmp_path):
        """Should handle multiline YAML values."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: >
  This is a very long description
  that spans multiple lines.
version: 1.0.0
created: 2024-01-01
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert "long description" in result.description
        assert "multiple lines" in result.description

    def test_handles_yaml_list(self, tmp_path):
        """Should handle YAML lists in frontmatter."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
isotopes:
  - Au-197
  - Ag-107
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.raw_frontmatter.get("isotopes") == ["Au-197", "Ag-107"]

    def test_preserves_raw_frontmatter(self, tmp_path):
        """Should preserve all raw frontmatter data."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
custom_field: custom_value
nested:
  key: value
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.raw_frontmatter["custom_field"] == "custom_value"
        assert result.raw_frontmatter["nested"]["key"] == "value"

    def test_raises_for_missing_frontmatter_delimiters(self, tmp_path):
        """Should raise ValueError for missing YAML delimiters."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """name: test
description: test
version: 1.0.0
created: 2024-01-01

Body without proper delimiters
"""
        )

        with pytest.raises(ValueError, match="missing YAML frontmatter"):
            extract_manifest(tmp_path)

    def test_handles_empty_frontmatter(self, tmp_path):
        """Should handle empty YAML frontmatter gracefully."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
---
Body only, no frontmatter content
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.name == "unknown"  # Default value
        assert result.description == ""  # Default value

    def test_handles_horizontal_rule_in_body(self, tmp_path):
        """Should handle --- in body without breaking parsing."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
---
# Body Content

Some text here.

---

More text after horizontal rule.

---

Even more text.
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert "horizontal rule" in result.body
        assert "Even more text" in result.body


class TestFieldValidation:
    """Test validation and defaults for manifest fields."""

    def test_uses_defaults_for_missing_required_fields(self, tmp_path):
        """Should use defaults when required fields are missing."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
facility: SNS
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.name == "unknown"
        assert result.description == ""
        assert result.version == "1.0.0"
        assert result.created == ""

    def test_optional_fields_default_to_none(self, tmp_path):
        """Should default optional fields to None."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.facility is None
        assert result.beamline is None
        assert result.detector is None
        assert result.sample_id is None
        assert result.isotope is None
        assert result.material_properties is None

    def test_handles_all_optional_fields(self, tmp_path):
        """Should handle all optional fields when present."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: complete_manifest
description: Full manifest
version: 1.0.0
created: 2024-01-01
facility: SNS
beamline: VENUS
detector: MCP
sample_id: SAMPLE-001
isotope: Au-197
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.facility == "SNS"
        assert result.beamline == "VENUS"
        assert result.detector == "MCP"
        assert result.sample_id == "SAMPLE-001"
        assert result.isotope == "Au-197"


class TestDatetimeConversion:
    """Test datetime handling in manifest parsing."""

    def test_converts_datetime_to_isoformat(self, tmp_path):
        """Should convert datetime objects to ISO format strings."""
        manifest_file = tmp_path / "manifest.md"
        # PyYAML auto-parses ISO timestamps as datetime objects
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-06-15T10:30:45
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert isinstance(result.created, str)
        assert "2024-06-15" in result.created

    def test_handles_date_only(self, tmp_path):
        """Should handle date-only values."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-06-15
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert "2024-06-15" in result.created

    def test_handles_string_timestamp(self, tmp_path):
        """Should preserve string timestamps as-is."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: "2024-06-15T10:30:45Z"
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.created == "2024-06-15T10:30:45Z"


class TestMaterialPropertiesExtraction:
    """Test material properties parsing."""

    def test_extracts_material_properties(self, tmp_path):
        """Should extract material_properties section."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
material_properties:
  density_g_cm3: 19.32
  atomic_mass_amu: 196.97
  temperature_k: 300.0
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.material_properties is not None
        assert result.material_properties.density_g_cm3 == 19.32
        assert result.material_properties.atomic_mass_amu == 196.97
        assert result.material_properties.temperature_k == 300.0

    def test_handles_missing_optional_temperature(self, tmp_path):
        """Should handle missing temperature_k (optional field)."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
material_properties:
  density_g_cm3: 19.32
  atomic_mass_amu: 196.97
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.material_properties is not None
        assert result.material_properties.temperature_k is None

    def test_handles_empty_material_properties(self, tmp_path):
        """Should handle empty material_properties section."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
material_properties:
---
Body
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.material_properties is None

    def test_handles_invalid_material_properties_gracefully(self, tmp_path):
        """Should log warning but not fail for invalid material properties."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
material_properties:
  density_g_cm3: invalid
  atomic_mass_amu: also_invalid
---
Body
"""
        )

        # Should not raise - invalid material properties are logged but not fatal
        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.material_properties is None


class TestBodyExtraction:
    """Test markdown body extraction."""

    def test_extracts_body_content(self, tmp_path):
        """Should extract markdown body after frontmatter."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
---
# Analysis Results

This is the **body** content.

- Item 1
- Item 2
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert "# Analysis Results" in result.body
        assert "**body**" in result.body
        assert "Item 1" in result.body

    def test_strips_body_whitespace(self, tmp_path):
        """Should strip leading/trailing whitespace from body."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
---


Body with extra whitespace


"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.body == "Body with extra whitespace"

    def test_handles_empty_body(self, tmp_path):
        """Should handle empty body after frontmatter."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: test
version: 1.0.0
created: 2024-01-01
---
"""
        )

        result = extract_manifest(tmp_path)

        assert result is not None
        assert result.body == ""


class TestErrorHandling:
    """Test error handling in manifest parsing."""

    def test_handles_unreadable_file(self, tmp_path):
        """Should raise appropriate error for unreadable files."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text("content")
        manifest_file.chmod(0o000)

        try:
            with pytest.raises(PermissionError):
                extract_manifest(tmp_path)
        finally:
            manifest_file.chmod(0o644)  # Restore permissions for cleanup

    def test_handles_invalid_yaml_syntax(self, tmp_path):
        """Should raise error for invalid YAML syntax."""
        import yaml

        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: test
description: [invalid yaml
  missing closing bracket
version: 1.0.0
---
Body
"""
        )

        with pytest.raises(yaml.YAMLError):
            extract_manifest(tmp_path)

    def test_handles_binary_content(self, tmp_path):
        """Should handle files with binary content gracefully."""
        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_bytes(b"\x00\x01\x02---\nname: test\n---\nBody")

        # Binary content should be handled gracefully - returns result without crashing.
        # The binary prefix may or may not corrupt the YAML parsing depending on
        # encoding handling, but the function should not raise.
        result = extract_manifest(tmp_path)
        assert result is not None
        # Verify we got a ManifestData object back
        assert hasattr(result, "name")
        assert hasattr(result, "body")


class TestMcpToolIntegration:
    """Test manifest parsing through MCP tool interface."""

    def test_mcp_tool_uses_extract_manifest(self, tmp_path):
        """Verify MCP tool wrapper calls extract_manifest correctly."""
        from pleiades.mcp.tools import extract_resonance_manifest

        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: mcp_test
description: MCP integration test
version: 1.0.0
created: 2024-01-01
isotope: Au-197
---
Body content
"""
        )

        result = extract_resonance_manifest(str(tmp_path))

        assert result["status"] == "success"
        assert result["data"]["name"] == "mcp_test"
        assert result["data"]["isotope"] == "Au-197"

    def test_mcp_tool_returns_error_for_missing_manifest(self, tmp_path):
        """MCP tool should return error status for missing manifest."""
        from pleiades.mcp.tools import extract_resonance_manifest

        result = extract_resonance_manifest(str(tmp_path))

        assert result["status"] == "error"
        assert "No manifest found" in result["error"]

    def test_mcp_tool_returns_json_serializable_result(self, tmp_path):
        """MCP tool should return JSON-serializable result."""
        import json

        from pleiades.mcp.tools import extract_resonance_manifest

        manifest_file = tmp_path / "manifest.md"
        manifest_file.write_text(
            """---
name: json_test
description: JSON serialization test
version: 1.0.0
created: 2024-06-15T10:30:00
material_properties:
  density_g_cm3: 19.32
  atomic_mass_amu: 196.97
---
Body
"""
        )

        result = extract_resonance_manifest(str(tmp_path))

        # Should be JSON-serializable
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # Verify structure
        parsed = json.loads(json_str)
        assert parsed["status"] == "success"
        assert "data" in parsed


if __name__ == "__main__":
    pytest.main(["-v", __file__])
