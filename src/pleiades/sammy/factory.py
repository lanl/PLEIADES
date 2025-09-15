#!/usr/bin/env python
"""Auto setup sammy runner with factory"""

import os
import re
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Union

import yaml

from pleiades.sammy.backends.docker import DockerSammyRunner
from pleiades.sammy.backends.local import LocalSammyRunner
from pleiades.sammy.backends.nova_ornl import NovaSammyRunner
from pleiades.sammy.config import DockerSammyConfig, LocalSammyConfig, NovaSammyConfig
from pleiades.sammy.interface import SammyFiles, SammyRunner
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class BackendType(Enum):
    """Supported SAMMY backend types."""

    LOCAL = "local"
    DOCKER = "docker"
    NOVA = "nova"


class FactoryError(Exception):
    """Base exception for factory errors."""

    pass


class BackendNotAvailableError(FactoryError):
    """Requested backend not available."""

    pass


class ConfigurationError(FactoryError):
    """Configuration error."""

    pass


class SammyFactory:
    """Factory for creating and managing SAMMY runners."""

    @staticmethod
    def list_available_backends() -> Dict[BackendType, bool]:
        """
        Check which backends are available in the current environment.

        Returns:
            Dict mapping backend types to their availability status

        Example:
            >>> SammyFactory.list_available_backends()
            {
                BackendType.LOCAL: True,
                BackendType.DOCKER: True,
                BackendType.NOVA: False
            }
        """
        available = {}

        # Check Local backend
        try:
            sammy_path = shutil.which("sammy")
            available[BackendType.LOCAL] = sammy_path is not None
            if sammy_path:
                logger.debug(f"Local SAMMY found at: {sammy_path}")
        except Exception as e:
            logger.debug(f"Error checking local backend: {str(e)}")
            available[BackendType.LOCAL] = False

        # Check Docker backend
        try:
            docker_available = shutil.which("docker") is not None
            if docker_available:
                # Check if we can run docker
                result = subprocess.run(["docker", "info"], capture_output=True, text=True)
                docker_available = result.returncode == 0
            available[BackendType.DOCKER] = docker_available
            if docker_available:
                logger.debug("Docker backend available")
        except Exception as e:
            logger.debug(f"Error checking docker backend: {str(e)}")
            available[BackendType.DOCKER] = False

        # Check NOVA backend
        try:
            nova_available = all(k in os.environ for k in ["NOVA_URL", "NOVA_API_KEY"])
            available[BackendType.NOVA] = nova_available
            if nova_available:
                logger.debug("NOVA credentials found")
        except Exception as e:
            logger.debug(f"Error checking NOVA backend: {str(e)}")
            available[BackendType.NOVA] = False

        return available

    @classmethod
    def create_runner(
        cls, backend_type: str, working_dir: Path, output_dir: Optional[Path] = None, **kwargs
    ) -> SammyRunner:
        """
        Create a SAMMY runner with the specified backend and configuration.

        Args:
            backend_type: Type of backend ("local", "docker", or "nova")
            working_dir: Working directory for SAMMY execution
            output_dir: Output directory for SAMMY results (defaults to working_dir/output)
            **kwargs: Backend-specific configuration options:
                Local backend:
                    sammy_executable: Path to SAMMY executable
                    shell_path: Path to shell
                Docker backend:
                    image_name: Docker image name
                    container_working_dir: Working directory in container
                    container_data_dir: Data directory in container
                NOVA backend:
                    url: NOVA service URL
                    api_key: NOVA API key
                    tool_id: SAMMY tool ID
                    timeout: Request timeout in seconds

        Returns:
            Configured SammyRunner instance

        Raises:
            BackendNotAvailableError: If requested backend is not available
            ConfigurationError: If configuration is invalid
        """
        try:
            # Convert string to enum
            try:
                backend = BackendType(backend_type.lower())
            except ValueError:
                raise ConfigurationError(f"Invalid backend type: {backend_type}")

            # Check backend availability
            available_backends = cls.list_available_backends()

            # For local backend, also check if explicit sammy_executable was provided
            if backend == BackendType.LOCAL and not available_backends[backend]:
                explicit_sammy = kwargs.get("sammy_executable")
                if explicit_sammy and Path(explicit_sammy).exists():
                    # Explicit executable provided and exists - allow local backend
                    pass
                else:
                    raise BackendNotAvailableError(f"Backend {backend.value} is not available")
            elif not available_backends[backend]:
                raise BackendNotAvailableError(f"Backend {backend.value} is not available")

            # Set default output directory if not specified
            if output_dir is None:
                output_dir = working_dir / "output"

            # Convert to Path objects
            working_dir = Path(working_dir)
            output_dir = Path(output_dir)

            # Create appropriate configuration and runner based on backend
            if backend == BackendType.LOCAL:
                config = LocalSammyConfig(
                    working_dir=working_dir,
                    output_dir=output_dir,
                    sammy_executable=kwargs.get("sammy_executable", "sammy"),
                    shell_path=kwargs.get("shell_path", Path("/bin/bash")),
                )
                runner = LocalSammyRunner(config)

            elif backend == BackendType.DOCKER:
                config = DockerSammyConfig(
                    working_dir=working_dir,
                    output_dir=output_dir,
                    image_name=kwargs.get("image_name", "kedokudo/sammy-docker"),
                    container_working_dir=Path(kwargs.get("container_working_dir", "/sammy/work")),
                    container_data_dir=Path(kwargs.get("container_data_dir", "/sammy/data")),
                )
                runner = DockerSammyRunner(config)

            elif backend == BackendType.NOVA:
                # For NOVA, try environment variables if not in kwargs
                url = kwargs.get("url") or os.environ.get("NOVA_URL")
                api_key = kwargs.get("api_key") or os.environ.get("NOVA_API_KEY")
                if not url or not api_key:
                    raise ConfigurationError("NOVA URL and API key must be provided")

                config = NovaSammyConfig(
                    working_dir=working_dir,
                    output_dir=output_dir,
                    url=url,
                    api_key=api_key,
                    tool_id=kwargs.get("tool_id", "neutrons_imaging_sammy"),
                    timeout=kwargs.get("timeout", 3600),
                )
                runner = NovaSammyRunner(config)

            # Validate configuration
            config.validate()
            return runner

        except Exception as e:
            if not isinstance(e, (BackendNotAvailableError, ConfigurationError)):
                logger.exception("Unexpected error creating runner")
                raise ConfigurationError(f"Failed to create runner: {str(e)}")
            raise

    @classmethod
    def from_config(cls, config_path: Union[str, Path]) -> SammyRunner:
        """
        Create a SAMMY runner from a configuration file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Configured SammyRunner instance

        Raises:
            ConfigurationError: If configuration file is invalid or missing
            BackendNotAvailableError: If requested backend is not available

        Example config file:
            backend: local
            working_dir: /path/to/work
            output_dir: /path/to/output

            local:
                sammy_executable: /path/to/sammy
                shell_path: /bin/bash

            docker:
                image_name: kedokudo/sammy-docker
                container_working_dir: /sammy/work
                container_data_dir: /sammy/data

            nova:
                url: ${NOVA_URL}
                api_key: ${NOVA_API_KEY}
                tool_id: neutrons_imaging_sammy
                timeout: 3600
        """
        try:
            # Load and parse configuration file
            config_path = Path(config_path)
            if not config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {config_path}")

            with open(config_path) as f:
                try:
                    config = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    raise ConfigurationError(f"Invalid YAML format: {str(e)}")

            # Validate basic structure
            if not isinstance(config, dict):
                raise ConfigurationError("Configuration must be a dictionary")

            required_fields = {"backend", "working_dir"}
            missing_fields = required_fields - set(config.keys())
            if missing_fields:
                raise ConfigurationError(f"Missing required fields: {missing_fields}")

            # Handle environment variable expansion
            def expand_env_vars(value: str) -> str:
                """Expand environment variables in string values."""
                if isinstance(value, str) and "${" in value:
                    pattern = r"\${([^}]+)}"
                    matches = re.finditer(pattern, value)
                    for match in matches:
                        env_var = match.group(1)
                        env_value = os.environ.get(env_var)
                        if env_value is None:
                            raise ConfigurationError(f"Environment variable not found: {env_var}")
                        value = value.replace(f"${{{env_var}}}", env_value)
                return value

            # Process configuration recursively
            def process_config(cfg):
                """Recursively process configuration dictionary."""
                if isinstance(cfg, dict):
                    return {k: process_config(v) for k, v in cfg.items()}
                elif isinstance(cfg, list):
                    return [process_config(v) for v in cfg]
                elif isinstance(cfg, str):
                    return expand_env_vars(cfg)
                return cfg

            config = process_config(config)

            # Convert paths
            working_dir = Path(config["working_dir"])
            output_dir = Path(config.get("output_dir", working_dir / "output"))

            # Get backend-specific configuration
            backend_type = config["backend"].lower()
            backend_config = config.get(backend_type, {})

            # Create runner using create_runner
            return cls.create_runner(
                backend_type=backend_type, working_dir=working_dir, output_dir=output_dir, **backend_config
            )

        except Exception as e:
            if not isinstance(e, (ConfigurationError, BackendNotAvailableError)):
                logger.exception("Unexpected error loading configuration")
                raise ConfigurationError(f"Failed to load configuration: {str(e)}")
            raise

    @classmethod
    def auto_select(
        cls, working_dir: Path, output_dir: Optional[Path] = None, preferred_backend: Optional[str] = None, **kwargs
    ) -> SammyRunner:
        """
        Auto-select and configure the best available SAMMY backend.

        The selection priority (unless overridden by preferred_backend):
        1. Local installation (fastest, simplest)
        2. Docker container (portable, isolated)
        3. NOVA web service (no local installation needed)

        Args:
            working_dir: Working directory for SAMMY execution
            output_dir: Optional output directory (defaults to working_dir/output)
            preferred_backend: Optional preferred backend type ("local", "docker", "nova")
            **kwargs: Backend-specific configuration options

        Returns:
            Configured SammyRunner instance

        Raises:
            BackendNotAvailableError: If no suitable backend is available
            ConfigurationError: If configuration is invalid

        Examples:
            >>> runner = SammyFactory.auto_select(
            ...     working_dir="/path/to/work",
            ...     preferred_backend="docker",
            ...     image_name="custom/sammy:latest"
            ... )
        """
        # Check available backends
        available = cls.list_available_backends()
        logger.debug(f"Available backends: {[b.value for b, v in available.items() if v]}")

        # If preferred backend specified, try it first
        if preferred_backend:
            try:
                preferred = BackendType(preferred_backend.lower())
                if available[preferred]:
                    logger.info(f"Using preferred backend: {preferred.value}")
                    return cls.create_runner(
                        backend_type=preferred.value, working_dir=working_dir, output_dir=output_dir, **kwargs
                    )
                else:
                    logger.warning(f"Preferred backend {preferred.value} not available, trying alternatives")
            except ValueError:
                raise ConfigurationError(f"Invalid preferred backend: {preferred_backend}")

        # Try backends in priority order
        backend_priority = [
            BackendType.LOCAL,  # Fastest, simplest
            BackendType.DOCKER,  # Portable, isolated
            BackendType.NOVA,  # No local installation
        ]

        errors = []
        for backend in backend_priority:
            if available[backend]:
                try:
                    logger.info(f"Attempting to use {backend.value} backend")
                    return cls.create_runner(
                        backend_type=backend.value, working_dir=working_dir, output_dir=output_dir, **kwargs
                    )
                except Exception as e:
                    logger.warning(f"Failed to configure {backend.value} backend: {str(e)}")
                    errors.append(f"{backend.value}: {str(e)}")
                    continue

        # If we get here, no backend was successfully configured
        error_details = "\n".join(errors)
        raise BackendNotAvailableError(f"No suitable backend available. Errors encountered:\n{error_details}")


