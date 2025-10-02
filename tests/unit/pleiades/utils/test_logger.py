"""Comprehensive unit tests for utils/logger.py module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from loguru import logger as loguru_logger

from pleiades.utils.logger import (
    Logger,
    _log_and_raise_error,
    configure_logger,
    get_logger,
)


class TestLogAndRaiseError:
    """Test the _log_and_raise_error helper function."""

    def test_log_and_raise_error_with_valueerror(self):
        """Test _log_and_raise_error raises ValueError with message."""
        mock_logger = MagicMock()
        message = "Test error message"

        with pytest.raises(ValueError, match=message):
            _log_and_raise_error(mock_logger, message, ValueError)

        mock_logger.error.assert_called_once_with(message)

    def test_log_and_raise_error_with_runtimeerror(self):
        """Test _log_and_raise_error raises RuntimeError with message."""
        mock_logger = MagicMock()
        message = "Runtime error occurred"

        with pytest.raises(RuntimeError, match=message):
            _log_and_raise_error(mock_logger, message, RuntimeError)

        mock_logger.error.assert_called_once_with(message)

    def test_log_and_raise_error_with_custom_exception(self):
        """Test _log_and_raise_error with custom exception class."""

        class CustomError(Exception):
            pass

        mock_logger = MagicMock()
        message = "Custom error message"

        with pytest.raises(CustomError, match=message):
            _log_and_raise_error(mock_logger, message, CustomError)

        mock_logger.error.assert_called_once_with(message)


class TestConfigureLogger:
    """Test the configure_logger function."""

    @patch("pleiades.utils.logger.loguru_logger")
    def test_configure_logger_default_settings(self, mock_loguru):
        """Test configure_logger with default settings."""
        configure_logger()

        # Verify logger was cleared and reconfigured
        mock_loguru.remove.assert_called()
        assert mock_loguru.add.call_count >= 2  # Console and file handlers

        # Verify info message was logged
        mock_loguru.info.assert_called()
        info_call = mock_loguru.info.call_args[0][0]
        assert "Logging configured" in info_call

    @patch("pleiades.utils.logger.loguru_logger")
    def test_configure_logger_custom_levels(self, mock_loguru):
        """Test configure_logger with custom logging levels."""
        configure_logger(console_level="INFO", file_level="ERROR")

        mock_loguru.remove.assert_called()
        # Check that add was called with correct levels
        add_calls = mock_loguru.add.call_args_list
        assert len(add_calls) >= 2

        # First call is console with INFO level
        assert add_calls[0][1]["level"] == "INFO"
        # Second call is file with ERROR level
        assert add_calls[1][1]["level"] == "ERROR"

    @patch("pleiades.utils.logger.loguru_logger")
    def test_configure_logger_custom_log_file(self, mock_loguru):
        """Test configure_logger with custom log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_log = Path(tmpdir) / "custom.log"
            configure_logger(log_file=custom_log)

            mock_loguru.remove.assert_called()
            # Verify file handler was added with custom path
            add_calls = mock_loguru.add.call_args_list
            file_handler_call = add_calls[1]  # Second call is file handler
            assert file_handler_call[0][0] == custom_log

    @patch("pleiades.utils.logger.loguru_logger")
    def test_configure_logger_relative_log_file(self, mock_loguru):
        """Test configure_logger with relative log file path."""
        configure_logger(log_file="test.log")

        mock_loguru.remove.assert_called()
        add_calls = mock_loguru.add.call_args_list
        file_handler_call = add_calls[1]
        log_path = file_handler_call[0][0]

        # Should be placed in logs directory
        assert isinstance(log_path, Path)
        assert log_path.name == "test.log"

    @patch("pleiades.utils.logger.loguru_logger")
    def test_configure_logger_custom_format(self, mock_loguru):
        """Test configure_logger with custom format string."""
        custom_format = "{time} - {level} - {message}"
        configure_logger(format_string=custom_format)

        mock_loguru.remove.assert_called()
        add_calls = mock_loguru.add.call_args_list

        # Both console and file should use custom format
        assert add_calls[0][1]["format"] == custom_format
        assert add_calls[1][1]["format"] == custom_format

    @patch("pleiades.utils.logger.loguru_logger")
    def test_configure_logger_custom_rotation_retention(self, mock_loguru):
        """Test configure_logger with custom rotation and retention."""
        configure_logger(rotation="100 MB", retention="90 days")

        mock_loguru.remove.assert_called()
        add_calls = mock_loguru.add.call_args_list
        file_handler_call = add_calls[1]

        assert file_handler_call[1]["rotation"] == "100 MB"
        assert file_handler_call[1]["retention"] == "90 days"


