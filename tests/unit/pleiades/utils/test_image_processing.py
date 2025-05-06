import numpy as np
import pytest
from pleiades.utils.image_processing import rebin

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
    print(f"{result=}")
    print(f"{expected_output=}")
    np.testing.assert_array_almost_equal(result, expected_output)


# def test_rebin_with_non_divisible_dimensions():
#     # Test with a 2D array where dimensions are not divisible by binning factor
#     data = np.array([[1, 2, 3],
#                      [4, 5, 6],
#                      [7, 8, 9]])
#     binning_factor = 2
#     with pytest.raises(ValueError):
#         rebin(data, binning_factor)


# def test_rebin_with_invalid_binning_factor():
#     # Test with an invalid binning factor (e.g., 0 or negative)
#     data = np.array([[1, 2],
#                      [3, 4]])
#     binning_factor = 0
#     with pytest.raises(ValueError):
#         rebin(data, binning_factor)


# def test_rebin_with_empty_array():
#     # Test with an empty array
#     data = np.array([[]])
#     binning_factor = 2
#     with pytest.raises(ValueError):
#         rebin(data, binning_factor)


# def test_rebin_with_large_binning_factor():
#     # Test with a binning factor larger than the array dimensions
#     data = np.array([[1, 2],
#                      [3, 4]])
#     binning_factor = 3
#     with pytest.raises(ValueError):
#         rebin(data, binning_factor)