"""Comprehensive unit tests for sammy/parfile.py module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from pleiades.sammy.parameters import (
    BroadeningParameterCard,
    DataReductionCard,
    ExternalRFunction,
    IsotopeCard,
    NormalizationBackgroundCard,
    ORRESCard,
    ParamagneticParameters,
    RadiusCard,
    ResonanceCard,
    UnusedCorrelatedCard,
    UserResolutionParameters,
)
from pleiades.sammy.parfile import CardOrder, SammyParameterFile


class TestCardOrder:
    """Test the CardOrder enum functionality."""

    def test_card_order_values(self):
        """Test that all expected card order values exist."""
        assert hasattr(CardOrder, "RESONANCE")
        assert hasattr(CardOrder, "FUDGE")
        assert hasattr(CardOrder, "EXTERNAL_R")
        assert hasattr(CardOrder, "BROADENING")
        assert hasattr(CardOrder, "UNUSED_CORRELATED")
        assert hasattr(CardOrder, "NORMALIZATION")
        assert hasattr(CardOrder, "RADIUS")
        assert hasattr(CardOrder, "DATA_REDUCTION")
        assert hasattr(CardOrder, "ORRES")
        assert hasattr(CardOrder, "ISOTOPE")
        assert hasattr(CardOrder, "PARAMAGNETIC")
        assert hasattr(CardOrder, "USER_RESOLUTION")

    def test_get_field_name(self):
        """Test the get_field_name method for each card type."""
        assert CardOrder.get_field_name(CardOrder.RESONANCE) == "resonance"
        assert CardOrder.get_field_name(CardOrder.FUDGE) == "fudge"
        assert CardOrder.get_field_name(CardOrder.EXTERNAL_R) == "external_r"
        assert CardOrder.get_field_name(CardOrder.BROADENING) == "broadening"
        assert CardOrder.get_field_name(CardOrder.UNUSED_CORRELATED) == "unused_correlated"
        assert CardOrder.get_field_name(CardOrder.NORMALIZATION) == "normalization"
        assert CardOrder.get_field_name(CardOrder.RADIUS) == "radius"
        assert CardOrder.get_field_name(CardOrder.DATA_REDUCTION) == "data_reduction"
        assert CardOrder.get_field_name(CardOrder.ORRES) == "orres"
        assert CardOrder.get_field_name(CardOrder.ISOTOPE) == "isotope"
        assert CardOrder.get_field_name(CardOrder.PARAMAGNETIC) == "paramagnetic"
        assert CardOrder.get_field_name(CardOrder.USER_RESOLUTION) == "user_resolution"

    def test_card_order_enum_iteration(self):
        """Test that CardOrder can be iterated over."""
        card_types = list(CardOrder)
        assert len(card_types) == 12  # Should have 12 card types
        assert CardOrder.RESONANCE in card_types
        assert CardOrder.USER_RESOLUTION in card_types


class TestSammyParameterFile:
    """Test the SammyParameterFile class functionality."""

    def test_initialization_empty(self):
        """Test creating an empty parameter file."""
        param_file = SammyParameterFile()
        assert param_file.fudge is None
        assert param_file.resonance is None
        assert param_file.external_r is None
        assert param_file.broadening is None
        assert param_file.unused_correlated is None
        assert param_file.normalization is None
        assert param_file.radius is None
        assert param_file.data_reduction is None
        assert param_file.orres is None
        assert param_file.paramagnetic is None
        assert param_file.user_resolution is None
        assert param_file.isotope is None

    def test_initialization_with_fudge(self):
        """Test creating a parameter file with fudge factor."""
        param_file = SammyParameterFile(fudge=0.5)
        assert param_file.fudge == 0.5

    def test_fudge_validation(self):
        """Test that fudge factor is validated (0.0 <= fudge <= 1.0)."""
        # Valid values
        param_file = SammyParameterFile(fudge=0.0)
        assert param_file.fudge == 0.0

        param_file = SammyParameterFile(fudge=1.0)
        assert param_file.fudge == 1.0

        # Invalid values
        with pytest.raises(ValidationError):
            SammyParameterFile(fudge=-0.1)

        with pytest.raises(ValidationError):
            SammyParameterFile(fudge=1.1)

    def test_to_string_empty(self):
        """Test converting empty parameter file to string."""
        param_file = SammyParameterFile()
        result = param_file.to_string()
        assert result == ""

    def test_to_string_with_fudge(self):
        """Test converting parameter file with fudge factor to string."""
        param_file = SammyParameterFile(fudge=0.75)
        result = param_file.to_string()
        assert "0.7500" in result

    @patch.object(ResonanceCard, "to_lines")
    def test_to_string_with_resonance(self, mock_to_lines):
        """Test converting parameter file with resonance card to string."""
        mock_to_lines.return_value = ["RESONANCES are listed next", "1.0 2.0 3.0"]

        mock_resonance = MagicMock(spec=ResonanceCard)
        mock_resonance.to_lines = mock_to_lines

        param_file = SammyParameterFile(resonance=mock_resonance)
        result = param_file.to_string()

        assert "RESONANCES are listed next" in result
        assert "1.0 2.0 3.0" in result
        mock_to_lines.assert_called_once()

    def test_from_string_empty_content(self):
        """Test parsing empty content raises ValueError."""
        with pytest.raises(ValueError, match="Empty parameter file content"):
            SammyParameterFile.from_string("")

    def test_from_string_with_fudge_only(self):
        """Test parsing content with only fudge factor."""
        content = "0.5000\n"
        param_file = SammyParameterFile.from_string(content)
        assert param_file.fudge == 0.5
        assert param_file.resonance is None

    def test_from_string_invalid_fudge(self):
        """Test parsing invalid content raises ValueError."""
        # "not_a_number" has characters beyond position 11, so it's treated as resonance data
        # This should fail when trying to parse as resonance entry
        content = "not_a_number\n"
        with pytest.raises(ValueError, match="Failed to parse resonance table"):
            SammyParameterFile.from_string(content)

    @patch.object(ResonanceCard, "from_lines")
    def test_from_string_with_resonance(self, mock_from_lines):
        """Test parsing content with resonance entries."""
        mock_resonance = MagicMock(spec=ResonanceCard)
        mock_from_lines.return_value = mock_resonance

        content = "-3661600.00 158770.000 3698500.+3  0.0000               0 0 1 0   1\n"
        param_file = SammyParameterFile.from_string(content)

        assert param_file.resonance == mock_resonance
        mock_from_lines.assert_called_once()

    def test_from_string_unimplemented_card(self):
        """Test parsing content with unimplemented card type raises ValueError."""
        # MISCEllaneous is not in the header dictionary, so it won't be recognized as a header
        # and will be treated as resonance data, which will fail parsing
        content = "MISCEllaneous parameters follow\nsome data\n"
        with pytest.raises(ValueError):
            SammyParameterFile.from_string(content)

    def test_get_card_class_with_header(self):
        """Test the _get_card_class_with_header method."""
        # Test with a header that should match
        with patch.object(BroadeningParameterCard, "is_header_line", return_value=True):
            card_type, card_class = SammyParameterFile._get_card_class_with_header(
                "BROADening parameters may be varied"
            )
            assert card_type == CardOrder.BROADENING
            assert card_class == BroadeningParameterCard

        # Test with a header that doesn't match
        with patch.object(BroadeningParameterCard, "is_header_line", return_value=False):
            card_type, card_class = SammyParameterFile._get_card_class_with_header("Unknown header line")
            assert card_type is None
            assert card_class is None

    def test_get_card_class(self):
        """Test the _get_card_class method."""
        assert SammyParameterFile._get_card_class(CardOrder.RESONANCE) == ResonanceCard
        assert SammyParameterFile._get_card_class(CardOrder.EXTERNAL_R) == ExternalRFunction
        assert SammyParameterFile._get_card_class(CardOrder.BROADENING) == BroadeningParameterCard
        assert SammyParameterFile._get_card_class(CardOrder.UNUSED_CORRELATED) == UnusedCorrelatedCard
        assert SammyParameterFile._get_card_class(CardOrder.NORMALIZATION) == NormalizationBackgroundCard
        assert SammyParameterFile._get_card_class(CardOrder.RADIUS) == RadiusCard
        assert SammyParameterFile._get_card_class(CardOrder.DATA_REDUCTION) == DataReductionCard
        assert SammyParameterFile._get_card_class(CardOrder.ORRES) == ORRESCard
        assert SammyParameterFile._get_card_class(CardOrder.ISOTOPE) == IsotopeCard
        assert SammyParameterFile._get_card_class(CardOrder.PARAMAGNETIC) == ParamagneticParameters
        assert SammyParameterFile._get_card_class(CardOrder.USER_RESOLUTION) == UserResolutionParameters

    def test_parse_card_success(self):
        """Test successful card parsing."""
        with patch.object(ResonanceCard, "from_lines") as mock_from_lines:
            mock_resonance = MagicMock(spec=ResonanceCard)
            mock_from_lines.return_value = mock_resonance

            lines = ["test line 1", "test line 2"]
            result = SammyParameterFile._parse_card(CardOrder.RESONANCE, lines)

            assert result == mock_resonance
            mock_from_lines.assert_called_once_with(lines)

    def test_parse_card_no_parser(self):
        """Test parsing card with no parser raises ValueError."""
        # Create a mock CardOrder value that's not in the card map
        mock_card_type = MagicMock()
        mock_card_type.name = "UNKNOWN_CARD"

        with patch.object(SammyParameterFile, "_get_card_class", return_value=None):
            with pytest.raises(ValueError, match="No parser implemented"):
                SammyParameterFile._parse_card(mock_card_type, ["test"])

    def test_parse_card_parsing_error(self):
        """Test that parsing errors are caught and re-raised with context."""
        with patch.object(ResonanceCard, "from_lines", side_effect=Exception("Parse error")):
            with pytest.raises(ValueError, match="Failed to parse RESONANCE card"):
                SammyParameterFile._parse_card(CardOrder.RESONANCE, ["test"])

    def test_from_file_success(self):
        """Test reading parameter file from disk successfully."""
        content = "0.7500\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".par", delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = Path(tmp_file.name)

        try:
            param_file = SammyParameterFile.from_file(tmp_file_path)
            assert param_file.fudge == 0.75
        finally:
            tmp_file_path.unlink()

    def test_from_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        non_existent_path = Path("/path/that/does/not/exist.par")
        with pytest.raises(FileNotFoundError, match="Parameter file not found"):
            SammyParameterFile.from_file(non_existent_path)

    def test_from_file_unicode_error(self):
        """Test handling of files with invalid encoding."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".par", delete=False) as tmp_file:
            # Write invalid UTF-8 bytes
            tmp_file.write(b"\xff\xfe\xfd\xfc")
            tmp_file_path = Path(tmp_file.name)

        try:
            with pytest.raises(ValueError, match="invalid encoding"):
                SammyParameterFile.from_file(tmp_file_path)
        finally:
            tmp_file_path.unlink()

    def test_from_file_parse_error(self):
        """Test handling of files with invalid content."""
        content = "invalid_fudge_value\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".par", delete=False) as tmp_file:
            tmp_file.write(content)
            tmp_file_path = Path(tmp_file.name)

        try:
            with pytest.raises(ValueError, match="Failed to parse"):
                SammyParameterFile.from_file(tmp_file_path)
        finally:
            tmp_file_path.unlink()

    def test_to_file_success(self):
        """Test writing parameter file to disk successfully."""
        param_file = SammyParameterFile(fudge=0.25)

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test.par"
            param_file.to_file(file_path)

            assert file_path.exists()
            content = file_path.read_text()
            assert "0.2500" in content

    def test_to_file_creates_parent_directories(self):
        """Test that to_file creates parent directories if they don't exist."""
        param_file = SammyParameterFile(fudge=0.5)

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "nested" / "dirs" / "test.par"
            param_file.to_file(file_path)

            assert file_path.exists()
            assert file_path.parent.exists()

    def test_to_file_format_error(self):
        """Test handling of formatting errors during file writing."""
        param_file = SammyParameterFile()

        # Mock to_string at the class level to raise an exception
        with patch.object(SammyParameterFile, "to_string", side_effect=Exception("Format error")):
            with tempfile.TemporaryDirectory() as tmp_dir:
                file_path = Path(tmp_dir) / "test.par"
                with pytest.raises(ValueError, match="Failed to format parameter file content"):
                    param_file.to_file(file_path)

    def test_print_parameters_empty(self, capsys):
        """Test printing empty parameter file."""
        param_file = SammyParameterFile()
        param_file.print_parameters()

        captured = capsys.readouterr()
        assert "Sammy Parameter File Details:" in captured.out
        assert "No cards present in the parameter file." in captured.out

    def test_print_parameters_with_fudge(self, capsys):
        """Test printing parameter file with fudge factor."""
        param_file = SammyParameterFile(fudge=0.85)
        param_file.print_parameters()

        captured = capsys.readouterr()
        assert "Sammy Parameter File Details:" in captured.out
        assert "fudge:" in captured.out
        assert "0.85" in captured.out

    def test_print_parameters_with_mock_card(self, capsys):
        """Test printing parameter file with a mock card."""
        mock_card = MagicMock(spec=ResonanceCard)
        mock_card.to_lines = MagicMock(return_value=["Header line", "Data line"])
        mock_card.detect_format = MagicMock(return_value="TestFormat")

        param_file = SammyParameterFile(resonance=mock_card)
        param_file.print_parameters()

        captured = capsys.readouterr()
        assert "resonance:" in captured.out
        assert "Format: TestFormat" in captured.out
        assert "Header: Header line" in captured.out

    def test_print_parameters_without_format_detection(self, capsys):
        """Test printing parameter file with card that doesn't have format detection."""
        # Create a mock that passes Pydantic validation
        mock_card = MagicMock(spec=BroadeningParameterCard)
        # Remove the format detection attributes
        del mock_card.to_lines
        del mock_card.detect_format

        # Create the parameter file with the mock
        param_file = SammyParameterFile()
        # Manually set the broadening after creation to bypass validation
        object.__setattr__(param_file, "broadening", mock_card)

        param_file.print_parameters()

        captured = capsys.readouterr()
        assert "broadening:" in captured.out
        assert "No format detection available for this card." in captured.out

    def test_main_not_implemented(self):
        """Test that the main block exists but is not implemented."""
        # This test verifies the existence of the NotImplementedError in __main__
        # We can't actually run the main block without complex execution context manipulation
        import pleiades.sammy.parfile

        # Read the source code to verify the NotImplementedError exists
        with open(pleiades.sammy.parfile.__file__, "r") as f:
            source = f.read()

        # Check that the main block contains NotImplementedError
        assert 'if __name__ == "__main__"' in source
        assert "NotImplementedError" in source


