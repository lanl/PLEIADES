"""PLEIADES MCP Server - AI-assisted neutron resonance analysis.

This module provides Model Context Protocol (MCP) server capabilities for PLEIADES,
enabling AI-assisted neutron resonance imaging analysis.

Installation:
    pip install pleiades-neutron[mcp]  # PyPI install
    pip install -e ".[mcp]"            # Editable install

Usage:
    pleiades-mcp           # Start the MCP server (console script)
    python -m pleiades.mcp # Module invocation

Example:
    >>> from pleiades.mcp import MCP_AVAILABLE
    >>> if MCP_AVAILABLE:
    ...     from pleiades.mcp.server import get_server
    ...     server = get_server()
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

# Attempt to import FastMCP, track availability
try:
    from fastmcp import FastMCP as _FastMCP

    MCP_AVAILABLE: bool = True
except ImportError as _import_error:
    MCP_AVAILABLE = False
    _FastMCP = None  # type: ignore[assignment, misc]
    # Warn during import so developers know MCP is unavailable
    warnings.warn(
        f"MCP dependencies not available ({_import_error}). Install with: pip install pleiades-neutron[mcp]",
        ImportWarning,
        stacklevel=2,
    )


def check_mcp_available() -> None:
    """Check if MCP dependencies are installed.

    Call this before using MCP functionality to get a clear error message.

    Raises:
        ImportError: If MCP dependencies are not installed.

    Example:
        >>> from pleiades.mcp import check_mcp_available
        >>> check_mcp_available()  # Raises ImportError if MCP not installed
    """
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP dependencies not installed.\n"
            "Install with:\n"
            "  pip install pleiades-neutron[mcp]  # PyPI install\n"
            "  pip install -e '.[mcp]'            # Editable install\n"
            "  pixi install -e mcp                # Pixi environment"
        )


# Re-export FastMCP only when available to avoid AttributeError
if MCP_AVAILABLE:
    FastMCP: type[FastMCP] = _FastMCP  # type: ignore[no-redef]
    __all__ = ["MCP_AVAILABLE", "FastMCP", "check_mcp_available"]
else:
    __all__ = ["MCP_AVAILABLE", "check_mcp_available"]
