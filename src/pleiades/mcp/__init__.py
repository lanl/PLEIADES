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

# Attempt to import FastMCP, track availability
# Following the nova backend pattern: no warning on import, clear error on use
try:
    from fastmcp import FastMCP

    MCP_AVAILABLE: bool = True
except ImportError:
    MCP_AVAILABLE = False
    FastMCP = None  # type: ignore[assignment, misc]


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


# Export FastMCP only when available
if MCP_AVAILABLE:
    __all__ = ["MCP_AVAILABLE", "FastMCP", "check_mcp_available"]
else:
    __all__ = ["MCP_AVAILABLE", "check_mcp_available"]
