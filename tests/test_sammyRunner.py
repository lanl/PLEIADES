import shutil
import os
from pleiades import sammyUtils, sammyRunner
import pathlib
import pytest
import logging
import subprocess

# Configure logging for the test
log_file = 'test_sammyRunner.log'

# Remove file if it already exists
if os.path.exists(log_file):
    os.remove(log_file)

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
file_handler = logging.FileHandler(log_file)
console_handler = logging.StreamHandler()

# Set levels for handlers
file_handler.setLevel(logging.INFO)
console_handler.setLevel(logging.INFO)

# Create formatters and add them to handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger_header_break = '====================================================='
logger_footer_break = '-----------------------------------------------------'

@pytest.fixture
def default_config():
    """Fixture to create and return a default config object."""
    return sammyUtils.SammyFitConfig()

def test_check_sammy_environment(default_config):
    """ Test if sammy enviornment exist and check for both a compiled and docker version of SAMMY """

    logger.info(logger_header_break)
    logger.info("Checking if SAMMY environment exists")

    sammy_compiled_exists, sammy_docker_exists = sammyRunner.check_sammy_environment(default_config)

    logger.info(logger_footer_break)

def test_set_sammy_call_method(default_config):
    """Test the set_sammy_call_method() function to determine the SAMMY run method."""
    
    # Test the set_sammy_call_method() function
    logger.info(logger_header_break)
    logger.info("Testing the set_sammy_call_method() function")
    sammy_call, sammy_command = sammyRunner.set_sammy_call_method(docker_image_name='sammy-docker', verbose_level=1)
    logger.info(f"Sammy call: {sammy_call}")
    logger.info(f"Sammy command: {sammy_command}")

    # Check if the sammy_call and sammy_command are strings
    assert isinstance(sammy_call, str)
    assert isinstance(sammy_command, str)
    logger.info(logger_footer_break)

    # Setting the sammy_run_method and sammy_command in the default config for subsequent tests
    default_config.params['sammy_run_method'] = sammy_call
    default_config.params['sammy_command'] = sammy_command

