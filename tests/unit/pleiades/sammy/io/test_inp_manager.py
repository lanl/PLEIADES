"""
Tests for the InpManager class.

This module tests the functionality of the InpManager class, which handles
the creation, formatting, and writing of SAMMY input (.inp) files based on
FitOptions configurations.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pleiades.sammy.fitting.options import FitOptions
from pleiades.sammy.io.inp_manager import InpManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for output files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_fit_options():
    """Create a mock FitOptions instance with predefined commands."""
    mock_options = MagicMock(spec=FitOptions)
    mock_options.get_alphanumeric_commands.return_value = [
        "PUT QUANTUM NUMBERS INTO PARAMETER FILE",
        "DO NOT SOLVE BAYES EQUATIONS",
        "USE ENDF PARAMETERS",
    ]
    return mock_options


def test_init_defaults():
    """Test that InpManager initializes with default values."""
    inp_manager = InpManager()
    assert isinstance(inp_manager.options, FitOptions)


def test_init_with_options():
    """Test that InpManager initializes with provided FitOptions."""
    options = FitOptions()
    inp_manager = InpManager(options)
    assert inp_manager.options is options


def test_set_options():
    """Test setting FitOptions after initialization."""
    inp_manager = InpManager()
    original_options = inp_manager.options

    new_options = FitOptions()
    inp_manager.set_options(new_options)

    assert inp_manager.options is not original_options
    assert inp_manager.options is new_options


def test_generate_commands(mock_fit_options):
    """Test generating SAMMY input commands from FitOptions."""
    inp_manager = InpManager(mock_fit_options)
    commands = inp_manager.generate_commands()

    assert isinstance(commands, list)
    assert commands == [
        "PUT QUANTUM NUMBERS INTO PARAMETER FILE",
        "DO NOT SOLVE BAYES EQUATIONS",
        "USE ENDF PARAMETERS",
    ]


def test_generate_inp_content(mock_fit_options):
    """Test generating content for SAMMY input file."""
    inp_manager = InpManager(mock_fit_options)
    content = inp_manager.generate_inp_content()

    assert isinstance(content, str)
    expected_content = (
        "PUT QUANTUM NUMBERS INTO PARAMETER FILE\n" "DO NOT SOLVE BAYES EQUATIONS\n" "USE ENDF PARAMETERS"
    )
    assert content == expected_content


def test_write_inp_file(temp_dir, mock_fit_options):
    """Test writing SAMMY input file to disk."""
    inp_manager = InpManager(mock_fit_options)
    output_path = temp_dir / "test.inp"

    result_path = inp_manager.write_inp_file(output_path)

    assert result_path == output_path
    assert output_path.exists()

    with open(output_path, "r") as f:
        content = f.read()

    expected_content = (
        "PUT QUANTUM NUMBERS INTO PARAMETER FILE\n" "DO NOT SOLVE BAYES EQUATIONS\n" "USE ENDF PARAMETERS"
    )
    assert content == expected_content


def test_write_inp_file_creates_directories(temp_dir, mock_fit_options):
    """Test writing SAMMY input file creates directories if needed."""
    inp_manager = InpManager(mock_fit_options)
    output_path = temp_dir / "nested" / "dir" / "test.inp"

    result_path = inp_manager.write_inp_file(output_path)

    assert result_path == output_path
    assert output_path.exists()


def test_write_inp_file_handles_errors():
    """Test that write_inp_file properly handles errors."""
    inp_manager = InpManager()

    # Try to write to an invalid path
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(IOError) as exc_info:
            inp_manager.write_inp_file(Path("/invalid/path/file.inp"))

    assert "Failed to write SAMMY input file" in str(exc_info.value)
    # The exact error message might vary based on the environment
    # so we only check that the main error message is included


def test_create_endf_inp(temp_dir):
    """Test creating input file for ENDF mode using class method."""
    output_path = temp_dir / "endf.inp"

    with patch.object(FitOptions, "from_endf_config") as mock_from_endf:
        mock_options = MagicMock(spec=FitOptions)
        mock_options.get_alphanumeric_commands.return_value = ["USE ENDF PARAMETERS"]
        mock_from_endf.return_value = mock_options

        result_path = InpManager.create_endf_inp(output_path)

        assert result_path == output_path
        assert output_path.exists()

        with open(output_path, "r") as f:
            content = f.read()

        assert content == "USE ENDF PARAMETERS"
        mock_from_endf.assert_called_once()


def test_create_fitting_inp(temp_dir):
    """Test creating input file for fitting mode using class method."""
    output_path = temp_dir / "fitting.inp"

    with patch.object(FitOptions, "from_fitting_config") as mock_from_fitting:
        mock_options = MagicMock(spec=FitOptions)
        mock_options.get_alphanumeric_commands.return_value = ["SOLVE BAYES EQUATIONS"]
        mock_from_fitting.return_value = mock_options

        result_path = InpManager.create_fitting_inp(output_path)

        assert result_path == output_path
        assert output_path.exists()

        with open(output_path, "r") as f:
            content = f.read()

        assert content == "SOLVE BAYES EQUATIONS"
        mock_from_fitting.assert_called_once()


def test_custom_inp_creation(temp_dir):
    """Test creating input file with custom options."""
    options = FitOptions.from_custom_config()
    inp_manager = InpManager(options)
    output_path = temp_dir / "custom.inp"

    result_path = inp_manager.write_inp_file(output_path)

    assert result_path == output_path
    assert output_path.exists()

    # The actual content will depend on the default values of FitOptions
    with open(output_path, "r") as f:
        content = f.read()

    assert isinstance(content, str)
    assert len(content) > 0  # Ensure some content was written
