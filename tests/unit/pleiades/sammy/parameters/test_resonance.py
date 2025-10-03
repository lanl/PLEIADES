from unittest.mock import patch

import pytest

from pleiades.sammy.parameters.resonance import ResonanceEntry, UnsupportedFormatError, VaryFlag


def test_valid_resonance_entry():
    line = "-3.6616E+06 1.5877E+05 3.6985E+09                       0 0 1     1"
    entry = ResonanceEntry.from_str(line)

    assert entry.resonance_energy == pytest.approx(-3.6616e6)
    assert entry.capture_width == pytest.approx(1.5877e5)
    assert entry.channel1_width == pytest.approx(3.6985e9)
    assert entry.channel2_width is None
    assert entry.channel3_width is None
    assert entry.vary_energy == VaryFlag.NO
    assert entry.vary_capture_width == VaryFlag.NO
    assert entry.vary_channel1 == VaryFlag.YES
    assert entry.igroup == 1


def test_resonance_entry_to_str():
    entry = ResonanceEntry(
        resonance_energy=-3.6616e6,
        capture_width=1.5877e5,
        channel1_width=3.6985e9,
        vary_energy=VaryFlag.NO,
        vary_capture_width=VaryFlag.NO,
        vary_channel1=VaryFlag.YES,
        igroup=1,
    )
    formatted_line = entry.to_str()
    assert formatted_line.startswith("-3.6616E+06 1.5877E+05 3.6985E+09")
    assert "0 0 1" in formatted_line


def test_unsupported_format_error():
    line = "-3.6616E+06 1.5877E+05 3.6985E+09                       0 0 1     1    -1.234"
    with pytest.raises(UnsupportedFormatError, match="SORRY! While SAMMY allows multi-line resonance entries"):
        ResonanceEntry.from_str(line)


def test_malformed_format_error():
    line = "-3.6616E+06 1.5877E+05 3.6985E+09 -1.234"
    with pytest.raises(ValueError, match="Empty line provided|Field required"):
        ResonanceEntry.from_str(line)


def test_missing_fields():
    line = "        1.5877E+05 3.6985E+09                       0 0 1     1"
    with pytest.raises(ValueError, match="Field required"):
        ResonanceEntry.from_str(line)


def test_partial_vary_flags():
    line = "-3.6616E+06 1.5877E+05 3.6985E+09                       1 0 0     2"
    entry = ResonanceEntry.from_str(line)
    assert entry.vary_energy == VaryFlag.YES
    assert entry.vary_capture_width == VaryFlag.NO
    assert entry.vary_channel1 == VaryFlag.NO
    assert entry.igroup == 2


def test_full_channel_widths():
    line = "-3.6616E+06 1.5877E+05 3.6985E+09 1.1234E+05 5.4321E+04           0 0 1     1"
    entry = ResonanceEntry.from_str(line)
    assert entry.channel1_width == pytest.approx(3.6985e9)
    assert entry.channel2_width == pytest.approx(1.1234e5)
    assert entry.channel3_width == pytest.approx(5.4321e4)


def test_logger_error_for_x_value():
    line = "-3.6616E+06 1.5877E+05 3.6985E+09                       0 0 1     1    abc"
    with patch("pleiades.sammy.parameters.resonance.logger") as mock_logger:
        ResonanceEntry.from_str(line)
        mock_logger.error.assert_called_once_with("Failed to parse X value: could not convert string to float: 'abc'")


def test_to_str_with_partial_channels():
    entry = ResonanceEntry(
        resonance_energy=-3.6616e6,
        capture_width=1.5877e5,
        channel1_width=3.6985e9,
        channel2_width=None,
        channel3_width=None,
        vary_energy=VaryFlag.YES,
        igroup=3,
    )
    formatted_line = entry.to_str()
    assert "3.6985E+09" in formatted_line
    assert " " * 11 in formatted_line  # Blank for channel2 and channel3


if __name__ == "__main__":
    pytest.main(["-v", __file__])
