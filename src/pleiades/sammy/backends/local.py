#!/usr/bin/env python
"""Local backend implementation for SAMMY execution."""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Union
from uuid import uuid4

from pleiades.sammy.config import LocalSammyConfig
from pleiades.sammy.interface import (
    EnvironmentPreparationError,
    SammyExecutionError,
    SammyExecutionResult,
    SammyFiles,
    SammyFilesMultiMode,
    SammyRunner,
)
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


def _move_broadening_inp_to_par(inp_file: Path, par_file: Path) -> None:
    """Move fitted broadening parameters from SAMNDF.INP to SAMNDF.PAR.

    After a JSON-mode pass, SAMMY writes broadening parameters into
    ``SAMNDF.INP`` (one or two ``BROADENING PARAMETERS FOLLOW`` data
    sections, plus the ``BROADENING IS WANTED`` command).  ``SAMNDF.PAR``
    does **not** contain a broadening section.

    Running a follow-up traditional-mode pass with broadening in the INP
    triggers ``STOP [Broadening parameters in both INPut & PAR files?]``
    because SAMMY interprets broadening in the INP data section as
    conflicting with the PAR file format.

    This helper:

    1. Extracts the **last** ``BROADENING PARAMETERS FOLLOW`` section from
       the INP (which contains the fitted values from pass 1).
    2. Appends that section to the PAR file.
    3. Strips the ``BROADENING IS WANTED`` command and all broadening data
       sections from the INP.

    This ensures pass 2 reads the fitted broadening from the PAR file only.

    Args:
        inp_file: Path to the SAMMY INP file (modified in-place).
        par_file: Path to the SAMMY PAR file (broadening section appended).
    """
    # --- Step 1: Extract broadening sections from INP ---
    with open(inp_file, encoding="utf-8") as f:
        lines = f.readlines()

    in_broadening = False
    filtered = []
    broadening_sections: list[list[str]] = []  # each section = [header, data..., blank]
    current_section: list[str] = []

    for line in lines:
        upper = line.upper().strip()

        # Remove the command
        if upper.startswith("BROADENING IS WANTED"):
            continue

        # Capture broadening data sections
        if upper.startswith("BROAD"):
            in_broadening = True
            current_section = [line]
            continue

        if in_broadening:
            current_section.append(line)
            if not line.strip():
                in_broadening = False
                broadening_sections.append(current_section)
                current_section = []
            continue

        filtered.append(line)

    # Handle broadening block that runs to EOF without a trailing blank line
    if in_broadening and current_section:
        broadening_sections.append(current_section)

    # Write cleaned INP
    with open(inp_file, "w", encoding="utf-8") as f:
        f.writelines(filtered)

    logger.debug(
        f"Stripped {len(broadening_sections)} broadening section(s) "
        f"and BROADENING IS WANTED command from {inp_file.name}"
    )

    # --- Step 2: Append last broadening section to PAR ---
    if broadening_sections:
        # Use the LAST section (contains fitted values from pass 1)
        fitted_section = broadening_sections[-1]

        with open(par_file, "a", encoding="utf-8") as f:
            # Ensure we start on a new line
            f.write("\n")
            f.writelines(fitted_section)

        logger.debug(f"Appended fitted broadening ({len(fitted_section)} lines) to {par_file.name}")
    else:
        logger.warning(f"No broadening sections found in {inp_file.name}")


def _enable_abundance_fitting_in_par(par_file: Path) -> None:
    """Modify a SAMMY parameter file in-place to enable per-isotope abundance fitting.

    Finds the Card Set 10 section (``ISOTOpic abundances and masses`` or
    ``NUCLIde abundances and masses``) and sets the IFLISO flag from 0 to 1
    for every isotope line.  IFLISO occupies columns 31-32 in the fixed-width
    Card-10 format (0 = fixed, 1 = vary).

    Args:
        par_file: Path to the SAMMY parameter file to modify in-place.
    """
    with open(par_file, encoding="utf-8") as f:
        lines = f.readlines()

    in_card10 = False
    in_continuation = False
    modified = []
    isotopes_modified = 0

    for line in lines:
        upper = line.upper().rstrip()

        # Detect Card 10 header
        if upper.startswith("ISOTO") or upper.startswith("NUCLI"):
            in_card10 = True
            in_continuation = False
            modified.append(line)
            continue

        if in_card10:
            # Blank line terminates Card 10
            if not line.strip():
                in_card10 = False
                in_continuation = False
                modified.append(line)
                continue

            stripped = line.strip()

            # "-1" marks the start of a spin-group continuation block
            if stripped == "-1":
                in_continuation = True
                modified.append(line)
                continue

            # Positively identify isotope data lines by atomic mass in cols 1-10.
            # Atomic masses are floats >= 1.0; continuation lines contain only
            # small integers for spin-group indices.
            is_isotope_line = False
            try:
                mass = float(line[:10])
                if mass >= 1.0:
                    is_isotope_line = True
                    in_continuation = False
            except (ValueError, IndexError):
                pass

            # Only modify IFLISO (columns 31-32) on isotope data lines
            if is_isotope_line and len(line) >= 32:
                line = line[:30] + " 1" + line[32:]
                isotopes_modified += 1

            modified.append(line)
        else:
            modified.append(line)

    with open(par_file, "w", encoding="utf-8") as f:
        f.writelines(modified)

    logger.debug(f"Enabled abundance fitting for {isotopes_modified} isotope(s) in {par_file.name}")


