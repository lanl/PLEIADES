#!/usr/bin/env python
"""Local backend implementation for SAMMY execution."""

import subprocess
import textwrap
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from pleiades.sammy.config import LocalSammyConfig
from pleiades.sammy.interface import (
    EnvironmentPreparationError,
    SammyExecutionError,
    SammyExecutionResult,
    SammyFiles,
    SammyRunner,
)
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

# Known SAMMY output file patterns
SAMMY_OUTPUT_FILES = {
    "SAMMY.LPT",  # Log file
    "SAMMIE.ODF",  # Output data file
    "SAMNDF.PAR",  # Updated parameter file
    "SAMRESOLVED.PAR",  # Additional parameter file
}


class LocalSammyRunner(SammyRunner):
    """Implementation of SAMMY runner for local installation."""

    def __init__(self, config: LocalSammyConfig):
        super().__init__(config)
        self.config: LocalSammyConfig = config
        self._moved_files: List[Path] = []

    def prepare_environment(self, files: SammyFiles) -> None:
        """Prepare environment for local SAMMY execution."""
        try:
            logger.debug("Validating input files")
            files.validate()

            # Move files to working directory - copy input and parameter files, symlink data file
            logger.debug("Moving files to working directory")
            files.move_to_working_dir(self.config.working_dir)

            # No need to validate directories as this is done in config validation
            logger.debug("Environment preparation complete")

        except Exception as e:
            raise EnvironmentPreparationError(f"Environment preparation failed: {str(e)}")

    def execute_sammy(self, files: SammyFiles) -> SammyExecutionResult:
        """Execute SAMMY using local installation."""
        execution_id = str(uuid4())
        start_time = datetime.now()

        logger.info(f"Starting SAMMY execution {execution_id}")
        logger.debug(f"Working directory: {self.config.working_dir}")

        sammy_command = textwrap.dedent(f"""\
            {self.config.sammy_executable} <<EOF
            {files.input_file.name}
            {files.parameter_file.name}
            {files.data_file.name}
            EOF""")

        try:
            process = subprocess.run(
                sammy_command,
                shell=True,
                executable=str(self.config.shell_path),
                env=self.config.env_vars,
                cwd=str(self.config.working_dir),
                capture_output=True,
                text=True,
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
