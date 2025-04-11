#!/usr/bin/env python
"""Unit tests for Last Card parameter parsing."""

import pytest

from pleiades.sammy.parameters.last import LastParameters


class TestLastParameters:
    """Test suite for Last Card parameter parsing.

    These tests serve as a placeholder and specification for the
    needed implementation of Last Card parsing.
    """

    @pytest.fixture
    def valid_last_a_lines(self):
        """Sample valid Last A (COVAR) format lines."""
        return [
            "COVARiance matrix is in binary form in another file",
        ]

    @pytest.fixture
    def valid_last_b_lines(self):
        """Sample valid Last B (EXPLI) format lines."""
        return [
            "EXPLIcit uncertainties and correlations follow",
            # TODO: Add example format lines when implementing
        ]

    @pytest.fixture
    def valid_last_c_lines(self):
        """Sample valid Last C (RELAT) format lines."""
        return [
            "RELATive uncertainties follow",
            # TODO: Add example format lines when implementing
        ]

    @pytest.fixture
    def valid_last_d_lines(self):
        """Sample valid Last D (PRIOR) format lines."""
        return [
            "PRIOR uncertainties follow in key word format",
            # TODO: Add example format lines when implementing
        ]

    def test_unimplemented_parsing(self, valid_last_a_lines):
        """Verify NotImplementedError is raised for parsing."""
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            LastParameters.from_lines(valid_last_a_lines)

    def test_unimplemented_formatting(self):
        """Verify NotImplementedError is raised for formatting."""
        params = LastParameters()
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            params.to_lines()

    @pytest.mark.skip(reason="Awaiting implementation")
    def test_last_a_parsing(self, valid_last_a_lines):
        """Test parsing of Last A (COVAR) format."""
        _ = LastParameters.from_lines(valid_last_a_lines)
        # TODO: Add assertions when implementing

    @pytest.mark.skip(reason="Awaiting implementation")
    def test_last_b_parsing(self, valid_last_b_lines):
        """Test parsing of Last B (EXPLI) format."""
        _ = LastParameters.from_lines(valid_last_b_lines)
        # TODO: Add assertions when implementing

    @pytest.mark.skip(reason="Awaiting implementation")
    def test_last_c_parsing(self, valid_last_c_lines):
        """Test parsing of Last C (RELAT) format."""
        _ = LastParameters.from_lines(valid_last_c_lines)
        # TODO: Add assertions when implementing

    @pytest.mark.skip(reason="Awaiting implementation")
    def test_last_d_parsing(self, valid_last_d_lines):
        """Test parsing of Last D (PRIOR) format."""
        _ = LastParameters.from_lines(valid_last_d_lines)
        # TODO: Add assertions when implementing

    @pytest.mark.skip(reason="Awaiting implementation")
    def test_last_a_exclusive(self, valid_last_a_lines, valid_last_b_lines):
        """Test that Last A cannot be combined with other formats."""
        combined_lines = valid_last_a_lines + valid_last_b_lines
        with pytest.raises(ValueError, match="Last A cannot be combined"):
            LastParameters.from_lines(combined_lines)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
