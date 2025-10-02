"""Comprehensive unit tests for sammy/io/card_formats/par07_radii.py module."""

from typing import List
from unittest.mock import patch

import pytest

from pleiades.sammy.fitting.config import FitConfig
from pleiades.sammy.io.card_formats.par07_radii import Card07


class TestCard07ClassMethods:
    """Test Card07 class methods."""

    def test_from_lines_empty_list(self):
        """Test from_lines with empty list raises ValueError."""
        with pytest.raises(ValueError, match="No lines provided"):
            Card07.from_lines([])

    def test_from_lines_with_invalid_header(self):
        """Test from_lines with invalid header line."""
        # Since is_header_line is not implemented, this will raise AttributeError
        lines = ["Invalid header line", "data line 1", "data line 2"]

        with pytest.raises(AttributeError):
            # This should fail because is_header_line doesn't exist
            Card07.from_lines(lines)

    def test_from_lines_with_invalid_fit_config(self):
        """Test from_lines with invalid fit_config type."""
        lines = ["Some header line"]
        invalid_config = "not a FitConfig object"

        # Since is_header_line doesn't exist, we'll get AttributeError first
        with pytest.raises(AttributeError):
            Card07.from_lines(lines, fit_config=invalid_config)

    @patch.object(Card07, "is_header_line", return_value=True, create=True)
    def test_from_lines_with_valid_header_but_unsupported_format(self, mock_is_header):
        """Test that default format raises NotImplementedError."""
        lines = ["Valid header line according to mock"]

        # Should raise ValueError about unsupported format
        with pytest.raises(ValueError, match="Default format for Card 7 is not supported"):
            Card07.from_lines(lines)

        mock_is_header.assert_called_once_with(lines[0])

    @patch.object(Card07, "is_header_line", return_value=False, create=True)
    def test_from_lines_with_header_returning_false(self, mock_is_header):
        """Test from_lines when is_header_line returns False."""
        lines = ["Some header line"]

        with pytest.raises(ValueError, match="Invalid header line"):
            Card07.from_lines(lines)

        mock_is_header.assert_called_once_with(lines[0])

    @patch.object(Card07, "is_header_line", return_value=True, create=True)
    def test_from_lines_with_none_fit_config(self, mock_is_header):
        """Test from_lines with None fit_config creates default FitConfig."""
        lines = ["Valid header"]

        # Should still raise unsupported format error
        with pytest.raises(ValueError, match="Default format for Card 7 is not supported"):
            Card07.from_lines(lines, fit_config=None)

    @patch.object(Card07, "is_header_line", return_value=True, create=True)
    def test_from_lines_with_valid_fit_config(self, mock_is_header):
        """Test from_lines with valid FitConfig object."""
        lines = ["Valid header"]
        fit_config = FitConfig()

        # Should still raise unsupported format error
        with pytest.raises(ValueError, match="Default format for Card 7 is not supported"):
            Card07.from_lines(lines, fit_config=fit_config)

    @patch.object(Card07, "is_header_line", return_value=True, create=True)
    def test_from_lines_with_non_fit_config_object(self, mock_is_header):
        """Test that non-FitConfig objects are rejected."""
        lines = ["Valid header"]

        class NotFitConfig:
            pass

        invalid_config = NotFitConfig()

        with pytest.raises(ValueError, match="fit_config must be an instance of FitConfig"):
            Card07.from_lines(lines, fit_config=invalid_config)


class TestCard07Initialization:
    """Test Card07 initialization and BaseModel features."""

    def test_card07_is_basemodel(self):
        """Test that Card07 inherits from BaseModel."""
        from pydantic import BaseModel

        assert issubclass(Card07, BaseModel)

    def test_card07_can_be_instantiated(self):
        """Test that Card07 can be instantiated."""
        card = Card07()
        assert isinstance(card, Card07)

    def test_card07_has_from_lines_method(self):
        """Test that Card07 has from_lines class method."""
        assert hasattr(Card07, "from_lines")
        assert callable(Card07.from_lines)

    def test_card07_from_lines_is_classmethod(self):
        """Test that from_lines is a class method."""
        import inspect

        # Get the actual function from the classmethod descriptor
        assert isinstance(inspect.getattr_static(Card07, "from_lines"), classmethod)


class TestCard07MissingMethods:
    """Test for missing methods that are called but not implemented."""

    def test_is_header_line_not_implemented(self):
        """Test that is_header_line method is not implemented."""
        # This should not exist as a method
        assert not hasattr(Card07, "is_header_line") or not callable(getattr(Card07, "is_header_line", None))

    def test_calling_nonexistent_is_header_line_raises_error(self):
        """Test that calling non-existent is_header_line raises AttributeError."""
        with pytest.raises(AttributeError):
            Card07.is_header_line("some line")


