#!/usr/bin/env python
"""Global configuration management for PLEIADES."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from pleiades.nuclear.models import DataRetrievalMethod, EndfLibrary, IsotopeParameters, nuclearParameters
from pleiades.utils.helper import VaryFlag

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

        # Handle the simple case where the value is exactly one workspace token.
        # If the replacement is None or does not actually change the value,
        # treat this as an unresolved or self-referential path and return None.
        if raw in mapping:
            replacement = mapping[raw]
            if replacement is None:
                return None
            replacement_str = str(replacement)
            if replacement_str == raw:
                return None
            raw = replacement_str

        # Perform iterative substitution of workspace tokens, tracking which
        # tokens have already been expanded to detect circular references,
        # including multi-level indirections (e.g., A -> B -> C -> A).
        visited_tokens = set()
        changed = True
        while changed:
            changed = False
            for token, path in mapping.items():
                if path is None:
                    continue
                if token in raw:
                    if token in visited_tokens:
                        # Circular reference detected (token reappeared after expansion).
                        return None
                    visited_tokens.add(token)
                    raw = raw.replace(token, str(path))
                    changed = True

    raw = os.path.expandvars(os.path.expanduser(raw))
    # If any workspace tokens remain at this point, the path could not be
    # resolved (possibly due to an indirect circular reference); return None.
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
    default_library: Optional[EndfLibrary] = None
    isotopes: List["IsotopeConfig"] = Field(default_factory=list)

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
        if self.nuclear.default_library is None:
            self.nuclear.default_library = EndfLibrary.ENDF_B_VIII_0
        if self.workspace and self.workspace.endf_dir is None:
            self.workspace.endf_dir = self.nuclear_data_cache_dir

        default_library = self.nuclear.default_library or EndfLibrary.ENDF_B_VIII_0
        self.nuclear.isotopes = [
            IsotopeConfig(**entry) if isinstance(entry, dict) else entry for entry in self.nuclear.isotopes
        ]
        for entry in self.nuclear.isotopes:
            if entry.endf_library is None:
                entry.endf_library = default_library

        for routine in self.fit_routines.values():
            routine_nuclear = routine.get("nuclear") or {}
            routine_isotopes = routine_nuclear.get("isotopes")
            if routine_isotopes is None:
                continue
            updated: List[IsotopeConfig] = []
            for entry in routine_isotopes:
                if isinstance(entry, dict):
                    entry = IsotopeConfig(**entry)
                if entry.endf_library is None:
                    entry.endf_library = default_library
                updated.append(entry)
            routine_nuclear["isotopes"] = updated
            routine["nuclear"] = routine_nuclear

        return self

    def build_nuclear_params(self, routine_id: Optional[str] = None) -> nuclearParameters:
        """Build nuclearParameters from configured isotope entries."""
        isotope_entries = None
        if routine_id:
            routine = self.fit_routines.get(routine_id, {})
            routine_isotopes = (routine.get("nuclear") or {}).get("isotopes")
            if routine_isotopes:
                isotope_entries = routine_isotopes
        if isotope_entries is None:
            isotope_entries = self.nuclear.isotopes
        if not isotope_entries:
            raise ValueError("No isotopes configured. Set fit_routines.<id>.nuclear.isotopes or nuclear.isotopes.")
        from pleiades.nuclear.isotopes.manager import IsotopeManager

        manager = IsotopeManager()
        isotopes: List[IsotopeParameters] = []

        default_library = self.nuclear.default_library or EndfLibrary.ENDF_B_VIII_0

        for entry in isotope_entries:
            if isinstance(entry, dict):
                entry = IsotopeConfig(**entry)

            isotope_params = manager.get_isotope_parameters_from_isotope_string(entry.isotope)
            if isotope_params is None:
                raise ValueError(f"Isotope not found: {entry.isotope}")

            isotope_params.abundance = entry.abundance
            isotope_params.uncertainty = entry.uncertainty
            isotope_params.vary_abundance = entry.vary_abundance
            isotope_params.endf_library = entry.endf_library or default_library

            isotopes.append(isotope_params)

        return nuclearParameters(isotopes=isotopes)

    def populate_fit_config_isotopes(self, fit_config: Any, routine_id: Optional[str] = None) -> Any:
        """Populate fit_config.nuclear_params.isotopes from config if missing."""
        if not hasattr(fit_config, "nuclear_params"):
            raise ValueError("fit_config must have a nuclear_params attribute")
        if not fit_config.nuclear_params.isotopes:
            fit_config.nuclear_params = self.build_nuclear_params(routine_id)
        return fit_config

    def ensure_endf_cache(
        self,
        routine_id: Optional[str] = None,
        method: DataRetrievalMethod = DataRetrievalMethod.DIRECT,
        output_dir: Optional[Path] = None,
        use_cache: bool = True,
    ) -> List[Path]:
        """Ensure ENDF cache files exist for configured isotopes."""
        if routine_id:
            routine = self.fit_routines.get(routine_id, {})
            routine_isotopes = (routine.get("nuclear") or {}).get("isotopes")
            isotope_entries = routine_isotopes if routine_isotopes is not None else self.nuclear.isotopes
        else:
            isotope_entries = self.nuclear.isotopes

        if not isotope_entries:
            raise ValueError("No isotopes configured. Set fit_routines.<id>.nuclear.isotopes or nuclear.isotopes.")

        from pleiades.nuclear.manager import NuclearDataManager

        output_dir = (
            Path(output_dir)
            if output_dir is not None
            else (
                self.workspace.endf_dir if self.workspace and self.workspace.endf_dir else self.nuclear_data_cache_dir
            )
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        set_config(self)
        manager = NuclearDataManager()
        default_library = self.nuclear.default_library or EndfLibrary.ENDF_B_VIII_0

        outputs: List[Path] = []
        for entry in isotope_entries:
            if isinstance(entry, dict):
                entry = IsotopeConfig(**entry)
            isotope_info = manager.isotope_manager.get_isotope_info(entry.isotope)
            if isotope_info is None:
                raise ValueError(f"Isotope not found: {entry.isotope}")
            library = entry.endf_library or default_library
            output_path = manager.download_endf_resonance_file(
                isotope=isotope_info,
                library=library,
                output_dir=str(output_dir),
                method=method,
                use_cache=use_cache,
            )
            outputs.append(output_path)

        return outputs

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

    def create_routine_dirs(
        self,
        base_routine_ids: Optional[List[str]] = None,
        timestamp: Optional[str] = None,
    ) -> List[Dict[str, Path]]:
        """Create timestamped routine directories under workspace.fitting_dir."""
        if not self.workspace or not self.workspace.fitting_dir:
            raise ValueError("workspace.fitting_dir is required to create routine directories")

        routine_ids = base_routine_ids or list(self.fit_routines.keys())
        if not routine_ids:
            raise ValueError("No fit_routines defined to create routine directories")

        if timestamp is None:
            from datetime import datetime, timezone

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        created: List[Dict[str, Path]] = []
        fitting_dir = self.workspace.fitting_dir

        for base_routine_id in routine_ids:
            routine_id = f"{base_routine_id}_{timestamp}"
            fit_dir = fitting_dir / routine_id
            results_dir = fit_dir / "results_dir"

            fit_dir.mkdir(parents=True, exist_ok=True)
            results_dir.mkdir(parents=True, exist_ok=True)

            created.append(
                {
                    "routine_id": routine_id,
                    "fit_dir": fit_dir,
                    "results_dir": results_dir,
                }
            )

        if self.workspace.results_dir:
            self.workspace.results_dir.mkdir(parents=True, exist_ok=True)

        return created

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


class IsotopeConfig(BaseModel):
    """Configuration for a single isotope entry."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    isotope: str
    abundance: Optional[float] = None
    uncertainty: Optional[float] = None
    vary_abundance: Optional[VaryFlag] = None
    endf_library: Optional[EndfLibrary] = None


NuclearConfig.model_rebuild()


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
