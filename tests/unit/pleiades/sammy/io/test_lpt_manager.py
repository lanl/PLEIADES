"""Comprehensive unit tests for sammy/io/lpt_manager.py module."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from pleiades.sammy.io.lpt_manager import (
    LptManager,
    parse_value_and_varied,
    split_lpt_values,
)
from pleiades.sammy.results.models import FitResults, RunResults
from pleiades.utils.helper import VaryFlag


class TestHelperFunctions:
    """Test helper functions."""

    def test_parse_value_and_varied_without_parenthesis(self):
        """Test parsing value without parenthesis (not varied)."""
        result = parse_value_and_varied("1.2345E+02")
        assert result == (123.45, False)

    def test_parse_value_and_varied_with_parenthesis(self):
        """Test parsing value with parenthesis (varied)."""
        result = parse_value_and_varied("1.2345E+02(  3)")
        assert result == (123.45, True)

    def test_parse_value_and_varied_negative_value(self):
        """Test parsing negative value."""
        result = parse_value_and_varied("-5.678E-03")
        assert result == (-0.005678, False)

    def test_parse_value_and_varied_with_spaces(self):
        """Test parsing value with spaces and parenthesis."""
        result = parse_value_and_varied("2.9660E+02 (  4)")
        assert result == (296.60, True)

    def test_parse_value_and_varied_invalid_format(self):
        """Test parsing invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Could not parse value"):
            parse_value_and_varied("not_a_number")

    def test_split_lpt_values_single_value(self):
        """Test splitting line with single value."""
        result = split_lpt_values("1.2345E+02")
        assert result == ["1.2345E+02"]

    def test_split_lpt_values_multiple_values(self):
        """Test splitting line with multiple values."""
        result = split_lpt_values("2.9660E+02(  4)  1.1592E-01(  5)")
        assert result == ["2.9660E+02(  4)", "1.1592E-01(  5)"]

    def test_split_lpt_values_mixed_formats(self):
        """Test splitting line with mixed formats."""
        result = split_lpt_values("3.0000E+02  4.5678E-01(  2)  -1.234E+00")
        assert result == ["3.0000E+02", "4.5678E-01(  2)", "-1.234E+00"]

    def test_split_lpt_values_empty_string(self):
        """Test splitting empty string returns empty list."""
        result = split_lpt_values("")
        assert result == []


class TestLptManagerInit:
    """Test LptManager initialization."""

    def test_init_empty(self):
        """Test initialization without parameters."""
        manager = LptManager()
        assert manager.run_results is not None
        assert isinstance(manager.run_results, RunResults)

    def test_init_with_run_results(self):
        """Test initialization with RunResults."""
        run_results = RunResults()
        manager = LptManager(run_results=run_results)
        assert manager.run_results is run_results

    @patch.object(LptManager, "process_lpt_file")
    def test_init_with_file_path(self, mock_process):
        """Test initialization with file path triggers processing."""
        manager = LptManager(file_path="test.lpt")
        mock_process.assert_called_once_with("test.lpt", manager.run_results)


class TestExtractIsotopeInfo:
    """Test extract_isotope_info method."""

    def test_extract_isotope_info_success(self):
        """Test successful extraction of isotope information."""
        manager = LptManager()
        nuclear_data = MagicMock()
        nuclear_data.isotopes = []

        lines = [
            "Some header",
            " Isotopic abundance and mass for each nuclide",
            " Nuclide    Abundance            Mass        Spin groups",
            "   1        1.000    (  3)      27.9769      1  2  3  4  5",
            "   2       4.6700E-02(  4)      28.9765      8  9 10",
            "",
            "Next section",
        ]

        result = manager.extract_isotope_info(lines, nuclear_data)

        assert result is True
        assert len(nuclear_data.isotopes) == 2

        # Check first isotope
        isotope1 = nuclear_data.isotopes[0]
        assert isotope1.abundance == 1.000
        assert isotope1.vary_abundance == VaryFlag.YES  # Has parenthesis
        assert len(isotope1.spin_groups) == 5

        # Check second isotope
        isotope2 = nuclear_data.isotopes[1]
        assert isotope2.abundance == 0.04670
        assert isotope2.vary_abundance == VaryFlag.YES
        assert len(isotope2.spin_groups) == 3

    def test_extract_isotope_info_no_data(self):
        """Test extraction when no isotope data present."""
        manager = LptManager()
        nuclear_data = MagicMock()
        nuclear_data.isotopes = []

        lines = ["No isotope information here", "Just random text"]

        result = manager.extract_isotope_info(lines, nuclear_data)

        assert result is False
        assert len(nuclear_data.isotopes) == 0

    def test_extract_isotope_info_without_parenthesis(self):
        """Test extraction when abundance has no parenthesis (not varied)."""
        manager = LptManager()
        nuclear_data = MagicMock()
        nuclear_data.isotopes = []

        lines = [
            " Isotopic abundance and mass for each nuclide",
            " Nuclide    Abundance            Mass        Spin groups",
            "   1        0.9223              27.9769      1  2",
        ]

        result = manager.extract_isotope_info(lines, nuclear_data)

        assert result is True
        assert len(nuclear_data.isotopes) == 1
        isotope = nuclear_data.isotopes[0]
        assert isotope.abundance == 0.9223
        assert isotope.vary_abundance == VaryFlag.NO  # No parenthesis


