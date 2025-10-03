#!/usr/bin/env python
"""NOVA web service backend implementation for SAMMY execution."""

import os
import zipfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from uuid import uuid4

from nova.galaxy import (
    Connection,
    Dataset,
    Parameters,
    Tool,
)

from pleiades.sammy.config import NovaSammyConfig
from pleiades.sammy.interface import (
    EnvironmentPreparationError,
    SammyExecutionError,
    SammyExecutionResult,
    SammyFiles,
    SammyRunner,
)
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class NovaConnectionError(Exception):
    """Raised when NOVA connection fails."""

    pass


class NovaSammyRunner(SammyRunner):
    """Implementation of SAMMY runner for NOVA web service."""

    def __init__(self, config: NovaSammyConfig):
        super().__init__(config)
        self.config: NovaSammyConfig = config
        self._nova: Optional[Connection] = None
        self._connection: Optional[Connection] = None
        self._datastore_name: Optional[str] = None
        self._temp_dir: Optional[TemporaryDirectory] = None

    def prepare_environment(self, files: SammyFiles) -> None:
        """
        Prepare NOVA environment and validate connection.

        Args:
            files: Container with paths to required input files

        Raises:
            EnvironmentPreparationError: If preparation fails
        """
        try:
            # Validate input files
            files.validate()

            self._connection = Connection(self.config.url, api_key=self.config.api_key)

            # Create temporary directory for downloads
            self._temp_dir = TemporaryDirectory()

        except Exception as e:
            raise EnvironmentPreparationError(f"NOVA environment preparation failed: {str(e)}")

    def execute_sammy(self, files: SammyFiles) -> SammyExecutionResult:
        """Execute SAMMY using NOVA web service."""
        execution_id = str(uuid4())
        start_time = datetime.now()

        logger.info(f"Starting SAMMY execution {execution_id} via NOVA")

        try:
            # Create unique datastore
            self._datastore_name = f"sammy_{execution_id}"
            datastore = self._connection.datastore(self._datastore_name)

            # Prepare tool and datasets
            tool = Tool(self._connection, tool_id=self.config.tool_id)

            # Add input files as datasets
            params = Parameters()
            params.add_input("inp", Dataset(str(files.input_file)))
            params.add_input("par", Dataset(str(files.parameter_file)))
            params.add_input("data", Dataset(str(files.data_file)))

            # Run SAMMY
            results = tool.run(datastore=self._datastore_name, parameters=params)

            # Get console output
            if self._temp_dir is None:
                raise SammyExecutionError("Temporary directory is not initialized.")
            output_zip = Path(self._temp_dir.name) / "sammy_outputs.zip"

            # Download and extract output files
            console_output = results.outputs["sammy_console_output"].get_content()
            results.outputs["sammy_output_files"].download(str(output_zip))

            # Extract files to output directory, handling nested structure
            with zipfile.ZipFile(output_zip) as zf:
                for zip_info in zf.filelist:
                    # Get just the filename, ignoring directory structure in ZIP
                    filename = Path(zip_info.filename).name
                    # Extract if it's a file (not directory) and starts with SAM
                    if not zip_info.is_dir() and (filename.startswith("SAM") or filename == "SAMMY.LPT"):
                        # Read the file from zip
                        with zf.open(zip_info) as source:
                            # Write to output directory
                            output_file = self.config.output_dir / filename
                            output_file.write_bytes(source.read())
                            logger.debug(f"Extracted {filename} to output directory")

            end_time = datetime.now()
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
            logger.exception(f"NOVA execution failed for {execution_id}")
            raise SammyExecutionError(f"NOVA execution failed: {str(e)}")

    def cleanup(self, files: Optional[SammyFiles] = None) -> None:
        """Clean up NOVA resources."""
        logger.debug("Performing NOVA cleanup")

        try:
            # Remove temporary directory if it exists
            if self._temp_dir is not None:
                self._temp_dir.cleanup()
                self._temp_dir = None

            if self._connection is not None:
                self._connection.close()
                self._connection = None

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def validate_config(self):
        """Validate the configuration."""
        return self.config.validate()


if __name__ == "__main__":
    # Setup paths
    test_data_dir = Path(__file__).parents[4] / "tests/data/ex012"
    working_dir = Path.home() / "tmp" / "sammy_nova_run"
    output_dir = working_dir / "output"

    try:
        # Get NOVA credentials from environment
        nova_url = os.environ.get("NOVA_URL")
        nova_api_key = os.environ.get("NOVA_API_KEY")

        if not nova_url or not nova_api_key:
            raise ValueError("NOVA_URL and NOVA_API_KEY environment variables must be set")

        # Create and validate config
        config = NovaSammyConfig(url=nova_url, api_key=nova_api_key, working_dir=working_dir, output_dir=output_dir)
        config.validate()

        # Create files container
        files = SammyFiles(
            input_file=test_data_dir / "ex012a.inp",
            parameter_file=test_data_dir / "ex012a.par",
            data_file=test_data_dir / "ex012a.dat",
        )

        # Create and use runner
        runner = NovaSammyRunner(config)

        # Execute pipeline
        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        # Process results
        if result.success:
            print(f"SAMMY execution successful (runtime: {result.runtime_seconds:.2f}s)")
            # NOTE: DO NOT collect here as nova runner packages all output files on the server
            #       and pleiades download the zip archive, extract and move to output directory.
            print(f"Output files available in: {output_dir}")
        else:
            print("SAMMY execution failed:")
            print(result.error_message)
            print("\nConsole output:")
            print(result.console_output)

    except Exception as e:
        print(f"Error running SAMMY: {str(e)}")

    finally:
        if "runner" in locals():
            runner.cleanup()
