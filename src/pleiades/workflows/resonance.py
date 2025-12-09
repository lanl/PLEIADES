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

import math
import re
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

from pleiades.nuclear.isotopes.manager import IsotopeManager

logger = loguru_logger.bind(name=__name__)

# Module-level IsotopeManager instance for data-driven isotope lookup
_isotope_manager = IsotopeManager()

# Compiled regex for validating primary_isotope format
# Format: Element symbol (1-2 chars, first uppercase) optionally followed by -number or -nat
# Examples: "Hf", "Hf-177", "Hf-nat", "U-235", "Au-197"
_ISOTOPE_PATTERN = re.compile(r"^[A-Z][a-z]?(-(\d+|nat))?$")


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
    # is not yet implemented (see #201)
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

    # Handle empty frontmatter (yaml.safe_load returns None for empty content)
    if frontmatter is None:
        frontmatter = {}

    # Handle datetime objects (PyYAML auto-parses ISO timestamps)
    if "created" in frontmatter and hasattr(frontmatter["created"], "isoformat"):
        frontmatter["created"] = frontmatter["created"].isoformat()

    # Extract markdown body (everything after the second "---")
    body = parts[2].strip()

    # Parse material properties if present
    material_props = None
    if "material_properties" in frontmatter and frontmatter["material_properties"]:
        mp = frontmatter["material_properties"]
        try:
            material_props = MaterialProperties(
                density_g_cm3=mp.get("density_g_cm3"),
                atomic_mass_amu=mp.get("atomic_mass_amu"),
                temperature_k=mp.get("temperature_k"),
            )
        except Exception as e:
            # Log but don't fail - material properties are optional for some workflows
            logger.warning(f"Invalid material_properties in manifest: {e}")

    # Parse enrichment configuration (Issue #204)
    use_natural_abundance = frontmatter.get("use_natural_abundance", True)
    enrichment = frontmatter.get("enrichment")

    # Parse explicit isotopes list (Issue #206)
    isotopes = frontmatter.get("isotopes")

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
        use_natural_abundance=use_natural_abundance,
        enrichment=enrichment,
        isotopes=isotopes,
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

    # Validate isotopes parameter
    if isotopes is not None and len(isotopes) == 0:
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.SIMPLIFIED,
            primary_isotope="unknown",
            error_message="isotopes parameter cannot be an empty list",
            error_step="parameter_validation",
            workflow_steps={},
        )

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
        # is not yet implemented (see #201) - matches validate_dataset logic
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
        # When skipping validation, detect workflow from available files
        sammy_data_dir = dataset_path / "sammy_data"
        try:
            has_sammy_files = sammy_data_dir.exists() and any(sammy_data_dir.glob("*.inp"))
        except (PermissionError, OSError) as e:
            logger.warning(f"Cannot access sammy_data directory: {e}")
            has_sammy_files = False
        has_imaging_data = (dataset_path / "raw").exists() and (dataset_path / "open_beam").exists()

        if has_sammy_files:
            workflow_type = WorkflowType.SIMPLIFIED
        elif has_imaging_data:
            workflow_type = WorkflowType.FULL
        else:
            # Neither workflow is available - return clear error
            return ResonanceResult(
                success=False,
                workflow_type=WorkflowType.SIMPLIFIED,
                primary_isotope="unknown",
                error_message="No SAMMY files (sammy_data/*.inp) or imaging data (raw/, open_beam/) found",
                error_step="file_discovery",
                workflow_steps=workflow_steps,
            )

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


