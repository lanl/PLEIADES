import numpy as np

from pleiades.utils.files import retrieve_number_of_frames_from_file_name, retrieve_time_bin_size_from_file_name


def test_produce_spectra_list_for_lanl():
    file_name = "image_m2M9997Ex512y512t1e6T20p1e6P100.tiff"
    number_of_frames = retrieve_number_of_frames_from_file_name(file_name)
    time_bin_size = retrieve_time_bin_size_from_file_name(file_name)

    assert number_of_frames == 20
    assert time_bin_size == 1e-6

    time_spectra = np.arange(0, number_of_frames * time_bin_size, time_bin_size)

    assert len(time_spectra) == number_of_frames
    assert time_spectra[0] == 0
    assert time_spectra[-1] == (number_of_frames - 1) * time_bin_size

    list_diff = np.diff(time_spectra)
    for _diff in list_diff:
        np.testing.assert_almost_equal(_diff, time_bin_size, decimal=6)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
