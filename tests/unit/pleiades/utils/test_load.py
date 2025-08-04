import astropy.io.fits as fits
import numpy as np
import pytest
import tifffile


@pytest.fixture(scope="function")
def data_fixture(tmpdir):
    # dummy tiff image data
    data = np.ones((3, 3))

    # TIFF files
    # -- valid tiff with generic name, no metadata
    generic = tmpdir / "generic_dir"
    generic.mkdir()

    tiff_file_name = generic / "generic.tiff"
    tifffile.imwrite(str(tiff_file_name), data)

    # Fits files
    fits_file_name = generic / "generic.fits"
    hdu = fits.PrimaryHDU(data)
    hdu.writeto(str(fits_file_name))

    # return the tmp files
    return tiff_file_name, fits_file_name


def test_load_tiff(data_fixture):
    # Test loading tiff files
    generic_tiff, generic_fits = list(map(str, data_fixture))

    # Load the tiff files
    loaded_generic_tiff = tifffile.imread(str(generic_tiff))

    # Check the loaded data
    assert np.array_equal(loaded_generic_tiff, np.ones((3, 3)))


def test_load_fits(data_fixture):
    # Test loading fits files
    generic_tiff, generic_fits = data_fixture

    # Load the fits files
    loaded_generic_fits = fits.getdata(str(generic_fits))

    # Check the loaded data
    assert np.array_equal(loaded_generic_fits, np.ones((3, 3)))


if __name__ == "__main__":
    pytest.main(["-v", __file__])