import logging
import inspect

def _log_and_raise_error(logger, message: str, exception_class: Exception):
    """
    Log an error message and raise an exception.
    
    Args:
        logger (logging.Logger): The logger instance to use for logging the error.
        message (str): The error message to log and raise.
        exception_class (Exception): The class of the exception to raise.
    
    Raises:
        exception_class: The exception with the provided message.
    """
    logger.error(message)
    raise exception_class(message)

class Logger:
    def __init__(self, name: str, level: int = logging.DEBUG, log_file: str = None):
        """
        Initialize a Logger instance.
        
        Args:
            name (str): The name of the logger.
            level (int): The logging level (default is logging.DEBUG).
            log_file (str, optional): The file to log messages to (default is None).
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create file handler if log_file is specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

        # Log a break line
        self.logger.info("logging initialized...")

    def debug(self, message: str):
        """
        Log a debug message.
        
        Args:
            message (str): The debug message to log.
        """
        self.logger.debug(message)

    def info(self, message: str):
        """
        Log an info message.
        
        Args:
            message (str): The info message to log.
        """
        self.logger.info(message)

    def warning(self, message: str):
        """
        Log a warning message.
        
        Args:
            message (str): The warning message to log.
        """
        self.logger.warning(message)

    def error(self, message: str):
        """
        Log an error message.
        
        Args:
            message (str): The error message to log.
        """
        self.logger.error(message)

    def critical(self, message: str):
        """
        Log a critical message.
        
        Args:
            message (str): The critical message to log.
        """
        self.logger.critical(message)

    