if __name__ == "__main__":
    import sys

    # Example paths
    test_data_dir = Path(__file__).parents[3] / "tests/data/ex012"
    working_dir = Path.home() / "tmp" / "sammy_factory_test"
    output_dir = working_dir / "output"

    # Example configuration file
    example_config = """
backend: docker
working_dir: {working_dir}
output_dir: {output_dir}

local:
    sammy_executable: sammy
    shell_path: /bin/bash

docker:
    image_name: kedokudo/sammy-docker
    container_working_dir: /sammy/work
    container_data_dir: /sammy/data

nova:
    url: ${{NOVA_URL}}
    api_key: ${{NOVA_API_KEY}}
    tool_id: neutrons_imaging_sammy
    timeout: 3600
"""

    try:
        print("\n=== SAMMY Factory Examples ===\n")

        # List available backends
        print("Checking available backends...")
        available = SammyFactory.list_available_backends()
        print("Available backends:")
        for backend, is_available in available.items():
            print(f"  {backend.value}: {'✓' if is_available else '✗'}")

        print("\n1. Create runner directly...")
        runner1 = SammyFactory.create_runner(backend_type="local", working_dir=working_dir, output_dir=output_dir)
        print(f"Created runner: {type(runner1).__name__}")

        print("\n2. Create runner from config file...")
        # Write example config
        config_file = working_dir / "sammy_config.yaml"
        working_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(example_config.format(working_dir=working_dir, output_dir=output_dir))
        runner2 = SammyFactory.from_config(config_file)
        print(f"Created runner: {type(runner2).__name__}")

        print("\n3. Auto-select backend...")
        runner3 = SammyFactory.auto_select(working_dir=working_dir, output_dir=output_dir)
        print(f"Selected backend: {type(runner3).__name__}")

        print("\n4. Test complete runner workflow...")
        # Create files container
        files = SammyFiles(
            input_file=test_data_dir / "ex012a.inp",
            parameter_file=test_data_dir / "ex012a.par",
            data_file=test_data_dir / "ex012a.dat",
        )

        # Execute SAMMY using auto-selected backend
        runner = SammyFactory.auto_select(
            working_dir=working_dir,
            output_dir=output_dir,
            preferred_backend="local",  # Try local first
        )

        print(f"Using runner: {type(runner).__name__}")
        print(f"Working directory: {working_dir}")
        print(f"Output directory: {output_dir}")

        # Execute pipeline
        print("\nPreparing environment...")
        runner.prepare_environment(files)

        print("Executing SAMMY...")
        result = runner.execute_sammy(files)

        # Process results
        if result.success:
            print(f"\nSAMMY execution successful (runtime: {result.runtime_seconds:.2f}s)")
            runner.collect_outputs(result)
            print(f"Output files available in: {output_dir}")
        else:
            print("\nSAMMY execution failed:")
            print(result.error_message)
            print("\nConsole output:")
            print(result.console_output)

    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        logger.exception("Example execution failed")
        sys.exit(1)

    finally:
        if "runner" in locals():
            runner.cleanup()

    print("\nExamples completed successfully")
