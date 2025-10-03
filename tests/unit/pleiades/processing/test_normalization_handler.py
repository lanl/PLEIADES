"""Comprehensive unit tests for processing/normalization_handler.py module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from pleiades.processing import DataType, MasterDictKeys, Roi
from pleiades.processing.normalization_handler import (
    combine_data,
    correct_data_for_proton_charge,
    correct_data_for_shutter_counts,
    get_counts_from_normalized_data,
    performing_normalization,
    remove_outliers,
    update_with_crop,
    update_with_data,
    update_with_list_of_files,
    update_with_rebin,
)


class TestUpdateWithListOfFiles:
    """Test update_with_list_of_files function."""

    @patch("pleiades.processing.normalization_handler.retrieve_list_of_most_dominant_extension_from_folder")
    def test_update_with_existing_folders(self, mock_retrieve):
        """Test updating master dict with list of files from existing folders."""
        mock_retrieve.return_value = (["file1.tiff", "file2.tiff"], ".tiff")

        with tempfile.TemporaryDirectory() as tmpdir:
            folder_path = tmpdir
            master_dict = {
                MasterDictKeys.data_type: DataType.sample,
                MasterDictKeys.list_folders: {folder_path: {MasterDictKeys.list_images: None}},
            }

            update_with_list_of_files(master_dict)

            assert master_dict[MasterDictKeys.list_folders][folder_path][MasterDictKeys.list_images] == [
                "file1.tiff",
                "file2.tiff",
            ]
            assert master_dict[MasterDictKeys.list_folders][folder_path][MasterDictKeys.ext] == ".tiff"
            mock_retrieve.assert_called_once_with(folder_path)

    def test_update_with_nonexistent_folder(self):
        """Test that FileNotFoundError is raised for non-existent folders."""
        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {"/nonexistent/folder": {MasterDictKeys.list_images: None}},
        }

        with pytest.raises(FileNotFoundError, match="Folder /nonexistent/folder does not exist"):
            update_with_list_of_files(master_dict)

    @patch("pleiades.processing.normalization_handler.retrieve_list_of_most_dominant_extension_from_folder")
    def test_update_multiple_folders(self, mock_retrieve):
        """Test updating master dict with multiple folders."""
        mock_retrieve.side_effect = [(["sample1.fits"], ".fits"), (["sample2.fits", "sample3.fits"], ".fits")]

        with tempfile.TemporaryDirectory() as tmpdir:
            folder1 = Path(tmpdir) / "folder1"
            folder2 = Path(tmpdir) / "folder2"
            folder1.mkdir()
            folder2.mkdir()

            master_dict = {
                MasterDictKeys.data_type: DataType.ob,
                MasterDictKeys.list_folders: {
                    str(folder1): {MasterDictKeys.list_images: None},
                    str(folder2): {MasterDictKeys.list_images: None},
                },
            }

            update_with_list_of_files(master_dict)

            assert len(master_dict[MasterDictKeys.list_folders][str(folder1)][MasterDictKeys.list_images]) == 1
            assert len(master_dict[MasterDictKeys.list_folders][str(folder2)][MasterDictKeys.list_images]) == 2
            assert mock_retrieve.call_count == 2


class TestUpdateWithData:
    """Test update_with_data function."""

    @patch("pleiades.processing.normalization_handler.load")
    def test_update_with_data_single_folder(self, mock_load):
        """Test loading data for single folder."""
        mock_data = np.ones((10, 256, 256))
        mock_load.return_value = mock_data

        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {
                "/path/to/data": {
                    MasterDictKeys.list_images: ["file1.tiff", "file2.tiff"],
                    MasterDictKeys.ext: ".tiff",
                    MasterDictKeys.data: None,
                }
            },
        }

        update_with_data(master_dict)

        assert np.array_equal(master_dict[MasterDictKeys.list_folders]["/path/to/data"][MasterDictKeys.data], mock_data)
        mock_load.assert_called_once_with(["file1.tiff", "file2.tiff"], ".tiff")

    @patch("pleiades.processing.normalization_handler.load")
    def test_update_with_data_multiple_folders(self, mock_load):
        """Test loading data for multiple folders."""
        mock_data1 = np.ones((5, 128, 128))
        mock_data2 = np.zeros((10, 256, 256))
        mock_load.side_effect = [mock_data1, mock_data2]

        master_dict = {
            MasterDictKeys.data_type: DataType.ob,
            MasterDictKeys.list_folders: {
                "/folder1": {MasterDictKeys.list_images: ["a.fits"], MasterDictKeys.ext: ".fits"},
                "/folder2": {MasterDictKeys.list_images: ["b.fits", "c.fits"], MasterDictKeys.ext: ".fits"},
            },
        }

        update_with_data(master_dict)

        assert master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data].shape == (5, 128, 128)
        assert master_dict[MasterDictKeys.list_folders]["/folder2"][MasterDictKeys.data].shape == (10, 256, 256)
        assert mock_load.call_count == 2


class TestUpdateWithCrop:
    """Test update_with_crop function."""

    def test_crop_with_valid_roi(self):
        """Test cropping with valid ROI."""
        master_dict = {MasterDictKeys.sample_data: {"/folder1": np.ones((10, 256, 256))}}

        roi = Roi(50, 50, 150, 150)
        update_with_crop(master_dict, roi)

        # Check that data was cropped
        assert master_dict[MasterDictKeys.sample_data]["/folder1"].shape == (10, 100, 100)

    def test_crop_with_none_roi(self):
        """Test that None ROI leaves data unchanged."""
        original_data = np.ones((10, 256, 256))
        master_dict = {MasterDictKeys.sample_data: {"/folder1": original_data.copy()}}

        update_with_crop(master_dict, None)

        # Data should be unchanged
        assert np.array_equal(master_dict[MasterDictKeys.sample_data]["/folder1"], original_data)

    @patch("pleiades.processing.normalization_handler.crop")
    def test_crop_multiple_folders(self, mock_crop):
        """Test cropping multiple folders."""
        mock_crop.side_effect = lambda data, roi: data[:, :100, :100]

        master_dict = {
            MasterDictKeys.sample_data: {"/folder1": np.ones((5, 256, 256)), "/folder2": np.zeros((10, 512, 512))}
        }

        roi = Roi(0, 0, 100, 100)
        update_with_crop(master_dict, roi)

        assert mock_crop.call_count == 2
        assert master_dict[MasterDictKeys.sample_data]["/folder1"].shape == (5, 100, 100)
        assert master_dict[MasterDictKeys.sample_data]["/folder2"].shape == (10, 100, 100)


class TestUpdateWithRebin:
    """Test update_with_rebin function."""

    @patch("pleiades.processing.normalization_handler.rebin")
    def test_rebin_with_factor_2(self, mock_rebin):
        """Test rebinning with factor 2."""
        input_data = np.ones((10, 256, 256))
        rebinned_data = np.ones((10, 128, 128))
        mock_rebin.return_value = rebinned_data

        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {"/folder1": {MasterDictKeys.data: input_data}},
        }

        update_with_rebin(master_dict, binning_factor=2)

        mock_rebin.assert_called_once_with(input_data, 2)
        assert master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data].shape == (10, 128, 128)

    def test_rebin_with_factor_1_skips(self):
        """Test that binning factor 1 skips rebinning."""
        original_data = np.ones((10, 256, 256))
        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {"/folder1": {MasterDictKeys.data: original_data.copy()}},
        }

        with patch("pleiades.processing.normalization_handler.rebin") as mock_rebin:
            update_with_rebin(master_dict, binning_factor=1)
            mock_rebin.assert_not_called()

        # Data should be unchanged
        assert np.array_equal(master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data], original_data)

    def test_rebin_with_invalid_factor(self):
        """Test that invalid binning factor raises ValueError."""
        master_dict = {MasterDictKeys.data_type: DataType.sample, MasterDictKeys.list_folders: {}}

        with pytest.raises(ValueError, match="Binning factor must be positive"):
            update_with_rebin(master_dict, binning_factor=0)

        with pytest.raises(ValueError, match="Binning factor must be positive"):
            update_with_rebin(master_dict, binning_factor=-1)


class TestRemoveOutliers:
    """Test remove_outliers function."""

    @patch("pleiades.processing.normalization_handler.image_processing_remove_outliers")
    def test_remove_outliers_basic(self, mock_remove_outliers):
        """Test basic outlier removal."""
        input_data = np.ones((10, 256, 256))
        cleaned_data = np.ones((10, 256, 256)) * 0.99
        mock_remove_outliers.return_value = cleaned_data

        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {"/folder1": {MasterDictKeys.data: input_data}},
        }

        remove_outliers(master_dict, dif=20.0, num_threads=4)

        mock_remove_outliers.assert_called_once_with(input_data, 20.0, 4)
        assert np.array_equal(master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data], cleaned_data)

    def test_remove_outliers_invalid_parameters(self):
        """Test that invalid parameters raise ValueError."""
        master_dict = {MasterDictKeys.data_type: DataType.sample, MasterDictKeys.list_folders: {}}

        with pytest.raises(ValueError, match="Outlier detection threshold must be positive"):
            remove_outliers(master_dict, dif=0, num_threads=4)

        with pytest.raises(ValueError, match="Number of threads must be positive"):
            remove_outliers(master_dict, dif=20.0, num_threads=0)

    @patch("pleiades.processing.normalization_handler.image_processing_remove_outliers")
    def test_remove_outliers_multiple_folders(self, mock_remove_outliers):
        """Test outlier removal on multiple folders."""
        mock_remove_outliers.side_effect = lambda data, dif, threads: data * 0.95

        master_dict = {
            MasterDictKeys.data_type: DataType.ob,
            MasterDictKeys.list_folders: {
                "/folder1": {MasterDictKeys.data: np.ones((5, 128, 128))},
                "/folder2": {MasterDictKeys.data: np.ones((10, 256, 256))},
            },
        }

        remove_outliers(master_dict, dif=15.0, num_threads=8)

        assert mock_remove_outliers.call_count == 2
        assert np.allclose(master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data], 0.95)


class TestCombineData:
    """Test combine_data function."""

    def test_combine_data_no_corrections(self):
        """Test combining data without any corrections."""
        ob_dict = {
            MasterDictKeys.data_type: DataType.ob,
            MasterDictKeys.list_folders: {
                "/ob1": {MasterDictKeys.data: np.ones((10, 100, 100)) * 2.0},
                "/ob2": {MasterDictKeys.data: np.ones((10, 100, 100)) * 3.0},
            },
        }

        norm_dict = {}
        combine_data(ob_dict, False, False, norm_dict)

        # Should be median of 2.0 and 3.0 = 2.5
        assert MasterDictKeys.obs_data_combined in norm_dict
        assert np.allclose(norm_dict[MasterDictKeys.obs_data_combined], 2.5)

    def test_combine_data_with_proton_charge(self):
        """Test combining data with proton charge correction."""
        ob_dict = {
            MasterDictKeys.data_type: DataType.ob,
            MasterDictKeys.list_folders: {
                "/ob1": {MasterDictKeys.data: np.ones((10, 50, 50)) * 100.0, MasterDictKeys.proton_charge: 2.0}
            },
        }

        norm_dict = {}
        combine_data(ob_dict, True, False, norm_dict)

        # Data should be divided by proton charge
        assert np.allclose(norm_dict[MasterDictKeys.obs_data_combined], 50.0)

    def test_combine_data_with_shutter_counts(self):
        """Test combining data with shutter count correction."""
        ob_dict = {
            MasterDictKeys.data_type: DataType.ob,
            MasterDictKeys.list_folders: {
                "/ob1": {MasterDictKeys.data: np.ones((2, 50, 50)) * 100.0, MasterDictKeys.list_shutters: [2.0, 4.0]}
            },
        }

        norm_dict = {}
        combine_data(ob_dict, False, True, norm_dict)

        # First frame divided by 2, second by 4
        expected = np.ones((2, 50, 50))
        expected[0] *= 50.0
        expected[1] *= 25.0
        assert np.allclose(norm_dict[MasterDictKeys.obs_data_combined], expected)

    def test_combine_data_removes_zeros(self):
        """Test that zero values are replaced with NaN."""
        ob_dict = {
            MasterDictKeys.data_type: DataType.ob,
            MasterDictKeys.list_folders: {"/ob1": {MasterDictKeys.data: np.zeros((5, 10, 10))}},
        }

        norm_dict = {}
        combine_data(ob_dict, False, False, norm_dict)

        # Zero values should become NaN
        assert np.all(np.isnan(norm_dict[MasterDictKeys.obs_data_combined]))


class TestCorrectDataForProtonCharge:
    """Test correct_data_for_proton_charge function."""

    def test_correct_with_proton_charge_enabled(self):
        """Test correction when enabled."""
        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {
                "/folder1": {MasterDictKeys.data: np.ones((10, 100, 100)) * 100.0, MasterDictKeys.proton_charge: 2.5}
            },
        }

        correct_data_for_proton_charge(master_dict, True)

        expected = 100.0 / 2.5
        assert np.allclose(master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data], expected)

    def test_correct_with_proton_charge_disabled(self):
        """Test that correction is skipped when disabled."""
        original_data = np.ones((10, 100, 100)) * 100.0
        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {
                "/folder1": {MasterDictKeys.data: original_data.copy(), MasterDictKeys.proton_charge: 2.5}
            },
        }

        correct_data_for_proton_charge(master_dict, False)

        # Data should be unchanged
        assert np.array_equal(master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data], original_data)

    def test_correct_multiple_folders(self):
        """Test correction on multiple folders with different proton charges."""
        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {
                "/folder1": {MasterDictKeys.data: np.ones((5, 50, 50)) * 100.0, MasterDictKeys.proton_charge: 2.0},
                "/folder2": {MasterDictKeys.data: np.ones((5, 50, 50)) * 200.0, MasterDictKeys.proton_charge: 4.0},
            },
        }

        correct_data_for_proton_charge(master_dict, True)

        assert np.allclose(master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data], 50.0)
        assert np.allclose(master_dict[MasterDictKeys.list_folders]["/folder2"][MasterDictKeys.data], 50.0)


class TestCorrectDataForShutterCounts:
    """Test correct_data_for_shutter_counts function."""

    def test_correct_with_shutter_counts_enabled(self):
        """Test correction when enabled."""
        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {
                "/folder1": {
                    MasterDictKeys.data: np.array(
                        [np.ones((100, 100)) * 100.0, np.ones((100, 100)) * 200.0, np.ones((100, 100)) * 300.0]
                    ),
                    MasterDictKeys.list_shutters: [2.0, 4.0, 6.0],
                }
            },
        }

        correct_data_for_shutter_counts(master_dict, True)

        data = master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data]
        assert np.allclose(data[0], 50.0)
        assert np.allclose(data[1], 50.0)
        assert np.allclose(data[2], 50.0)

    def test_correct_with_shutter_counts_disabled(self):
        """Test that correction is skipped when disabled."""
        original_data = np.ones((3, 100, 100)) * 100.0
        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {
                "/folder1": {MasterDictKeys.data: original_data.copy(), MasterDictKeys.list_shutters: [2.0, 4.0, 6.0]}
            },
        }

        correct_data_for_shutter_counts(master_dict, False)

        # Data should be unchanged
        assert np.array_equal(master_dict[MasterDictKeys.list_folders]["/folder1"][MasterDictKeys.data], original_data)


class TestPerformingNormalization:
    """Test performing_normalization function."""

    def test_normalization_without_background(self):
        """Test basic normalization without background correction."""
        sample_dict = {MasterDictKeys.list_folders: {"/sample1": {MasterDictKeys.data: np.ones((10, 100, 100)) * 50.0}}}

        norm_dict = {MasterDictKeys.obs_data_combined: np.ones((10, 100, 100)) * 100.0, MasterDictKeys.sample_data: {}}

        performing_normalization(sample_dict, norm_dict, None)

        # Transmission = Sample / OB = 50 / 100 = 0.5
        assert "/sample1" in norm_dict[MasterDictKeys.sample_data]
        assert np.allclose(norm_dict[MasterDictKeys.sample_data]["/sample1"], 0.5)

    def test_normalization_with_background(self):
        """Test normalization with background ROI correction."""
        # Create sample data with higher values in background region
        sample_data = np.ones((5, 100, 100)) * 50.0
        sample_data[:, :10, :10] = 100.0  # Higher values in background ROI

        sample_dict = {MasterDictKeys.list_folders: {"/sample1": {MasterDictKeys.data: sample_data}}}

        # OB data with different background
        ob_data = np.ones((5, 100, 100)) * 100.0
        ob_data[:, :10, :10] = 200.0  # Different values in background ROI

        norm_dict = {MasterDictKeys.obs_data_combined: ob_data, MasterDictKeys.sample_data: {}}

        background_roi = Roi(0, 0, 10, 10)
        performing_normalization(sample_dict, norm_dict, background_roi)

        # Check that background correction was applied
        result = norm_dict[MasterDictKeys.sample_data]["/sample1"]
        assert result.shape == (5, 100, 100)
        # Background correction coefficient = median(OB_bg) / median(Sample_bg) = 200 / 100 = 2
        # Transmission = (Sample / OB) * coeff = (50 / 100) * 2 = 1.0
        assert np.allclose(result[:, 50, 50], 1.0, rtol=0.1)

    def test_normalization_handles_division_by_zero(self):
        """Test that division by zero is handled gracefully."""
        sample_dict = {MasterDictKeys.list_folders: {"/sample1": {MasterDictKeys.data: np.ones((5, 50, 50)) * 10.0}}}

        # OB with some zero values
        ob_data = np.ones((5, 50, 50)) * 100.0
        ob_data[0, 10:20, 10:20] = 0.0  # Zero values in OB

        norm_dict = {MasterDictKeys.obs_data_combined: ob_data, MasterDictKeys.sample_data: {}}

        performing_normalization(sample_dict, norm_dict, None)

        result = norm_dict[MasterDictKeys.sample_data]["/sample1"]
        # Check that inf/nan values are replaced with 0
        assert np.all(np.isfinite(result))
        assert np.all(result[0, 10:20, 10:20] == 0.0)


class TestGetCountsFromNormalizedData:
    """Test get_counts_from_normalized_data function."""

    def test_get_counts_basic(self):
        """Test basic count extraction."""
        # Create normalized data (transmission values)
        normalized_data = np.ones((10, 100, 100)) * 0.5

        counts, uncertainties = get_counts_from_normalized_data(normalized_data)

        assert counts.shape == (10,)
        assert uncertainties.shape == (10,)
        assert np.allclose(counts, 0.5)  # Average transmission

    def test_get_counts_with_varying_transmission(self):
        """Test count extraction with varying transmission values."""
        normalized_data = np.zeros((5, 50, 50))
        for i in range(5):
            normalized_data[i] = (i + 1) * 0.2  # 0.2, 0.4, 0.6, 0.8, 1.0

        counts, uncertainties = get_counts_from_normalized_data(normalized_data)

        assert counts.shape == (5,)
        assert np.allclose(counts, [0.2, 0.4, 0.6, 0.8, 1.0])

    def test_get_counts_handles_nan_values(self):
        """Test that NaN values are handled properly."""
        normalized_data = np.ones((5, 50, 50)) * 0.7
        normalized_data[0, 10, 10] = np.nan
        normalized_data[1, :, :] = np.nan  # Entire frame is NaN

        counts, uncertainties = get_counts_from_normalized_data(normalized_data)

        assert counts.shape == (5,)
        # nanmean should handle NaN values
        assert np.isfinite(counts[0])  # Should still compute mean excluding NaN
        assert counts[1] == 0.0  # All NaN should result in 0

    def test_get_counts_invalid_input(self):
        """Test that invalid inputs raise appropriate errors."""
        # Not a numpy array
        with pytest.raises(TypeError, match="Normalized data must be a numpy array"):
            get_counts_from_normalized_data([1, 2, 3])

        # Wrong dimensions
        with pytest.raises(ValueError, match="Expected 3D array"):
            get_counts_from_normalized_data(np.ones((10, 10)))

    @patch("pleiades.processing.normalization_handler.logger")
    def test_get_counts_warns_about_outliers(self, mock_logger):
        """Test that warnings are logged for outliers."""
        normalized_data = np.ones((5, 50, 50)) * 0.8
        normalized_data[0, 10:20, 10:20] = 3.0  # Outliers > 2.0

        counts, uncertainties = get_counts_from_normalized_data(normalized_data)

        # Should warn about outliers
        assert any("transmission > 2.0" in str(call) for call in mock_logger.warning.call_args_list)

    @patch("pleiades.processing.normalization_handler.logger")
    def test_get_counts_warns_about_low_transmission(self, mock_logger):
        """Test that warnings are logged for very low transmission values."""
        normalized_data = np.ones((5, 50, 50)) * 0.5
        # Set more than 10% of pixels to very low transmission
        normalized_data[:, :25, :25] = 0.005  # Below threshold

        counts, uncertainties = get_counts_from_normalized_data(normalized_data)

        # Should warn about low transmission
        assert any("very low transmission" in str(call) for call in mock_logger.warning.call_args_list)


class TestIntegrationScenarios:
    """Test integration scenarios with multiple functions."""

    def test_full_normalization_workflow(self):
        """Test a complete normalization workflow."""
        # Create sample data
        sample_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {
                "/sample": {MasterDictKeys.data: np.ones((10, 100, 100)) * 80.0, MasterDictKeys.proton_charge: 2.0}
            },
        }

        # Create OB data
        ob_dict = {
            MasterDictKeys.data_type: DataType.ob,
            MasterDictKeys.list_folders: {
                "/ob": {MasterDictKeys.data: np.ones((10, 100, 100)) * 100.0, MasterDictKeys.proton_charge: 1.0}
            },
        }

        # Apply corrections
        correct_data_for_proton_charge(sample_dict, True)
        correct_data_for_proton_charge(ob_dict, True)

        # Combine OB data
        norm_dict = {MasterDictKeys.sample_data: {}}
        combine_data(ob_dict, True, False, norm_dict)

        # Perform normalization
        performing_normalization(sample_dict, norm_dict, None)

        # Get counts
        transmission = norm_dict[MasterDictKeys.sample_data]["/sample"]
        counts, uncertainties = get_counts_from_normalized_data(transmission)

        # Check results
        # Sample: 80/2 = 40, OB: 100/1 = 100, Transmission = 40/100 = 0.4
        assert np.allclose(counts, 0.4)

    @patch("pleiades.processing.normalization_handler.retrieve_list_of_most_dominant_extension_from_folder")
    @patch("pleiades.processing.normalization_handler.load")
    def test_workflow_with_file_discovery(self, mock_load, mock_retrieve):
        """Test workflow including file discovery."""
        # Setup mocks
        mock_retrieve.return_value = (["sample.tiff"], ".tiff")
        mock_load.return_value = np.ones((5, 50, 50)) * 100.0

        with tempfile.TemporaryDirectory() as tmpdir:
            master_dict = {
                MasterDictKeys.data_type: DataType.sample,
                MasterDictKeys.list_folders: {tmpdir: {MasterDictKeys.list_images: None}},
            }

            # File discovery
            update_with_list_of_files(master_dict)

            # Load data
            update_with_data(master_dict)

            # Apply rebinning
            update_with_rebin(master_dict, binning_factor=2)

            # Verify workflow
            assert master_dict[MasterDictKeys.list_folders][tmpdir][MasterDictKeys.ext] == ".tiff"
            assert MasterDictKeys.data in master_dict[MasterDictKeys.list_folders][tmpdir]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_master_dict(self):
        """Test functions with empty master dictionaries."""
        empty_dict = {MasterDictKeys.data_type: DataType.sample, MasterDictKeys.list_folders: {}}

        # These should handle empty dicts gracefully
        update_with_data(empty_dict)
        update_with_rebin(empty_dict, 2)
        remove_outliers(empty_dict, 20.0, 4)
        correct_data_for_proton_charge(empty_dict, True)
        correct_data_for_shutter_counts(empty_dict, True)

        # Verify dict remains empty
        assert len(empty_dict[MasterDictKeys.list_folders]) == 0

    def test_division_by_zero_in_corrections(self):
        """Test handling of zero values in corrections."""
        master_dict = {
            MasterDictKeys.data_type: DataType.sample,
            MasterDictKeys.list_folders: {
                "/folder": {
                    MasterDictKeys.data: np.ones((5, 50, 50)) * 100.0,
                    MasterDictKeys.proton_charge: 0.0,  # Zero proton charge
                }
            },
        }

        # The function doesn't explicitly handle zero division, it will produce inf/nan
        correct_data_for_proton_charge(master_dict, True)

        # Check that the result contains inf values
        result = master_dict[MasterDictKeys.list_folders]["/folder"][MasterDictKeys.data]
        assert np.all(np.isinf(result))

    def test_mismatched_data_shapes(self):
        """Test handling of mismatched data shapes in normalization."""
        sample_dict = {MasterDictKeys.list_folders: {"/sample": {MasterDictKeys.data: np.ones((10, 100, 100))}}}

        # OB with different number of time channels
        norm_dict = {
            MasterDictKeys.obs_data_combined: np.ones((5, 100, 100)),  # Different time channels
            MasterDictKeys.sample_data: {},
        }

        # This should handle the mismatch (zip will stop at shortest)
        performing_normalization(sample_dict, norm_dict, None)

        result = norm_dict[MasterDictKeys.sample_data]["/sample"]
        # Output array matches sample shape, but only first 5 frames are normalized
        assert result.shape[0] == 10  # Matches sample size
        # First 5 frames should be normalized (1.0 since sample == OB)
        assert np.allclose(result[:5], 1.0)
        # Remaining frames are uninitialized (empty_like leaves garbage values)
