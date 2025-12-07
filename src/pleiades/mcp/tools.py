"""MCP tool wrappers for PLEIADES workflow functions.

This module exposes PLEIADES workflow functions as MCP tools using
the @mcp_tool decorator. Tools accept string paths (MCP convention)
and return JSON-serializable dicts.

Output format:
    Success: {"status": "success", "data": {...}}
    Error: {"status": "error", "error": "error message"}

Security Notes:
    These tools accept any file system path provided by the MCP client.
    Path traversal (../) is permitted - ensure MCP server runs with
    appropriate file system permissions for your deployment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pleiades.mcp.decorators import mcp_tool
from pleiades.utils.logger import loguru_logger
from pleiades.workflows import resonance as workflows

logger = loguru_logger.bind(name=__name__)

# Maximum recursion depth for JSON serialization (protects against circular refs)
_MAX_SERIALIZATION_DEPTH = 100


def _convert_to_json_serializable(obj: Any, _depth: int = 0) -> Any:
    """Convert an object to JSON-serializable format.

    Handles Path objects, Pydantic models, and nested structures.
    Includes depth protection against circular references.

    Args:
        obj: Object to convert.
        _depth: Internal recursion depth counter (do not set manually).

    Returns:
        JSON-serializable version of the object.

    Raises:
        ValueError: If recursion depth exceeds limit (possible circular reference).
    """
    if _depth > _MAX_SERIALIZATION_DEPTH:
        raise ValueError("Exceeded maximum serialization depth (possible circular reference)")

    if obj is None:
        return None
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "model_dump"):
        # Pydantic model - use JSON mode for proper datetime/etc serialization
        return _convert_to_json_serializable(obj.model_dump(mode="json"), _depth + 1)
    if isinstance(obj, dict):
        return {k: _convert_to_json_serializable(v, _depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_to_json_serializable(item, _depth + 1) for item in obj]
    # Primitive types (str, int, float, bool) are already serializable
    return obj


@mcp_tool(
    description="Validate a neutron resonance dataset structure and check readiness for analysis.",
    parameter_descriptions={
        "dataset_path": "Path to the dataset directory containing resonance data.",
    },
)
def validate_resonance_dataset(dataset_path: str) -> dict:
    """Validate a resonance dataset for analysis.

    Checks that the dataset has the required structure and files
    to run resonance analysis.

    Args:
        dataset_path: Path to the dataset directory.

    Returns:
        Dict with status and validation results or error message.
    """
    try:
        path = Path(dataset_path)
        result = workflows.validate_dataset(path)

        # Convert result to JSON-serializable dict
        data = _convert_to_json_serializable(result)

        return {
            "status": "success",
            "data": data,
        }
    except Exception as e:
        logger.warning(f"validate_resonance_dataset failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@mcp_tool(
    description="Extract and parse the manifest from a neutron resonance dataset.",
    parameter_descriptions={
        "dataset_path": "Path to the dataset directory containing a manifest file.",
    },
)
def extract_resonance_manifest(dataset_path: str) -> dict:
    """Extract manifest from a resonance dataset.

    Searches for manifest files in the dataset directory and extracts
    the YAML frontmatter containing dataset metadata.

    Args:
        dataset_path: Path to the dataset directory.

    Returns:
        Dict with status and manifest data or error message.
    """
    try:
        path = Path(dataset_path)
        # Pass directory path - workflow searches for manifest files internally
        result = workflows.extract_manifest(path)

        if result is None:
            return {
                "status": "error",
                "error": f"No manifest found in {path} (searched: manifest.md, smcp_manifest.md, manifest_intermediate.md)",
            }

        # Convert result to JSON-serializable dict
        data = _convert_to_json_serializable(result)

        return {
            "status": "success",
            "data": data,
        }
    except Exception as e:
        logger.warning(f"extract_resonance_manifest failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@mcp_tool(
    description="Perform neutron resonance analysis on a dataset using SAMMY.",
    parameter_descriptions={
        "dataset_path": "Path to the dataset directory containing resonance data.",
        "backend": "SAMMY execution backend: 'auto', 'local', 'docker', or 'nova'.",
    },
)
def analyze_resonance(dataset_path: str, backend: str = "auto") -> dict:
    """Analyze a resonance dataset.

    Runs resonance analysis on the dataset using the appropriate
    workflow (full imaging or simplified SAMMY-only).

    Args:
        dataset_path: Path to the dataset directory.
        backend: SAMMY execution backend (default: "auto").

    Returns:
        Dict with status and analysis results or error message.
    """
    try:
        path = Path(dataset_path)
        result = workflows.analyze_resonance(path, backend=backend)

        if result is None:
            return {
                "status": "error",
                "error": "Analysis returned no results",
            }

        # Convert result to JSON-serializable dict
        data = _convert_to_json_serializable(result)

        return {
            "status": "success",
            "data": data,
        }
    except Exception as e:
        logger.warning(f"analyze_resonance failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


__all__ = [
    "analyze_resonance",
    "extract_resonance_manifest",
    "validate_resonance_dataset",
]
