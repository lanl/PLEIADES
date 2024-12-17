#!/usr/env/bin python
"""Interface for SAMMY execution backends."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Dict, Union, List, Protocol, AsyncContextManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SammyBackendType(Enum):
    """Enumeration of available SAMMY backend types."""
    LOCAL = auto()
    DOCKER = auto()
    NOVA = auto()

@dataclass
class SammyFiles:
    """Container for SAMMY input/output files."""
    input_file: Path
    parameter_file: Path
    data_file: Path
    working_dir: Path
    
    def validate_input_files(self) -> None:
        """Validate that all required input files exist."""
        for field_name in ['input_file', 'parameter_file', 'data_file']:
            file_path = getattr(self, field_name)
            if not file_path.exists():
                raise FileNotFoundError(
                    f"{field_name.replace('_', ' ').title()} not found: {file_path}"
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

class BackendConfig(Protocol):
    """Protocol defining required configuration interface."""
    def validate(self) -> bool:
        """Validate configuration."""
        ...

class LocalBackendConfig(BackendConfig):
    """Configuration for local SAMMY installation."""
    sammy_executable: Path
    shell_path: Path = Path("/bin/bash")

class DockerBackendConfig(BackendConfig):
    """Configuration for Docker backend."""
    image_name: str
    container_working_dir: Path
    volume_mappings: Dict[Path, Path]  # host_path -> container_path

class NovaBackendConfig(BackendConfig):
    """Configuration for NOVA web service."""
    url: str
    api_key: str
    tool_id: str = "neutrons_imaging_sammy"

class SammyRunner(ABC):
    """Abstract base class for SAMMY execution backends."""

    def __init__(self, config: BackendConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def prepare_environment(self, files: SammyFiles) -> None:
        """
        Prepare the execution environment.
        
        This includes:
        - Validating input files
        - Setting up working directory
        - Preparing files for execution
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
        
        This includes:
        - Removing temporary files
        - Cleaning up containers
        - Closing connections
        """
        raise NotImplementedError

    async def __aenter__(self) -> 'SammyRunner':
        """Allow usage as async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensure cleanup on context exit."""
        await self.cleanup()

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate backend configuration."""
        raise NotImplementedError

# Custom exceptions for better error handling
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
