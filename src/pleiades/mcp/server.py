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

from typing import TYPE_CHECKING

from pleiades.mcp import MCP_AVAILABLE, check_mcp_available

if TYPE_CHECKING:
    from fastmcp import FastMCP

# Server instance created at module load for decorator support
_server: FastMCP | None = None

if MCP_AVAILABLE:
    from fastmcp import FastMCP as _FastMCP

    _server = _FastMCP("pleiades-mcp")


def get_server() -> FastMCP:
    """Get the MCP server instance.

    Returns:
        The FastMCP server instance.

    Raises:
        ImportError: If MCP dependencies are not installed.
        RuntimeError: If server initialization failed unexpectedly.
    """
    check_mcp_available()
    if _server is None:
        raise RuntimeError("MCP server not initialized. This should not happen if MCP is available.")
    return _server


def main() -> None:
    """Start the PLEIADES MCP server.

    Raises:
        ImportError: If MCP dependencies are not installed.
    """
    from pleiades.utils.logger import logger

    server = get_server()
    logger.info("Starting PLEIADES MCP server...")
    server.run()


__all__ = ["get_server", "main"]
