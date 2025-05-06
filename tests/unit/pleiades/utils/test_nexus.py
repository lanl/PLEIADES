import pytest
import h5py
from unittest.mock import MagicMock, patch
from pleiades.utils.nexus import get_proton_charge


@pytest.fixture
def mock_h5py_file():
    with patch("h5py.File", autospec=True) as mock_file:
        yield mock_file

def test_get_proton_charge_valid_pc_units(mock_h5py_file):
    mock_h5py_file.return_value.__enter__.return_value = {
        "entry": {"proton_charge": [1.2e12]}
    }
    result = get_proton_charge("mock_file_path", units="pc")
    assert result == 1.2e12

def test_get_proton_charge_valid_c_units(mock_h5py_file):
    mock_h5py_file.return_value.__enter__.return_value = {
        "entry": {"proton_charge": [1.2e12]}
    }
    result = get_proton_charge("mock_file_path", units="c")
    assert result == 1.2

def test_get_proton_charge_file_not_found(mock_h5py_file):
    mock_h5py_file.side_effect = FileNotFoundError
    result = get_proton_charge("non_existent_file")
    assert result is None

def test_get_proton_charge_none_input():
    result = get_proton_charge(None)
    assert result is None

def test_get_proton_charge_missing_proton_charge_key(mock_h5py_file):
    mock_h5py_file.return_value.__enter__.return_value = {
        "entry": {}
    }
    with pytest.raises(KeyError):
        get_proton_charge("mock_file_path")