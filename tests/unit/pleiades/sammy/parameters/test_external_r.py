#!/usr/bin/env python
"""Unit tests for SAMMY external R-function parameters."""

import pytest

from pleiades.sammy.parameters.external_r import ExternalREntry, ExternalRFormat, ExternalRFunction, VaryFlag

# Sample test data
FORMAT3_LINES = [
    "EXTERnal R-function parameters follow",
    " 1 2 1.2340E+00 5.6780E+00 1.2300E-01 4.5600E-01 7.8900E-01  1 0 0 1 0",
    " 2 1 2.3450E+00 6.7890E+00 2.3400E-01 5.6700E-01 8.9000E-01  0 1 0 0 1",
    "",
]

FORMAT3A_LINES = [
    "R-EXTernal parameters follow",
    " 1210010001.2340E+005.6780E+001.2300E-014.5600E-017.8900E-018.9000E-019.0000E-01",
    " 2120100102.3450E+006.7890E+002.3400E-015.6700E-018.9000E-019.1000E-019.2000E-01",
    "",
]


# Test ExternalREntry
class TestExternalREntry:
    def test_format3_parsing(self):
        """Test parsing of Format 3 entries"""
        line = " 1 2 1.2340E+00 5.6780E+00 1.2300E-01 4.5600E-01 7.8900E-01  1 0 0 1 0"
        entry = ExternalREntry.from_str(line, ExternalRFormat.FORMAT_3)

        assert entry.spin_group == 1
        assert entry.channel == 2
        assert entry.E_down == pytest.approx(1.2340)
        assert entry.E_up == pytest.approx(5.6780)
        assert entry.R_con == pytest.approx(0.1230)
        assert entry.R_lin == pytest.approx(0.4560)
        assert entry.s_alpha == pytest.approx(0.7890)
        assert entry.vary_E_down == VaryFlag.YES
        assert entry.vary_E_up == VaryFlag.NO
        assert entry.vary_R_con == VaryFlag.NO
        assert entry.vary_R_lin == VaryFlag.YES
        assert entry.vary_s_alpha == VaryFlag.NO

    def test_format3a_parsing(self):
        """Test parsing of Format 3A entries"""
        line = " 1210010001.2340E+005.6780E+001.2300E-014.5600E-017.8900E-018.9000E-019.0000E-01"
        for i, char in enumerate(line):
            print(f"{i + 1:2d}: {char}")
        entry = ExternalREntry.from_str(line, ExternalRFormat.FORMAT_3A)

        assert entry.spin_group == 1
        assert entry.channel == 2
        assert entry.E_down == pytest.approx(1.2340)
        assert entry.E_up == pytest.approx(5.6780)
        assert entry.R_con == pytest.approx(0.1230)
        assert entry.R_lin == pytest.approx(0.4560)
        assert entry.s_con == pytest.approx(0.7890)
        assert entry.s_lin == pytest.approx(0.8900)
        assert entry.R_q == pytest.approx(0.9000)
        assert entry.vary_E_down == VaryFlag.YES
        assert entry.vary_E_up == VaryFlag.NO
        assert entry.vary_R_con == VaryFlag.NO
        assert entry.vary_R_lin == VaryFlag.YES
        assert entry.vary_s_con == VaryFlag.NO
        assert entry.vary_s_lin == VaryFlag.NO
        assert entry.vary_R_q == VaryFlag.NO

    def test_empty_line(self):
        """Test handling of empty lines"""
        with pytest.raises(ValueError, match="Empty line provided"):
            ExternalREntry.from_str("", ExternalRFormat.FORMAT_3)

    def test_negative_s_alpha(self):
        """Test validation of negative s_alpha value"""
        line = " 1 2 1.2340E+00 5.6780E+00 1.2300E-01 4.5600E-01 -7.8900E-01  1 0 0 1 0"
        with pytest.raises(ValueError, match=".*greater than or equal to 0.*"):
            ExternalREntry.from_str(line, ExternalRFormat.FORMAT_3)

    def test_format_specific_fields(self):
        """Test validation of format-specific fields"""
        # Test Format 3 with Format 3A fields
        with pytest.raises(ValueError, match="Format 3a specific fields should not be set for Format 3"):
            ExternalREntry(
                format_type=ExternalRFormat.FORMAT_3,
                spin_group=1,
                channel=2,
                E_down=1.234,
                E_up=5.678,
                R_con=0.123,
                R_lin=0.456,
                s_alpha=0.789,
                s_con=0.890,  # This should cause an error
            )

        # Test Format 3A with Format 3 fields
        with pytest.raises(ValueError, match="Format 3 specific fields should not be set for Format 3a"):
            ExternalREntry(
                format_type=ExternalRFormat.FORMAT_3A,
                spin_group=1,
                channel=2,
                E_down=1.234,
                E_up=5.678,
                R_con=0.123,
                R_lin=0.456,
                s_con=0.789,
                s_lin=0.890,
                R_q=0.901,
                s_alpha=0.789,  # This should cause an error
            )


