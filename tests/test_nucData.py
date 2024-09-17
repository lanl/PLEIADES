import os
from pleiades import nucData
import pathlib
import pytest
import logging

## Configure logging for the test
# Set file name
log_file = 'test_nucData.log'

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

# Set up logger breaks for better readability
logger_header_break = '====================================================='
logger_footer_break = '-----------------------------------------------------'

# Path to the PLEIADES repo nuclear data files
NUCDATA_PATH = pathlib.Path(__file__).parent.parent / "nucDataLibs" / "isotopeInfo"

@pytest.fixture
def isotope_info_file():
    """Returns the path to the isotope.info file in the PLEIADES repo."""
    return str(NUCDATA_PATH / "isotopes.info")

@pytest.fixture
def ame_file():
    """Returns the path to the mass.mas20 file in the PLEIADES repo."""
    return str(NUCDATA_PATH / "mass.mas20")

@pytest.fixture
def neutron_file():
    """Returns the path to the neutrons.list file in the PLEIADES repo."""
    return str(NUCDATA_PATH / "neutrons.list")


def test_extract_isotope_info(isotope_info_file):
    """Test extracting isotope info from the actual isotope.info file."""
    logger.info(logger_header_break)
    logger.info("Testing extracting isotope info from the isotope.info file")
    logger.info(f"Isotope info file: {isotope_info_file}")
    
    isotope = "H-1"
    logger.info(f"Testing extracting info for {isotope}")
    spin, abundance = nucData.extract_isotope_info(isotope_info_file, isotope)
    logger.info(f"Spin: {spin}, Abundance: {abundance}")
    assert spin == "0.5"
    assert abundance == "99.9885"

    isotope = "Cl-37"
    logger.info(f"Testing extracting info for {isotope}")
    spin, abundance = nucData.extract_isotope_info(isotope_info_file, isotope)
    logger.info(f"Spin: {spin}, Abundance: {abundance}")
    assert spin == "1.5"
    assert abundance == "24.22"

    isotope = "C-12"
    logger.info(f"Testing extracting info for {isotope}")
    spin, abundance = nucData.extract_isotope_info(isotope_info_file, isotope)
    logger.info(f"Spin: {spin}, Abundance: {abundance}")
    assert spin == "0.0"
    assert abundance == "98.93"
    
    isotope = "U-241"
    logger.info(f"Testing extracting info for {isotope}")
    spin, abundance = nucData.extract_isotope_info(isotope_info_file, isotope)
    logger.info(f"Spin: {spin}, Abundance: {abundance}")
    assert spin is None
    assert abundance is None
    
    logger.info("Isotope info tested successfully")
    logger.info(logger_footer_break)
    
def test_parse_ame_line():
    """Test parsing a line from the AME file."""
    logger.info(logger_header_break)
    logger.info("Testing parsing a line from the AME file")

    line = "   0    6    6   12 C             0.0         0.0        7680.1446     0.0002  B- -17338.0681     0.9999   12 000000.0         0.0"
    parsed_data = nucData.parse_ame_line(line)

    logger.info(f"Parsed Data: {parsed_data}")
    
    assert parsed_data["NZ"] == 0
    assert parsed_data["N"] == 6
    assert parsed_data["Z"] == 6
    assert parsed_data["A"] == 12
    assert parsed_data["mass"] == 0.0
    assert parsed_data["mass_unc"] == 0.0

    logger.info("AME line parsing tested successfully")
    logger.info(logger_footer_break)
    
    
def test_get_info():
    """Test extracting element and atomic number from a string."""
    logger.info(logger_header_break)
    logger.info("Testing extraction of element and atomic number from isotopic string")

    isotope = "H-1"
    logger.info(f"Testing get_info for {isotope}")
    element, atomic_number = nucData.get_info(isotope)
    logger.info(f"Element: {element}, Atomic Number: {atomic_number}")
    assert element == "H"
    assert atomic_number == 1

    isotope = "C-12"
    logger.info(f"Testing get_info for {isotope}")
    element, atomic_number = nucData.get_info(isotope)
    logger.info(f"Element: {element}, Atomic Number: {atomic_number}")
    assert element == "C"
    assert atomic_number == 12

    # Test for malformed strings
    isotope = "InvalidString"
    logger.info(f"Testing get_info for {isotope}")
    element, atomic_number = nucData.get_info(isotope)
    logger.info(f"Element: {element}, Atomic Number: {atomic_number}")
    assert element == ""
    assert atomic_number is None

    logger.info("get_info function tested successfully")
    logger.info(logger_footer_break)
    
def test_get_mass_from_ame(ame_file, monkeypatch):
    """Test fetching the atomic mass from the actual mass.mas20 file."""
    logger.info(logger_header_break)
    logger.info("Testing fetching the atomic mass from mass.mas20")

    # Use monkeypatch to override the pleiades_dir path for nucData
    monkeypatch.setattr(nucData, "pleiades_dir", pathlib.Path(ame_file).parent.parent.parent) 
    
    # Test for a few isotopes
    isotope = "H-1"
    logger.info(f"Testing get_mass_from_ame for {isotope}")
    mass = nucData.get_mass_from_ame(isotope)
    logger.info(f"Mass: {mass}")
    assert mass == pytest.approx(1.0078, rel=1e-4)

    isotope = "He-4"
    logger.info(f"Testing get_mass_from_ame for {isotope}")
    mass = nucData.get_mass_from_ame(isotope)
    logger.info(f"Mass: {mass}")
    assert mass == pytest.approx(4.0026, rel=1e-4)

    isotope = "C-12"
    logger.info(f"Testing get_mass_from_ame for {isotope}")
    mass = nucData.get_mass_from_ame(isotope)
    logger.info(f"Mass: {mass}")
    assert mass == pytest.approx(12.000, rel=1e-4)
    
    # Test for an isotope not present in the file
    isotope = "U-244"
    logger.info(f"Testing get_mass_from_ame for {isotope}")
    mass = nucData.get_mass_from_ame(isotope)
    logger.info(f"Mass: {mass}")
    assert mass is None

    logger.info("Atomic mass fetching from AME file tested successfully")
    logger.info(logger_footer_break)


def test_get_mat_number(neutron_file, monkeypatch):
    """Test retrieving the mat number from the neutrons.list file."""
    logger.info(logger_header_break)
    logger.info("Testing fetching the ENDF mat number from neutrons.list")

    # Use monkeypatch to override the pleiades_dir path for nucData
    monkeypatch.setattr(nucData, "pleiades_dir", pathlib.Path(neutron_file).parent.parent.parent)  # Points to root directory

    # Test with known isotopes
    isotope = "Fe-56"
    logger.info(f"Testing get_mat_number for {isotope}")
    mat_number = nucData.get_mat_number(isotope)
    logger.info(f"Mat number: {mat_number}")
    assert mat_number == 2631  

    isotope = "U-238"
    logger.info(f"Testing get_mat_number for {isotope}")
    mat_number = nucData.get_mat_number(isotope)
    logger.info(f"Mat number: {mat_number}")
    assert mat_number == 9237  

    # Test for an isotope not present in the file
    isotope = "InvalidIsotope"
    logger.info(f"Testing get_mat_number for {isotope}")
    with pytest.raises(ValueError):
        mat_number = nucData.get_mat_number(isotope)