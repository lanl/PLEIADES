import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from loguru import logger as loguru_logger

# Remove default configuration
loguru_logger.remove()

# Set up default configuration for console logging
loguru_logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# Create logs directory if it doesn't exist
logs_dir = Path(os.getcwd()) / "pleiades_logs"
logs_dir.mkdir(exist_ok=True)

# Set up default log file with hourly timestamp
default_log_filename = f"pleiades_{datetime.now().strftime('%Y%m%d_%H')}.log"
default_log_path = logs_dir / default_log_filename

# Add file logger with default settings
loguru_logger.add(
    default_log_path,
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="10 MB",
    retention="30 days",
)


def _log_and_raise_error(logger, message: str, exception_class: Exception):
    """
    Log an error message and raise an exception.

    Args:
        logger: The logger instance to use for logging the error.
        message (str): The error message to log and raise.
        exception_class (Exception): The class of the exception to raise.

    Raises:
        exception_class: The exception with the provided message.
    """
    logger.error(message)
    raise exception_class(message)


def configure_logger(
    console_level: str = "DEBUG",
    file_level: str = "DEBUG",
    log_file: Optional[Union[str, Path]] = None,
    rotation: str = "10 MB",
    retention: str = "30 days",
    format_string: Optional[str] = None,
):
    """
    Configure the loguru logger with custom settings.

    Args:
        console_level (str): Logging level for console output
        file_level (str): Logging level for file output
        log_file (Optional[Union[str, Path]]): Custom log file path
        rotation (str): When to rotate the log file (size or time)
        retention (str): How long to keep log files
        format_string (Optional[str]): Custom format string for log messages
    """
    # Remove all existing handlers
    loguru_logger.remove()

    # Default format if none provided
    if not format_string:
        console_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    else:
        console_format = file_format = format_string

    # Add console logger
    loguru_logger.add(sys.stderr, level=console_level, format=console_format)

    # Add file logger
    if log_file is None:
        log_file = default_log_path
    else:
        # If custom log file is provided but isn't an absolute path,
        # put it in the logs directory
        log_file = Path(log_file)
        if not log_file.is_absolute():
            log_file = logs_dir / log_file

    loguru_logger.add(
        log_file,
        level=file_level,
        format=file_format,
        rotation=rotation,
        retention=retention,
    )

    loguru_logger.info(f"Logging configured. Log file: {log_file}")


class Logger:
    """
    Backward-compatible Logger class that wraps loguru.

    This class maintains the same interface as the original Logger class
    but uses loguru under the hood for better logging capabilities.
    """

    def __init__(self, name: str, level: str = "DEBUG", log_file: Optional[str] = None):
        """
        Initialize a Logger instance.

        Args:
            name (str): The name of the logger.
            level (str): The logging level (default is "DEBUG").
            log_file (str, optional): The file to log messages to (default is None).
        """
        self.name = name
        self.level = level

        # If custom log file is specified, configure a new sink for it
        if log_file and log_file != str(default_log_path):
            log_path = Path(log_file)
            # If not an absolute path, place in logs directory
            if not log_path.is_absolute():
                log_path = logs_dir / log_path

            self.log_file = log_path

            # Add a file handler if specified
            loguru_logger.add(
                self.log_file,
                level=level,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                rotation="10 MB",
                retention="30 days",
            )

        # Log a break line to indicate initialization
        loguru_logger.bind(name=name).info("logging initialized...")

    def debug(self, message: str):
        """
        Log a debug message.

        Args:
            message (str): The debug message to log.
        """
        loguru_logger.bind(name=self.name).debug(message)

    def info(self, message: str):
        """
        Log an info message.

        Args:
            message (str): The info message to log.
        """
        loguru_logger.bind(name=self.name).info(message)

    def warning(self, message: str):
        """
        Log a warning message.

        Args:
            message (str): The warning message to log.
        """
        loguru_logger.bind(name=self.name).warning(message)

    def error(self, message: str):
        """
        Log an error message.

        Args:
            message (str): The error message to log.
        """
        loguru_logger.bind(name=self.name).error(message)

    def critical(self, message: str):
        """
        Log a critical message.

        Args:
            message (str): The critical message to log.
        """
        loguru_logger.bind(name=self.name).critical(message)


# Make the loguru logger available directly
get_logger = loguru_logger.bind
