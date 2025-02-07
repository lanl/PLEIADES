#!/usr/bin/env python
"""Unit tests for Card Set 16 (User-Defined Resolution Function) parsing."""

import pytest

from pleiades.sammy.parameters.helper import VaryFlag
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
        assert len(lines) == 2
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


if __name__ == "__main__":
    pytest.main(["-v", __file__])
