import pytest

from pleiades.sammy.alphanumerics.pcm_out import CovarianceMatrixOutputOptions


def test_default_option():
    """Test the default option."""
    options = CovarianceMatrixOutputOptions()
    assert options.write_correlations_into_compact_format is False
    assert options.put_correlations_into_compact_format is False
    assert options.write_covariances_into_compact_format is False
    assert options.put_covariances_into_compact_format is False
    assert options.put_covariance_matrix_into_endf_file_32 is False
    assert options.get_alphanumeric_commands() == []


def test_valid_option_with_single_boolean():
    """Test a valid option with a single boolean flag."""
    options = CovarianceMatrixOutputOptions(write_correlations_into_compact_format=True)
    assert options.write_correlations_into_compact_format is True
    assert options.put_correlations_into_compact_format is False
    assert options.write_covariances_into_compact_format is False
    assert options.put_covariances_into_compact_format is False
    assert options.put_covariance_matrix_into_endf_file_32 is False
    assert options.get_alphanumeric_commands() == ["WRITE CORRELATIONS INTO COMPACT FORMAT"]


def test_mutually_exclusive_options_1():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        CovarianceMatrixOutputOptions(write_correlations_into_compact_format=True, put_correlations_into_compact_format=True)


def test_mutually_exclusive_options_2():
    """Test mutually exclusive options."""
    with pytest.raises(ValueError):
        CovarianceMatrixOutputOptions(write_covariances_into_compact_format=True, put_covariances_into_compact_format=True)


def test_valid_combination_of_options_1():
    """Test a valid combination of options."""
    options = CovarianceMatrixOutputOptions(put_covariance_matrix_into_endf_file_32=True)
    assert options.write_correlations_into_compact_format is False
    assert options.put_correlations_into_compact_format is False
    assert options.write_covariances_into_compact_format is False
    assert options.put_covariances_into_compact_format is False
    assert options.put_covariance_matrix_into_endf_file_32 is True
    assert options.get_alphanumeric_commands() == ["PUT COVARIANCE MATRIX INTO ENDF FILE 32"]


def test_valid_combination_of_options_2():
    """Test a valid combination of options."""
    options = CovarianceMatrixOutputOptions(write_correlations_into_compact_format=True)
    assert options.write_correlations_into_compact_format is True
    assert options.put_correlations_into_compact_format is False
    assert options.write_covariances_into_compact_format is False
    assert options.put_covariances_into_compact_format is False
    assert options.put_covariance_matrix_into_endf_file_32 is False
    assert options.get_alphanumeric_commands() == ["WRITE CORRELATIONS INTO COMPACT FORMAT"]


def test_invalid_option():
    """Test an invalid option with multiple mutually exclusive flags."""
    with pytest.raises(ValueError):
        CovarianceMatrixOutputOptions(
            write_correlations_into_compact_format=True,
            put_correlations_into_compact_format=True,
            write_covariances_into_compact_format=True,
        )


def test_switching_options():
    """Test switching options."""
    options = CovarianceMatrixOutputOptions()
    assert options.get_alphanumeric_commands() == []

    options = CovarianceMatrixOutputOptions(write_correlations_into_compact_format=True)
    assert options.write_correlations_into_compact_format is True
    assert options.get_alphanumeric_commands() == ["WRITE CORRELATIONS INTO COMPACT FORMAT"]

    options = CovarianceMatrixOutputOptions(put_correlations_into_compact_format=True)
    assert options.put_correlations_into_compact_format is True
    assert options.get_alphanumeric_commands() == ["PUT CORRELATIONS INTO COMPACT FORMAT"]

    options = CovarianceMatrixOutputOptions(write_covariances_into_compact_format=True)
    assert options.write_covariances_into_compact_format is True
    assert options.get_alphanumeric_commands() == ["WRITE COVARIANCES INTO COMPACT FORMAT"]

    options = CovarianceMatrixOutputOptions(put_covariances_into_compact_format=True)
    assert options.put_covariances_into_compact_format is True
    assert options.get_alphanumeric_commands() == ["PUT COVARIANCES INTO COMPACT FORMAT"]

    options = CovarianceMatrixOutputOptions(put_covariance_matrix_into_endf_file_32=True)
    assert options.put_covariance_matrix_into_endf_file_32 is True
    assert options.get_alphanumeric_commands() == ["PUT COVARIANCE MATRIX INTO ENDF FILE 32"]


if __name__ == "__main__":
    pytest.main()
