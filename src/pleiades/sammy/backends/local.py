#!/usr/env/bin python
"""Local backend implementation for SAMMY execution."""

import logging
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from pleiades.sammy.config import LocalSammyConfig
from pleiades.sammy.interface import (
    EnvironmentPreparationError,
    OutputCollectionError,
    SammyExecutionError,
    SammyExecutionResult,
    SammyFiles,
    SammyRunner,
)

logger = logging.getLogger(__name__)

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
            {files.input_file}
            {files.parameter_file}
            {files.data_file}
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
                    f"SAMMY execution failed with return code {process.returncode}. "
                    "Check console output for details."
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

    def collect_outputs(self, result: SammyExecutionResult) -> None:
        """Collect and validate output files after execution."""
        collection_start = datetime.now()
        logger.info(f"Collecting outputs for execution {result.execution_id}")

        try:
            self._moved_files = []  # Reset moved files list
            found_outputs = set()

            # First check for known output files
            for known_file in SAMMY_OUTPUT_FILES:
                output_file = self.config.working_dir / known_file
                if output_file.is_file():
                    found_outputs.add(output_file)
                    logger.debug(f"Found known output file: {known_file}")

            # Then look for any additional SAM* files
            for output_file in self.config.working_dir.glob("SAM*"):
                if output_file.is_file() and output_file not in found_outputs:
                    found_outputs.add(output_file)
                    logger.debug(f"Found additional output file: {output_file.name}")

            if not found_outputs:
                logger.warning("No SAMMY output files found")
                if result.success:
                    logger.error("SAMMY reported success but produced no output files")
                return

            # Move all found outputs
            for output_file in found_outputs:
                dest = self.config.output_dir / output_file.name
                try:
                    if dest.exists():
                        logger.debug(f"Removing existing output file: {dest}")
                        dest.unlink()

                    output_file.rename(dest)
                    self._moved_files.append(dest)
                    logger.debug(f"Moved {output_file} to {dest}")

                except OSError as e:
                    self._rollback_moves()
                    raise OutputCollectionError(f"Failed to move output file {output_file}: {str(e)}")

            logger.info(
                f"Successfully collected {len(self._moved_files)} output files in "
                f"{(datetime.now() - collection_start).total_seconds():.2f} seconds"
            )

        except Exception as e:
            self._rollback_moves()
            raise OutputCollectionError(f"Output collection failed: {str(e)}")

    def _rollback_moves(self) -> None:
        """Rollback any moved files in case of error."""
        for moved_file in self._moved_files:
            try:
                original = self.config.working_dir / moved_file.name
                moved_file.rename(original)
            except Exception as e:
                logger.error(f"Failed to rollback move for {moved_file}: {str(e)}")

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
