#!/usr/env/bin python
"""
Interface definitions for SAMMY execution system.

This module defines the core interfaces and data structures used across
all SAMMY backend implementations.
"""

import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

SAMMY_OUTPUT_FILES = {
    "SAMMY.LPT",  # Log file
    "SAMMY.LST",  #
    "SAMNDF.PAR",  # Updated parameter file based on SAMMY run
    "SAMNDF.INP",  # Updated input file based on SAMMY run
    "SAMMY.IO",  # terminal output file from SAMMY run
}


class SammyBackendType(Enum):
    """Enumeration of available SAMMY backend types."""

    LOCAL = auto()
    DOCKER = auto()
    NOVA = auto()


@dataclass
class SammyFiles:
    """Container for SAMMY input files."""

    input_file: Path
    parameter_file: Path
    data_file: Path

    # Store original paths for cleanup
    _original_input_file: Optional[Path] = None
    _original_parameter_file: Optional[Path] = None
    _original_data_file: Optional[Path] = None

    def validate(self) -> None:
        """
        Validate that all required input files exist.

        Raises:
            FileNotFoundError: If any required file is missing
        """
        for field_name, file_path in self.__dict__.items():
            if field_name.startswith("_"):
                continue
            if not file_path.exists():
                raise FileNotFoundError(f"{field_name.replace('_', ' ').title()} not found: {file_path}")
            if not file_path.is_file():
                raise FileNotFoundError(f"{field_name.replace('_', ' ').title()} is not a file: {file_path}")

    def move_to_working_dir(self, working_dir: Path) -> None:
        """
        Move files to the working directory according to the desired strategy:
        - input_file: copy to working directory
        - parameter_file: copy to working directory
        - data_file: symlink to working directory

        Updates the object's file path attributes to point to the files in the working directory.
        Can be safely called multiple times - will clean up previous working files first.

        Args:
            working_dir: Path to the working directory

        Raises:
            FileExistsError: If target files already exist in working directory
            OSError: If file operations fail
        """
        logger.debug(f"Moving files to working directory: {working_dir}")

        # If we already moved files to a working directory, clean them up first
        if self._original_input_file is not None:
            self.cleanup_working_files()

        # Save original paths for cleanup (only if not already saved)
        self._original_input_file = self.input_file
        self._original_parameter_file = self.parameter_file
        self._original_data_file = self.data_file

        # Copy input file
        working_input = working_dir / self.input_file.name
        if working_input.exists():
            logger.debug(f"Removing existing file: {working_input}")
            working_input.unlink()
        logger.debug(f"Copying input file: {self._original_input_file} -> {working_input}")
        shutil.copy2(self._original_input_file, working_input)
        self.input_file = working_input

        # Copy parameter file
        working_param = working_dir / self.parameter_file.name
        if working_param.exists():
            logger.debug(f"Removing existing file: {working_param}")
            working_param.unlink()
        logger.debug(f"Copying parameter file: {self._original_parameter_file} -> {working_param}")
        shutil.copy2(self._original_parameter_file, working_param)
        self.parameter_file = working_param

        # Symlink data file
        working_data = working_dir / self.data_file.name
        if working_data.exists():
            logger.debug(f"Removing existing file: {working_data}")
            working_data.unlink()
        logger.debug(f"Creating symlink for data file: {self._original_data_file} -> {working_data}")
        working_data.symlink_to(self._original_data_file)
        self.data_file = working_data

    def cleanup_working_files(self) -> None:
        """
        Remove any files copied or symlinked to the working directory,
        and restore original file paths.
        """
        logger.debug("Cleaning up working files")

        # Only cleanup if we have moved files
        if self._original_input_file is None:
            return

        # Remove symlinked data file
        if self.data_file.exists() and self.data_file.is_symlink():
            logger.debug(f"Removing symlink: {self.data_file}")
            self.data_file.unlink()

        # Remove copied input file
        if self.input_file.exists() and not self.input_file.is_symlink():
            logger.debug(f"Removing file: {self.input_file}")
            self.input_file.unlink()

        # Remove copied parameter file
        if self.parameter_file.exists() and not self.parameter_file.is_symlink():
            logger.debug(f"Removing file: {self.parameter_file}")
            self.parameter_file.unlink()

        # Restore original paths
        self.input_file = self._original_input_file
        self.parameter_file = self._original_parameter_file
        self.data_file = self._original_data_file

        # Clear backup paths
        self._original_input_file = None
        self._original_parameter_file = None
        self._original_data_file = None


@dataclass
class SammyExecutionResult:
    """Detailed results of a SAMMY execution."""

    success: bool
    execution_id: str  # Unique identifier for this run
    start_time: datetime
    end_time: datetime
    console_output: str
    error_message: Optional[str] = None

    @property
    def runtime_seconds(self) -> float:
        """Calculate execution time in seconds."""
        return (self.end_time - self.start_time).total_seconds()


