#!/usr/env/bin python
"""
Interface definitions for SAMMY execution system.

This module defines the core interfaces and data structures used across
all SAMMY backend implementations.
"""

import logging
import os
from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path

from pleiades.sammy.config.config_errors import ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class BaseSammyConfig(ABC):
    """Base configuration for all SAMMY backends."""

    # Grab the current working directory as the default
    working_fit_dir: Path = field(default_factory=lambda: Path(os.getcwd()))

    # Set the results directory to a subdirectory of the working_fit_dir
    working_results_dir: Path = field(default=None)  # Results directory

    def __post_init__(self):
        """Initialize the results directory based on the working directory."""
        self.working_results_dir = self.working_results_dir or self.working_fit_dir / "results"

    def prepare_directories(self) -> None:
        """
        Create and prepare required directories.

        Raises:
            ConfigurationError: If directory creation fails
        """
        try:
            # Create needed directories if they don't exist
            self.working_fit_dir.mkdir(parents=True, exist_ok=True)
            self.working_results_dir.mkdir(parents=True, exist_ok=True)

        except Exception as e:
            raise ConfigurationError(f"Failed to create directories: {str(e)}")

    def validate(self) -> bool:
        """
        Validate the configuration.

        Returns:
            bool: True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Create directories first
        self.prepare_directories()

        # Validate working directory is writable
        if not os.access(self.working_fit_dir, os.W_OK):
            raise ConfigurationError(f"Working fit directory not writable: {self.working_dir}")

        # Validate output directory is writable
        if not os.access(self.working_results_dir, os.W_OK):
            raise ConfigurationError(f"Working results directory not writable: {self.output_dir}")

        return True
