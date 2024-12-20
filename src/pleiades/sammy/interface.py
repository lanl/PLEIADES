#!/usr/env/bin python
"""
Interface definitions for SAMMY execution system.

This module defines the core interfaces and data structures used across
all SAMMY backend implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Protocol
import logging

logger = logging.getLogger(__name__)

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
                raise FileNotFoundError(
                    f"{field_name.replace('_', ' ').title()} not found: {file_path}"
                )
            if not file_path.is_file():
                raise FileNotFoundError(
                    f"{field_name.replace('_', ' ').title()} is not a file: {file_path}"
                )


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
    working_dir: Path          # Directory for SAMMY execution
    output_dir: Path          # Directory for SAMMY outputs
    
    def validate(self) -> bool:
        """
        Validate the configuration.
        
        Returns:
            bool: True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate working directory exists and is writable
        if not self.working_dir.exists():
            raise ConfigurationError(f"Working directory does not exist: {self.working_dir}")
        if not os.access(self.working_dir, os.W_OK):
            raise ConfigurationError(f"Working directory not writable: {self.working_dir}")
            
        # Ensure output directory exists and is writable
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if not os.access(self.output_dir, os.W_OK):
            raise ConfigurationError(f"Output directory not writable: {self.output_dir}")
            
        return True

class SammyRunner(ABC):
    """Abstract base class for SAMMY execution backends."""

    def __init__(self, config: BaseSammyConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def prepare_environment(self, files: SammyFiles) -> None:
        """
        Prepare the execution environment.
        
        Args:
            files: Container with file information
            
        Raises:
            EnvironmentPreparationError: If preparation fails
        """
        raise NotImplementedError

    @abstractmethod
    async def execute_sammy(self, files: SammyFiles) -> SammyExecutionResult:
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
    async def collect_outputs(self, files: SammyFiles, result: SammyExecutionResult) -> None:
        """
        Collect and process output files after execution.
        
        Args:
            files: Container with file information
            result: Execution result to be updated with output information
            
        Raises:
            OutputCollectionError: If output collection fails
        """
        raise NotImplementedError

    @abstractmethod
    async def cleanup(self, files: SammyFiles) -> None:
        """
        Clean up resources after execution.
        
        Args:
            files: Container with file information
            
        Raises:
            CleanupError: If cleanup fails
        """
        raise NotImplementedError

    async def __aenter__(self) -> 'SammyRunner':
        """Allow usage as async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensure cleanup on context exit."""
        if hasattr(self, 'files'):
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