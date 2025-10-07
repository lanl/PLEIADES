"""Tests for the normalization router."""

from unittest.mock import MagicMock, patch

import pytest

from pleiades.processing import Facility
from pleiades.processing.models_ornl import Transmission
from pleiades.processing.normalization import normalization


class TestNormalizationRouter:
    """Test the normalization router functionality."""

    def test_routes_to_ornl_implementation(self):
        """Test that ORNL facility routes to normalization_ornl."""
        with patch("pleiades.processing.normalization_ornl.normalization_ornl") as mock_ornl:
            mock_ornl.return_value = [MagicMock(spec=Transmission)]

            result = normalization(list_sample_folders=["sample"], list_obs_folders=["ob"], facility=Facility.ornl)

            # Check that ornl implementation was called
            mock_ornl.assert_called_once_with(
                sample_folders=["sample"],
                ob_folders=["ob"],
                nexus_dir=None,
                roi=None,
                combine_mode=False,
                output_folder=None,
            )

            # Check return value
            assert isinstance(result, list)
            assert len(result) == 1

    def test_converts_single_string_to_list(self):
        """Test that single string folders are converted to lists."""
        with patch("pleiades.processing.normalization_ornl.normalization_ornl") as mock_ornl:
            mock_ornl.return_value = []

            normalization(list_sample_folders="single_sample", list_obs_folders="single_ob", facility=Facility.ornl)

            # Check that strings were converted to lists
            mock_ornl.assert_called_once()
            call_args = mock_ornl.call_args[1]
            assert call_args["sample_folders"] == ["single_sample"]
            assert call_args["ob_folders"] == ["single_ob"]

    def test_lanl_not_implemented(self):
        """Test that LANL facility raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="LANL normalization not yet implemented"):
            normalization(list_sample_folders=["sample"], list_obs_folders=["ob"], facility=Facility.lanl)

    def test_unknown_facility_raises_error(self):
        """Test that unknown facility raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="not implemented"):
            normalization(list_sample_folders=["sample"], list_obs_folders=["ob"], facility="unknown_facility")

    def test_passes_kwargs_through(self):
        """Test that additional kwargs are passed through."""
        with patch("pleiades.processing.normalization_ornl.normalization_ornl") as mock_ornl:
            mock_ornl.return_value = []

            normalization(
                list_sample_folders=["sample"],
                list_obs_folders=["ob"],
                facility=Facility.ornl,
                pc_uncertainty=0.01,
                custom_param="test",
            )

            # Check that kwargs were passed
            call_args = mock_ornl.call_args[1]
            assert call_args["pc_uncertainty"] == 0.01
            assert call_args["custom_param"] == "test"

    def test_parameter_name_mapping(self):
        """Test that nexus_path is mapped to nexus_dir for ORNL."""
        with patch("pleiades.processing.normalization_ornl.normalization_ornl") as mock_ornl:
            mock_ornl.return_value = []

            normalization(
                list_sample_folders=["sample"],
                list_obs_folders=["ob"],
                nexus_path="/path/to/nexus",
                facility=Facility.ornl,
            )

            # Check parameter mapping
            call_args = mock_ornl.call_args[1]
            assert call_args["nexus_dir"] == "/path/to/nexus"
            assert "nexus_path" not in call_args

    def test_combine_mode_passed_through(self):
        """Test that combine_mode is passed through correctly."""
        with patch("pleiades.processing.normalization_ornl.normalization_ornl") as mock_ornl:
            mock_ornl.return_value = []

            normalization(
                list_sample_folders=["sample"], list_obs_folders=["ob"], facility=Facility.ornl, combine_mode=True
            )

            call_args = mock_ornl.call_args[1]
            assert call_args["combine_mode"] is True
