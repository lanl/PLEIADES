# Migrating to Loguru

PLEIADES has migrated from Python's native logging to [Loguru](https://github.com/Delgan/loguru) to provide a better logging experience. This document provides guidance on how to use the new logging system.

## Benefits of Loguru

- Simpler API with sensible defaults
- Pretty logging with colors in the terminal
- Automatic rotation of log files
- Support for structured logging
- Better stack trace formatting
- No need for complex configuration

## Using the Logger in Your Code

### Before (native logging)

```python
import logging
logger = logging.getLogger(__name__)

# Log messages
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### After (with Loguru)

```python
from pleiades.utils.logger import loguru_logger

# Set the module name
logger = loguru_logger.bind(name=__name__)

# Log messages
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Replacing logging.basicConfig

If you previously used `logging.basicConfig()`, you can replace it with our `configure_logger()` function:

```python
# Before
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# After
from pleiades.utils.logger import configure_logger
configure_logger(console_level="INFO")
```

## Backward Compatibility

For backward compatibility, we maintain the original `Logger` class which now wraps Loguru:

```python
from pleiades.utils.logger import Logger
logger = Logger(name=__name__, level="DEBUG")

logger.debug("Debug message")
```

## Advanced Usage

### Custom Configuration

You can customize the logger behavior:

```python
from pleiades.utils.logger import configure_logger

configure_logger(
    console_level="INFO",                         # Console output level
    file_level="DEBUG",                           # File output level
    log_file="my_custom_logfile.log",             # Custom log filename
    rotation="1 day",                             # Rotate logs daily
    retention="1 week",                           # Keep logs for 1 week
    format_string="{time} | {message}"            # Custom format
)
```

### Context Attributes

Loguru supports adding context to log records:

```python
logger = loguru_logger.bind(component="nuclear", version="1.0")
logger.info("Component initialized")  # Will include component and version in log
```

### Exception Logging

Loguru provides enhanced exception logging:

```python
try:
    1 / 0
except Exception:
    logger.exception("An error occurred")  # Will log the full traceback
```

### Programmatic Log Level Setting

```python
from pleiades.utils.logger import configure_logger

# Set different levels for console and file
configure_logger(console_level="WARNING", file_level="DEBUG")
```

## Default Log File Location

By default, Loguru will create a log file named `pleiades_YYYYMMDD_HHMMSS.log` in the current working directory.

You can change this by calling `configure_logger()` with a custom path.
