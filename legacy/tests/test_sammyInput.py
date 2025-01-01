import logging
import os

import pytest

from pleiades import sammyInput
from pleiades.sammyStructures import SammyFitConfig

## Configure logging for the test
# Set file name
log_file = "test_sammyInput.log"

# Remove file if it already exists
if os.path.exists(log_file):
    os.remove(log_file)

# Create handlers
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
file_handler = logging.FileHandler(log_file)
console_handler = logging.StreamHandler()

# Set levels for handlers
file_handler.setLevel(logging.INFO)
console_handler.setLevel(logging.INFO)

# Create formatters and add them to handlers
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger_header_break = "====================================================="
logger_footer_break = "-----------------------------------------------------"


@pytest.fixture
def input_file():
    """Fixture to create an InputFile instance."""
    return sammyInput.InputFile()


def test_init_without_config(input_file):
    """Test initializing InputFile without a config file."""
    logger.info(logger_header_break)
    logger.info("Testing initializing InputFile without a config file")

    assert isinstance(input_file, sammyInput.InputFile)
    assert "Card1" in input_file.data
    assert "Card2" in input_file.data
    assert input_file.data["Card2"]["elmnt"] == "H_1"  # Default value for isotope

    logger.info("InputFile initialized successfully")
    logger.info(logger_footer_break)


def test_update_with_config(input_file):
    """Test updating InputFile with isotope-specific config."""
    logger.info(logger_header_break)
    logger.info("Testing updating InputFile with isotope-specific config")

    config = SammyFitConfig()
    config.params["isotopes"] = {"names": ["U-235", "U-238"]}
    logger.info(f"Config loaded successfully with isotopes: {config.params['isotopes']['names']}")
    input_file.update_with_config(config)
    assert input_file.data["Card2"]["elmnt"] == "U-235"  # Selects isotope with lowest mass
    assert input_file.data["Card2"]["aw"] == "auto"  # Atomic weight should be auto

    logger.info("InputFile updated successfully")
    logger.info(logger_footer_break)


def test_process_method(input_file):
    """Test the process method formats input cards correctly."""
    logger.info(logger_header_break)
    logger.info("Testing the process method of InputFile")

    input_file.process()
    assert isinstance(input_file.processed_cards, list)
    assert len(input_file.processed_cards) > 0

    logger.info("InputFile processed successfully")
    logger.info(logger_footer_break)


def test_write_method(input_file, tmpdir):
    """Test the write method writes a SAMMY input file."""
    logger.info(logger_header_break)
    logger.info("Testing the write method of InputFile")

    output_file = os.path.join(tmpdir, "sammy_test.inp")
    input_file.process().write(output_file)
    logger.info(f"Output file written to: {output_file}")
    assert os.path.exists(output_file)
    with open(output_file, "r") as f:
        content = f.read()
    assert "DEFAULT SAMMY INPUT FILE" in content

    logger.info("InputFile written successfully")
    logger.info(logger_footer_break)


def test_format_type_A():
    """Test the format_type_A method for formatting strings."""
    logger.info(logger_header_break)
    logger.info("Testing the format_type_A method of InputFile")

    formatted_str = sammyInput.InputFile.format_type_A("Test", 10)
    assert formatted_str == "Test      "

    logger.info("format_type_A method tested successfully")
    logger.info(logger_footer_break)


def test_format_type_F():
    """Test the format_type_F method for formatting floats."""
    logger.info(logger_header_break)
    logger.info("Testing the format_type_F method of InputFile")

    formatted_float = sammyInput.InputFile.format_type_F(1.2345, 10)

    assert len(formatted_float) == 10  # Ensure the formatted string is 10 characters wide
    assert formatted_float.strip() == "1.2345"  # Check that the float part is correct

    logger.info("format_type_F method tested successfully")
    logger.info(logger_footer_break)


def test_format_type_I():
    """Test the format_type_I method for formatting integers."""
    logger.info(logger_header_break)
    logger.info("Testing the format_type_I method of InputFile")

    formatted_int = sammyInput.InputFile.format_type_I(123, 5)
    assert len(formatted_int) == 5
    assert formatted_int == "  123"

    logger.info("format_type_I method tested successfully")
    logger.info(logger_footer_break)


# flush and close the all logger handlers
for handler in logger.handlers:
    handler.flush()
    handler.close()