class TestExtractRadiusInfo:
    """Test extract_radius_info method."""

    def test_extract_radius_info_success(self):
        """Test successful extraction of radius information."""
        manager = LptManager()

        # Create mock isotopes with spin groups
        isotope1 = MagicMock()
        isotope1.spin_groups = [
            MagicMock(spin_group_number=1),
            MagicMock(spin_group_number=4),
            MagicMock(spin_group_number=5),
        ]
        isotope1.radius_parameters = None

        isotope2 = MagicMock()
        isotope2.spin_groups = [
            MagicMock(spin_group_number=2),
            MagicMock(spin_group_number=3),
        ]
        isotope2.radius_parameters = None

        nuclear_data = MagicMock()
        nuclear_data.isotopes = [isotope1, isotope2]

        lines = [
            "EFFECTIVE RADIUS    TRUE RADIUS  SPIN GROUP NUMBER FOR THESE RADII",
            "                                       # channel numbers",
            "    4.1364200        4.1364200       1 #  1  2  3",
            "                                     4 #  1  2  3",
            "                                     5 #  1  2  3",
            "    4.9437200        4.9437200       2 #  1  2  3",
            "                                     3 #  1  2",
            "",
            "Next section",
        ]

        result = manager.extract_radius_info(lines, nuclear_data)

        assert result is True

        # Check isotope1 has radius for spin groups 1, 4, 5
        assert len(isotope1.radius_parameters) == 1
        rad1 = isotope1.radius_parameters[0]
        assert rad1.effective_radius == 4.1364200
        assert rad1.true_radius == 4.1364200
        assert len(rad1.spin_groups) == 3  # Groups 1, 4, 5

        # Check isotope2 has radius for spin groups 2, 3
        assert len(isotope2.radius_parameters) == 1
        rad2 = isotope2.radius_parameters[0]
        assert rad2.effective_radius == 4.9437200
        assert rad2.true_radius == 4.9437200
        assert len(rad2.spin_groups) == 2  # Groups 2, 3

    def test_extract_radius_info_no_data(self):
        """Test extraction when no radius data present."""
        manager = LptManager()
        nuclear_data = MagicMock()
        nuclear_data.isotopes = []

        lines = ["No radius information here", "Just random text"]

        result = manager.extract_radius_info(lines, nuclear_data)

        assert result is False


class TestExtractBroadeningInfo:
    """Test extract_broadening_info method."""

    def test_extract_broadening_info_with_radius(self):
        """Test extraction with RADIUS field."""
        manager = LptManager()
        physics_data = MagicMock()
        physics_data.broadening_parameters = MagicMock()

        lines = [
            "  RADIUS         TEMPERATURE      THICKNESS",
            "  6.5000E+00(  1)  3.0000E+02       3.4716E-01(  2)",
            "",
            "    DELTA-L         DELTA-T-GAUS     DELTA-T-EXP",
            "  0.0000E+00       2.5200E-03       0.0000E+00",
        ]

        result = manager.extract_broadening_info(lines, physics_data)

        assert result is True
        assert physics_data.broadening_parameters.crfn == 6.5
        assert physics_data.broadening_parameters.temp == 300.0
        assert physics_data.broadening_parameters.thick == 0.34716
        assert physics_data.broadening_parameters.deltal == 0.0
        assert physics_data.broadening_parameters.deltag == 0.00252
        assert physics_data.broadening_parameters.deltae == 0.0

    def test_extract_broadening_info_without_radius(self):
        """Test extraction without RADIUS field."""
        manager = LptManager()
        physics_data = MagicMock()
        physics_data.broadening_parameters = MagicMock()

        lines = [
            "  TEMPERATURE      THICKNESS",
            "  3.0000E+02(  1)  3.4716E-01",
            "",
            "    DELTA-L         DELTA-T-GAUS     DELTA-T-EXP",
            "  1.0000E-03(  2)  2.5200E-03       5.0000E-03(  3)",
        ]

        result = manager.extract_broadening_info(lines, physics_data)

        assert result is True
        assert physics_data.broadening_parameters.temp == 300.0
        assert physics_data.broadening_parameters.thick == 0.34716
        assert physics_data.broadening_parameters.deltal == 0.001
        assert physics_data.broadening_parameters.deltag == 0.00252
        assert physics_data.broadening_parameters.deltae == 0.005

    def test_extract_broadening_info_no_data(self):
        """Test extraction when no broadening data present."""
        manager = LptManager()
        physics_data = MagicMock()
        physics_data.broadening_parameters = MagicMock()

        lines = ["No broadening information here"]

        result = manager.extract_broadening_info(lines, physics_data)

        assert result is False


