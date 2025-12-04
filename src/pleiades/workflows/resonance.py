"""High-level resonance analysis workflows for PLEIADES.

This module provides simple, high-level functions that orchestrate
complete resonance analysis workflows. These functions can be called
directly by users or exposed via MCP tools.

Example:
    >>> from pleiades.workflows import validate_dataset, analyze_resonance
    >>> result = validate_dataset("/path/to/dataset")
    >>> if result.valid:
    ...     analysis = analyze_resonance("/path/to/dataset")
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from pleiades.utils.logger import loguru_logger
from pleiades.workflows.models import (
    FitQuality,
    ManifestData,
    MaterialProperties,
    ResonanceResult,
    ValidationIssue,
    ValidationResult,
    WorkflowType,
)

if TYPE_CHECKING:
    from pleiades.sammy.interface import SammyRunner

logger = loguru_logger.bind(name=__name__)


def validate_dataset(dataset_path: str | Path) -> ValidationResult:
    """Validate a dataset for resonance analysis.

    Checks that the dataset has the required structure and files
    to run resonance analysis. Determines whether the dataset supports
    the full imaging workflow or simplified SAMMY-only workflow.

    Args:
        dataset_path: Path to the dataset directory.

    Returns:
        ValidationResult with validation status and detected capabilities.

    Example:
        >>> result = validate_dataset("/data/Au197_sample")
        >>> if result.valid:
        ...     print(f"Ready for {result.recommended_workflow.value} workflow")
        >>> else:
        ...     for error in result.errors:
        ...         print(f"Error: {error.message}")
    """
    dataset_path = Path(dataset_path)
    issues: list[ValidationIssue] = []

    logger.info(f"Validating dataset: {dataset_path}")

    # Check dataset exists
    if not dataset_path.exists():
        return ValidationResult(
            valid=False,
            dataset_path=dataset_path,
            issues=[
                ValidationIssue(
                    severity="error",
                    message=f"Dataset directory does not exist: {dataset_path}",
                    path=dataset_path,
                )
            ],
        )

    if not dataset_path.is_dir():
        return ValidationResult(
            valid=False,
            dataset_path=dataset_path,
            issues=[
                ValidationIssue(
                    severity="error",
                    message=f"Path is not a directory: {dataset_path}",
                    path=dataset_path,
                )
            ],
        )

    # Check for imaging data (full workflow)
    raw_dir = dataset_path / "raw"
    ob_dir = dataset_path / "open_beam"
    metadata_dir = dataset_path / "metadata"

    has_raw = raw_dir.exists() and raw_dir.is_dir()
    has_ob = ob_dir.exists() and ob_dir.is_dir()
    has_metadata = metadata_dir.exists() and metadata_dir.is_dir()

    # Check for SAMMY files (simplified workflow)
    sammy_data_dir = dataset_path / "sammy_data"
    has_sammy_files = False
    if sammy_data_dir.exists():
        inp_files = list(sammy_data_dir.glob("*.inp"))
        has_sammy_files = len(inp_files) > 0

    # Check for manifest
    manifest_paths = [
        dataset_path / "manifest_intermediate.md",
        dataset_path / "smcp_manifest.md",
        dataset_path / "manifest.md",
    ]
    has_manifest = any(p.exists() for p in manifest_paths)

    # Determine workflow capabilities
    can_run_full = has_raw and has_ob
    can_run_simplified = has_sammy_files

    # Build validation issues
    if not can_run_full and not can_run_simplified:
        issues.append(
            ValidationIssue(
                severity="error",
                message="Dataset does not contain imaging data (raw/, open_beam/) or SAMMY files (sammy_data/*.inp)",
                path=dataset_path,
            )
        )

    if has_raw and not has_ob:
        issues.append(
            ValidationIssue(
                severity="warning",
                message="Open beam directory not found - normalization may fail",
                path=ob_dir,
            )
        )

    if has_raw and not has_metadata:
        issues.append(
            ValidationIssue(
                severity="warning",
                message="Metadata directory not found - may need manual TOF calibration",
                path=metadata_dir,
            )
        )

    if not has_manifest:
        issues.append(
            ValidationIssue(
                severity="warning",
                message="No manifest file found - analysis parameters must be provided explicitly",
                path=dataset_path,
            )
        )

    # Validate SAMMY files if present
    if has_sammy_files:
        inp_files = list(sammy_data_dir.glob("*.inp"))
        for inp_file in inp_files:
            par_file = inp_file.with_suffix(".par")
            dat_file = inp_file.with_suffix(".dat")

            if not par_file.exists():
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Missing parameter file for {inp_file.name}",
                        path=par_file,
                    )
                )
            if not dat_file.exists():
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Missing data file for {inp_file.name}",
                        path=dat_file,
                    )
                )

    # Determine recommended workflow
    # Prefer simplified workflow when both are available since full workflow
    # is not yet implemented (see #172)
    recommended = None
    if can_run_simplified:
        recommended = WorkflowType.SIMPLIFIED
    elif can_run_full:
        recommended = WorkflowType.FULL

    # Dataset is valid if there are no errors
    has_errors = any(i.severity == "error" for i in issues)

    result = ValidationResult(
        valid=not has_errors,
        dataset_path=dataset_path,
        can_run_full_workflow=can_run_full,
        can_run_simplified_workflow=can_run_simplified,
        recommended_workflow=recommended,
        has_raw_data=has_raw,
        has_open_beam=has_ob,
        has_metadata=has_metadata,
        has_sammy_files=has_sammy_files,
        has_manifest=has_manifest,
        issues=issues,
    )

    if result.valid:
        logger.info(f"Dataset valid, recommended workflow: {recommended}")
    else:
        logger.warning(f"Dataset validation failed: {len(result.errors)} errors")

    return result


def extract_manifest(dataset_path: str | Path) -> ManifestData | None:
    """Extract and parse manifest from dataset.

    Args:
        dataset_path: Path to the dataset directory.

    Returns:
        ManifestData if manifest found and valid, None otherwise.

    Raises:
        ValueError: If manifest exists but has invalid format.
    """
    dataset_path = Path(dataset_path)

    # Try different manifest names
    manifest_paths = [
        dataset_path / "manifest_intermediate.md",
        dataset_path / "smcp_manifest.md",
        dataset_path / "manifest.md",
    ]

    manifest_path = None
    for candidate in manifest_paths:
        if candidate.exists():
            manifest_path = candidate
            break

    if manifest_path is None:
        logger.debug(f"No manifest found in {dataset_path}")
        return None

    logger.info(f"Parsing manifest: {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        content = f.read()

    # Split YAML frontmatter from Markdown body
    # Use maxsplit=2 to handle "---" in the markdown body (e.g., horizontal rules)
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid manifest format in {manifest_path}: missing YAML frontmatter")

    # Parse YAML frontmatter
    yaml_content = parts[1].strip()
    frontmatter = yaml.safe_load(yaml_content)

    # Handle datetime objects (PyYAML auto-parses ISO timestamps)
    if "created" in frontmatter and hasattr(frontmatter["created"], "isoformat"):
        frontmatter["created"] = frontmatter["created"].isoformat()

    # Extract markdown body (everything after the second "---")
    body = parts[2].strip()

    # Parse material properties if present
    material_props = None
    if "material_properties" in frontmatter and frontmatter["material_properties"]:
        mp = frontmatter["material_properties"]
        material_props = MaterialProperties(
            density_g_cm3=mp.get("density_g_cm3"),
            atomic_mass_amu=mp.get("atomic_mass_amu"),
            temperature_k=mp.get("temperature_k"),
        )

    return ManifestData(
        name=frontmatter.get("name", "unknown"),
        description=frontmatter.get("description", ""),
        version=frontmatter.get("version", "1.0.0"),
        created=frontmatter.get("created", ""),
        facility=frontmatter.get("facility"),
        beamline=frontmatter.get("beamline"),
        detector=frontmatter.get("detector"),
        sample_id=frontmatter.get("sample_id"),
        isotope=frontmatter.get("isotope"),
        material_properties=material_props,
        body=body,
        raw_frontmatter=frontmatter,
    )


def analyze_resonance(
    dataset_path: str | Path,
    *,
    backend: str = "auto",
    isotopes: list[str] | None = None,
    skip_validation: bool = False,
) -> ResonanceResult:
    """Execute complete resonance analysis workflow.

    This is the main entry point for resonance analysis. It automatically
    detects the appropriate workflow (full or simplified) based on the
    dataset contents and executes all necessary steps.

    Full workflow steps (imaging data):
        1. Validate dataset structure
        2. Normalize transmission data
        3. Convert to SAMMY format
        4. Retrieve ENDF nuclear parameters
        5. Execute SAMMY fitting
        6. Parse and return results

    Simplified workflow steps (pre-existing SAMMY files):
        1. Validate dataset structure
        2. Execute SAMMY fitting
        3. Parse and return results

    Args:
        dataset_path: Path to the dataset directory.
        backend: SAMMY backend to use ('local', 'docker', 'nova', or 'auto').
        isotopes: List of isotopes to analyze. If None, detected from manifest.
        skip_validation: Skip dataset validation (use with caution).

    Returns:
        ResonanceResult with analysis results and output paths.
        If the dataset is invalid and skip_validation=False, returns a
        ResonanceResult with success=False and an appropriate error message.

    Example:
        >>> result = analyze_resonance("/data/Au197_sample")
        >>> if result.success:
        ...     print(f"Reduced chi²: {result.reduced_chi_squared:.3f}")
        ...     print(f"Fit quality: {result.fit_quality.value}")
        >>> else:
        ...     print(f"Analysis failed: {result.error_message}")
    """
    import time

    dataset_path = Path(dataset_path)
    start_time = time.time()
    workflow_steps: dict[str, str] = {}

    logger.info(f"Starting resonance analysis: {dataset_path}")

    # Step 1: Validate dataset
    if not skip_validation:
        workflow_steps["validation"] = "running"
        validation = validate_dataset(dataset_path)

        if not validation.valid:
            return ResonanceResult(
                success=False,
                workflow_type=WorkflowType.SIMPLIFIED,
                primary_isotope="unknown",
                error_message="Dataset validation failed",
                error_step="validation",
                workflow_steps={"validation": "failed"},
            )
        workflow_steps["validation"] = "completed"

        # Determine workflow type
        # Prefer simplified workflow when both are available since full workflow
        # is not yet implemented (see #172) - matches validate_dataset logic
        if validation.can_run_simplified_workflow:
            workflow_type = WorkflowType.SIMPLIFIED
        elif validation.can_run_full_workflow:
            workflow_type = WorkflowType.FULL
        else:
            return ResonanceResult(
                success=False,
                workflow_type=WorkflowType.SIMPLIFIED,
                primary_isotope="unknown",
                error_message="No valid workflow detected for dataset",
                error_step="validation",
                workflow_steps=workflow_steps,
            )
    else:
        # Assume simplified workflow if skipping validation
        sammy_data_dir = dataset_path / "sammy_data"
        if sammy_data_dir.exists() and list(sammy_data_dir.glob("*.inp")):
            workflow_type = WorkflowType.SIMPLIFIED
        else:
            workflow_type = WorkflowType.FULL

    # Extract manifest for parameters
    manifest = extract_manifest(dataset_path)
    primary_isotope = "unknown"
    if manifest and manifest.isotope:
        primary_isotope = manifest.isotope
    if isotopes:
        primary_isotope = isotopes[0]

    # Execute appropriate workflow
    if workflow_type == WorkflowType.SIMPLIFIED:
        return _execute_simplified_workflow(
            dataset_path=dataset_path,
            primary_isotope=primary_isotope,
            backend=backend,
            start_time=start_time,
            workflow_steps=workflow_steps,
        )
    else:
        return _execute_full_workflow(
            dataset_path=dataset_path,
            manifest=manifest,
            primary_isotope=primary_isotope,
            isotopes=isotopes,
            backend=backend,
            start_time=start_time,
            workflow_steps=workflow_steps,
        )


def _execute_simplified_workflow(
    dataset_path: Path,
    primary_isotope: str,
    backend: str,
    start_time: float,
    workflow_steps: dict[str, str],
) -> ResonanceResult:
    """Execute simplified workflow with pre-existing SAMMY files."""
    import time

    from pleiades.sammy.interface import SammyFiles
    from pleiades.sammy.results.manager import ResultsManager

    sammy_data_dir = dataset_path / "sammy_data"

    # Find SAMMY input files
    inp_files = list(sammy_data_dir.glob("*.inp"))
    if not inp_files:
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.SIMPLIFIED,
            primary_isotope=primary_isotope,
            error_message=f"No .inp files found in {sammy_data_dir}",
            error_step="file_discovery",
            workflow_steps=workflow_steps,
        )

    inp_file = inp_files[0]
    par_file = inp_file.with_suffix(".par")
    dat_file = inp_file.with_suffix(".dat")

    # Validate required files
    if not par_file.exists():
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.SIMPLIFIED,
            primary_isotope=primary_isotope,
            error_message=f"Parameter file not found: {par_file}",
            error_step="file_discovery",
            workflow_steps=workflow_steps,
        )

    if not dat_file.exists():
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.SIMPLIFIED,
            primary_isotope=primary_isotope,
            error_message=f"Data file not found: {dat_file}",
            error_step="file_discovery",
            workflow_steps=workflow_steps,
        )

    logger.info(f"Running simplified workflow with {inp_file.name}")

    # Create working/output directories
    sammy_working = dataset_path / "sammy_working"
    sammy_output = dataset_path / "sammy_output"
    sammy_working.mkdir(exist_ok=True)
    sammy_output.mkdir(exist_ok=True)

    # Get SAMMY runner
    workflow_steps["backend_setup"] = "running"
    try:
        runner = _get_sammy_runner(backend, sammy_working, sammy_output)
        workflow_steps["backend_setup"] = "completed"
    except Exception as e:
        logger.error(f"Failed to create SAMMY runner: {e}")
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.SIMPLIFIED,
            primary_isotope=primary_isotope,
            error_message=str(e),
            error_step="backend_setup",
            workflow_steps=workflow_steps,
        )

    # Execute SAMMY
    workflow_steps["sammy_execution"] = "running"
    files = SammyFiles(
        input_file=inp_file,
        parameter_file=par_file,
        data_file=dat_file,
    )

    try:
        runner.prepare_environment(files)
        exec_result = runner.execute_sammy(files)

        if not exec_result.success:
            return ResonanceResult(
                success=False,
                workflow_type=WorkflowType.SIMPLIFIED,
                primary_isotope=primary_isotope,
                error_message=f"SAMMY execution failed: {exec_result.error_message}",
                error_step="sammy_execution",
                workflow_steps=workflow_steps,
            )

        runner.collect_outputs(exec_result)
        workflow_steps["sammy_execution"] = "completed"
    except Exception as e:
        logger.error(f"SAMMY execution error: {e}")
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.SIMPLIFIED,
            primary_isotope=primary_isotope,
            error_message=str(e),
            error_step="sammy_execution",
            workflow_steps=workflow_steps,
        )

    # Parse results
    workflow_steps["results_parsing"] = "running"
    try:
        lpt_file = sammy_output / "SAMMY.LPT"
        lst_file = sammy_output / "SAMMY.LST"

        results_manager = ResultsManager(
            lpt_file_path=lpt_file,
            lst_file_path=lst_file,
        )

        fit_results = results_manager.run_results.fit_results
        if not fit_results:
            error_msg = "No fit results found in SAMMY output"
            logger.error(error_msg)
            return ResonanceResult(
                success=False,
                workflow_type=WorkflowType.SIMPLIFIED,
                primary_isotope=primary_isotope,
                error_message=error_msg,
                error_step="results_parsing",
                workflow_steps=workflow_steps,
            )

        final_fit = fit_results[-1]
        chi_sq = final_fit.chi_squared_results

        # Extract broadening parameters if available
        temperature = None
        number_density = None
        try:
            broadening = final_fit.physics_data.broadening_parameters
            temperature = float(broadening.temp)
            number_density = float(broadening.thick)
        except (AttributeError, KeyError) as e:
            logger.debug(f"Broadening parameters not available: {e}")

        workflow_steps["results_parsing"] = "completed"
    except Exception as e:
        logger.error(f"Results parsing error: {e}")
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.SIMPLIFIED,
            primary_isotope=primary_isotope,
            error_message=str(e),
            error_step="results_parsing",
            workflow_steps=workflow_steps,
        )

    # Build successful result
    runtime = time.time() - start_time

    return ResonanceResult(
        success=True,
        workflow_type=WorkflowType.SIMPLIFIED,
        primary_isotope=primary_isotope,
        isotopes_analyzed=[primary_isotope],
        chi_squared=float(chi_sq.chi_squared) if chi_sq.chi_squared else None,
        reduced_chi_squared=float(chi_sq.reduced_chi_squared) if chi_sq.reduced_chi_squared else None,
        degrees_of_freedom=chi_sq.dof,
        fit_quality=FitQuality.from_chi_squared(chi_sq.reduced_chi_squared) if chi_sq.reduced_chi_squared else None,
        number_density=number_density,
        temperature_k=temperature,
        output_dir=sammy_output,
        lpt_file=lpt_file,
        lst_file=lst_file,
        par_file=sammy_output / "SAMMY.PAR",
        runtime_seconds=runtime,
        workflow_steps=workflow_steps,
    )


def _execute_full_workflow(
    dataset_path: Path,
    manifest: ManifestData | None,
    primary_isotope: str,
    isotopes: list[str] | None,
    backend: str,
    start_time: float,
    workflow_steps: dict[str, str],
) -> ResonanceResult:
    """Execute full workflow from imaging data.

    This is a placeholder for the full imaging workflow.
    Full implementation will be added when imaging processing
    infrastructure is ready.
    """
    # TODO(#172): Implement full imaging workflow
    # This requires:
    # - pleiades.processing.normalization
    # - pleiades.sammy.io.data_manager (CSV to SAMMY conversion)
    # - pleiades.sammy.io.json_manager (multi-isotope JSON config)
    # - pleiades.sammy.io.inp_manager (INP file generation)

    logger.warning("Full imaging workflow not yet implemented")

    return ResonanceResult(
        success=False,
        workflow_type=WorkflowType.FULL,
        primary_isotope=primary_isotope,
        error_message="Full imaging workflow not yet implemented. Use simplified workflow with pre-existing SAMMY files.",
        error_step="workflow_selection",
        workflow_steps=workflow_steps,
    )


def _get_sammy_runner(
    backend: str,
    working_dir: Path,
    output_dir: Path,
) -> SammyRunner:
    """Get appropriate SAMMY runner based on backend selection.

    Args:
        backend: Backend type ('local', 'docker', 'nova', or 'auto').
        working_dir: SAMMY working directory.
        output_dir: SAMMY output directory.

    Returns:
        Configured SammyRunner instance.

    Raises:
        ValueError: If backend is not available.
        FileNotFoundError: If local SAMMY executable not found.
    """
    from pleiades.sammy.factory import SammyFactory

    working_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    if backend == "auto":
        logger.info("Auto-selecting SAMMY backend")
        return SammyFactory.auto_select(
            working_dir=working_dir,
            output_dir=output_dir,
        )

    logger.info(f"Creating {backend} SAMMY backend")
    return SammyFactory.create_runner(
        backend_type=backend,
        working_dir=working_dir,
        output_dir=output_dir,
    )