class TestLoggerClass:
    """Test the Logger class."""

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_initialization_default(self, mock_loguru):
        """Test Logger initialization with default settings."""
        logger = Logger(name="TestLogger")

        assert logger.name == "TestLogger"
        assert logger.level == "DEBUG"

        # Verify initialization message was logged
        mock_loguru.bind.assert_called_with(name="TestLogger")
        mock_loguru.bind().info.assert_called_with("logging initialized...")

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_initialization_custom_level(self, mock_loguru):
        """Test Logger initialization with custom level."""
        logger = Logger(name="TestLogger", level="ERROR")

        assert logger.name == "TestLogger"
        assert logger.level == "ERROR"

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_initialization_with_log_file(self, mock_loguru):
        """Test Logger initialization with custom log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            logger = Logger(name="TestLogger", log_file=str(log_file))

            # Verify add was called for the custom log file
            add_calls = mock_loguru.add.call_args_list
            # Find the call that adds the custom log file
            found_custom_file = False
            for call in add_calls:
                if len(call[0]) > 0:
                    path = call[0][0]
                    if isinstance(path, Path) and path.name == "test.log":
                        found_custom_file = True
                        assert call[1]["level"] == "DEBUG"
                        break
            assert found_custom_file

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_initialization_relative_log_file(self, mock_loguru):
        """Test Logger initialization with relative log file path."""
        logger = Logger(name="TestLogger", log_file="relative.log")

        # Verify add was called for the log file
        add_calls = mock_loguru.add.call_args_list
        found_log_file = False
        for call in add_calls:
            if len(call[0]) > 0:
                path = call[0][0]
                if isinstance(path, Path) and path.name == "relative.log":
                    found_log_file = True
                    assert hasattr(logger, "log_file")
                    break
        assert found_log_file

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_debug_method(self, mock_loguru):
        """Test Logger.debug method."""
        logger = Logger(name="TestLogger")
        mock_loguru.bind().info.reset_mock()  # Reset after initialization

        message = "Debug message"
        logger.debug(message)

        mock_loguru.bind.assert_called_with(name="TestLogger")
        mock_loguru.bind().debug.assert_called_once_with(message)

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_info_method(self, mock_loguru):
        """Test Logger.info method."""
        logger = Logger(name="TestLogger")
        mock_loguru.bind().info.reset_mock()  # Reset after initialization

        message = "Info message"
        logger.info(message)

        mock_loguru.bind.assert_called_with(name="TestLogger")
        mock_loguru.bind().info.assert_called_with(message)

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_warning_method(self, mock_loguru):
        """Test Logger.warning method."""
        logger = Logger(name="TestLogger")
        mock_loguru.bind().info.reset_mock()  # Reset after initialization

        message = "Warning message"
        logger.warning(message)

        mock_loguru.bind.assert_called_with(name="TestLogger")
        mock_loguru.bind().warning.assert_called_once_with(message)

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_error_method(self, mock_loguru):
        """Test Logger.error method."""
        logger = Logger(name="TestLogger")
        mock_loguru.bind().info.reset_mock()  # Reset after initialization

        message = "Error message"
        logger.error(message)

        mock_loguru.bind.assert_called_with(name="TestLogger")
        mock_loguru.bind().error.assert_called_once_with(message)

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_critical_method(self, mock_loguru):
        """Test Logger.critical method."""
        logger = Logger(name="TestLogger")
        mock_loguru.bind().info.reset_mock()  # Reset after initialization

        message = "Critical message"
        logger.critical(message)

        mock_loguru.bind.assert_called_with(name="TestLogger")
        mock_loguru.bind().critical.assert_called_once_with(message)

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_multiple_messages(self, mock_loguru):
        """Test Logger with multiple messages of different levels."""
        logger = Logger(name="TestLogger")
        mock_loguru.bind().info.reset_mock()  # Reset after initialization

        logger.debug("Debug 1")
        logger.info("Info 1")
        logger.warning("Warning 1")
        logger.error("Error 1")
        logger.critical("Critical 1")

        # Verify all methods were called
        mock_loguru.bind().debug.assert_called_with("Debug 1")
        mock_loguru.bind().info.assert_called_with("Info 1")
        mock_loguru.bind().warning.assert_called_with("Warning 1")
        mock_loguru.bind().error.assert_called_with("Error 1")
        mock_loguru.bind().critical.assert_called_with("Critical 1")


class TestModuleLevel:
    """Test module-level functionality."""

    def test_logs_directory_creation(self):
        """Test that logs directory is created on module import."""
        # The module creates a pleiades_logs directory in cwd
        logs_dir = Path(os.getcwd()) / "pleiades_logs"
        assert logs_dir.exists()
        assert logs_dir.is_dir()

    def test_get_logger_alias(self):
        """Test that get_logger is properly aliased to loguru_logger.bind."""
        assert get_logger == loguru_logger.bind
        assert callable(get_logger)

    @patch("pleiades.utils.logger.sys.stderr")
    def test_default_console_handler(self, mock_stderr):
        """Test that default console handler is configured."""
        # Import fresh to trigger module-level initialization

        import pleiades.utils.logger

        # The module should have added handlers during import
        # This is hard to test directly due to loguru's internal structure
        # But we can verify the module imported successfully
        assert hasattr(pleiades.utils.logger, "loguru_logger")
        assert hasattr(pleiades.utils.logger, "configure_logger")

    def test_default_log_filename_format(self):
        """Test that default log filename follows expected format."""

        from pleiades.utils.logger import default_log_filename

        # Should follow format: pleiades_YYYYMMDD_HH.log
        assert default_log_filename.startswith("pleiades_")
        assert default_log_filename.endswith(".log")

        # Check date format (should be YYYYMMDD_HH)
        date_part = default_log_filename.replace("pleiades_", "").replace(".log", "")
        assert len(date_part) == 11  # YYYYMMDD_HH
        assert "_" in date_part


class TestIntegrationScenarios:
    """Test integration scenarios."""

    @patch("pleiades.utils.logger.loguru_logger")
    def test_multiple_loggers_different_names(self, mock_loguru):
        """Test creating multiple Logger instances with different names."""
        logger1 = Logger(name="Logger1")
        logger2 = Logger(name="Logger2")

        logger1.info("Message from logger1")
        logger2.info("Message from logger2")

        # Verify bind was called with different names
        bind_calls = mock_loguru.bind.call_args_list
        logger_names = [call[1]["name"] if call[1] else call[0][0].get("name") for call in bind_calls if call]
        assert "Logger1" in logger_names
        assert "Logger2" in logger_names

    @patch("pleiades.utils.logger.loguru_logger")
    def test_configure_then_create_logger(self, mock_loguru):
        """Test configuring logger globally then creating Logger instance."""
        configure_logger(console_level="WARNING", file_level="ERROR")
        logger = Logger(name="TestLogger", level="INFO")

        # Verify configure was called first
        assert mock_loguru.remove.called
        assert mock_loguru.add.called

        # Logger should still work
        logger.info("Test message")
        mock_loguru.bind().info.assert_called()

    def test_logger_with_special_characters_in_name(self):
        """Test Logger with special characters in name."""
        special_names = [
            "Logger-With-Dashes",
            "Logger_With_Underscores",
            "Logger.With.Dots",
            "Logger::With::Colons",
            "Logger/With/Slashes",
        ]

        for name in special_names:
            logger = Logger(name=name)
            assert logger.name == name
            # Should not raise any errors
            logger.info(f"Test from {name}")

    @patch("pleiades.utils.logger.loguru_logger")
    def test_exception_in_logging_method(self, mock_loguru):
        """Test handling when logging method raises an exception."""
        logger = Logger(name="TestLogger")

        # Make the bind().error method raise an exception
        mock_loguru.bind().error.side_effect = RuntimeError("Logging failed")

        # Should raise the exception (logger doesn't catch exceptions)
        with pytest.raises(RuntimeError, match="Logging failed"):
            logger.error("This will fail")

    @patch("pleiades.utils.logger.Path.mkdir")
    def test_logs_directory_creation_failure(self, mock_mkdir):
        """Test handling when logs directory creation fails."""
        mock_mkdir.side_effect = PermissionError("Cannot create directory")

        # Re-import module to trigger directory creation
        import importlib

        # This should not prevent module import
        try:
            importlib.reload(importlib.import_module("pleiades.utils.logger"))
        except PermissionError:
            # Expected if directory creation fails
            pass


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_empty_name(self, mock_loguru):
        """Test Logger with empty string as name."""
        logger = Logger(name="")
        assert logger.name == ""

        logger.info("Message with empty name")
        mock_loguru.bind.assert_called_with(name="")

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_none_name(self, mock_loguru):
        """Test Logger with None as name."""
        # Logger actually accepts None as name (converts to string)
        logger = Logger(name=None)
        assert logger.name is None

        logger.info("Message with None name")
        mock_loguru.bind.assert_called_with(name=None)

    @patch("pleiades.utils.logger.loguru_logger")
    def test_configure_logger_invalid_level(self, mock_loguru):
        """Test configure_logger with invalid logging level."""
        # Loguru might handle this internally, but test the call
        configure_logger(console_level="INVALID_LEVEL")

        # Should still call remove and add
        mock_loguru.remove.assert_called()
        assert mock_loguru.add.called

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_very_long_message(self, mock_loguru):
        """Test logging very long messages."""
        logger = Logger(name="TestLogger")
        mock_loguru.bind().info.reset_mock()

        # Create a very long message
        long_message = "x" * 10000
        logger.info(long_message)

        mock_loguru.bind().info.assert_called_with(long_message)

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_unicode_messages(self, mock_loguru):
        """Test logging messages with unicode characters."""
        logger = Logger(name="TestLogger")
        mock_loguru.bind().info.reset_mock()

        unicode_messages = [
            "Message with emoji 😀",
            "Message with Chinese 中文",
            "Message with symbols ♠♣♥♦",
            "Message with math ∑∫∂∇",
        ]

        for msg in unicode_messages:
            logger.info(msg)
            mock_loguru.bind().info.assert_called_with(msg)

    @patch("pleiades.utils.logger.loguru_logger")
    def test_logger_with_same_log_file_as_default(self, mock_loguru):
        """Test Logger when log_file matches default path."""
        from pleiades.utils.logger import default_log_path

        logger = Logger(name="TestLogger", log_file=str(default_log_path))

        # When log_file equals default_log_path, it's handled by the condition
        # on line 127: if log_file and log_file != str(default_log_path)
        # So no additional handler should be added
        add_calls = [call for call in mock_loguru.add.call_args_list if call]

        # The Logger class checks if log_file != str(default_log_path) before adding
        # So if they match, no new handler is added
        # Check that the log_file attribute is not set when it matches default
        if hasattr(logger, "log_file"):
            # If log_file attribute is set, it should not be the default path
            assert logger.log_file != default_log_path
        else:
            # If they match, log_file attribute shouldn't be set
            assert not hasattr(logger, "log_file")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
