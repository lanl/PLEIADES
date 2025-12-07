#!/usr/bin/env python
"""Test suite for pleiades.mcp module initialization.

Tests cover:
- MCP availability detection
- Graceful degradation when MCP dependencies are missing
- Conditional exports
- Error message clarity
"""

import pytest

# Detect fastmcp availability at module load (correct pattern)
try:
    import fastmcp  # noqa: F401

    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False


class TestMCPAvailability:
    """Test MCP availability detection and reporting."""

    def test_mcp_available_flag_is_boolean(self):
        """MCP_AVAILABLE should be a boolean."""
        from pleiades.mcp import MCP_AVAILABLE

        assert isinstance(MCP_AVAILABLE, bool)

    def test_mcp_available_matches_fastmcp_installed(self):
        """MCP_AVAILABLE should match whether fastmcp is installed."""
        from pleiades.mcp import MCP_AVAILABLE

        assert MCP_AVAILABLE == HAS_FASTMCP

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_fastmcp_exported_when_available(self):
        """FastMCP should be importable when available."""
        from pleiades.mcp import FastMCP

        assert FastMCP is not None


class TestCheckMCPAvailable:
    """Test check_mcp_available function."""

    def test_check_mcp_available_exists(self):
        """check_mcp_available should be importable."""
        from pleiades.mcp import check_mcp_available

        assert callable(check_mcp_available)

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_check_mcp_available_does_not_raise_when_installed(self):
        """check_mcp_available should not raise when MCP is installed."""
        from pleiades.mcp import check_mcp_available

        # Should not raise
        check_mcp_available()

    @pytest.mark.skipif(HAS_FASTMCP, reason="fastmcp is installed")
    def test_check_mcp_available_raises_when_not_installed(self):
        """check_mcp_available should raise ImportError when MCP is not installed."""
        from pleiades.mcp import check_mcp_available

        with pytest.raises(ImportError, match="MCP dependencies not installed"):
            check_mcp_available()


class TestServerModule:
    """Test server module components."""

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_get_server_returns_fastmcp_instance(self):
        """get_server should return a FastMCP instance."""
        from pleiades.mcp.server import get_server

        server = get_server()
        assert server is not None
        assert server.name == "pleiades-mcp"

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_get_server_returns_same_instance(self):
        """get_server should return the same instance on multiple calls."""
        from pleiades.mcp.server import get_server

        server1 = get_server()
        server2 = get_server()
        assert server1 is server2

    def test_main_function_is_callable(self):
        """main function should be importable and callable."""
        from pleiades.mcp.server import main

        assert callable(main)


class TestModuleEntry:
    """Test module entry point (__main__)."""

    def test_run_function_exists(self):
        """run function should be importable from __main__."""
        from pleiades.mcp.__main__ import run

        assert callable(run)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