class TestExtractNormalizationInfo:
    """Test extract_normalization_info method."""

    def test_extract_normalization_info_success(self):
        """Test successful extraction of normalization parameters."""
        manager = LptManager()
        physics_data = MagicMock()
        physics_data.normalization_parameters = MagicMock()

        lines = [
            "  NORMALIZATION    BCKG     BCKG*E    BCKG*SQRT(E)",
            "  9.5802E-01(  1)  1.0000E-01  2.0000E-02(  2)  3.0000E-03",
            "",
            "  BCKG*EXP        BCKG*EXP(-E)",
            "  4.0000E-04(  3)  5.0000E-05",
        ]

        result = manager.extract_normalization_info(lines, physics_data)

        assert result is True
        norm = physics_data.normalization_parameters
        assert norm.anorm == 0.95802
        assert norm.flag_anorm == VaryFlag.YES
        assert norm.backa == 0.1
        assert norm.flag_backa == VaryFlag.NO
        assert norm.backb == 0.02
        assert norm.flag_backb == VaryFlag.YES
        assert norm.backc == 0.003
        assert norm.flag_backc == VaryFlag.NO
        assert norm.backd == 0.0004
        assert norm.flag_backd == VaryFlag.YES
        assert norm.backf == 0.00005
        assert norm.flag_backf == VaryFlag.NO

    def test_extract_normalization_info_no_data(self):
        """Test extraction when no normalization data present."""
        manager = LptManager()
        physics_data = MagicMock()
        physics_data.normalization_parameters = MagicMock()

        lines = ["No normalization information here"]

        result = manager.extract_normalization_info(lines, physics_data)

        assert result is False


class TestExtractChiSquaredInfo:
    """Test extract_chi_squared_info method."""

    def test_extract_chi_squared_info_success(self):
        """Test successful extraction of chi-squared information."""
        manager = LptManager()
        chi_squared_results = MagicMock()

        lines = [
            "Some text",
            "CUSTOMARY CHI SQUARED =   188355.0",
            "More text",
            "CUSTOMARY CHI SQUARED DIVIDED BY NDAT =   11.9697",
            "Even more text",
            "Number of experimental data points =   15734",
        ]

        result = manager.extract_chi_squared_info(lines, chi_squared_results)

        assert result is True
        assert chi_squared_results.chi_squared == 188355.0
        assert chi_squared_results.reduced_chi_squared == 11.9697
        assert chi_squared_results.dof == 15734

    def test_extract_chi_squared_info_missing_data(self):
        """Test extraction when some chi-squared data missing."""
        manager = LptManager()
        chi_squared_results = MagicMock()

        lines = [
            "CUSTOMARY CHI SQUARED =   188355.0",
            # Missing reduced chi-squared and dof
        ]

        result = manager.extract_chi_squared_info(lines, chi_squared_results)

        assert result is False

    def test_extract_chi_squared_info_scientific_notation(self):
        """Test extraction with scientific notation."""
        manager = LptManager()
        chi_squared_results = MagicMock()

        lines = [
            "CUSTOMARY CHI SQUARED =   5.4752E+04",
            "CUSTOMARY CHI SQUARED DIVIDED BY NDAT =   3.4794E+00",
            "Number of experimental data points =   15734",
        ]

        result = manager.extract_chi_squared_info(lines, chi_squared_results)

        assert result is True
        assert chi_squared_results.chi_squared == 54752.0
        assert chi_squared_results.reduced_chi_squared == 3.4794
        assert chi_squared_results.dof == 15734