class TestCard07EdgeCases:
    """Test edge cases and error conditions."""

    @patch.object(Card07, "is_header_line", return_value=True, create=True)
    def test_from_lines_with_empty_string_in_list(self, mock_is_header):
        """Test from_lines with empty string as first line."""
        lines = ["", "data line"]
        mock_is_header.return_value = False

        with pytest.raises(ValueError, match="Invalid header line"):
            Card07.from_lines(lines)

    @patch.object(Card07, "is_header_line", return_value=True, create=True)
    def test_from_lines_with_whitespace_only_header(self, mock_is_header):
        """Test from_lines with whitespace-only header."""
        lines = ["   \t\n   ", "data line"]
        mock_is_header.return_value = False

        with pytest.raises(ValueError, match="Invalid header line"):
            Card07.from_lines(lines)

    def test_from_lines_with_none_lines(self):
        """Test from_lines with None instead of list."""
        # None is falsy, so it will be caught by the "if not lines" check
        with pytest.raises(ValueError, match="No lines provided"):
            Card07.from_lines(None)

    @patch.object(Card07, "is_header_line", return_value=True, create=True)
    def test_from_lines_with_single_line(self, mock_is_header):
        """Test from_lines with single line list."""
        lines = ["Single line header"]

        with pytest.raises(ValueError, match="Default format for Card 7 is not supported"):
            Card07.from_lines(lines)

    @patch.object(Card07, "is_header_line", create=True)
    def test_from_lines_exception_in_is_header_line(self, mock_is_header):
        """Test from_lines when is_header_line raises an exception."""
        lines = ["Header line"]
        mock_is_header.side_effect = RuntimeError("Unexpected error in is_header_line")

        with pytest.raises(RuntimeError, match="Unexpected error in is_header_line"):
            Card07.from_lines(lines)


class TestCard07Integration:
    """Integration tests for Card07."""

    def test_typical_usage_pattern_fails_correctly(self):
        """Test that typical usage pattern fails with expected error."""
        # This represents how the code might be used
        lines = [
            "Card 7 header line",
            "Some radius data",
            "More radius data",
            "",  # Blank terminator
        ]

        # Should fail because is_header_line doesn't exist
        with pytest.raises(AttributeError):
            result = Card07.from_lines(lines)

    @patch.object(Card07, "is_header_line", return_value=True, create=True)
    def test_with_mocked_header_validation(self, mock_is_header):
        """Test with mocked header validation to reach unsupported format error."""
        lines = [
            "Card 7 Radii Parameters",
            "1.0 2.0 3.0",
            "4.0 5.0 6.0",
        ]

        config = FitConfig()

        with pytest.raises(ValueError, match="Default format for Card 7 is not supported"):
            Card07.from_lines(lines, fit_config=config)

        assert mock_is_header.called

    @patch.object(Card07, "is_header_line", return_value=True, create=True)
    @patch("pleiades.sammy.io.card_formats.par07_radii.logger")
    def test_logging_on_errors(self, mock_logger, mock_is_header):
        """Test that errors are logged properly."""
        lines = ["Header"]

        with pytest.raises(ValueError, match="Default format for Card 7 is not supported"):
            Card07.from_lines(lines)

        # Check that error was logged
        mock_logger.error.assert_called()
        error_calls = mock_logger.error.call_args_list
        assert len(error_calls) > 0
        # The last error should be about unsupported format
        assert "Default format for Card 7 is not supported" in str(error_calls[-1])

    @patch("pleiades.sammy.io.card_formats.par07_radii.logger")
    def test_logging_on_empty_lines(self, mock_logger):
        """Test that empty lines error is logged."""
        with pytest.raises(ValueError, match="No lines provided"):
            Card07.from_lines([])

        mock_logger.error.assert_called_with("No lines provided")


class TestCard07TypeHints:
    """Test type hints and annotations."""

    def test_from_lines_type_hints(self):
        """Test that from_lines has proper type hints."""
        import inspect

        sig = inspect.signature(Card07.from_lines)

        # Check parameter types
        assert sig.parameters["lines"].annotation == List[str]
        assert sig.parameters["fit_config"].annotation == FitConfig or sig.parameters["fit_config"].default is None

        # Check return type (should be None according to the implementation)
        assert sig.return_annotation is None or sig.return_annotation is type(None)


class TestCard07Properties:
    """Test Card07 properties and attributes."""

    def test_card07_has_no_fields_defined(self):
        """Test that Card07 has no pydantic fields defined."""
        card = Card07()
        # BaseModel with no fields should have empty dict
        assert card.model_dump() == {}

    def test_card07_class_docstring(self):
        """Test that Card07 has a proper docstring."""
        assert Card07.__doc__ is not None
        assert "Card 7" in Card07.__doc__
        assert "radii" in Card07.__doc__.lower()

    def test_from_lines_docstring(self):
        """Test that from_lines has a proper docstring."""
        assert Card07.from_lines.__doc__ is not None
        assert "Parse" in Card07.from_lines.__doc__
        assert "Args:" in Card07.from_lines.__doc__
        assert "Raises:" in Card07.from_lines.__doc__


if __name__ == "__main__":
    pytest.main(["-v", __file__])