@dataclass
class BaseSammyConfig(ABC):
    """Base configuration for all SAMMY backends."""

    working_dir: Path  # Directory for SAMMY execution
    output_dir: Path  # Directory for SAMMY outputs

    def prepare_directories(self) -> None:
        """
        Create and prepare required directories.

        Raises:
            ConfigurationError: If directory creation fails
        """
        try:
            # Create working directory if it doesn't exist
            self.working_dir.mkdir(parents=True, exist_ok=True)

            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)

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
        if not os.access(self.working_dir, os.W_OK):
            raise ConfigurationError(f"Working directory not writable: {self.working_dir}")

        # Validate output directory is writable
        if not os.access(self.output_dir, os.W_OK):
            raise ConfigurationError(f"Output directory not writable: {self.output_dir}")

        return True


class SammyRunner(ABC):
    """Abstract base class for SAMMY execution backends."""

    def __init__(self, config: BaseSammyConfig):
        self.config = config
        self.logger = loguru_logger.bind(name=f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def prepare_environment(self, files: SammyFiles) -> None:
        """
        Prepare the execution environment.

        Args:
            files: Container with file information

        Raises:
            EnvironmentPreparationError: If preparation fails
        """
        raise NotImplementedError

    @abstractmethod
    def execute_sammy(self, files: SammyFiles) -> SammyExecutionResult:
        """
        Execute SAMMY with prepared files.

        Args:
            files: Container with validated and prepared files

        Returns:
            Execution results including status and outputs

        Raises:
            SammyExecutionError: If execution fails
        """
        raise NotImplementedError

    @abstractmethod
    def cleanup(self, files: SammyFiles) -> None:
        """
        Clean up resources after execution.

        Args:
            files: Container with file information

        Raises:
            CleanupError: If cleanup fails
        """
        raise NotImplementedError

    async def __aenter__(self) -> "SammyRunner":
        """Allow usage as async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensure cleanup on context exit."""
        if hasattr(self, "files"):
            await self.cleanup(self.files)

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate backend configuration.

        Returns:
            bool: True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        raise NotImplementedError

    def collect_outputs(self, result: SammyExecutionResult) -> None:
        """
        Collect and validate output files after execution.

        Args:
            result: Execution result containing status information

        Raises:
            OutputCollectionError: If output collection fails
        """
        collection_start = datetime.now()
        logger.info(f"Collecting outputs for execution {result.execution_id}")

        try:
            self._moved_files = []
            found_outputs = set()

            # First check for known output files
            for known_file in SAMMY_OUTPUT_FILES:
                output_file = self.config.working_dir / known_file
                if output_file.is_file():
                    found_outputs.add(output_file)
                    logger.debug(f"Found known output file: {known_file}")

            # Then look for any additional SAM* files
            for output_file in self.config.working_dir.glob("SAM*"):
                if output_file.is_file() and output_file not in found_outputs:
                    found_outputs.add(output_file)
                    logger.debug(f"Found additional output file: {output_file.name}")

            if not found_outputs:
                logger.warning("No SAMMY output files found")
                if result.success:
                    logger.error("SAMMY reported success but produced no output files")
                return

            # Move all found outputs
            for output_file in found_outputs:
                dest = self.config.output_dir / output_file.name
                try:
                    if dest.exists():
                        logger.debug(f"Removing existing output file: {dest}")
                        dest.unlink()
                    output_file.rename(dest)
                    self._moved_files.append(dest)
                    logger.debug(f"Moved {output_file} to {dest}")
                except OSError as e:
                    self._rollback_moves()
                    raise OutputCollectionError(f"Failed to move output file {output_file}: {str(e)}")

            logger.info(
                f"Successfully collected {len(self._moved_files)} output files in "
                f"{(datetime.now() - collection_start).total_seconds():.2f} seconds"
            )

        except Exception as e:
            self._rollback_moves()
            raise OutputCollectionError(f"Output collection failed: {str(e)}")

    def _rollback_moves(self) -> None:
        """Rollback any moved files in case of error."""
        for moved_file in self._moved_files:
            try:
                original = self.config.working_dir / moved_file.name
                moved_file.rename(original)
            except Exception as e:
                logger.error(f"Failed to rollback move for {moved_file}: {str(e)}")


# Custom exceptions
class SammyError(Exception):
    """Base exception for SAMMY-related errors."""

    pass


class EnvironmentPreparationError(SammyError):
    """Raised when environment preparation fails."""

    pass


class SammyExecutionError(SammyError):
    """Raised when SAMMY execution fails."""

    pass


class OutputCollectionError(SammyError):
    """Raised when output collection fails."""

    pass


class ConfigurationError(SammyError):
    """Raised when configuration is invalid."""

    pass


class CleanupError(SammyError):
    """Raised when cleanup fails."""

    pass
