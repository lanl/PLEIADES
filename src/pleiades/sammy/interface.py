#!/usr/env/bin python
"""
Interface definitions for SAMMY execution system.

This module defines the core interfaces and data structures used across
all SAMMY backend implementations.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from pleiades.sammy.config.base_config import BaseSammyConfig
from pleiades.sammy.config.config_errors import OutputCollectionError

logger = logging.getLogger(__name__)

SAMMY_OUTPUT_FILES = {
    "SAMMY.LPT",  # Log file
    "SAMMIE.ODF",  # Output data file
    "SAMNDF.PAR",  # Updated parameter file
    "SAMRESOLVED.PAR",  # Additional parameter file
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

    def validate(self) -> None:
        """
        Validate that all required input files exist.

        Raises:
            FileNotFoundError: If any required file is missing
        """
        for field_name, file_path in self.__dict__.items():
            if not file_path.exists():
                raise FileNotFoundError(f"{field_name.replace('_', ' ').title()} not found: {file_path}")
            if not file_path.is_file():
                raise FileNotFoundError(f"{field_name.replace('_', ' ').title()} is not a file: {file_path}")


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


class SammyRunner(ABC):
    """Abstract base class for SAMMY execution backends."""

    def __init__(self, config: BaseSammyConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

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
