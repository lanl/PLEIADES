#!/usr/bin/env python
"""Unit tests for Card Set 13 (Background Function Parameters) parsing.

Currently tests for NotImplementedError as functionality is not yet implemented.
"""

import pytest

from pleiades.sammy.parameters.background import BackgroundParameters, BackgroundType


class TestBackgroundParameters:
    """Test suite for Card Set 13 (Background) parameter parsing and formatting.

    Format from Table VI B.2:
    Card Set 13 contains various background function definitions.
    Currently unimplemented - tests verify NotImplementedError is raised.
    """

    @pytest.fixture
    def valid_const_lines(self):
        """Sample valid CONST background lines."""
        return [
            "BACKGround functions",
            "CONST 1 1.234E+00 2.345E-03 1.000E+01 1.000E+02",
        ]

    @pytest.fixture
    def valid_const_params(self):
        """Sample valid CONST background parameters."""
        return BackgroundParameters(
            type=BackgroundType.CONST,
        )

    def test_from_lines_not_implemented(self, valid_const_lines):
        """Test that from_lines raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            BackgroundParameters.from_lines(valid_const_lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_to_lines_not_implemented(self, valid_const_params):
        """Test that to_lines raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            valid_const_params.to_lines()
        assert "not yet implemented" in str(exc_info.value)

    @pytest.mark.parametrize("background_type", list(BackgroundType))
    def test_all_types_not_implemented(self, background_type):
        """Test NotImplementedError for all background types."""
        params = BackgroundParameters(type=background_type)
        with pytest.raises(NotImplementedError) as exc_info:
            params.to_lines()
        assert "not yet implemented" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
