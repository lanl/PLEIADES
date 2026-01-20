#!/usr/bin/env python
"""Global configuration management for PLEIADES."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_NUCLEAR_SOURCES = {
    "DIRECT": "https://www-nds.iaea.org/public/download-endf",
    "API": "https://www-nds.iaea.org/exfor/servlet",
}


def _expand_path(value: Optional[Any], workspace: Optional["WorkspaceConfig"] = None) -> Optional[Path]:
    if value is None:
        return None

    raw = str(value)
    if workspace is not None:
        mapping = {
            "${workspace.root}": workspace.root,
            "${workspace.endf_dir}": workspace.endf_dir,
            "${workspace.fitting_dir}": workspace.fitting_dir,
            "${workspace.results_dir}": workspace.results_dir,
            "${workspace.data_dir}": workspace.data_dir,
            "${workspace.image_dir}": workspace.image_dir,
        }
        if raw in mapping:
            replacement = mapping[raw]
            if replacement is None or str(replacement) == raw:
                return None
        for token, path in mapping.items():
            if path is not None:
                raw = raw.replace(token, str(path))

    raw = os.path.expandvars(os.path.expanduser(raw))
    if "${workspace." in raw:
        return None
    return Path(raw)


class WorkspaceConfig(BaseModel):
    """Workspace directory configuration for PLEIADES."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: Optional[Path] = None
    endf_dir: Optional[Path] = None
    fitting_dir: Optional[Path] = None
    results_dir: Optional[Path] = None
    data_dir: Optional[Path] = None
    image_dir: Optional[Path] = None

    @model_validator(mode="after")
    def _expand_paths(self) -> "WorkspaceConfig":
        self.root = _expand_path(self.root)
        self.endf_dir = _expand_path(self.endf_dir, self)
        self.fitting_dir = _expand_path(self.fitting_dir, self)
        self.results_dir = _expand_path(self.results_dir, self)
        self.data_dir = _expand_path(self.data_dir, self)
        self.image_dir = _expand_path(self.image_dir, self)
        return self


class NuclearConfig(BaseModel):
    """Nuclear data configuration for PLEIADES."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data_cache_dir: Optional[Path] = None
    sources: Dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_NUCLEAR_SOURCES))
    default_library: Optional[str] = None

    @model_validator(mode="after")
    def _expand_paths(self) -> "NuclearConfig":
        self.data_cache_dir = _expand_path(self.data_cache_dir)
        return self


class SammyConfig(BaseModel):
    """SAMMY backend configuration for PLEIADES."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    backend: Optional[str] = None
    local: Dict[str, Any] = Field(default_factory=dict)
    docker: Dict[str, Any] = Field(default_factory=dict)
    nova: Dict[str, Any] = Field(default_factory=dict)


class PleiadesConfig(BaseModel):
    """Global configuration for PLEIADES."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    pleiades_version: Optional[int] = None

    workspace: Optional[WorkspaceConfig] = None
    nuclear: Optional[NuclearConfig] = None
    sammy: Optional[SammyConfig] = None

    datasets: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    fit_routines: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    runs: list[Dict[str, Any]] = Field(default_factory=list)
    results_index: Dict[str, Any] = Field(default_factory=dict)

    # Nuclear data configuration
    nuclear_data_cache_dir: Path = Field(default_factory=lambda: Path(os.path.expanduser("~/.pleiades/nuclear_data")))

    # Nuclear data retrieval methods and URLs
    nuclear_data_sources: Dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_NUCLEAR_SOURCES))

    # Other configuration sections can be added here as needed

    @model_validator(mode="after")
    def _normalize_config(self) -> "PleiadesConfig":
        """Normalize paths and keep nuclear fields in sync."""
        if self.workspace:
            self.nuclear_data_cache_dir = _expand_path(self.nuclear_data_cache_dir, self.workspace)
        else:
            self.nuclear_data_cache_dir = _expand_path(self.nuclear_data_cache_dir)
            self.workspace = WorkspaceConfig(endf_dir=self.nuclear_data_cache_dir)

        if self.nuclear is None:
            self.nuclear = NuclearConfig(
                data_cache_dir=self.nuclear_data_cache_dir,
                sources=dict(self.nuclear_data_sources),
            )
        else:
            if self.workspace:
                self.nuclear.data_cache_dir = _expand_path(self.nuclear.data_cache_dir, self.workspace)
            else:
                self.nuclear.data_cache_dir = _expand_path(self.nuclear.data_cache_dir)

            if self.nuclear.data_cache_dir is None:
                self.nuclear.data_cache_dir = self.nuclear_data_cache_dir
            else:
                self.nuclear_data_cache_dir = self.nuclear.data_cache_dir

            if not self.nuclear.sources:
                self.nuclear.sources = dict(self.nuclear_data_sources)
            else:
                self.nuclear_data_sources = dict(self.nuclear.sources)
        if self.workspace and self.workspace.endf_dir is None:
            self.workspace.endf_dir = self.nuclear_data_cache_dir
        return self

    def ensure_directories(self):
        """Ensure all configured directories exist."""
        self.nuclear_data_cache_dir.mkdir(parents=True, exist_ok=True)
        if self.workspace:
            for path in (
                self.workspace.root,
                self.workspace.endf_dir,
                self.workspace.fitting_dir,
                self.workspace.results_dir,
                self.workspace.data_dir,
                self.workspace.image_dir,
            ):
                if path is not None:
                    path.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary."""
        return self.model_dump(mode="json")

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
            yaml.safe_dump(self.to_dict(), f, sort_keys=False)

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

        return cls.from_dict(config_dict)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PleiadesConfig":
        """Build a configuration from a dictionary."""
        return cls.model_validate(config_dict or {})


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