class LocalSammyRunner(SammyRunner):
    """Implementation of SAMMY runner for local installation."""

    def __init__(self, config: LocalSammyConfig):
        super().__init__(config)
        self.config: LocalSammyConfig = config
        self._moved_files: List[Path] = []

    def prepare_environment(self, files: Union[SammyFiles, SammyFilesMultiMode]) -> None:
        """Prepare environment for local SAMMY execution."""
        try:
            logger.debug("Validating input files")
            files.validate()

            # Additional validation for JSON mode
            if isinstance(files, SammyFilesMultiMode):
                logger.debug("Performing JSON-ENDF mapping validation")
                self._validate_json_endf_mapping(files)

            # Move files to working directory
            logger.debug("Moving files to working directory")
            files.move_to_working_dir(self.config.working_dir)

            # No need to validate directories as this is done in config validation
            logger.debug("Environment preparation complete")

        except Exception as e:
            raise EnvironmentPreparationError(f"Environment preparation failed: {str(e)}")

    def _validate_json_endf_mapping(self, files: SammyFilesMultiMode) -> None:
        """
        Validate that JSON configuration references existing ENDF files.

        Args:
            files: SammyFilesMultiMode containing JSON config and ENDF directory

        Raises:
            ValueError: If JSON references missing ENDF files
        """
        import json

        try:
            # Parse JSON to find referenced ENDF files
            with open(files.json_config_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # Find isotope entries (lists in JSON) - keys are ENDF filenames
            endf_files_referenced = []
            for key, value in json_data.items():
                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    # Key is the ENDF filename (e.g., "079-Au-197.B-VIII.0.par")
                    endf_files_referenced.append(key)

            # Check each referenced ENDF file exists in ENDF directory
            missing_files = []
            for endf_filename in endf_files_referenced:
                endf_path = files.endf_directory / endf_filename
                if not endf_path.exists():
                    missing_files.append(endf_filename)

            if missing_files:
                raise ValueError(
                    f"JSON references missing ENDF files: {missing_files}. "
                    f"Expected in directory: {files.endf_directory}"
                )

            logger.debug(f"JSON-ENDF validation passed: {len(endf_files_referenced)} ENDF files verified")

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON configuration file: {e}")

    def _build_env(self) -> dict:
        """Build environment variables for SAMMY subprocess."""
        env = dict(os.environ)
        env.update(self.config.env_vars)
        if "LD_LIBRARY_PATH" in env:
            env["LD_LIBRARY_PATH"] = f"/usr/lib64:{env['LD_LIBRARY_PATH']}"
        else:
            env["LD_LIBRARY_PATH"] = "/usr/lib64"
        return env

    def _run_sammy_once(self, sammy_input: str, env: dict) -> subprocess.CompletedProcess:
        """Run a single SAMMY subprocess invocation."""
        return subprocess.run(
            [str(self.config.sammy_executable)],
            input=sammy_input,
            shell=False,
            text=True,
            env=env,
            cwd=str(self.config.working_dir),
            capture_output=True,
        )

    def execute_sammy(self, files: Union[SammyFiles, SammyFilesMultiMode]) -> SammyExecutionResult:
        """Execute SAMMY using local installation.

        For ``SammyFilesMultiMode`` with ``fit_abundances=True``, a transparent
        two-pass strategy is used:

        1. **Pass 1 (JSON mode)** – SAMMY reads the JSON config and ENDF files,
           generates an internal parameter file (``SAMNDF.PAR``), and fits global
           parameters (thickness, normalization) with fixed per-isotope abundances.
        2. **Pass 2 (traditional mode)** – The generated ``SAMNDF.PAR`` is modified
           to set Card-10 IFLISO flags to 1 (vary abundance), then SAMMY re-runs
           in traditional mode to fit per-isotope abundances.

        The caller sees a single ``SammyExecutionResult``; the two passes are an
        implementation detail.
        """
        execution_id = str(uuid4())
        start_time = datetime.now()

        logger.info(f"Starting SAMMY execution {execution_id}")
        logger.debug(f"Working directory: {self.config.working_dir}")

        # Prepare input text for SAMMY based on mode
        if isinstance(files, SammyFilesMultiMode):
            sammy_input = f"{files.input_file.name}\n#file {files.json_config_file.name}\n{files.data_file.name}\n\n"
            logger.debug("Using JSON mode input format")
        else:
            sammy_input = f"{files.input_file.name}\n{files.parameter_file.name}\n{files.data_file.name}\n\n"
            logger.debug("Using traditional mode input format")

        try:
            env = self._build_env()

            # --- Pass 1 ---
            process = self._run_sammy_once(sammy_input, env)

            console_output = process.stdout + process.stderr
            success = " Normal finish to SAMMY" in console_output

            if not success:
                logger.error(f"SAMMY execution failed for {execution_id}")
                return SammyExecutionResult(
                    success=False,
                    execution_id=execution_id,
                    start_time=start_time,
                    end_time=datetime.now(),
                    console_output=console_output,
                    error_message=f"SAMMY execution failed with return code {process.returncode}. Check console output for details.",
                )

            # --- Pass 2 (abundance fitting) ---
            if isinstance(files, SammyFilesMultiMode) and files.fit_abundances:
                samndf_par = self.config.working_dir / "SAMNDF.PAR"
                samndf_inp = self.config.working_dir / "SAMNDF.INP"

                if samndf_par.exists() and samndf_inp.exists():
                    logger.info("Pass 2: enabling per-isotope abundance fitting (IFLISO=1)")
                    _enable_abundance_fitting_in_par(samndf_par)
                    # Move fitted broadening from INP → PAR to avoid
                    # "Broadening parameters in both INPut & PAR files?" error.
                    _move_broadening_inp_to_par(samndf_inp, samndf_par)

                    # Resolve the data file name as it exists in working_dir
                    data_name = files.data_file.name
                    sammy_input_2 = f"{samndf_inp.name}\n{samndf_par.name}\n{data_name}\n\n"

                    process2 = self._run_sammy_once(sammy_input_2, env)

                    console_output_2 = process2.stdout + process2.stderr
                    success = " Normal finish to SAMMY" in console_output_2
                    console_output += "\n--- Pass 2 (abundance fitting) ---\n" + console_output_2

                    if not success:
                        logger.error(f"SAMMY pass 2 (abundance) failed for {execution_id}")
                else:
                    logger.error(
                        "fit_abundances=True but SAMNDF.PAR/INP not found after pass 1; "
                        "cannot perform abundance fitting"
                    )
                    success = False

            end_time = datetime.now()
            logger.info(f"SAMMY execution completed for {execution_id} (success={success})")

            return SammyExecutionResult(
                success=success,
                execution_id=execution_id,
                start_time=start_time,
                end_time=end_time,
                console_output=console_output,
                error_message=None if success else "SAMMY pass 2 (abundance fitting) failed. Check console output.",
            )

        except Exception as e:
            logger.exception(f"SAMMY execution failed for {execution_id}")
            raise SammyExecutionError(f"SAMMY execution failed: {str(e)}")

    def cleanup(self) -> None:
        """Clean up after execution."""
        logger.debug("Performing cleanup for local backend")
        self._moved_files = []

    def validate_config(self) -> bool:
        """Validate the configuration."""
        return self.config.validate()


if __name__ == "__main__":
    from pathlib import Path

    # Setup paths
    sammy_executable = Path.home() / "code.ornl.gov/SAMMY/build/bin/sammy"
    test_data_dir = Path(__file__).parents[4] / "tests/data/ex012"
    working_dir = Path.home() / "tmp/pleiades_test"
    output_dir = working_dir / "output"

    # Create config
    config = LocalSammyConfig(sammy_executable=sammy_executable, working_dir=working_dir, output_dir=output_dir)
    config.validate()

    # Create files container
    files = SammyFiles(
        input_file=test_data_dir / "ex012a.inp",
        parameter_file=test_data_dir / "ex012a.par",
        data_file=test_data_dir / "ex012a.dat",
    )

    try:
        # Create and use runner
        runner = LocalSammyRunner(config)

        # Prepare environment
        runner.prepare_environment(files)

        # Execute SAMMY
        result = runner.execute_sammy(files)

        # Process results
        if result.success:
            print(f"SAMMY execution successful (runtime: {result.runtime_seconds:.2f}s)")
            runner.collect_outputs(result)
        else:
            print("SAMMY execution failed:")
            print(result.error_message)
            print("\nConsole output:")
            print(result.console_output)

    except Exception as e:
        print(f"Error running SAMMY: {str(e)}")

    finally:
        # Cleanup
        runner.cleanup()
