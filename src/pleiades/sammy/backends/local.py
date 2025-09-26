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
            with open(files.json_config_file, "r") as f:
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

    def execute_sammy(self, files: Union[SammyFiles, SammyFilesMultiMode]) -> SammyExecutionResult:
        """Execute SAMMY using local installation."""
        execution_id = str(uuid4())
        start_time = datetime.now()

        logger.info(f"Starting SAMMY execution {execution_id}")
        logger.debug(f"Working directory: {self.config.working_dir}")

        # Generate command based on file type
        # Prepare input text for SAMMY based on mode
        if isinstance(files, SammyFilesMultiMode):
            # JSON mode input format
            sammy_input = f"{files.input_file.name}\n#file {files.json_config_file.name}\n{files.data_file.name}\n\n"
            logger.debug("Using JSON mode input format")
        else:
            # Traditional mode input format
            sammy_input = f"{files.input_file.name}\n{files.parameter_file.name}\n{files.data_file.name}\n\n"
            logger.debug("Using traditional mode input format")

        try:
            # Ensure libcrypto.so.1.1 is found by adding /usr/lib64 to LD_LIBRARY_PATH
            env = dict(os.environ)
            env.update(self.config.env_vars)
            if "LD_LIBRARY_PATH" in env:
                env["LD_LIBRARY_PATH"] = f"/usr/lib64:{env['LD_LIBRARY_PATH']}"
            else:
                env["LD_LIBRARY_PATH"] = "/usr/lib64"

            # Use safer subprocess call without shell
            process = subprocess.run(
                [str(self.config.sammy_executable)],
                input=sammy_input,
                shell=False,
                text=True,
                env=env,
                cwd=str(self.config.working_dir),
                capture_output=True,
            )

            end_time = datetime.now()
            console_output = process.stdout + process.stderr
            success = " Normal finish to SAMMY" in console_output

            if not success:
                logger.error(f"SAMMY execution failed for {execution_id}")
                error_message = (
                    f"SAMMY execution failed with return code {process.returncode}. Check console output for details."
                )
            else:
                logger.info(f"SAMMY execution completed successfully for {execution_id}")
                error_message = None

            return SammyExecutionResult(
                success=success,
                execution_id=execution_id,
                start_time=start_time,
                end_time=end_time,
                console_output=console_output,
                error_message=error_message,
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