class TestExtractResultsFromString:
    """Test extract_results_from_string method."""

    @patch.object(LptManager, "extract_chi_squared_info", return_value=True)
    @patch.object(LptManager, "extract_normalization_info", return_value=True)
    @patch.object(LptManager, "extract_broadening_info", return_value=True)
    @patch.object(LptManager, "extract_radius_info", return_value=True)
    @patch.object(LptManager, "extract_isotope_info", return_value=True)
    def test_extract_results_from_string_all_found(
        self, mock_isotope, mock_radius, mock_broadening, mock_norm, mock_chi
    ):
        """Test extracting all results from string."""
        manager = LptManager()
        test_string = "Test LPT block content"

        result = manager.extract_results_from_string(test_string)

        assert isinstance(result, FitResults)
        mock_isotope.assert_called_once()
        mock_radius.assert_called_once()
        mock_broadening.assert_called_once()
        mock_norm.assert_called_once()
        mock_chi.assert_called_once()

    @patch.object(LptManager, "extract_chi_squared_info", return_value=False)
    @patch.object(LptManager, "extract_normalization_info", return_value=False)
    @patch.object(LptManager, "extract_broadening_info", return_value=False)
    @patch.object(LptManager, "extract_radius_info", return_value=False)
    @patch.object(LptManager, "extract_isotope_info", return_value=False)
    def test_extract_results_from_string_none_found(
        self, mock_isotope, mock_radius, mock_broadening, mock_norm, mock_chi
    ):
        """Test extracting when no results found logs info messages."""
        manager = LptManager()
        test_string = "Empty LPT block"

        with patch("pleiades.sammy.io.lpt_manager.logger") as mock_logger:
            result = manager.extract_results_from_string(test_string)

            assert isinstance(result, FitResults)
            assert mock_logger.info.call_count == 5  # One for each missing result type


class TestSplitLptBlocks:
    """Test split_lpt_blocks method."""

    def test_split_lpt_blocks_single_block(self):
        """Test splitting with single block."""
        manager = LptManager()
        content = """
Some header
***** INITIAL VALUES FOR PARAMETERS
Initial block content
More content
"""

        result = manager.split_lpt_blocks(content)

        assert len(result) == 1
        assert result[0][0] == "***** INITIAL VALUES FOR PARAMETERS"
        assert "Initial block content" in result[0][1]

    def test_split_lpt_blocks_multiple_blocks(self):
        """Test splitting with multiple blocks."""
        manager = LptManager()
        content = """
Header
***** INITIAL VALUES FOR PARAMETERS
Initial content
***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS
Intermediate content
***** NEW VALUES FOR RESONANCE PARAMETERS
New content
Footer
"""

        result = manager.split_lpt_blocks(content)

        assert len(result) == 3
        assert result[0][0] == "***** INITIAL VALUES FOR PARAMETERS"
        assert result[1][0] == "***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS"
        assert result[2][0] == "***** NEW VALUES FOR RESONANCE PARAMETERS"
        assert "Initial content" in result[0][1]
        assert "Intermediate content" in result[1][1]
        assert "New content" in result[2][1]

    def test_split_lpt_blocks_no_delimiters(self):
        """Test splitting content with no delimiters."""
        manager = LptManager()
        content = "Just some random content without delimiters"

        result = manager.split_lpt_blocks(content)

        assert len(result) == 0


class TestProcessLptFile:
    """Test process_lpt_file method."""

    def test_process_lpt_file_success(self):
        """Test successful processing of LPT file."""
        manager = LptManager()
        run_results = RunResults()

        test_content = """
***** INITIAL VALUES FOR PARAMETERS
Initial block
***** INTERMEDIATE VALUES FOR RESONANCE PARAMETERS
Intermediate block
***** NEW VALUES FOR RESONANCE PARAMETERS
New block
"""

        with patch("builtins.open", mock_open(read_data=test_content)):
            with patch.object(manager, "extract_results_from_string") as mock_extract:
                mock_extract.return_value = FitResults()

                result = manager.process_lpt_file("test.lpt", run_results)

                # Method doesn't return True, just doesn't return False
                assert result is not False
                assert mock_extract.call_count == 3

    def test_process_lpt_file_no_run_results(self):
        """Test processing fails when no RunResults provided."""
        manager = LptManager()

        with pytest.raises(ValueError, match="A RunResults object must be provided"):
            manager.process_lpt_file("test.lpt", None)

    def test_process_lpt_file_file_not_found(self):
        """Test processing when file not found."""
        manager = LptManager()
        run_results = RunResults()

        with patch("builtins.open", side_effect=FileNotFoundError()):
            with patch("pleiades.sammy.io.lpt_manager.logger") as mock_logger:
                result = manager.process_lpt_file("nonexistent.lpt", run_results)

                assert result is False
                mock_logger.error.assert_called()

    def test_process_lpt_file_generic_exception(self):
        """Test processing with generic exception."""
        manager = LptManager()
        run_results = RunResults()

        with patch("builtins.open", side_effect=Exception("Read error")):
            with patch("pleiades.sammy.io.lpt_manager.logger") as mock_logger:
                result = manager.process_lpt_file("test.lpt", run_results)

                assert result is False
                mock_logger.error.assert_called()


