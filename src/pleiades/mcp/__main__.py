"""Entry point for running PLEIADES MCP server as a module.

Usage:
    python -m pleiades.mcp

This is equivalent to running the `pleiades-mcp` console script.
"""

from __future__ import annotations

import sys


def run() -> None:
    """Run the MCP server with proper error handling."""
    try:
        from pleiades.mcp.server import main

        main()
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServer stopped.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
