#!/usr/env/bin python
"""
Configuration management for SAMMY execution backends.

This module provides concrete configuration classes for each SAMMY backend type,
inheriting from the base configuration defined in the interface module.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse
import shutil

from pleiades.sammy.interface import BaseSammyConfig, ConfigurationError

@dataclass
class LocalSammyConfig(BaseSammyConfig):
    """Configuration for local SAMMY installation."""
    sammy_executable: Path
    shell_path: Path = Path("/bin/bash")
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate local SAMMY configuration."""
        # Validate base configuration first
        super().validate()
        
        # Validate SAMMY executable exists and is executable
        sammy_path = shutil.which(str(self.sammy_executable))
        if not sammy_path:
            raise ConfigurationError(f"SAMMY executable not found: {self.sammy_executable}")
        self.sammy_executable = Path(sammy_path)
        
        # Validate shell exists
        if not self.shell_path.exists():
            raise ConfigurationError(f"Shell not found: {self.shell_path}")
            
        return True

@dataclass
class DockerSammyConfig(BaseSammyConfig):
    """Configuration for Docker-based SAMMY execution."""
    image_name: str
    container_working_dir: Path = Path("/sammy")
    volume_mappings: Dict[Path, Path] = field(default_factory=dict)
    network: Optional[str] = None
    
    def validate(self) -> bool:
        """Validate Docker SAMMY configuration."""
        # Validate base configuration first
        super().validate()
        
        # Validate image name format
        if not self.image_name:
            raise ConfigurationError("Docker image name cannot be empty")
            
        # Validate container working directory is absolute
        if not self.container_working_dir.is_absolute():
            raise ConfigurationError("Container working directory must be absolute path")
            
        # Validate volume mappings exist on host
        for host_path in self.volume_mappings:
            if not host_path.exists():
                raise ConfigurationError(f"Host path does not exist: {host_path}")
                
        return True

@dataclass
class NovaSammyConfig(BaseSammyConfig):
    """Configuration for NOVA web service SAMMY execution."""
    url: str
    api_key: str
    tool_id: str = "neutrons_imaging_sammy"
    timeout: int = 3600  # Default 1 hour timeout
    verify_ssl: bool = True
    
    def validate(self) -> bool:
        """Validate NOVA SAMMY configuration."""
        # First validate base configuration
        super().validate()
        
        # Validate URL format
        try:
            parsed_url = urlparse(self.url)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                raise ConfigurationError(f"Invalid URL format: {self.url}")
        except Exception as e:
            raise ConfigurationError(f"URL validation failed: {str(e)}")
            
        # Validate API key format
        if not self.api_key or len(self.api_key) < 32:
            raise ConfigurationError("Invalid API key format")
            
        # Validate timeout
        if self.timeout <= 0:
            raise ConfigurationError(f"Invalid timeout value: {self.timeout}")
            
        return True