import logging

def _log_and_raise_error(logger, message: str, exception_class: Exception):
    logger.error(message)
    raise exception_class(message)

class Logger:
    def __init__(self, name: str, level: int = logging.DEBUG, log_file: str = None):
        
        # 
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
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)

    