class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""

    @patch.object(ResonanceCard, "from_lines")
    @patch.object(BroadeningParameterCard, "from_lines")
    @patch.object(NormalizationBackgroundCard, "from_lines")
    def test_complex_parameter_file(self, mock_norm_from_lines, mock_broad_from_lines, mock_res_from_lines):
        """Test parsing a complex parameter file with multiple cards."""
        # Setup mocks
        mock_resonance = MagicMock(spec=ResonanceCard)
        mock_broadening = MagicMock(spec=BroadeningParameterCard)
        mock_normalization = MagicMock(spec=NormalizationBackgroundCard)

        mock_res_from_lines.return_value = mock_resonance
        mock_broad_from_lines.return_value = mock_broadening
        mock_norm_from_lines.return_value = mock_normalization

        # Mock is_header_line for proper card detection
        with (
            patch.object(BroadeningParameterCard, "is_header_line") as mock_broad_header,
            patch.object(NormalizationBackgroundCard, "is_header_line") as mock_norm_header,
        ):

            def broad_header_check(line):
                return "BROADening" in line

            def norm_header_check(line):
                return "NORMAlization" in line

            mock_broad_header.side_effect = broad_header_check
            mock_norm_header.side_effect = norm_header_check

            content = """0.5000
-3661600.00 158770.000 3698500.+3  0.0000               0 0 1 0   1

BROADening parameters may be varied
1.0 2.0 3.0

NORMAlization and background
4.0 5.0 6.0
"""

            param_file = SammyParameterFile.from_string(content)

            assert param_file.fudge == 0.5
            assert param_file.resonance == mock_resonance
            assert param_file.broadening == mock_broadening
            assert param_file.normalization == mock_normalization

    def test_round_trip_conversion(self):
        """Test that a parameter file can be converted to string and back."""
        original = SammyParameterFile(fudge=0.333)

        # Convert to string
        content = original.to_string()

        # Parse back from string
        parsed = SammyParameterFile.from_string(content)

        # Compare - fudge should be close (accounting for formatting)
        assert abs(parsed.fudge - 0.333) < 0.0001

    def test_file_round_trip(self):
        """Test that a parameter file can be written to disk and read back."""
        original = SammyParameterFile(fudge=0.666)

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test.par"

            # Write to file
            original.to_file(file_path)

            # Read back from file
            loaded = SammyParameterFile.from_file(file_path)

            # Compare
            assert abs(loaded.fudge - 0.666) < 0.0001
