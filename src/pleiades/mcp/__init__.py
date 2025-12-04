"""PLEIADES MCP Server - AI-assisted neutron resonance analysis.

This module provides Model Context Protocol (MCP) server capabilities for PLEIADES,
enabling AI-assisted neutron resonance imaging analysis.

Installation:
    pip install pleiades-neutron[mcp]

Usage:
    pleiades-mcp  # Start the MCP server
    python -m pleiades.mcp  # Alternative
"""

try:
    from fastmcp import FastMCP as _FastMCP

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    _FastMCP = None  # type: ignore[misc, assignment]


def check_mcp_available() -> None:
    """Check if MCP dependencies are installed.

    Raises:
        ImportError: If MCP dependencies are not installed.
    """
    if not MCP_AVAILABLE:
        raise ImportError("MCP dependencies not installed. Install with: pip install pleiades-neutron[mcp]")


# Re-export FastMCP only when available to avoid confusion
if MCP_AVAILABLE:
    FastMCP = _FastMCP
    __all__ = ["MCP_AVAILABLE", "FastMCP", "check_mcp_available"]
else:
    __all__ = ["MCP_AVAILABLE", "check_mcp_available"]
