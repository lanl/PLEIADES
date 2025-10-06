"""
PLEIADES - Python Libraries Extensions for Isotopic Analysis via Detailed Examination of SAMMY.

A Python package for analyzing neutron resonance data using SAMMY.
"""

import argparse

from pleiades.utils.logger import configure_logger, loguru_logger

# Import _version if available
try:
    from ._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

# Export main components
__all__ = ["loguru_logger", "configure_logger"]


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="PLEIADES - Python Libraries Extensions for Isotopic Analysis via Detailed Examination of SAMMY",
        prog="pleiades",
    )
    parser.add_argument("--version", action="store_true", help="Print version information")
    args = parser.parse_args()

    if args.version:
        print(f"PLEIADES version {__version__}")
