import numpy as np
import pytest
from pleiades.utils.image_processing import rebin
from pleiades.utils.image_processing import crop
from pleiades.processing import Roi


# rebin
def test_rebin_with_valid_input():
    # Test with a 2D array and binning factor of 2
    data = np.array([[[1, 2, 3, 4],
                     [5, 6, 7, 8],
                     [9, 10, 11, 12],
                     [13, 14, 15, 16]],
                     [[1, 2, 3, 4],
                     [5, 6, 7, 8],
                     [9, 10, 11, 12],
                     [13, 14, 15, 16]]])
    binning_factor = 2
    expected_output = np.array([[[3.5, 5.5],
                                 [11.5, 13.5]],
                                 [[3.5, 5.5],
                                 [11.5, 13.5]]])
    result = rebin(data, binning_factor)
    np.testing.assert_array_almost_equal(result, expected_output)


def test_rebin_with_non_divisible_dimensions():
    # Test with a 2D array where dimensions are not divisible by binning factor
    data = np.array([[1, 2, 3],
                     [4, 5, 6],
                     [7, 8, 9]])
    binning_factor = 2
    with pytest.raises(ValueError):
        rebin(data, binning_factor)


def test_rebin_with_invalid_binning_factor():
    # Test with an invalid binning factor (e.g., 0 or negative)
    data = np.array([[1, 2],
                     [3, 4]])
    binning_factor = 0
    with pytest.raises(ValueError):
        rebin(data, binning_factor)


def test_rebin_with_empty_array():
    # Test with an empty array
    data = np.array([[]])
    binning_factor = 2
    with pytest.raises(ValueError):
        rebin(data, binning_factor)


def test_rebin_with_large_binning_factor():
    # Test with a binning factor larger than the array dimensions
    data = np.array([[1, 2],
                     [3, 4]])
    binning_factor = 3
    with pytest.raises(ValueError):
        rebin(data, binning_factor)

# crop
def test_crop_with_valid_roi():
    # Test with a valid ROI
    data = np.array([[[1, 2, 3, 4],
                        [5, 6, 7, 8],
                        [9, 10, 11, 12],
                        [13, 14, 15, 16]]])
    roi = Roi(1, 1, 3, 3)  # Crop to a 2x2 region
    expected_output = np.array([[[6, 7],
                                    [10, 11]]])
    result = crop(data, roi)
    np.testing.assert_array_equal(result, expected_output)


def test_crop_with_roi_out_of_bounds():
    # Test with an ROI that goes out of bounds
    data = np.array([[[1, 2, 3],
                        [4, 5, 6],
                        [7, 8, 9]]])
    roi = Roi(1, 1, 4, 4)  # ROI exceeds array bounds
    with pytest.raises(IndexError):
        crop(data, roi)


def test_crop_with_empty_roi():
    # Test with an ROI that results in an empty crop
    data = np.array([[[1, 2, 3],
                        [4, 5, 6],
                        [7, 8, 9]]])
    roi = Roi(1, 1, 1, 1)  # ROI defines an empty region
    expected_output = np.array([[]]).reshape(1, 0, 0)
    result = crop(data, roi)
    np.testing.assert_array_equal(result, expected_output)


def test_crop_with_full_image_roi():
    # Test with an ROI that selects the entire image
    data = np.array([[[1, 2, 3],
                        [4, 5, 6],
                        [7, 8, 9]]])
    roi = Roi(0, 0, 3, 3)  # ROI covers the entire image
    expected_output = data
    result = crop(data, roi)
    np.testing.assert_array_equal(result, expected_output)


def test_crop_with_invalid_roi():
    # Test with an invalid ROI (e.g., negative coordinates)
    data = np.array([[[1, 2, 3],
                        [4, 5, 6],
                        [7, 8, 9]]])
    with pytest.raises(ValueError):
        roi = Roi(-1, -1, 2, 2)  # Negative coordinates
        crop(data, roi)
