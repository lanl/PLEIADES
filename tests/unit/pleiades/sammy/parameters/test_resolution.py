#!/usr/bin/env python
"""Unit tests for Card Set 14 (Resolution Function Parameters) parsing.

Currently tests for NotImplementedError as functionality is not yet implemented.
"""

import pytest

from pleiades.sammy.parameters.resolution import (
    GEELResolutionParameters,
    GELINAResolutionParameters,
    NTOFResolutionParameters,
    ResolutionType,
    RPIResolutionParameters,
    UserResolutionParameters,
)


class TestResolutionParameters:
    """Test suite for Card Set 14 (Resolution) parameter parsing and formatting.

    Format from Table VI B.2:
    Card Set 14 supports multiple resolution function types each with their own
    multi-line parameter structure.
    Currently unimplemented - tests verify NotImplementedError is raised.
    """

    @pytest.fixture
    def valid_rpi_lines(self):
        """Sample valid RPI resolution lines."""
        return [
            "RPI Resolution",
            "BURST 1 1.234E+00 2.345E-03",
            "TAU   1 1 1 1 1 3.456E+00 4.567E+00 5.678E+00 6.789E+00 7.890E+00",
        ]

    @pytest.fixture
    def valid_geel_lines(self):
        """Sample valid GEEL resolution lines."""
        return [
            "GEEL resolution",
            "BURST 1 1.234E+00 2.345E-03",
        ]

    @pytest.fixture
    def valid_gelina_lines(self):
        """Sample valid GELINA resolution lines."""
        return [
            "GELINa resolution",
            "BURST 1 1.234E+00 2.345E-03",
        ]

    @pytest.fixture
    def valid_ntof_lines(self):
        """Sample valid NTOF resolution lines."""
        return [
            "NTOF resolution",
            "BURST 1 1.234E+00 2.345E-03",
        ]

    @pytest.fixture
    def valid_user_lines(self):
        """Sample valid user-defined resolution lines."""
        return [
            "USER-Defined resolution function",
            "FILE=resolution.dat",
        ]

    @pytest.fixture
    def valid_params_by_type(self):
        """Sample valid parameters for each resolution type."""
        return {
            ResolutionType.RPI: RPIResolutionParameters(),
            ResolutionType.GEEL: GEELResolutionParameters(),
            ResolutionType.GELINA: GELINAResolutionParameters(),
            ResolutionType.NTOF: NTOFResolutionParameters(),
            ResolutionType.USER: UserResolutionParameters(),
        }

    def test_rpi_not_implemented(self, valid_rpi_lines):
        """Test that RPI resolution parsing raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            RPIResolutionParameters.from_lines(valid_rpi_lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_geel_not_implemented(self, valid_geel_lines):
        """Test that GEEL resolution parsing raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            GEELResolutionParameters.from_lines(valid_geel_lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_gelina_not_implemented(self, valid_gelina_lines):
        """Test that GELINA resolution parsing raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            GELINAResolutionParameters.from_lines(valid_gelina_lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_ntof_not_implemented(self, valid_ntof_lines):
        """Test that NTOF resolution parsing raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            NTOFResolutionParameters.from_lines(valid_ntof_lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_user_not_implemented(self, valid_user_lines):
        """Test that user-defined resolution parsing raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            UserResolutionParameters.from_lines(valid_user_lines)
        assert "not yet implemented" in str(exc_info.value)

    def test_to_lines_not_implemented(self, valid_params_by_type):
        """Test that to_lines raises NotImplementedError for all types."""
        for params in valid_params_by_type.values():
            with pytest.raises(NotImplementedError) as exc_info:
                params.to_lines()
            assert "not yet implemented" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
