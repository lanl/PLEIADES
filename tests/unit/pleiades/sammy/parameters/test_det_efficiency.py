#!/usr/bin/env python
"""Unit tests for Card Set 15 (Detector Efficiency Parameters) parsing.

Currently tests for NotImplementedError as functionality is not yet implemented.
"""

import pytest

from pleiades.sammy.parameters.det_efficiency import DetectorEfficiencyParameters


@pytest.mark.skip(reason="Tests are disabled due to non-implementation.")
class TestDetectorEfficiencyParameters:
    """Test suite for Card Set 15 (Detector Efficiency) parameter parsing and formatting.

    Format from Table VI B.2:
    Card Set 15 defines detector efficiencies for spin groups:
    - Header line "DETECtor efficiencies"
    - One or more efficiency definitions
    - Each definition includes efficiency value, uncertainty, flag, and group numbers
    - Special handling for >29 groups (continued lines)
    - Special handling for >99 groups (wider group number fields)

    Currently unimplemented - tests verify NotImplementedError is raised.
    """

    def test_from_lines_basic_not_implemented(self):
        """Test that from_lines raises NotImplementedError for basic format."""
        lines = [
            "DETECtor efficiencies",
            "1.234E+00 2.345E-03  1  1  2  3",
        ]
        with pytest.raises(NotImplementedError) as exc_info:
            DetectorEfficiencyParameters.from_lines(lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_from_lines_multi_not_implemented(self):
        """Test that from_lines raises NotImplementedError for multiple groups."""
        lines = [
            "DETECtor efficiencies",
            "1.234E+00 2.345E-03  1  1  2  3",
            "3.456E+00 4.567E-03  0  4  5  6",
            "5.678E+00 6.789E-03  1  7  8  9",
        ]
        with pytest.raises(NotImplementedError) as exc_info:
            DetectorEfficiencyParameters.from_lines(lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_from_lines_continuation_not_implemented(self):
        """Test that from_lines raises NotImplementedError for continued groups."""
        lines = [
            "DETECtor efficiencies",
            "1.234E+00 2.345E-03  1  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15-1",
            "16 17 18 19 20 21 22 23 24 25 26 27 28 29 30",
        ]
        with pytest.raises(NotImplementedError) as exc_info:
            DetectorEfficiencyParameters.from_lines(lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_from_lines_wide_format_not_implemented(self):
        """Test that from_lines raises NotImplementedError for wide format."""
        lines = [
            "DETECtor efficiencies",
            "1.234E+00 2.345E-03  1    1    2    3    4    5-1",
            "   6    7    8    9   10",
        ]
        with pytest.raises(NotImplementedError) as exc_info:
            DetectorEfficiencyParameters.from_lines(lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_to_lines_not_implemented(self):
        """Test that to_lines raises NotImplementedError."""
        params = DetectorEfficiencyParameters()
        with pytest.raises(NotImplementedError) as exc_info:
            params.to_lines()
        assert "not yet implemented" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
