import shutil
import os
from pleiades import sammyUtils, sammyRunner
import pathlib
import pytest
import logging
import subprocess

## Configure logging for the test
# Set file name
log_file = 'test_sammyUtils.log'

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

def test_sammyUtils_sammy_config(default_config):
    """Test the sammyUtils.SammyFitConfig class by loading the default config."""
    
    # Check if default_config is a SammyFitConfig object
    logger.info(logger_header_break)
    logger.info("Checking if default config is a SammyFitConfig object")
    assert isinstance(default_config, sammyUtils.SammyFitConfig)
    logger.info("Default config loaded successfully")
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

def test_create_parFile_from_endf(default_config):
    """Test the creation of a parFile from an ENDF file."""

    logger.info(logger_header_break)
    test_isotope = 'U-238'
    logger.info(f"Testing the creation of a parFile from an ENDF file for with test isotope: {test_isotope}")

    # Grab the sammy_call and sammy_command from the sammyRunner.set_sammy_call_method() function
    sammy_call, sammy_command = sammyRunner.set_sammy_call_method(docker_image_name = 'sammy-docker',verbose_level=1)

    # Update the default config with a U-238 isotope
    logger.info("Updating default config with U-238 isotope")
    default_config.params['isotopes']['names'] = [test_isotope]
    default_config.params['sammy_run_method'] = sammy_call
    default_config.params['sammy_command'] = sammy_command
    default_config.params['isotopes']['names'] = [test_isotope]
    default_config.params['isotopes']['abundances'] = [1.0]
    default_config.params['fit_energy_min'] = 0.1
    default_config.params['fit_energy_max'] = 10.0

    # Create the parFile from the ENDF file
    logger.info(f"Creating parFile from ENDF file for {test_isotope}")

    # test create_parFile_from_endf() function with config object. 
    sammyUtils.create_parFile_from_endf(default_config, verbose_level=0)

    # Before running sammy_par_from_endf() we need to check if the 
    # u238 directory was created in the .archive/endf/u238
    endfFile_path = pathlib.Path(default_config.params['directories']['endf_dir'])
    isotope_dir_path = pathlib.Path(endfFile_path / test_isotope)
    logger.info(f"Checking if endf directory was created at {isotope_dir_path}")
    assert isotope_dir_path.exists()

    # Check if the parFile was created
    logger.info(f"Checking if SAMNDF.PAR parFile was created at {isotope_dir_path / 'results'}")
    
    parFile_path = pathlib.Path(isotope_dir_path / 'results' / 'SAMNDF.PAR')
    assert parFile_path.exists()
    logger.info(logger_footer_break)

def final_file_checks_and_cleanup(default_config):
    """Test if the directories created by the default config are created and then delete them."""
    # Check if default archive and data directory were created
    archive_dir_path = pathlib.Path(default_config.params['directories']['archive_dir'])
    endf_dir_path = pathlib.Path(default_config.params['directories']['endf_dir'])
    data_dir_path = pathlib.Path(default_config.params['directories']['data_dir'])
    assert archive_dir_path.exists()
    assert endf_dir_path.exists()
    assert data_dir_path.exists()
    logger.info("Default archive and data directories created successfully")

    # Remove the directories created when the config was loaded even if there are files in them
    shutil.rmtree(endf_dir_path)
    shutil.rmtree(archive_dir_path)
    shutil.rmtree(data_dir_path)
    logger.info("Default archive and data directories removed successfully")

# flush and close the all logger handlers
for handler in logger.handlers:
    handler.flush()
    handler.close()


