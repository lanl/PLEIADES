from unittest.mock import patch

import pytest

from pleiades.utils.nexus import get_proton_charge, get_proton_charge_dict


@pytest.fixture
def mock_h5py_file():
    with patch("h5py.File", autospec=True) as mock_file:
        yield mock_file


def test_get_proton_charge_valid_pc_units(mock_h5py_file):
    mock_h5py_file.return_value.__enter__.return_value = {"entry": {"proton_charge": [1.2e12]}}
    result = get_proton_charge("mock_file_path", units="pc")
    assert result == 1.2e12


def test_get_proton_charge_valid_c_units(mock_h5py_file):
    mock_h5py_file.return_value.__enter__.return_value = {"entry": {"proton_charge": [1.2e12]}}
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
    mock_h5py_file.return_value.__enter__.return_value = {"entry": {}}
    with pytest.raises(KeyError):
        get_proton_charge("mock_file_path")


def test_get_proton_charge_dict_valid_case(mock_h5py_file):
    mock_h5py_file.return_value.__enter__.return_value = {"entry": {"proton_charge": [1.2e12]}}
    list_sample_nexus = ["sample1.nxs", "sample2.nxs"]
    list_nexus_obs = ["ob1.nxs", "ob2.nxs"]
    nbr_sample_folders = 2
    nbr_obs_folders = 2

    result = get_proton_charge_dict(list_sample_nexus, list_nexus_obs, nbr_sample_folders, nbr_obs_folders)
    assert result["state"] is True
    assert result["sample"] == [1.2e12, 1.2e12]
    assert result["ob"] == [1.2e12, 1.2e12]


def test_get_proton_charge_dict_mismatched_sample_folders(mock_h5py_file):
    list_sample_nexus = ["sample1.nxs"]
    list_nexus_obs = ["ob1.nxs", "ob2.nxs"]
    nbr_sample_folders = 2
    nbr_obs_folders = 2

    result = get_proton_charge_dict(list_sample_nexus, list_nexus_obs, nbr_sample_folders, nbr_obs_folders)
    assert result["state"] is False
    assert result["sample"] is None
    assert result["ob"] is None


def test_get_proton_charge_dict_mismatched_ob_folders(mock_h5py_file):
    list_sample_nexus = ["sample1.nxs", "sample2.nxs"]
    list_nexus_obs = ["ob1.nxs"]
    nbr_sample_folders = 2
    nbr_obs_folders = 2

    result = get_proton_charge_dict(list_sample_nexus, list_nexus_obs, nbr_sample_folders, nbr_obs_folders)
    assert result["state"] is False
    assert result["sample"] is None
    assert result["ob"] is None


def test_get_proton_charge_dict_missing_sample_proton_charge(mock_h5py_file):
    def mock_get_proton_charge(nexus, units="pc"):
        return None if nexus == "sample2.nxs" else 1.2e12

    with patch("pleiades.utils.nexus.get_proton_charge", side_effect=mock_get_proton_charge):
        list_sample_nexus = ["sample1.nxs", "sample2.nxs"]
        list_nexus_obs = ["ob1.nxs", "ob2.nxs"]
        nbr_sample_folders = 2
        nbr_obs_folders = 2

        result = get_proton_charge_dict(list_sample_nexus, list_nexus_obs, nbr_sample_folders, nbr_obs_folders)
        assert result["state"] is False
        assert result["sample"] is None
        assert result["ob"] is None


def test_get_proton_charge_dict_missing_ob_proton_charge(mock_h5py_file):
    def mock_get_proton_charge(nexus, units="pc"):
        return None if nexus == "ob2.nxs" else 1.2e12

    with patch("pleiades.utils.nexus.get_proton_charge", side_effect=mock_get_proton_charge):
        list_sample_nexus = ["sample1.nxs", "sample2.nxs"]
        list_nexus_obs = ["ob1.nxs", "ob2.nxs"]
        nbr_sample_folders = 2
        nbr_obs_folders = 2

        result = get_proton_charge_dict(list_sample_nexus, list_nexus_obs, nbr_sample_folders, nbr_obs_folders)
        assert result["state"] is False
        assert result["sample"] is None
        assert result["ob"] is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])