def _get_isotope_composition(
    user_isotopes: list[str] | None,
    manifest: ManifestData | None,
    primary_isotope: str,
) -> tuple[list[str], list[float]]:
    """Get isotope list and abundances for analysis.

    Determines the isotopes and their relative abundances based on:
    1. User-specified isotopes (highest priority) - equal weights
    2. Manifest isotopes list (Issue #206) - explicit subset with equal weights
    3. Manifest enrichment data - custom composition
    4. Natural abundance from isotopes.info - data-driven lookup

    Args:
        user_isotopes: User-specified list of isotopes (takes priority).
        manifest: Parsed manifest data (may contain isotopes list or enrichment info).
        primary_isotope: Primary isotope from manifest or detection.
            Valid formats: "Hf-177", "Hf-nat", "Hf"

    Returns:
        Tuple of (isotope_list, abundance_list).

    Raises:
        ValueError: If no isotopes can be determined or primary_isotope format is invalid.

    Example:
        >>> isotopes, abundances = _get_isotope_composition(None, None, "Hf-177")
        >>> # Returns all 6 natural Hf isotopes with natural abundances
    """
    # Priority 1: User-specified isotopes with equal weights
    if user_isotopes:
        abundances = [1.0 / len(user_isotopes)] * len(user_isotopes)
        return user_isotopes, abundances

    # Priority 2: Manifest isotopes list with equal weights (Issue #206)
    # Note: Empty list falls through to natural abundance lookup
    if manifest and manifest.isotopes:
        abundances = [1.0 / len(manifest.isotopes)] * len(manifest.isotopes)
        return list(manifest.isotopes), abundances

    # Priority 3: Manifest enrichment data
    # Use explicit iteration to ensure isotope-abundance pairing is correct
    if manifest and not manifest.use_natural_abundance and manifest.enrichment:
        items = list(manifest.enrichment.items())
        isotopes = [iso for iso, _ in items]
        abundances = [abund for _, abund in items]
        return isotopes, abundances

    # Priority 4: Natural abundance from isotopes.info
    # Validate primary_isotope format before extraction
    if not primary_isotope or not primary_isotope.strip():
        raise ValueError("primary_isotope cannot be empty. Valid formats: 'Hf-177', 'Hf-nat', 'Hf'")

    # Validate format using module-level compiled pattern
    if not _ISOTOPE_PATTERN.match(primary_isotope.strip()):
        raise ValueError(
            f"Invalid primary_isotope format: '{primary_isotope}'. "
            f"Valid formats: 'Hf-177', 'Hf-nat', 'Hf'. "
            f"Element symbol must start with uppercase letter (e.g., 'Hf', not 'hf')."
        )

    # Extract element from primary_isotope (e.g., "Hf-177" -> "Hf", "Hf" -> "Hf", "Hf-nat" -> "Hf")
    element = primary_isotope.split("-")[0]

    # Get natural composition from IsotopeManager
    composition = _isotope_manager.get_natural_composition(element)

    if not composition:
        raise ValueError(
            f"No natural isotopes found for element '{element}' (from primary_isotope='{primary_isotope}'). "
            f"Valid formats: 'Hf-177', 'Hf-nat', 'Hf'. "
            f"Element symbol must be a valid chemical element (e.g., 'Hf', 'U', 'Au'). "
            f"Alternatively, provide explicit isotopes via the isotopes parameter."
        )

    # Use explicit iteration to ensure isotope-abundance pairing is correct
    items = list(composition.items())
    isotopes = [iso for iso, _ in items]
    abundances = [abund for _, abund in items]

    return isotopes, abundances


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

        # Verify SAMMY produced output files
        if not lpt_file.exists():
            error_msg = f"SAMMY output file not found: {lpt_file}"
            logger.error(error_msg)
            return ResonanceResult(
                success=False,
                workflow_type=WorkflowType.SIMPLIFIED,
                primary_isotope=primary_isotope,
                error_message=error_msg,
                error_step="results_parsing",
                workflow_steps=workflow_steps,
            )

        if not lst_file.exists():
            error_msg = f"SAMMY output file not found: {lst_file}"
            logger.error(error_msg)
            return ResonanceResult(
                success=False,
                workflow_type=WorkflowType.SIMPLIFIED,
                primary_isotope=primary_isotope,
                error_message=error_msg,
                error_step="results_parsing",
                workflow_steps=workflow_steps,
            )

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

        # Extract broadening parameters (Issue #204: upgraded from debug to warning)
        temperature = None
        number_density = None
        try:
            broadening = final_fit.physics_data.broadening_parameters
            temperature = float(broadening.temp)
            number_density = float(broadening.thick)
        except (AttributeError, KeyError, ValueError, TypeError) as e:
            # Broadening parameters are important for fit quality assessment
            # Missing parameters may indicate incomplete SAMMY output
            logger.warning(f"Broadening parameters not available in SAMMY output: {e}")

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

    # Use 'is not None' instead of truthiness check since 0.0 is a valid chi-squared value
    # Also check chi_sq itself is not None before accessing its attributes
    chi_squared_val = None
    reduced_chi_sq_val = None
    dof_val = None
    if chi_sq is not None:
        chi_squared_val = float(chi_sq.chi_squared) if chi_sq.chi_squared is not None else None
        reduced_chi_sq_val = float(chi_sq.reduced_chi_squared) if chi_sq.reduced_chi_squared is not None else None
        dof_val = chi_sq.dof if chi_sq.dof is not None else None
    fit_quality_val = FitQuality.from_chi_squared(reduced_chi_sq_val) if reduced_chi_sq_val is not None else None

    return ResonanceResult(
        success=True,
        workflow_type=WorkflowType.SIMPLIFIED,
        primary_isotope=primary_isotope,
        isotopes_analyzed=[primary_isotope],
        chi_squared=chi_squared_val,
        reduced_chi_squared=reduced_chi_sq_val,
        degrees_of_freedom=dof_val,
        fit_quality=fit_quality_val,
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

    Full workflow steps:
        1. Normalization (TIFF images → transmission spectra)
        2. Format conversion (CSV → SAMMY .twenty format)
        3. ENDF retrieval (download nuclear parameters)
        4. INP file generation (create SAMMY input)
        5. SAMMY execution (run fitting)
        6. Results parsing (extract fit parameters)
        7. Plotting (generate fit plot)

    Args:
        dataset_path: Path to dataset directory.
        manifest: Parsed manifest data (optional but recommended).
        primary_isotope: Primary isotope being analyzed.
        isotopes: List of isotopes for multi-isotope analysis.
        backend: SAMMY backend to use.
        start_time: Workflow start time for runtime calculation.
        workflow_steps: Dictionary to track step completion.

    Returns:
        ResonanceResult with analysis results.
    """
    import time

    from pleiades.processing import Facility
    from pleiades.processing.normalization import normalization
    from pleiades.sammy.interface import SammyFilesMultiMode
    from pleiades.sammy.io.data_manager import convert_csv_to_sammy_twenty
    from pleiades.sammy.io.inp_manager import InpManager
    from pleiades.sammy.io.json_manager import JsonManager
    from pleiades.sammy.results.manager import ResultsManager

    # Step 1: Normalization (imaging data -> transmission spectra)
    workflow_steps["normalization"] = "running"
    logger.info("Step 1: Running normalization")

    try:
        sample_folders = [str(dataset_path / "raw")]
        ob_folders = [str(dataset_path / "open_beam")]
        nexus_path = str(dataset_path / "metadata")

        # Determine facility from manifest or default to ORNL (Issue #204)
        # Facility class only has 'ornl' and 'lanl' values
        facility = Facility.ornl  # Default
        if manifest and manifest.facility:
            facility_str = manifest.facility.lower()
            if facility_str in ("sns", "ornl"):
                facility = Facility.ornl
            elif facility_str in ("lansce", "lanl"):
                # LANSCE is at LANL (Los Alamos Neutron Science Center)
                facility = Facility.lanl
            else:
                # Unsupported facilities (e.g., J-PARC) default to ORNL with warning
                logger.warning(f"Unsupported facility '{manifest.facility}', defaulting to ORNL")

        spectra_dir = dataset_path / "spectra"
        spectra_dir.mkdir(exist_ok=True)

        transmissions = normalization(
            list_sample_folders=sample_folders,
            list_obs_folders=ob_folders,
            nexus_path=nexus_path,
            facility=facility,
            output_folder=str(spectra_dir),
        )

        if not transmissions:
            raise ValueError("Normalization produced no transmission spectra")

        workflow_steps["normalization"] = f"completed ({len(transmissions)} spectra)"
        logger.info(f"Normalization completed: {len(transmissions)} spectra")
    except Exception as e:
        logger.error(f"Normalization failed: {e}")
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.FULL,
            primary_isotope=primary_isotope,
            error_message=f"Normalization failed: {e}",
            error_step="normalization",
            workflow_steps=workflow_steps,
        )

    # Step 2: Format conversion (CSV -> SAMMY .twenty)
    workflow_steps["format_conversion"] = "running"
    logger.info("Step 2: Converting to SAMMY format")

    try:
        twenty_dir = dataset_path / "twenty"
        twenty_dir.mkdir(exist_ok=True)

        # Find transmission files created by normalization (space/tab-delimited .txt)
        txt_files = list(spectra_dir.glob("*transmission*.txt"))
        if not txt_files:
            txt_files = list(spectra_dir.glob("*.txt"))

        if not txt_files:
            raise ValueError(
                f"No transmission files found in {spectra_dir}. "
                f"Expected files matching '*transmission*.txt' or '*.txt'. "
                f"Check normalization output_folder setting."
            )

        twenty_files = []
        for txt_file in txt_files:
            # Replace .txt extension with .twenty
            twenty_file = twenty_dir / (txt_file.stem + ".twenty")
            convert_csv_to_sammy_twenty(str(txt_file), str(twenty_file))
            twenty_files.append(twenty_file)

        workflow_steps["format_conversion"] = f"completed ({len(twenty_files)} files)"
        logger.info(f"Format conversion completed: {len(twenty_files)} files")
    except Exception as e:
        logger.error(f"Format conversion failed: {e}")
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.FULL,
            primary_isotope=primary_isotope,
            error_message=f"Format conversion failed: {e}",
            error_step="format_conversion",
            workflow_steps=workflow_steps,
        )

    # Step 3: ENDF retrieval (nuclear data download)
    workflow_steps["endf_retrieval"] = "running"
    logger.info("Step 3: Retrieving ENDF nuclear data")

    try:
        # Determine isotopes for analysis using data-driven lookup (Issue #204)
        # Priority: user-specified > manifest enrichment > natural abundance from isotopes.info
        analysis_isotopes, abundances = _get_isotope_composition(
            user_isotopes=isotopes,
            manifest=manifest,
            primary_isotope=primary_isotope,
        )

        logger.info(f"Isotope composition: {dict(zip(analysis_isotopes, abundances))}")

        # Validate isotope list
        if not analysis_isotopes or not all(analysis_isotopes):
            raise ValueError(f"Invalid isotope configuration: {analysis_isotopes}")

        # Use dataset_path as working_dir (ENDF .par files go here)
        working_dir = dataset_path

        json_manager = JsonManager()
        json_path = json_manager.create_json_config(
            isotopes=analysis_isotopes,
            abundances=abundances,
            working_dir=str(working_dir),
            custom_global_settings={
                "forceRMoore": "yes",
                "purgeSpinGroups": "yes",
                "fudge": "0.7",
            },
        )

        # Validate JSON config was created
        if json_path is None or not json_path.exists():
            raise FileNotFoundError(f"JSON config file not created: {json_path}")

        # Verify ENDF parameter files were downloaded
        # Files use ENDF naming convention: e.g., 072-Hf-174.B-VIII.0.par
        for isotope in analysis_isotopes:
            # Match pattern like "*Hf-174*.par"
            pattern = f"*{isotope}*.par"
            matching_files = list(working_dir.glob(pattern))
            if not matching_files:
                raise FileNotFoundError(f"ENDF parameter file not found for {isotope} (pattern: {pattern})")

        workflow_steps["endf_retrieval"] = f"completed ({len(analysis_isotopes)} isotopes)"
        logger.info(f"ENDF retrieval completed: {', '.join(analysis_isotopes)}")
    except Exception as e:
        logger.error(f"ENDF retrieval failed: {e}")
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.FULL,
            primary_isotope=primary_isotope,
            error_message=f"ENDF retrieval failed: {e}",
            error_step="endf_retrieval",
            workflow_steps=workflow_steps,
        )

    # Step 4: SAMMY input file generation
    workflow_steps["inp_generation"] = "running"
    logger.info("Step 4: Generating SAMMY input file")

    try:
        # Get material properties from manifest
        if manifest and manifest.material_properties:
            mat_props = manifest.material_properties
            density = mat_props.density_g_cm3
            atomic_mass = mat_props.atomic_mass_amu
            temperature = mat_props.temperature_k or 293.6
        else:
            raise ValueError("Material properties required in manifest for full workflow")

        element = primary_isotope.split("-")[0]
        # Calculate weighted average mass number from isotope composition (Issue #204)
        mass_number = 0.0
        valid_isotope_count = 0
        for iso, abund in zip(analysis_isotopes, abundances):
            parts = iso.split("-")
            if len(parts) > 1:
                mass_part = parts[1]
                # Skip "nat" suffix - it's not a mass number
                if mass_part.lower() == "nat":
                    continue
                try:
                    mass_number += int(mass_part) * abund
                    valid_isotope_count += 1
                except ValueError:
                    logger.warning(f"Invalid mass number in isotope '{iso}', skipping")
                    continue

        # Validate we processed at least one valid isotope with a mass number
        if valid_isotope_count == 0:
            raise ValueError(
                f"No valid mass numbers found in isotopes {analysis_isotopes}. "
                f"Isotope strings must include numeric mass number (e.g., 'Hf-177', not 'Hf' or 'Hf-nat')."
            )

        # Use floor + 0.5 for consistent rounding (avoids banker's rounding)
        mass_number = int(math.floor(mass_number + 0.5))

        material_props = {
            "element": element,
            "mass_number": mass_number,
            "density_g_cm3": density,
            "atomic_mass_amu": atomic_mass,
            "abundance": 1.0,
            "thickness_mm": 0.05,  # Will be fitted by SAMMY
            "temperature_K": temperature,
            "min_energy": 1.0,
            "max_energy_eV": 200.0,
        }

        # Get resolution file path if available
        resolution_file_path = _get_resolution_file_path(dataset_path)

        inp_file = working_dir / "fitting.inp"
        InpManager.create_multi_isotope_inp(
            inp_file,
            title=f"{primary_isotope} resonance analysis",
            material_properties=material_props,
            resolution_file_path=resolution_file_path,
        )
        workflow_steps["inp_generation"] = "completed"
        logger.info("INP file generation completed")
    except Exception as e:
        logger.error(f"INP generation failed: {e}")
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.FULL,
            primary_isotope=primary_isotope,
            error_message=f"INP generation failed: {e}",
            error_step="inp_generation",
            workflow_steps=workflow_steps,
        )

    # Step 5: SAMMY execution
    workflow_steps["sammy_execution"] = "running"
    logger.info("Step 5: Running SAMMY")

    try:
        sammy_working = dataset_path / "sammy_working"
        sammy_output = dataset_path / "sammy_output"

        runner = _get_sammy_runner(backend, sammy_working, sammy_output)

        # Use first transmission file
        data_file = twenty_files[0] if twenty_files else None
        if not data_file:
            raise ValueError("No transmission data available for fitting")

        files = SammyFilesMultiMode(
            input_file=inp_file,
            json_config_file=Path(json_path),
            data_file=data_file,
            endf_directory=working_dir,
        )

        runner.prepare_environment(files)
        exec_result = runner.execute_sammy(files)

        if not exec_result.success:
            raise RuntimeError(f"SAMMY execution failed: {exec_result.error_message}")

        runner.collect_outputs(exec_result)
        workflow_steps["sammy_execution"] = f"completed ({exec_result.runtime_seconds:.2f}s)"
        logger.info(f"SAMMY execution completed in {exec_result.runtime_seconds:.2f}s")
    except Exception as e:
        logger.error(f"SAMMY execution failed: {e}")
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.FULL,
            primary_isotope=primary_isotope,
            error_message=f"SAMMY execution failed: {e}",
            error_step="sammy_execution",
            workflow_steps=workflow_steps,
        )

    # Step 6: Results parsing
    workflow_steps["results_parsing"] = "running"
    logger.info("Step 6: Parsing results")

    try:
        lpt_file = sammy_output / "SAMMY.LPT"
        lst_file = sammy_output / "SAMMY.LST"

        if not lpt_file.exists() or not lst_file.exists():
            raise FileNotFoundError("SAMMY output files not found")

        results_manager = ResultsManager(
            lpt_file_path=lpt_file,
            lst_file_path=lst_file,
        )

        fit_results = results_manager.run_results.fit_results
        if not fit_results:
            raise ValueError("No fit results found in SAMMY output")

        final_fit = fit_results[-1]
        chi_sq = final_fit.chi_squared_results

        # Extract broadening parameters (Issue #204: upgraded from debug to warning)
        temperature_result = None
        number_density = None
        try:
            broadening = final_fit.physics_data.broadening_parameters
            temperature_result = float(broadening.temp)
            number_density = float(broadening.thick)
        except (AttributeError, KeyError, ValueError, TypeError) as e:
            # Broadening parameters are important for fit quality assessment
            # Missing parameters may indicate incomplete SAMMY output
            logger.warning(f"Broadening parameters not available in SAMMY output: {e}")

        workflow_steps["results_parsing"] = "completed"
        logger.info("Results parsing completed")
    except Exception as e:
        logger.error(f"Results parsing failed: {e}")
        return ResonanceResult(
            success=False,
            workflow_type=WorkflowType.FULL,
            primary_isotope=primary_isotope,
            error_message=f"Results parsing failed: {e}",
            error_step="results_parsing",
            workflow_steps=workflow_steps,
        )

    # Step 7: Generate fitting plot
    workflow_steps["plotting"] = "running"
    logger.info("Step 7: Generating plot")

    plot_file = None
    try:
        plot_file = dataset_path / "fit_results.png"

        fig = results_manager.plot_transmission(
            figsize=(12, 8),
            title=f"{primary_isotope} Resonance Fit",
            xscale="log",
            data_color="blue",
            final_color="red",
            show=False,
            show_diff=True,
            plot_uncertainty=True,
        )

        fig.savefig(str(plot_file), dpi=300, bbox_inches="tight")
        workflow_steps["plotting"] = f"completed ({plot_file.name})"
        logger.info(f"Plot saved to {plot_file}")

        import matplotlib.pyplot as plt

        plt.close(fig)
    except Exception as e:
        logger.warning(f"Plotting failed (non-critical): {e}")
        workflow_steps["plotting"] = f"failed ({e})"
        plot_file = None

    # Build successful result
    runtime = time.time() - start_time

    chi_squared_val = float(chi_sq.chi_squared) if chi_sq and chi_sq.chi_squared is not None else None
    reduced_chi_sq_val = (
        float(chi_sq.reduced_chi_squared) if chi_sq and chi_sq.reduced_chi_squared is not None else None
    )
    dof_val = chi_sq.dof if chi_sq and chi_sq.dof is not None else None
    fit_quality_val = FitQuality.from_chi_squared(reduced_chi_sq_val) if reduced_chi_sq_val is not None else None

    return ResonanceResult(
        success=True,
        workflow_type=WorkflowType.FULL,
        primary_isotope=primary_isotope,
        isotopes_analyzed=analysis_isotopes,
        chi_squared=chi_squared_val,
        reduced_chi_squared=reduced_chi_sq_val,
        degrees_of_freedom=dof_val,
        fit_quality=fit_quality_val,
        number_density=number_density,
        temperature_k=temperature_result,
        output_dir=sammy_output,
        lpt_file=lpt_file,
        lst_file=lst_file,
        par_file=sammy_output / "SAMMY.PAR",
        plot_file=plot_file,
        runtime_seconds=runtime,
        workflow_steps=workflow_steps,
    )


def _get_resolution_file_path(dataset_path: Path) -> Path | None:
    """Get resolution file path for VENUS resonance analysis.

    Resolution file is facility-specific. Checks:
    1. VENUS_RES_FUNC environment variable
    2. Default VENUS location

    Args:
        dataset_path: Dataset root directory.

    Returns:
        Path to resolution file or None.
    """
    import os

    # Check environment variable
    venus_res = os.environ.get("VENUS_RES_FUNC", "")
    if venus_res:
        res_path = Path(venus_res)
        if res_path.exists():
            return res_path

    # Check default VENUS location
    default_venus_res = Path.home() / "SNS" / "VENUS" / "shared" / "instrument" / "resonance"
    if default_venus_res.exists():
        res_files = list(default_venus_res.glob("*.txt"))
        if res_files:
            return res_files[0]

    return None


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
