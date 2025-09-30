#!/usr/bin/env python
"""Global configuration management for PLEIADES."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class PleiadesConfig:
    """Global configuration for PLEIADES."""

    # Nuclear data configuration
    nuclear_data_cache_dir: Path = field(default_factory=lambda: Path(os.path.expanduser("~/.pleiades/nuclear_data")))

    # Nuclear data retrieval methods and URLs
    nuclear_data_sources: Dict[str, str] = field(
        default_factory=lambda: {
            "DIRECT": "https://www-nds.iaea.org/public/download-endf",  # IAEA direct file download
            "API": "https://www-nds.iaea.org/exfor/servlet",  # IAEA EXFOR API for section retrieval
        }
    )

    # Other configuration sections can be added here as needed

    def __post_init__(self):
        """Ensure Path objects for all directory configurations."""
        self.nuclear_data_cache_dir = Path(self.nuclear_data_cache_dir)

    def ensure_directories(self):
        """Ensure all configured directories exist."""
        self.nuclear_data_cache_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary."""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                result[key] = str(value)
            else:
                result[key] = value
        return result

    def save(self, path: Optional[Path] = None) -> Path:
        """
        Save configuration to a YAML file.

        Args:
            path: Path to save configuration file. If None, uses default location.

        Returns:
            Path to the saved configuration file.
        """
        if path is None:
            path = Path(os.path.expanduser("~/.pleiades/config.yaml"))

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save config as YAML
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f)

        return path

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PleiadesConfig":
        """
        Load configuration from a YAML file.

        Args:
            path: Path to load configuration file. If None, uses default location.

        Returns:
            Loaded configuration object.
        """
        if path is None:
            path = Path(os.path.expanduser("~/.pleiades/config.yaml"))

        if not path.exists():
            return cls()

        with open(path, "r") as f:
            config_dict = yaml.safe_load(f)

        if not config_dict:
            return cls()

        # Convert string paths back to Path objects
        if "nuclear_data_cache_dir" in config_dict:
            config_dict["nuclear_data_cache_dir"] = Path(config_dict["nuclear_data_cache_dir"])

        return cls(**config_dict)


# Global configuration instance
_config: Optional[PleiadesConfig] = None


def get_config() -> PleiadesConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = PleiadesConfig.load()
        _config.ensure_directories()
    return _config


def set_config(config: PleiadesConfig) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
    _config.ensure_directories()


def reset_config() -> None:
    """Reset the global configuration to defaults."""
    global _config
    _config = PleiadesConfig()
    _config.ensure_directories()
