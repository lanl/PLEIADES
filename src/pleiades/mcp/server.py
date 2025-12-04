"""PLEIADES MCP Server implementation.

This module provides the FastMCP server that exposes PLEIADES workflow functions
as MCP tools for AI-assisted neutron resonance analysis.

Full implementation in issue #166.
"""

from pleiades.mcp import MCP_AVAILABLE, check_mcp_available

if MCP_AVAILABLE:
    from fastmcp import FastMCP

    mcp = FastMCP("pleiades-mcp")

    # Tools will be registered here in issue #166
    # Example:
    # @mcp.tool
    # def analyze_resonance(dataset_path: str) -> dict:
    #     ...
else:
    mcp = None  # type: ignore[assignment]


def main() -> None:
    """Start the PLEIADES MCP server."""
    check_mcp_available()
    # mcp is guaranteed to be defined after check_mcp_available() succeeds
    mcp.run()  # type: ignore[union-attr]


__all__ = ["main"]
