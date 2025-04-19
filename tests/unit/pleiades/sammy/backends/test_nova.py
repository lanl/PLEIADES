#!/usr/bin/env python
"""Unit tests for NOVA SAMMY backend implementation (updated for new API)."""

import os
import zipfile
from unittest import mock

import pytest

from pleiades.sammy.backends.nova_ornl import NovaSammyRunner
from pleiades.sammy.config.interface import SammyFiles
from pleiades.sammy.config.sammy_options import NovaSammyConfig

# Mock environment variables
os.environ["NOVA_URL"] = "https://mock_nova_url"
os.environ["NOVA_API_KEY"] = "mock_api_key"


def create_dummy_zip(destination):
    """Helper function to create a dummy zip file at `destination`."""
    with zipfile.ZipFile(destination, "w") as zf:
        # Create dummy files that meet the extraction criteria:
        zf.writestr("SAMMY.LPT", "dummy content LPT")
        zf.writestr("SAMMY.PAR", "dummy content PAR")


@pytest.fixture
def nova_config(temp_working_dir):
    """Create NOVA SAMMY configuration."""
    config = NovaSammyConfig(
        url=os.environ["NOVA_URL"],
        api_key=os.environ["NOVA_API_KEY"],
        working_dir=temp_working_dir,
        output_dir=temp_working_dir / "output",
    )
    config.validate()
    return config


@pytest.fixture
def mock_connection():
    """Mock the Connection object from nova-galaxy."""
    with mock.patch("pleiades.sammy.backends.nova_ornl.Connection") as mock_connection_class:
        instance = mock_connection_class.return_value
        # Simulate the datastore creation method on the connection
        instance.datastore.return_value = "mock_datastore"
        yield instance


@pytest.fixture
def mock_tool():
    """Mock the Tool object."""
    with mock.patch("pleiades.sammy.backends.nova_ornl.Tool") as mock_tool_class:
        yield mock_tool_class.return_value


@pytest.fixture
def dummy_download(monkeypatch):
    """Fixture to replace the download method so that it creates a dummy zip file."""

    def download_stub(destination):
        create_dummy_zip(destination)

    return download_stub


class TestNovaSammyRunner:
    """Tests for NovaSammyRunner with updated nova-galaxy API and download stub."""

    def test_initialization(self, nova_config, mock_connection):
        """Should initialize with valid config."""
        runner = NovaSammyRunner(nova_config)
        assert runner.config == nova_config

    def test_prepare_environment(self, nova_config, mock_sammy_files, mock_connection):
        """Should prepare environment successfully."""
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        assert runner._connection is mock_connection
        # Check that the temporary directory has been created.
        assert runner._temp_dir is not None

    def test_execute_sammy_success(self, nova_config, mock_sammy_files, mock_connection, mock_tool, dummy_download):
        """Should execute SAMMY successfully."""
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        # Setup the mock for a successful SAMMY run.
        result_mock = mock.MagicMock()
        result_mock.outputs = {
            "sammy_console_output": mock.MagicMock(get_content=lambda: " Normal finish to SAMMY"),
            "sammy_output_files": mock.MagicMock(),
        }
        # Replace the download method with our dummy that creates a zip file.
        result_mock.outputs["sammy_output_files"].download.side_effect = dummy_download
        mock_tool.run.return_value = result_mock

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        assert result.success
        assert "Normal finish to SAMMY" in result.console_output
        assert result.error_message is None

    def test_execute_sammy_failure(self, nova_config, mock_sammy_files, mock_connection, mock_tool, dummy_download):
        """Should handle SAMMY execution failure."""
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        # Setup the mock for a SAMMY run failure.
        result_mock = mock.MagicMock()
        result_mock.outputs = {
            "sammy_console_output": mock.MagicMock(get_content=lambda: "SAMMY execution failed"),
            "sammy_output_files": mock.MagicMock(),
        }
        # Ensure the dummy download is used so zipfile.ZipFile can open the file.
        result_mock.outputs["sammy_output_files"].download.side_effect = dummy_download
        mock_tool.run.return_value = result_mock

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        # In this failure scenario, the console output does not contain the success phrase.
        assert not result.success
        assert result.error_message == "SAMMY execution failed"

    def test_collect_outputs(self, nova_config, mock_sammy_files, mock_connection, mock_tool, dummy_download):
        """Should collect output files."""
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        # Setup a successful execution scenario.
        result_mock = mock.MagicMock()
        result_mock.outputs = {
            "sammy_console_output": mock.MagicMock(get_content=lambda: " Normal finish to SAMMY"),
            "sammy_output_files": mock.MagicMock(),
        }
        result_mock.outputs["sammy_output_files"].download.side_effect = dummy_download
        mock_tool.run.return_value = result_mock

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        # Simulate the extraction by ensuring the output directory exists.
        output_dir = nova_config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Invoke collect_outputs (assuming it performs additional output handling if needed).
        runner.collect_outputs(result)

        # Confirm that the expected output files have been extracted.
        assert (output_dir / "SAMMY.LPT").exists()
        assert (output_dir / "SAMMY.PAR").exists()

    def test_cleanup(self, nova_config, mock_sammy_files, mock_connection):
        """Should perform cleanup successfully."""
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        runner.cleanup()

        # Verify the connection is cleared.
        assert runner._connection is None
        # If the connection mock supports close(), confirm it was called.
        if hasattr(mock_connection, "close"):
            mock_connection.close.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