class TestIntegrationWithRealFile:
    """Integration tests using real LPT file samples."""

    def test_process_real_lpt_file(self):
        """Test processing a real LPT file if available."""
        # Use the test data file if it exists
        test_file = Path("tests/data/ex012/answers/ex012aa.lpt")

        if test_file.exists():
            manager = LptManager()
            run_results = RunResults()

            result = manager.process_lpt_file(str(test_file), run_results)

            assert result is not False  # Method returns None on success, False on failure
            assert len(run_results.fit_results) > 0

            # Check that some data was extracted
            first_result = run_results.fit_results[0]
            assert first_result.nuclear_data is not None
            assert first_result.physics_data is not None
            assert first_result.chi_squared_results is not None
        else:
            pytest.skip("Test LPT file not available")

    def test_extract_from_real_content(self):
        """Test extraction from real LPT content snippet."""
        manager = LptManager()

        # Real content from SAMMY LPT file
        real_content = """
 Isotopic abundance and mass for each nuclide --
 Nuclide    Abundance            Mass        Spin groups
    1        1.000    (  3)      27.9769      1  2  3  4  5  6  7
    2       4.6700E-02(  4)      28.9765      8  9 10 11 12 13 14 15 16 17

EFFECTIVE RADIUS    "TRUE" RADIUS  SPIN GROUP NUMBER FOR THESE RADII
                                       # channel numbers
    4.1364200        4.1364200       1 #  1  2  3
                                     2 #  1  2  3

  TEMPERATURE      THICKNESS
  3.0000E+02       3.4716E-01

    DELTA-L         DELTA-T-GAUS     DELTA-T-EXP
  0.0000E+00       2.5200E-03       0.0000E+00

CUSTOMARY CHI SQUARED =   188355.
CUSTOMARY CHI SQUARED DIVIDED BY NDAT =   11.9697
Number of experimental data points =   15734
"""

        result = manager.extract_results_from_string(real_content)

        # Check isotope extraction
        assert len(result.nuclear_data.isotopes) == 2
        assert result.nuclear_data.isotopes[0].abundance == 1.0
        assert result.nuclear_data.isotopes[1].abundance == 0.0467

        # Check broadening extraction
        assert result.physics_data.broadening_parameters.temp == 300.0
        assert result.physics_data.broadening_parameters.thick == 0.34716

        # Check chi-squared extraction
        assert result.chi_squared_results.chi_squared == 188355.0
        assert result.chi_squared_results.reduced_chi_squared == 11.9697
        assert result.chi_squared_results.dof == 15734


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_parse_value_with_extra_spaces(self):
        """Test parsing values with extra spaces."""
        # The function expects properly formatted scientific notation
        # Extra leading spaces cause the regex not to match
        assert parse_value_and_varied("1.234E+02  ") == (123.4, False)
        assert parse_value_and_varied("1.234E+02  (  5)") == (123.4, True)

    def test_empty_lines_in_extraction(self):
        """Test extraction methods handle empty lines gracefully."""
        manager = LptManager()
        nuclear_data = MagicMock()
        nuclear_data.isotopes = []

        lines = ["", "", " Isotopic abundance and mass for each nuclide", "", ""]

        result = manager.extract_isotope_info(lines, nuclear_data)
        assert result is False  # No actual data extracted

    def test_malformed_lines_in_extraction(self):
        """Test extraction handles malformed lines."""
        manager = LptManager()
        nuclear_data = MagicMock()
        nuclear_data.isotopes = []

        lines = [
            " Isotopic abundance and mass for each nuclide",
            " Nuclide    Abundance            Mass        Spin groups",
            "   1        INVALID              27.9769      1  2  3",  # Invalid abundance
        ]

        result = manager.extract_isotope_info(lines, nuclear_data)
        assert result is False  # Should not crash, just fail to extract
