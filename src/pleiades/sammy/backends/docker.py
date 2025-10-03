#!/usr/bin/env python
"""Docker backend implementation for SAMMY execution."""

import shutil
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from pleiades.sammy.config import DockerSammyConfig
from pleiades.sammy.interface import (
    EnvironmentPreparationError,
    SammyExecutionError,
    SammyExecutionResult,
    SammyFiles,
    SammyRunner,
)
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class DockerSammyRunner(SammyRunner):
    """Implementation of SAMMY runner for Docker container."""

    def __init__(self, config: DockerSammyConfig):
        super().__init__(config)
        self.config = config
        self._moved_files = []

    def prepare_environment(self, files: SammyFiles) -> None:
        """
        Prepare environment for Docker SAMMY execution.

        Args:
            files: Container with paths to required input files

        Raises:
            EnvironmentPreparationError: If preparation fails
        """
        try:
            # Validate input files exist
            files.validate()

            # Validate docker is available
            if shutil.which("docker") is None:
                raise EnvironmentPreparationError("Docker not found in PATH")

            # Verify docker image exists
            result = subprocess.run(
                ["docker", "image", "inspect", self.config.image_name], capture_output=True, text=True
            )
            if result.returncode != 0:
                raise EnvironmentPreparationError(f"Docker image not found: {self.config.image_name}")

        except EnvironmentPreparationError:
            raise  # Reraise to avoid double logging
        except Exception as e:
            raise EnvironmentPreparationError(f"Environment preparation failed: {str(e)}")

    def execute_sammy(self, files: SammyFiles) -> SammyExecutionResult:
        """
        Execute SAMMY using Docker container.

        Args:
            files: Container with paths to required input files

        Returns:
            SammyExecutionResult containing execution status and outputs

        Raises:
            SammyExecutionError: If execution fails
        """
        execution_id = str(uuid4())
        start_time = datetime.now()

        logger.info(f"Starting SAMMY execution {execution_id} in Docker")
        logger.debug(f"Input files from: {files.input_file.parent}")
        logger.debug(f"Working directory: {self.config.working_dir}")

        # Prepare container paths for input files
        container_input = str(self.config.container_data_dir / files.input_file.name)
        container_params = str(self.config.container_data_dir / files.parameter_file.name)
        container_data = str(self.config.container_data_dir / files.data_file.name)

        # Construct docker run command
        docker_cmd = [
            "docker",
            "run",
            "--rm",  # Remove container after execution
            "-i",  # Interactive mode for heredoc input
            # Mount working directory
            "-v",
            f"{self.config.working_dir}:{self.config.container_working_dir}",
            # Mount data directory
            "-v",
            f"{files.input_file.parent}:{self.config.container_data_dir}",
            # Set working directory
            "-w",
            str(self.config.container_working_dir),
            # Image name
            self.config.image_name,
            # SAMMY command (will receive input via stdin)
            "sammy",
        ]

        # Prepare SAMMY input
        sammy_input = textwrap.dedent(f"""\
            {container_input}
            {container_params}
            {container_data}
            """)

        try:
            process = subprocess.run(docker_cmd, input=sammy_input, text=True, capture_output=True)

            end_time = datetime.now()
            console_output = process.stdout + process.stderr

            if process.returncode != 0:
                logger.error(f"Docker execution failed with code {process.returncode}")
                return SammyExecutionResult(
                    success=False,
                    execution_id=execution_id,
                    start_time=start_time,
                    end_time=end_time,
                    console_output=console_output,
                    error_message=f"Docker execution failed with code {process.returncode}",
                )

            # Check SAMMY output for success
            success = " Normal finish to SAMMY" in console_output
            error_message = None if success else "SAMMY execution failed"

            if not success:
                logger.error(f"SAMMY execution failed for {execution_id}")
            else:
                logger.info(f"SAMMY execution completed successfully for {execution_id}")

            return SammyExecutionResult(
                success=success,
                execution_id=execution_id,
                start_time=start_time,
                end_time=end_time,
                console_output=console_output,
                error_message=error_message,
            )

        except Exception as e:
            logger.exception(f"Docker execution failed for {execution_id}")
            raise SammyExecutionError(f"Docker execution failed: {str(e)}")

    def cleanup(self) -> None:
        """Clean up after execution."""
        logger.debug("Performing cleanup")
        self._moved_files = []

    def validate_config(self) -> bool:
        """Validate the configuration."""
        return self.config.validate()


if __name__ == "__main__":
    # Setup paths
    test_data_dir = Path(__file__).parents[4] / "tests/data/ex012"
    working_dir = Path.home() / "tmp" / "sammy_docker_run"
    output_dir = working_dir / "output"

    try:
        # Create and validate config
        config = DockerSammyConfig(image_name="kedokudo/sammy-docker", working_dir=working_dir, output_dir=output_dir)
        config.validate()

        # Create files container
        files = SammyFiles(
            input_file=test_data_dir / "ex012a.inp",
            parameter_file=test_data_dir / "ex012a.par",
            data_file=test_data_dir / "ex012a.dat",
        )

        # Create and use runner
        runner = DockerSammyRunner(config)

        # Execute pipeline
        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        # Process results
        if result.success:
            print(f"SAMMY execution successful (runtime: {result.runtime_seconds:.2f}s)")
            runner.collect_outputs(result)
            print(f"Output files available in: {output_dir}")
        else:
            print("SAMMY execution failed:")
            print(result.error_message)
            print("\nConsole output:")
            print(result.console_output)

    except Exception as e:
        print(f"Error running SAMMY: {str(e)}")

    finally:
        runner.cleanup()
