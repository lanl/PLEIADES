#!/usr/bin/env python
"""Unit tests for Card Set 16 (User-Defined Resolution Function) parsing."""

import pytest

from pleiades.utils.helper import VaryFlag
from pleiades.sammy.parameters.user_resolution import UserResolutionParameters


class TestUserResolutionParameters:
    """Test suite for USER-Defined resolution function parameter parsing."""

    @pytest.fixture
    def valid_header_line(self):
        """Sample valid header line."""
        return "USER-Defined resolution function"

    @pytest.fixture
    def valid_burst_line(self):
        """Sample valid BURST parameter line."""
        return "BURST 1    1.234E+00 2.345E-03"
        #       |     |    |         |
        #       |     |    |         21-30: Uncertainty
        #       |     |    11-20: Burst width
        #       |     7: Flag
        #       1-5: "BURST"

    @pytest.fixture
    def valid_channel_line(self):
        """Sample valid CHANN parameter line."""
        return "CHANN 1    1.234E+03 2.345E+00 3.456E-03"
        #       |     |    |         |         |
        #       |     |    |         |         31-40: Uncertainty
        #       |     |    |         21-30: Channel width
        #       |     |    11-20: Energy
        #       |     7: Flag
        #       1-5: "CHANN"

    @pytest.fixture
    def valid_file_line(self):
        """Sample valid FILE parameter line."""
        return "FILE=resolution_data.txt"
        #       |    |
        #       |    6-75: Filename
        #       1-5: "FILE="

    def test_parse_header_only(self, valid_header_line):
        """Test parsing of minimal case with only header line."""
        params = UserResolutionParameters.from_lines([valid_header_line])
        assert params.type == "USER"
        assert params.burst_width is None
        assert params.burst_uncertainty is None
        assert params.burst_flag == VaryFlag.NO
        assert params.channel_energies == []
        assert params.channel_widths == []
        assert params.channel_uncertainties == []
        assert params.channel_flags == []
        assert params.filenames == []

    def test_parse_invalid_header(self):
        """Test parsing with invalid header line."""
        with pytest.raises(ValueError, match="Invalid header"):
            UserResolutionParameters.from_lines(["WRONG resolution function"])

    def test_parse_burst_line(self, valid_header_line, valid_burst_line):
        """Test parsing of BURST parameter line."""
        params = UserResolutionParameters.from_lines([valid_header_line, valid_burst_line])

        # Check burst parameters
        assert params.burst_width == pytest.approx(1.234)
        assert params.burst_uncertainty == pytest.approx(2.345e-3)
        assert params.burst_flag == VaryFlag.YES

        # Verify other parameters are empty
        assert params.channel_energies == []
        assert params.filenames == []

    def test_burst_line_formatting(self):
        """Test formatting of BURST parameters."""
        params = UserResolutionParameters(burst_width=1.234, burst_uncertainty=2.345e-3, burst_flag=VaryFlag.YES)

        lines = params.to_lines()
        assert len(lines) == 3
        assert lines[0] == "USER-Defined resolution function"

        # Check burst line format
        burst_line = lines[1]
        assert burst_line.startswith("BURST")
        assert len(burst_line) >= 30  # At least up to uncertainty field
        assert burst_line[6:7] == "1"  # Flag value

        # Parse the formatted line to verify values
        parsed = UserResolutionParameters.from_lines(lines)
        assert parsed.burst_width == pytest.approx(1.234)
        assert parsed.burst_uncertainty == pytest.approx(2.345e-3)
        assert parsed.burst_flag == VaryFlag.YES

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "BURST x    1.234E+00 2.345E-03",  # Invalid flag
            "BURST 1    invalid   2.345E-03",  # Invalid width
            "BURST",  # Incomplete line
            "BURTS 1    1.234E+00 2.345E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_burst_line(self, valid_header_line, invalid_line):
        """Test parsing of invalid BURST parameter lines."""
        with pytest.raises(ValueError):
            UserResolutionParameters.from_lines([valid_header_line, invalid_line])

    def test_parse_single_channel_line(self, valid_header_line, valid_channel_line):
        """Test parsing of single CHANN parameter line."""
        params = UserResolutionParameters.from_lines([valid_header_line, valid_channel_line])

        # Check channel parameters
        assert len(params.channel_energies) == 1
        assert len(params.channel_widths) == 1
        assert len(params.channel_uncertainties) == 1
        assert len(params.channel_flags) == 1

        assert params.channel_energies[0] == pytest.approx(1.234e3)
        assert params.channel_widths[0] == pytest.approx(2.345)
        assert params.channel_uncertainties[0] == pytest.approx(3.456e-3)
        assert params.channel_flags[0] == VaryFlag.YES

    def test_parse_multiple_channel_lines(self, valid_header_line):
        """Test parsing of multiple CHANN parameter lines."""
        lines = [
            valid_header_line,
            "CHANN 1    1.234E+03 2.345E+00 3.456E-03",
            "CHANN 0    4.567E+03 5.678E+00 6.789E-03",
            "CHANN 3    7.890E+03 8.901E+00 9.012E-03",
        ]

        params = UserResolutionParameters.from_lines(lines)

        # Check all channel parameters are parsed
        assert len(params.channel_energies) == 3
        assert len(params.channel_widths) == 3
        assert len(params.channel_uncertainties) == 3
        assert len(params.channel_flags) == 3

        # Check first channel
        assert params.channel_energies[0] == pytest.approx(1.234e3)
        assert params.channel_widths[0] == pytest.approx(2.345)
        assert params.channel_uncertainties[0] == pytest.approx(3.456e-3)
        assert params.channel_flags[0] == VaryFlag.YES

        # Check second channel
        assert params.channel_energies[1] == pytest.approx(4.567e3)
        assert params.channel_widths[1] == pytest.approx(5.678)
        assert params.channel_uncertainties[1] == pytest.approx(6.789e-3)
        assert params.channel_flags[1] == VaryFlag.NO

        # Check third channel
        assert params.channel_energies[2] == pytest.approx(7.890e3)
        assert params.channel_widths[2] == pytest.approx(8.901)
        assert params.channel_uncertainties[2] == pytest.approx(9.012e-3)
        assert params.channel_flags[2] == VaryFlag.PUP

    def test_channel_line_formatting(self):
        """Test formatting of CHANN parameters."""
        params = UserResolutionParameters(
            channel_energies=[1.234e3, 4.567e3],
            channel_widths=[2.345, 5.678],
            channel_uncertainties=[3.456e-3, 6.789e-3],
            channel_flags=[VaryFlag.YES, VaryFlag.NO],
        )

        lines = params.to_lines()
        assert len(lines) == 4  # Header + 2 channel lines + blank line
        assert lines[0] == "USER-Defined resolution function"

        # Check first channel line
        assert lines[1].startswith("CHANN")
        assert lines[1][6:7] == "1"  # Flag value

        # Parse the formatted lines to verify values
        parsed = UserResolutionParameters.from_lines(lines)
        assert len(parsed.channel_energies) == 2
        assert parsed.channel_energies[0] == pytest.approx(1.234e3)
        assert parsed.channel_widths[0] == pytest.approx(2.345)
        assert parsed.channel_uncertainties[0] == pytest.approx(3.456e-3)
        assert parsed.channel_flags[0] == VaryFlag.YES

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "CHANN x    1.234E+03 2.345E+00 3.456E-03",  # Invalid flag
            "CHANN 1    invalid   2.345E+00 3.456E-03",  # Invalid energy
            "CHANN 1    1.234E+03 invalid   3.456E-03",  # Invalid width
            "CHANN",  # Incomplete line
            "CHANL 1    1.234E+03 2.345E+00 3.456E-03",  # Wrong identifier
        ],
    )
    def test_parse_invalid_channel_line(self, valid_header_line, invalid_line):
        """Test parsing of invalid CHANN parameter lines."""
        with pytest.raises(ValueError):
            UserResolutionParameters.from_lines([valid_header_line, invalid_line])

    def test_parse_single_file_line(self, valid_header_line, valid_file_line):
        """Test parsing of single FILE parameter line."""
        params = UserResolutionParameters.from_lines([valid_header_line, valid_file_line])

        # Check file parameters
        assert len(params.filenames) == 1
        assert params.filenames[0] == "resolution_data.txt"

    def test_parse_multiple_file_lines(self, valid_header_line):
        """Test parsing of multiple FILE parameter lines."""
        lines = [valid_header_line, "FILE=resolution_data1.txt", "FILE=resolution_data2.txt", "FILE=resolution_data3.txt"]

        params = UserResolutionParameters.from_lines(lines)

        # Check all files are parsed
        assert len(params.filenames) == 3
        assert params.filenames[0] == "resolution_data1.txt"
        assert params.filenames[1] == "resolution_data2.txt"
        assert params.filenames[2] == "resolution_data3.txt"

    def test_file_line_formatting(self):
        """Test formatting of FILE parameters."""
        params = UserResolutionParameters(filenames=["resolution_data1.txt", "resolution_data2.txt"])

        lines = params.to_lines()
        assert len(lines) == 4  # Header + 2 file lines + blank line
        assert lines[0] == "USER-Defined resolution function"

        # Check file lines
        assert lines[1] == "FILE=resolution_data1.txt"
        assert lines[2] == "FILE=resolution_data2.txt"

        # Parse the formatted lines to verify values
        parsed = UserResolutionParameters.from_lines(lines)
        assert len(parsed.filenames) == 2
        assert parsed.filenames[0] == "resolution_data1.txt"
        assert parsed.filenames[1] == "resolution_data2.txt"

    @pytest.mark.parametrize(
        "invalid_line",
        [
            "FILE",  # Incomplete line
            "FILE resolution_data.txt",  # Missing equals sign
            "FILES=resolution_data.txt",  # Wrong identifier
            "FILE=",  # Missing filename
        ],
    )
    def test_parse_invalid_file_line(self, valid_header_line, invalid_line):
        """Test parsing of invalid FILE parameter lines."""
        with pytest.raises(ValueError):
            UserResolutionParameters.from_lines([valid_header_line, invalid_line])

    def test_complete_parameter_set(self, valid_header_line, valid_burst_line, valid_channel_line, valid_file_line):
        """Test parsing of complete parameter set with all optional sections."""
        lines = [valid_header_line, valid_burst_line, valid_channel_line, valid_file_line]

        params = UserResolutionParameters.from_lines(lines)

        # Check burst parameters
        assert params.burst_width == pytest.approx(1.234)
        assert params.burst_uncertainty == pytest.approx(2.345e-3)
        assert params.burst_flag == VaryFlag.YES

        # Check channel parameters
        assert len(params.channel_energies) == 1
        assert params.channel_energies[0] == pytest.approx(1.234e3)
        assert params.channel_widths[0] == pytest.approx(2.345)
        assert params.channel_uncertainties[0] == pytest.approx(3.456e-3)
        assert params.channel_flags[0] == VaryFlag.YES

        # Check file parameters
        assert len(params.filenames) == 1
        assert params.filenames[0] == "resolution_data.txt"

    def test_blank_line_at_end(self):
        """Test that formatted output includes blank line at end per spec."""
        params = UserResolutionParameters(filenames=["test.dat"])

        lines = params.to_lines()
        assert len(lines) >= 2  # At least header, content, and blank line
        assert lines[-1] == ""  # Last line should be blank

    def test_mixed_section_order(self):
        """Test that sections can appear in any order."""
        lines = [
            "USER-Defined resolution function",
            "FILE=data1.txt",
            "CHANN 1    1.000E+03 2.000E+00 3.000E-03",
            "BURST 1    1.234E+00 2.345E-03",
            "CHANN 0    2.000E+03 3.000E+00 4.000E-03",
            "FILE=data2.txt",
            "",  # blank line
        ]

        params = UserResolutionParameters.from_lines(lines)

        # Verify all sections parsed correctly regardless of order
        assert len(params.channel_energies) == 2
        assert len(params.filenames) == 2
        assert params.burst_width is not None

        # Verify specific values
        assert params.channel_energies[0] == pytest.approx(1000.0)
        assert params.channel_energies[1] == pytest.approx(2000.0)
        assert params.filenames == ["data1.txt", "data2.txt"]
        assert params.burst_width == pytest.approx(1.234)

    def test_maximum_filename_length(self):
        """Test that filename field respects column limit."""
        # Generate filename that's too long (>70 characters)
        long_filename = "x" * 71

        with pytest.raises(ValueError, match="exceeds maximum length"):
            UserResolutionParameters.from_lines(["USER-Defined resolution function", f"FILE={long_filename}", ""])


if __name__ == "__main__":
    pytest.main(["-v", __file__])
