"""PLEIADES MCP Server implementation.

This module provides the FastMCP server that exposes PLEIADES workflow functions
as MCP tools for AI-assisted neutron resonance analysis.

The server instance is created at module load time to support decorator-based
tool registration (@mcp.tool). Use get_server() for type-safe access.

Usage:
    pleiades-mcp          # Console script
    python -m pleiades.mcp  # Module invocation

TODO(#166): Add tool registration and discovery.
"""

from __future__ import annotations

from pleiades.mcp import MCP_AVAILABLE, check_mcp_available

# Server instance created at module load for decorator support
_server = None

if MCP_AVAILABLE:
    from fastmcp import FastMCP

    _server = FastMCP("pleiades-mcp")


def get_server():
    """Get the MCP server instance.

    Returns:
        The FastMCP server instance.

    Raises:
        ImportError: If MCP dependencies are not installed.
    """
    check_mcp_available()
    # After check_mcp_available() passes, _server is guaranteed to be initialized
    return _server


def main() -> None:
    """Start the PLEIADES MCP server.

    Raises:
        ImportError: If MCP dependencies are not installed.
    """
    from pleiades.utils.logger import loguru_logger

    server = get_server()
    loguru_logger.info("Starting PLEIADES MCP server...")
    server.run()


__all__ = ["get_server", "main"]
