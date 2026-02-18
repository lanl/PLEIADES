#!/usr/bin/env python
"""Global configuration management for PLEIADES."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from pleiades.nuclear.models import DataRetrievalMethod, EndfLibrary, IsotopeParameters, nuclearParameters
from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.helper import VaryFlag
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

DEFAULT_NUCLEAR_SOURCES = {
    "DIRECT": "https://www-nds.iaea.org/public/download-endf",
    "API": "https://www-nds.iaea.org/exfor/servlet",
}


def _expand_path(value: Optional[Any], workspace: Optional["WorkspaceConfig"] = None) -> Optional[Path]:
    """Expand a path-like value into an absolute/relative ``Path`` object.

    Expansion behavior:
    - Accepts ``Path`` or string-like inputs.
    - Expands ``~`` and environment variables (e.g. ``$HOME``).
    - When ``workspace`` is provided, replaces supported
      ``${workspace.<field>}`` tokens.
    - Returns ``None`` when tokens cannot be resolved or when a circular
      token reference is detected.

    Args:
        value: Raw value from config (string/Path/None).
        workspace: Workspace model used for token substitution.

    Returns:
        Expanded ``Path`` or ``None`` if unresolved.
    """
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

    # Working root directory for PLEIADES. This is the base path that other workspace-relative paths can reference.
    root: Optional[Path] = None

    # Optional subdirectory for ENDF cache files. If not set, defaults to the same path as nuclear_data_cache_dir in NuclearConfig.
    endf_dir: Optional[Path] = None

    # Optional subdirectory for fit routine working directories. Each routine gets its own subdirectory here with a specific routine_id name.
    fitting_dir: Optional[Path] = None

    # Optional subdirectory for aggregate results across routines (e.g., combined CSVs, summary reports). This is separate from the per-routine fit_results_dir.
    results_dir: Optional[Path] = None

    # Optional subdirectory for input data files (e.g., transmission .dat/.twenty). This is separate from the fitting and results directories.
    # Each fit_routine sub directory should have a symlink to the relevant data files from this directory to avoid duplication.
    data_dir: Optional[Path] = None

    # Optional subdirectory for generated images/plots. This is separate from the fitting and results directories.
    image_dir: Optional[Path] = None

    @model_validator(mode="after")
    def _expand_paths(self) -> "WorkspaceConfig":
        """Normalize workspace paths after model construction.

        This is intentionally ordered in two phases:
        1. Expand ``root`` first.
        2. Expand all other fields that may reference ``${workspace.root}``
           or other workspace tokens.

        The explicit ordering keeps token substitution deterministic and makes
        field dependencies easy to reason about during maintenance.
        """
        # Pass 1: resolve root so dependent fields can reference it.
        self._expand_root_path()

        # Pass 2: resolve fields that may contain workspace token references.
        self._expand_dependent_paths()
        return self

    def _expand_root_path(self) -> None:
        """Pass 1: normalize only ``workspace.root``.

        ``root`` is treated as the anchor for other workspace paths, so it must
        be expanded before token-based expansion of dependent fields.
        """
        self.root = _expand_path(self.root)

    def _expand_dependent_paths(self) -> None:
        """Pass 2: normalize fields that may reference ``${workspace.*}`` tokens.

        This uses the already-expanded ``self.root`` (and any other resolved
        workspace fields) as the substitution source.
        """
        for field_name in ("endf_dir", "fitting_dir", "results_dir", "data_dir", "image_dir"):
            # Resolve each field independently so unresolved/circular references
            # in one field do not prevent expansion of the others.
            raw_value = getattr(self, field_name)
            setattr(self, field_name, _expand_path(raw_value, self))


class NuclearConfig(BaseModel):
    """Nuclear data configuration for PLEIADES.

    This is the global/default nuclear configuration. Per-fit overrides live in
    FitRoutineConfig.nuclear and are used when present.
    """

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
    """SAMMY backend configuration for PLEIADES.

    This captures how to execute SAMMY (local, docker, nova) and the backend-specific
    settings required to launch it.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    backend: Optional[str] = None
    local: Dict[str, Any] = Field(default_factory=dict)
    docker: Dict[str, Any] = Field(default_factory=dict)
    nova: Dict[str, Any] = Field(default_factory=dict)


