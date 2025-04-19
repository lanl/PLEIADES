# Custom exceptions
class SammyError(Exception):
    """Base exception for SAMMY-related errors."""

    pass


class EnvironmentPreparationError(SammyError):
    """Raised when environment preparation fails."""

    pass


class SammyExecutionError(SammyError):
    """Raised when SAMMY execution fails."""

    pass


class OutputCollectionError(SammyError):
    """Raised when output collection fails."""

    pass


class ConfigurationError(SammyError):
    """Raised when configuration is invalid."""

    pass


class CleanupError(SammyError):
    """Raised when cleanup fails."""

    pass
