#!/usr/bin/env python
"""Unit tests for NOVA SAMMY backend implementation."""

import os
from datetime import datetime
from unittest import mock

import pytest

from pleiades.sammy.backends.nova_ornl import NovaSammyRunner
from pleiades.sammy.config import NovaSammyConfig
from pleiades.sammy.interface import SammyFiles

# Mock environment variables
os.environ["NOVA_URL"] = "https://mock_nova_url"
os.environ["NOVA_API_KEY"] = "mock_api_key"


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
def mock_nova_connection():
    """Mock the NovaConnection object."""
    with mock.patch("pleiades.sammy.backends.nova_ornl.NovaConnection") as mock_connection:
        yield mock_connection.return_value


@pytest.fixture
def mock_tool():
    """Mock the Tool object."""
    with mock.patch("pleiades.sammy.backends.nova_ornl.Tool") as mock_tool:
        yield mock_tool.return_value


@pytest.fixture
def mock_nova(mock_nova_connection, mock_tool):
    """Mock the Nova object."""
    with mock.patch("pleiades.sammy.backends.nova_ornl.Nova") as mock_nova:
        instance = mock_nova.return_value
        instance.connect.return_value.__enter__.return_value = mock_nova_connection
        instance.connect.return_value.__enter__.return_value.tool = mock_tool
        yield instance


@pytest.fixture
def mock_zipfile(monkeypatch):
    """Mock the zipfile module."""
    mock_zip_ref = mock.MagicMock()
    mock_zip_ref.filelist = ["SAMMY.LPT", "SAMMY.PAR"]
    mock_zipfile_class = mock.MagicMock(return_value=mock_zip_ref)
    monkeypatch.setattr("pleiades.sammy.backends.nova_ornl.zipfile.ZipFile", mock_zipfile_class)
    return mock_zipfile_class


class TestNovaSammyRunner:
    """Tests for NovaSammyRunner."""

    def test_initialization(self, nova_config, mock_nova):
        """Should initialize with valid config."""
        _ = mock_nova  # make pre-commit happy
        runner = NovaSammyRunner(nova_config)
        assert runner.config == nova_config

    def test_prepare_environment(self, nova_config, mock_sammy_files, mock_nova):
        """Should prepare environment successfully."""
        _ = mock_nova  # make pre-commit happy
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        assert nova_config.output_dir.exists()

    def test_execute_sammy_success(self, nova_config, mock_sammy_files, mock_nova, mock_zipfile):
        """Should execute SAMMY successfully."""
        _ = mock_zipfile  # make pre-commit happy
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        # Mock the tool run method
        mock_nova.connect.return_value.__enter__.return_value.tool.run.return_value = mock.MagicMock(
            get_dataset=lambda _: mock.MagicMock(get_content=lambda: " Normal finish to SAMMY"),
            get_collection=lambda _: mock.MagicMock(download=lambda _: None),
        )

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        assert result.success
        assert "Normal finish to SAMMY" in result.console_output
        assert result.error_message is None

    def test_execute_sammy_failure(self, nova_config, mock_sammy_files, mock_nova, monkeypatch):
        """Should handle SAMMY execution failure."""
        _ = mock_nova  # make pre-commit happy
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        # Mock the execute_sammy method to simulate failure
        monkeypatch.setattr(
            runner,
            "execute_sammy",
            lambda _: mock.MagicMock(
                success=False,
                execution_id="test",
                start_time=datetime.now(),
                end_time=datetime.now(),
                console_output="SAMMY execution failed",
                error_message="Forced failure",
            ),
        )

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        assert not result.success
        assert "Forced failure" in result.error_message

    def test_collect_outputs(self, nova_config, mock_sammy_files, mock_nova, mock_zipfile):
        """Should collect output files."""
        _ = mock_zipfile  # make pre-commit happy
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        # Mock the tool run method
        mock_nova.connect.return_value.__enter__.return_value.tool.run.return_value = mock.MagicMock(
            get_dataset=lambda _: mock.MagicMock(get_content=lambda: "Normal finish to SAMMY"),
            get_collection=lambda _: mock.MagicMock(download=lambda _: None),
        )

        runner.prepare_environment(files)
        result = runner.execute_sammy(files)

        # Create mock output files
        output_dir = nova_config.output_dir
        (output_dir / "SAMMY.LPT").touch()
        (output_dir / "SAMMY.PAR").touch()

        runner.collect_outputs(result)

        assert (output_dir / "SAMMY.LPT").exists()
        assert (output_dir / "SAMMY.PAR").exists()

    def test_cleanup(self, nova_config, mock_sammy_files, mock_nova):
        """Should perform cleanup successfully."""
        _ = mock_nova  # make pre-commit happy
        runner = NovaSammyRunner(nova_config)
        files = SammyFiles(**mock_sammy_files)

        runner.prepare_environment(files)
        runner.cleanup()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