class DatasetMetadata(BaseModel):
    """Metadata for a dataset entry to be used in DatasetConfig.

    These fields are used to seed INP generation (energy bounds, element hints, etc.)
    and can be extended without changing the core schema.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow", populate_by_name=True)

    # Facility where the data was collected (e.g., LANSCE, SNS).
    facility: Optional[str] = None
    # Instrument or beamline identifier.
    instrument: Optional[str] = None
    # General timestamp for when the data was recorded (UTC recommended).
    recorded_date: Optional[datetime] = Field(default=None, alias="RecordedDate")

    # Energy bounds for the dataset (in eV).
    min_energy_eV: Optional[float] = None
    max_energy_eV: Optional[float] = None


class DatasetConfig(BaseModel):
    """Configuration for a dataset entry.

    A dataset represents an input data file (e.g. transmission .dat/.twenty)
    plus optional metadata for building a FitConfig/INP.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # brief description of the dataset
    description: Optional[str] = None

    # Kind of data (e.g., transmission, capture)
    data_kind: Optional[str] = None

    # Path to the data file/files
    path_to_data_files: Optional[Path] = None

    # Metadata for the given dataset
    metadata: Optional[DatasetMetadata] = None


class FitRoutineConfig(BaseModel):
    """Configuration for a single fit routine.

    A routine defines how a specific fit should be run (dataset selection,
    fit mode, and optional FitConfig overrides).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    dataset_id: Optional[str] = None
    mode: Optional[str] = None
    update_from_results: Optional[bool] = None
    fit_config: Optional[FitConfig] = None


class PleiadesConfig(BaseModel):
    """Global configuration for PLEIADES.

    High-level intent:
    - workspace: where PLEIADES writes files
    - nuclear: global isotope defaults and ENDF cache
    - sammy: how to execute SAMMY
    - datasets: input data definitions
    - fit_routines: per-run configurations (including FitConfig)
    - runs/results_index: execution records and outputs
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    pleiades_version: Optional[int] = None

    workspace: Optional[WorkspaceConfig] = None
    nuclear: Optional[NuclearConfig] = None
    sammy: Optional[SammyConfig] = None

    datasets: Dict[str, DatasetConfig] = Field(default_factory=dict)
    fit_routines: Dict[str, FitRoutineConfig] = Field(default_factory=dict)
    runs: list[Dict[str, Any]] = Field(default_factory=list)
    results_index: Dict[str, Any] = Field(default_factory=dict)

    # Nuclear data configuration
    nuclear_data_cache_dir: Path = Field(default_factory=lambda: Path(os.path.expanduser("~/.pleiades/nuclear_data")))

    # Nuclear data retrieval methods and URLs
    nuclear_data_sources: Dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_NUCLEAR_SOURCES))

    # Other configuration sections can be added here as needed

    @model_validator(mode="after")
    def _normalize_config(self) -> "PleiadesConfig":
        """Normalize paths and keep nuclear fields in sync.

        This also normalizes routine-level isotope entries (fills defaults for
        endf_library) so downstream code can rely on consistent types.
        """
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

        # Normalize fit_routines into typed models.
        new_fit_routines: Dict[str, FitRoutineConfig] = {}
        for routine_id, routine in self.fit_routines.items():
            if isinstance(routine, dict):
                routine = FitRoutineConfig.model_validate(routine)
            new_fit_routines[routine_id] = routine

        self.fit_routines = new_fit_routines
        return self

    @model_validator(mode="after")
    def _require_fit_routines(self, info) -> "PleiadesConfig":
        """Require fit_routines when loading from a user config."""
        if info.context and info.context.get("require_fit_routines"):
            if not self.fit_routines:
                raise ValueError("fit_routines must be defined in the config file")
        return self

    def build_nuclear_params(self, routine_id: Optional[str] = None) -> nuclearParameters:
        """Build nuclearParameters from configured isotope entries.

        This method converts configuration-level isotope entries
        (``self.nuclear.isotopes``) into concrete ``IsotopeParameters`` objects
        used by SAMMY fit execution.

        The implementation intentionally applies two safeguards:
            1. Duplicate isotope identifiers are detected early and logged as
               warnings so users can correct accidental duplicate entries in
               configuration files.
            2. Objects returned by ``IsotopeManager`` are deep-copied before
               mutation (abundance, uncertainty, vary flag, library) to avoid
               mutating shared/cached manager state across runs.

        Args:
            routine_id: Optional routine identifier. Currently unused but kept
                for API compatibility with routine-aware workflows.

        Returns:
            ``nuclearParameters`` populated with per-isotope values from config.

        Raises:
            ValueError: If no isotopes are configured.
            ValueError: If any isotope string cannot be resolved by
                ``IsotopeManager``.
        """
        isotope_entries = None
        isotope_entries = self.nuclear.isotopes
        if not isotope_entries:
            raise ValueError("No isotopes configured. Set nuclear.isotopes.")
        from pleiades.nuclear.isotopes.manager import IsotopeManager

        manager = IsotopeManager()
        isotopes: List[IsotopeParameters] = []
        seen_isotopes: set[str] = set()
        retrieved_instance_ids: Dict[str, int] = {}

        default_library = self.nuclear.default_library or EndfLibrary.ENDF_B_VIII_0

        for entry in isotope_entries:
            # Normalize plain dict entries into the typed isotope model.
            if isinstance(entry, dict):
                entry = IsotopeConfig(**entry)

            # Warn on duplicate config entries before final nuclearParameters
            # validation. Validation still rejects duplicate isotope names, but
            # this warning points users to the root config issue sooner.
            if entry.isotope in seen_isotopes:
                logger.warning(
                    f"Duplicate isotope entry detected in config for '{entry.isotope}'. "
                    "This may trigger duplicate isotope validation errors."
                )
            else:
                seen_isotopes.add(entry.isotope)

            # Fetch baseline isotope parameters from the isotope manager.
            retrieved_isotope_params = manager.get_isotope_parameters_from_isotope_string(entry.isotope)
            if retrieved_isotope_params is None:
                raise ValueError(f"Isotope not found: {entry.isotope}")

            # If the manager returns the same object instance for repeated
            # lookups, warn that we are about to isolate mutation via copying.
            previous_instance_id = retrieved_instance_ids.get(entry.isotope)
            current_instance_id = id(retrieved_isotope_params)
            if previous_instance_id == current_instance_id:
                logger.warning(
                    f"IsotopeManager returned a reused IsotopeParameters instance for '{entry.isotope}'; "
                    "applying changes to a deep copy to prevent shared-state mutation."
                )
            retrieved_instance_ids[entry.isotope] = current_instance_id

            # Apply config-specific overrides on a deep copy to avoid mutating
            # manager-owned/cached instances.
            isotope_params = retrieved_isotope_params.model_copy(deep=True)
            isotope_params.abundance = entry.abundance
            isotope_params.uncertainty = entry.uncertainty
            isotope_params.vary_abundance = entry.vary_abundance
            isotope_params.endf_library = entry.endf_library or default_library

            # Collect per-entry isotope params; nuclearParameters validates
            # aggregate constraints (including duplicate isotope names).
            isotopes.append(isotope_params)

        return nuclearParameters(isotopes=isotopes)

    def populate_fit_config_isotopes(self, fit_config: Any, routine_id: Optional[str] = None) -> Any:
        """Populate fit_config.nuclear_params.isotopes from config if missing.

        This is the bridge that ensures a FitConfig has isotopes before INP/PAR
        generation or SAMMY execution.
        """
        if not hasattr(fit_config, "nuclear_params"):
            raise ValueError("fit_config must have a nuclear_params attribute")
        if not fit_config.nuclear_params.isotopes:
            fit_config.nuclear_params = self.build_nuclear_params(routine_id)
        return fit_config

    def ensure_endf_cache(
        self,
        routine_id: Optional[str] = None,
        method: DataRetrievalMethod = DataRetrievalMethod.DIRECT,
        endf_cache_dir: Optional[Path] = None,
        use_cache: bool = True,
        update_config: bool = True,
    ) -> List[Path]:
        """Ensure ENDF cache files exist for configured isotopes.

        This method validates configured isotopes, resolves a target output
        directory, and delegates file retrieval to ``NuclearDataManager``.
        For each isotope entry, it requests the resonance file and returns the
        list of resulting file paths.

        Args:
            routine_id: Optional routine identifier (reserved for future routine-specific
                behavior).
            method: Nuclear data retrieval method.
            endf_cache_dir: Optional override for the ENDF cache/output directory.
            use_cache: If True, reuse existing cached artifacts when available.
            update_config: If True, update module-global config via ``set_config(self)``
                before constructing ``NuclearDataManager``.

        Returns:
            List of output paths, one per configured isotope, in the same order
            as ``self.nuclear.isotopes``.

        Raises:
            ValueError: If no isotopes are configured.
            ValueError: If an isotope identifier cannot be resolved by the
                isotope manager.

        Side Effects:
            - Creates ``endf_cache_dir`` (or resolved default cache directory)
              if it does not exist.
            - Optionally updates module-global config state when
              ``update_config=True``.
        """
        isotope_entries = self.nuclear.isotopes

        if not isotope_entries:
            raise ValueError("No isotopes configured. Set nuclear.isotopes.")

        from pleiades.nuclear.manager import NuclearDataManager

        endf_cache_dir = (
            Path(endf_cache_dir)
            if endf_cache_dir is not None
            else (
                self.workspace.endf_dir if self.workspace and self.workspace.endf_dir else self.nuclear_data_cache_dir
            )
        )
        # Ensure download destination exists before any retrieval calls.
        endf_cache_dir.mkdir(parents=True, exist_ok=True)

        # Keep this side effect opt-in/explicit for callers that need global
        # configuration state synchronized for downstream manager behavior.
        if update_config:
            set_config(self)
        manager = NuclearDataManager()
        default_library = self.nuclear.default_library or EndfLibrary.ENDF_B_VIII_0

        outputs: List[Path] = []
        for entry in isotope_entries:
            if isinstance(entry, dict):
                entry = IsotopeConfig(**entry)
            # Resolve isotope metadata used by the download manager.
            isotope_info = manager.isotope_manager.get_isotope_info(entry.isotope)
            if isotope_info is None:
                raise ValueError(f"Isotope not found: {entry.isotope}")
            # Apply per-isotope library override when present; otherwise use
            # the config default library.
            library = entry.endf_library or default_library
            output_path = manager.download_endf_resonance_file(
                isotope=isotope_info,
                library=library,
                output_dir=str(endf_cache_dir),
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
    ) -> List[Dict[str, str | Path]]:
        """Create per-routine fit directories and a per-fit results subdirectory.

        Directory layout produced by this method:
            <workspace.fitting_dir>/<routine_id>/
            <workspace.fitting_dir>/<routine_id>/fit_results_dir/

        Where ``routine_id`` is built as ``<base_routine_id>_<timestamp>``.

        Args:
            base_routine_ids: Optional list of base routine names. If omitted, all keys
                from ``self.fit_routines`` are used.
            timestamp: Optional UTC timestamp string to make routine directories unique.
                If omitted, a timestamp in ``YYYYMMDDTHHMMSSZ`` format is generated.

        Returns:
            A list of dictionaries, one per created routine directory, each containing:
            - ``routine_id`` (str): The final timestamped routine identifier.
            - ``fit_dir`` (Path): The routine working directory under ``fitting_dir``.
            - ``fit_results_dir`` (Path): Subdirectory for SAMMY outputs for that routine.

        Raises:
            ValueError: If ``workspace.fitting_dir`` is not configured.
            ValueError: If no routine ids are available to create.
        """
        # The fitting root is required because each routine directory is created under it.
        if not self.workspace or not self.workspace.fitting_dir:
            raise ValueError("workspace.fitting_dir is required to create routine directories")

        # If explicit routine ids are not provided, use configured fit routine keys.
        routine_ids = base_routine_ids or list(self.fit_routines.keys())
        if not routine_ids:
            raise ValueError("No fit_routines defined to create routine directories")

        # Generate a UTC timestamp once so all routines created in this call share it.
        if timestamp is None:
            from datetime import datetime, timezone

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        created: List[Dict[str, str | Path]] = []
        fitting_dir = self.workspace.fitting_dir

        for base_routine_id in routine_ids:
            # Compose a run-unique routine id and derive both routine directories.
            routine_id = f"{base_routine_id}_{timestamp}"
            fit_dir = fitting_dir / routine_id
            fit_results_dir = fit_dir / "fit_results_dir"

            # Ensure both the routine root and its SAMMY output subdirectory exist.
            fit_dir.mkdir(parents=True, exist_ok=True)
            fit_results_dir.mkdir(parents=True, exist_ok=True)

            created.append(
                {
                    "routine_id": routine_id,
                    "fit_dir": fit_dir,
                    "fit_results_dir": fit_results_dir,
                }
            )

        # Ensure workspace-level aggregate results directory exists (if configured).
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
        return cls.model_validate(config_dict or {}, context={"require_fit_routines": True})


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
