#!/usr/bin/env python
"""Shared pytest fixtures for SAMMY tests."""

import os
import shutil
from pathlib import Path
from typing import Dict, Generator
from unittest.mock import Mock

import pytest


@pytest.fixture
def test_data_dir() -> Path:
    """Get path to test data directory."""
    return Path(__file__).parents[2] / "tests/data/ex012"


@pytest.fixture
def temp_working_dir(tmp_path) -> Path:
    """Create temporary working directory."""
    work_dir = tmp_path / "sammy_test"
    work_dir.mkdir(exist_ok=True)
    return work_dir


@pytest.fixture
def temp_output_dir(temp_working_dir) -> Path:
    """Create temporary output directory."""
    output_dir = temp_working_dir / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture
def mock_sammy_files(test_data_dir, temp_working_dir) -> Dict[str, Path]:
    """Provide paths to test input files.

    Copies the real test files to the temporary directory to ensure path safety.
    """
    # Create a subdirectory for the test files
    test_files_dir = temp_working_dir / "test_files"
    test_files_dir.mkdir(exist_ok=True)

    # Copy the test files to the temporary directory
    src_files = {
        "input_file": "ex012a.inp",
        "parameter_file": "ex012a.par",
        "data_file": "ex012a.dat",
    }

    result = {}
    for key, filename in src_files.items():
        src_path = test_data_dir / filename
        dest_path = test_files_dir / filename
        shutil.copy2(src_path, dest_path)
        result[key] = dest_path

    return result


@pytest.fixture
def mock_sammy_output() -> str:
    """Provide mock SAMMY output with success message."""
    return """
    SAMMY execution log
    ... processing ...
    Normal finish to SAMMY
    """


@pytest.fixture
def mock_sammy_error_output() -> str:
    """Provide mock SAMMY output with error message."""
    return """
    SAMMY execution log
    Error: Invalid input parameters
    SAMMY execution failed
    """


@pytest.fixture
def mock_sammy_results(temp_working_dir) -> None:
    """Create mock SAMMY output files."""
    # Create some mock output files
    files = ["SAMMY.LPT", "SAMMY.PAR", "SAMMY.LST", "SAMMY.ODF"]
    for file in files:
        (temp_working_dir / file).write_text("Mock SAMMY output")


@pytest.fixture
def clean_env() -> Generator:
    """Remove SAMMY-related environment variables temporarily."""
    # Store original environment
    orig_env = {}
    env_vars = ["SAMMY_PATH", "NOVA_URL", "NOVA_API_KEY"]

    for var in env_vars:
        orig_env[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]

    yield

    # Restore original environment
    for var, value in orig_env.items():
        if value is not None:
            os.environ[var] = value


@pytest.fixture
def mock_docker():
    """Mock Docker client."""
    mock = Mock()
    mock.containers.run.return_value = "Mock container"
    mock.images.get.return_value = True
    return mock


@pytest.fixture
def mock_nova():
    """Mock NOVA client."""
    mock = Mock()
    mock.connect.return_value.__enter__.return_value = mock
    mock.create_data_store.return_value = "mock_datastore"
    return mock
