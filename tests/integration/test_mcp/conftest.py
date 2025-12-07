"""Fixtures for MCP integration tests.

Provides test data and common setup for integration testing.
"""

import pytest


@pytest.fixture
def sample_dataset(tmp_path):
    """Create a minimal sample dataset for testing.

    Returns:
        Path to temporary dataset directory with manifest and sample files.
    """
    dataset_dir = tmp_path / "test_dataset"
    dataset_dir.mkdir()

    # Create manifest
    manifest = dataset_dir / "manifest.md"
    manifest.write_text(
        """---
name: integration_test_dataset
description: Dataset for MCP integration testing
version: 1.0.0
created: 2024-06-15T10:00:00
facility: TEST
beamline: TEST_BEAM
isotope: Si-28
material_properties:
  density_g_cm3: 2.33
  atomic_mass_amu: 28.0855
  temperature_k: 300.0
---
# Integration Test Dataset

This is a minimal dataset for integration testing.
"""
    )

    return dataset_dir


@pytest.fixture
def sample_dataset_no_manifest(tmp_path):
    """Create a dataset directory without manifest.

    Returns:
        Path to temporary dataset directory without manifest.
    """
    dataset_dir = tmp_path / "no_manifest_dataset"
    dataset_dir.mkdir()

    # Create a dummy file so directory isn't empty
    (dataset_dir / "data.txt").write_text("sample data")

    return dataset_dir


@pytest.fixture
def sample_dataset_invalid_manifest(tmp_path):
    """Create a dataset with invalid manifest.

    Returns:
        Path to temporary dataset directory with invalid manifest.
    """
    dataset_dir = tmp_path / "invalid_manifest_dataset"
    dataset_dir.mkdir()

    # Create invalid manifest (no YAML delimiters)
    manifest = dataset_dir / "manifest.md"
    manifest.write_text(
        """name: test
This is not valid YAML frontmatter format
"""
    )

    return dataset_dir
