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

@pytest.fixture
def default_config():
    """Fixture to create and return a default config object."""
    return sammyUtils.SammyFitConfig()

def test_sammy_calls(default_config):
    """ Test for both a compiled and docker version of SAMMY """

    # Look for compiled version of SAMMY in the path
    sammy_path = shutil.which('sammy')
    if sammy_path:
        logger.info(f"Compiled SAMMY binary found at {sammy_path}")
        compiled_sammy_exists = True

        # Update the default config with the calls to the compiled SAMMY binary
        default_config.params['sammy_run_method'] = 'compiled'
        default_config.params['sammy_command'] = 'sammy'

    else:
        logger.warning("Compiled SAMMY binary not found.")
        compiled_sammy_exists = False

    # Check if Docker image exists
    docker_image = 'sammy-docker'
    docker_command = f'docker image inspect {docker_image}'
    try:
        subprocess.check_output(docker_command, shell=True, stderr=subprocess.STDOUT)
        logger.info(f"Found Docker image: {docker_image}")
        docker_image_exists = True

        # Update the default config with the calls to the Docker image
        default_config.params['sammy_run_method'] = 'docker'
        default_config.params['sammy_command'] = docker_image
        
    except subprocess.CalledProcessError:
        logger.warning(f"Docker image {docker_image} not found.")
        docker_image_exists = False

    # Assert that either the compiled SAMMY exists or the Docker image exists
    if not sammy_path and not docker_image_exists:
        logger.error("Neither a compiled version of SAMMY nor the SAMMY Docker image is available.")
        pytest.fail("Neither a compiled version of SAMMY nor the SAMMY Docker image is available.")
    else:
        if compiled_sammy_exists == True and docker_image_exists == False:
            logger.info("SAMMY is available as a compiled binary.")
        elif compiled_sammy_exists == False and docker_image_exists == True:
            logger.info("SAMMY is available as a Docker image.")
        else:
            logger.info("Both a compiled SAMMY binary and a Docker image are available.")
