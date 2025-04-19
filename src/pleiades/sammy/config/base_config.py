#!/usr/env/bin python
"""
base configuration for all SAMMY runs on all backends
This module defines the `BaseSammyConfig` class, which serves as the foundation
for all SAMMY backend configurations.

This class should be called first to initialize the configuration of the working fit directory
and the working results directory. Then once the input, parameter, and data files are set,
the `validate` method should be called to check the configuration's validity.

The `BaseSammyConfig` class is designed to be extended by specific backend
configurations, such as local SAMMY execution, Docker-based execution, or
web service-based execution (e.g., NOVA). It is not intended to be instantiated
directly but rather to act as a blueprint for concrete implementations.
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
    """
    Base configuration for SAMMY runs.

    This module defines the `BaseSammyConfig` class, which serves as the foundation
    for all SAMMY backend configurations. It provides common functionality and
    interfaces required for running SAMMY simulations, including:

    1. Managing the working directory (`working_fit_dir`) where SAMMY is executed.
    2. Managing the results directory (`working_results_dir`) where output files
    are stored after execution.
    3. Ensuring that required directories are created and writable.
    4. Providing validation methods to check if configured properly before execution of SAMMY.

    Classes that inherit from `BaseSammyConfig` should implement additional
    backend-specific functionality and validation logic as needed.
    """

    # Input and parameter files for SAMMY.
    # Not initialized until provided by user
    input_file: Path = field(init=False, repr=False)
    parameter_file: Path = field(init=False, repr=False)

    # Symbolic link to a data file for SAMMY
    # Not initialized until symlink set by user.
    data_symlink: Path = field(init=False, repr=False)

    # Grab the current working directory as the default
    working_fit_dir: Path = field(default_factory=lambda: Path(os.getcwd()))

    # Set the results directory to a subdirectory of the working_fit_dir
    working_results_dir: Path = field(default=None)

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

    def validate_fit_dirs(self) -> bool:
        """Validate the configuration of the working sammy fit directory.
            It must have the following:
            - a working_fit_dir that is accessible
            - a working_results_dir that is accessible
        Returns:
            bool: True if configuration of working sammy fit directory is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """

        # Validate working directory is writable
        if not os.access(self.working_fit_dir, os.W_OK):
            raise ConfigurationError(f"Working fit directory not writable: {self.working_dir}")

        # Validate output directory is writable
        if not os.access(self.working_results_dir, os.W_OK):
            raise ConfigurationError(f"Working results directory not writable: {self.output_dir}")

        return True

    def validate_files(self) -> bool:
        """Vlidate the files needed by sammy in the working fit directory.
            SAMMY needs the following files
            - an input file.
            - a parameter file
            - a data file (symbolic link)

        Returns:
            bool: True if all required files are present and valid

        Raises:
            ConfigurationError: If all files are not present
        """

        # Validate the input file exists.
        # This is either a user defined name or a default name of 'input.inp'
        if not self.input_file.exists():
            raise ConfigurationError(f"Input file not found: {self.input_file}")
        if not self.input_file.is_file():
            raise ConfigurationError(f"Input file is not a file: {self.input_file}")
        if not self.input_file.is_readable():
            raise ConfigurationError(f"Input file not readable: {self.input_file}")

        # Validate the parameter file exists.
        # This is either a user defined name or a default name of 'params.par'
        if not self.parameter_file.exists():
            raise ConfigurationError(f"Parameter file not found: {self.parameter_file}")
        if not self.parameter_file.is_file():
            raise ConfigurationError(f"Parameter file is not a file: {self.parameter_file}")
        if not self.parameter_file.is_readable():
            raise ConfigurationError(f"Parameter file not readable: {self.parameter_file}")

        # Validate the data symlink exists.
        # This is either a user defined name or a default name of 'data'
        if not self.data_symlink.exists():
            raise ConfigurationError(f"Data symlink not found: {self.data_symlink}")
        if not self.data_symlink.is_symlink():
            raise ConfigurationError(f"Data symlink is not a symlink: {self.data_symlink}")
        if not self.data_symlink.is_readable():
            raise ConfigurationError(f"Data symlink not readable: {self.data_symlink}")

    def validate_final(self) -> bool:
        """
        Validate the configuration before calling SAMMY.

        This method checks the validity of the configuration by validating
        directories and files required before SAMMY execution
        """
        try:
            self.validate_fit_dirs()
            self.validate_files()
        except ConfigurationError as e:
            logger.error(f"Final Configuration validation failed: {e}")
            return False

        logger.info("Final Configuration is valid")
        return True