# Test ExternalRFunction
class TestExternalRFunction:
    def test_format3_parsing(self):
        """Test parsing of complete Format 3 card set"""
        r_function = ExternalRFunction.from_lines(FORMAT3_LINES)
        assert r_function.format_type == ExternalRFormat.FORMAT_3
        assert len(r_function.entries) == 2

        # Test first entry
        entry1 = r_function.entries[0]
        assert entry1.spin_group == 1
        assert entry1.channel == 2

        # Test second entry
        entry2 = r_function.entries[1]
        assert entry2.spin_group == 2
        assert entry2.channel == 1

    def test_format3a_parsing(self):
        """Test parsing of complete Format 3A card set"""
        r_function = ExternalRFunction.from_lines(FORMAT3A_LINES)
        assert r_function.format_type == ExternalRFormat.FORMAT_3A
        assert len(r_function.entries) == 2

    def test_invalid_header(self):
        """Test handling of invalid header"""
        bad_lines = ["WRONG header line", " 1 2 1.2340E+00 5.6780E+00 1.2300E-01 4.5600E-01 7.8900E-01  1 0 0 1 0", ""]
        with pytest.raises(ValueError, match="Invalid header line"):
            ExternalRFunction.from_lines(bad_lines)

    def test_empty_lines(self):
        """Test handling of empty input"""
        with pytest.raises(ValueError, match="No lines provided"):
            ExternalRFunction.from_lines([])

    def test_roundtrip_format3(self):
        """Test that to_lines() output can be parsed back correctly for Format 3"""
        original = ExternalRFunction.from_lines(FORMAT3_LINES)
        roundtrip = ExternalRFunction.from_lines(original.to_lines())

        assert len(original.entries) == len(roundtrip.entries)
        for orig_entry, rt_entry in zip(original.entries, roundtrip.entries):
            assert orig_entry.spin_group == rt_entry.spin_group
            assert orig_entry.channel == rt_entry.channel
            assert orig_entry.E_down == pytest.approx(rt_entry.E_down)
            assert orig_entry.E_up == pytest.approx(rt_entry.E_up)
            assert orig_entry.R_con == pytest.approx(rt_entry.R_con)
            assert orig_entry.R_lin == pytest.approx(rt_entry.R_lin)
            assert orig_entry.s_alpha == pytest.approx(rt_entry.s_alpha)

    def test_roundtrip_format3a(self):
        """Test that to_lines() output can be parsed back correctly for Format 3A"""
        original = ExternalRFunction.from_lines(FORMAT3A_LINES)
        roundtrip = ExternalRFunction.from_lines(original.to_lines())

        assert len(original.entries) == len(roundtrip.entries)
        for orig_entry, rt_entry in zip(original.entries, roundtrip.entries):
            assert orig_entry.spin_group == rt_entry.spin_group
            assert orig_entry.channel == rt_entry.channel
            assert orig_entry.E_down == pytest.approx(rt_entry.E_down)
            assert orig_entry.E_up == pytest.approx(rt_entry.E_up)
            assert orig_entry.R_con == pytest.approx(rt_entry.R_con)
            assert orig_entry.R_lin == pytest.approx(rt_entry.R_lin)
            assert orig_entry.s_con == pytest.approx(rt_entry.s_con)
            assert orig_entry.s_lin == pytest.approx(rt_entry.s_lin)
            assert orig_entry.R_q == pytest.approx(rt_entry.R_q)

    def test_header_detection(self):
        """Test header line detection"""
        assert ExternalRFunction.is_header_line("EXTERnal R-function parameters follow") == ExternalRFormat.FORMAT_3
        assert ExternalRFunction.is_header_line("R-EXTernal parameters follow") == ExternalRFormat.FORMAT_3A
        assert ExternalRFunction.is_header_line("Invalid header") is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
