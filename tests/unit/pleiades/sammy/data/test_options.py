"""Comprehensive unit tests for sammy/data/options.py module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from pleiades.sammy.data.options import HISTOGRAM_BIN_RANGE, RESIDUAL_YLIM, DataTypeOptions, SammyData
from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions


class TestDataTypeOptions:
    """Test DataTypeOptions enum."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        assert DataTypeOptions.TRANSMISSION == "TRANSMISSION"
        assert DataTypeOptions.TOTAL_CROSS_SECTION == "TOTAL CROSS SECTION"
        assert DataTypeOptions.SCATTERING == "SCATTERING"
        assert DataTypeOptions.ELASTIC == "ELASTIC"
        assert DataTypeOptions.DIFFERENTIAL_ELASTIC == "DIFFERENTIAL ELASTIC"
        assert DataTypeOptions.DIFFERENTIAL_REACTION == "DIFFERENTIAL REACTION"
        assert DataTypeOptions.REACTION == "REACTION"
        assert DataTypeOptions.INELASTIC_SCATTERING == "INELASTIC SCATTERING"
        assert DataTypeOptions.FISSION == "FISSION"
        assert DataTypeOptions.CAPTURE == "CAPTURE"
        assert DataTypeOptions.SELF_INDICATION == "SELF INDICATION"
        assert DataTypeOptions.INTEGRAL == "INTEGRAL"
        assert DataTypeOptions.COMBINATION == "COMBINATION"

    def test_enum_is_string(self):
        """Test that enum values are strings."""
        assert isinstance(DataTypeOptions.TRANSMISSION.value, str)
        assert DataTypeOptions.TRANSMISSION == "TRANSMISSION"


class TestSammyDataInitialization:
    """Test SammyData initialization."""

    def test_sammy_data_defaults(self):
        """Test the default values of SammyData."""
        params = SammyData()

        assert params.data_file is None
        assert params.data_type == DataTypeOptions.TRANSMISSION
        assert params.data_format == "LST"
        assert params.energy_units == EnergyUnitOptions.eV
        assert params.cross_section_units == CrossSectionUnitOptions.barn
        assert params.data is None

    def test_sammy_data_custom_values(self):
        """Test custom values of SammyData."""
        params = SammyData(
            data_type=DataTypeOptions.CAPTURE,
            data_format="DAT",
            energy_units=EnergyUnitOptions.keV,
            cross_section_units=CrossSectionUnitOptions.millibarn,
        )

        assert params.data_type == DataTypeOptions.CAPTURE
        assert params.data_format == "DAT"
        assert params.energy_units == EnergyUnitOptions.keV
        assert params.cross_section_units == CrossSectionUnitOptions.millibarn

    def test_invalid_data_type(self):
        """Test invalid data type."""
        with pytest.raises(ValueError):
            SammyData(data_file=Path("invalid.dat"), data_type="INVALID_TYPE")

    @patch("pleiades.sammy.data.options.SammyData.load")
    def test_init_with_file_loads_automatically(self, mock_load):
        """Test that providing a file path triggers automatic loading."""
        test_path = Path("/test/file.lst")

        sammy_data = SammyData(data_file=test_path)

        assert sammy_data.data_file == test_path
        mock_load.assert_called_once()

    def test_column_names_defined(self):
        """Test that _all_column_names is properly defined."""
        sammy_data = SammyData()

        assert len(sammy_data._all_column_names) == 13
        assert sammy_data._all_column_names[0] == "Energy"
        assert "Experimental transmission (dimensionless)" in sammy_data._all_column_names
        assert "Final theoretical cross section as evaluated by SAMMY (barns)" in sammy_data._all_column_names


class TestSammyDataLoad:
    """Test SammyData load method."""

    def test_load_valid_csv(self):
        """Test loading a valid CSV file."""
        csv_content = """1.0 0.5 0.01 0.49 0.51 0.95 0.02 0.94 0.96
2.0 0.6 0.01 0.59 0.61 0.85 0.02 0.84 0.86
3.0 0.7 0.01 0.69 0.71 0.75 0.02 0.74 0.76"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".lst", delete=False) as tmp:
            tmp.write(csv_content)
            tmp_path = Path(tmp.name)

        try:
            sammy_data = SammyData(data_file=tmp_path, data_type=DataTypeOptions.TRANSMISSION)

            # Check data was loaded
            assert sammy_data.data is not None
            assert len(sammy_data.data) == 3
            assert sammy_data.data.shape[1] == 9

            # Check column names were assigned
            assert "Energy" in sammy_data.data.columns
            assert sammy_data.data["Energy"].tolist() == [1.0, 2.0, 3.0]

        finally:
            tmp_path.unlink()

    def test_load_with_comments(self):
        """Test loading CSV with comment lines."""
        csv_content = """# This is a comment
# Another comment
1.0 0.5 0.01 0.49 0.51 0.95 0.02 0.94 0.96
2.0 0.6 0.01 0.59 0.61 0.85 0.02 0.84 0.86"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".lst", delete=False) as tmp:
            tmp.write(csv_content)
            tmp_path = Path(tmp.name)

        try:
            sammy_data = SammyData(data_file=tmp_path, data_type=DataTypeOptions.TRANSMISSION)

            # Comments should be ignored
            assert len(sammy_data.data) == 2

        finally:
            tmp_path.unlink()

    def test_load_fewer_columns_raises_validation_error(self):
        """Test loading CSV with fewer columns raises validation error for transmission data."""
        csv_content = """1.0 0.5 0.01
2.0 0.6 0.01
3.0 0.7 0.01"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".lst", delete=False) as tmp:
            tmp.write(csv_content)
            tmp_path = Path(tmp.name)

        try:
            sammy_data = SammyData()  # Default is TRANSMISSION type
            sammy_data.data_file = tmp_path

            # Should raise validation error for missing transmission columns
            with pytest.raises(ValueError, match="Missing required transmission column"):
                sammy_data.load()

        finally:
            tmp_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file."""
        sammy_data = SammyData()
        sammy_data.data_file = Path("/nonexistent/file.lst")

        with pytest.raises(FileNotFoundError):
            sammy_data.load()


class TestValidateColumns:
    """Test validate_columns method."""

    def test_validate_transmission_data_valid(self):
        """Test validation of valid transmission data."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 2.0],
                "Experimental transmission (dimensionless)": [0.9, 0.8],
                "Absolute uncertainty in experimental transmission": [0.01, 0.01],
                "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)": [0.89, 0.79],
                "Final theoretical transmission as evaluated by SAMMY (dimensionless)": [0.91, 0.81],
            }
        )

        sammy_data = SammyData(data_type=DataTypeOptions.TRANSMISSION)
        sammy_data.data = data

        # Should not raise
        sammy_data.validate_columns()

    def test_validate_transmission_data_missing_column(self):
        """Test validation fails for transmission data missing required column."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 2.0],
                "Experimental transmission (dimensionless)": [0.9, 0.8],
                "Absolute uncertainty in experimental transmission": [0.01, 0.01],
                "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)": [0.89, 0.79],
            }
        )

        sammy_data = SammyData(data_type=DataTypeOptions.TRANSMISSION)
        sammy_data.data = data

        with pytest.raises(ValueError, match="Missing required transmission column"):
            sammy_data.validate_columns()

    def test_validate_cross_section_data_valid(self):
        """Test validation of valid cross-section data."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 2.0],
                "Experimental cross section (barns)": [10.0, 20.0],
                "Absolute uncertainty in experimental cross section": [0.5, 0.6],
                "Zeroth-order theoretical cross section as evaluated by SAMMY (barns)": [9.5, 19.5],
                "Final theoretical cross section as evaluated by SAMMY (barns)": [10.1, 20.1],
            }
        )

        sammy_data = SammyData(data_type=DataTypeOptions.TOTAL_CROSS_SECTION)
        sammy_data.data = data

        # Should not raise
        sammy_data.validate_columns()

    def test_validate_cross_section_with_transmission_columns_fails(self):
        """Test validation fails if cross-section data has transmission columns."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 2.0],
                "Experimental cross section (barns)": [10.0, 20.0],
                "Absolute uncertainty in experimental cross section": [0.5, 0.6],
                "Zeroth-order theoretical cross section as evaluated by SAMMY (barns)": [9.5, 19.5],
                "Final theoretical cross section as evaluated by SAMMY (barns)": [10.1, 20.1],
                "Experimental transmission (dimensionless)": [0.9, 0.8],  # Should not be here
            }
        )

        sammy_data = SammyData(data_type=DataTypeOptions.TOTAL_CROSS_SECTION)
        sammy_data.data = data

        with pytest.raises(ValueError, match="Unexpected transmission column"):
            sammy_data.validate_columns()

    def test_validate_scattering_data(self):
        """Test validation for SCATTERING data type."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 2.0],
                "Experimental cross section (barns)": [10.0, 20.0],
                "Absolute uncertainty in experimental cross section": [0.5, 0.6],
                "Zeroth-order theoretical cross section as evaluated by SAMMY (barns)": [9.5, 19.5],
                "Final theoretical cross section as evaluated by SAMMY (barns)": [10.1, 20.1],
            }
        )

        sammy_data = SammyData(data_type=DataTypeOptions.SCATTERING)
        sammy_data.data = data

        # Should not raise
        sammy_data.validate_columns()


class TestPlotMethods:
    """Test plotting methods."""

    @patch("matplotlib.pyplot.show")
    def test_plot_transmission_basic(self, mock_show):
        """Test basic transmission plotting."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 2.0, 3.0],
                "Experimental transmission (dimensionless)": [0.9, 0.8, 0.7],
                "Absolute uncertainty in experimental transmission": [0.01, 0.01, 0.01],
                "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)": [0.89, 0.79, 0.69],
                "Final theoretical transmission as evaluated by SAMMY (dimensionless)": [0.91, 0.81, 0.71],
            }
        )

        sammy_data = SammyData()
        sammy_data.data = data

        result = sammy_data.plot_transmission(show=True)

        assert result is None
        mock_show.assert_called_once()
        plt.close("all")

    def test_plot_transmission_returns_figure_when_show_false(self):
        """Test that plot returns figure object when show=False."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 2.0, 3.0],
                "Experimental transmission (dimensionless)": [0.9, 0.8, 0.7],
                "Final theoretical transmission as evaluated by SAMMY (dimensionless)": [0.91, 0.81, 0.71],
            }
        )

        sammy_data = SammyData()
        sammy_data.data = data

        fig = sammy_data.plot_transmission(show=False)

        assert fig is not None
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    @patch("matplotlib.pyplot.show")
    def test_plot_transmission_with_residuals(self, mock_show):
        """Test transmission plotting with residuals."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 2.0, 3.0],
                "Experimental transmission (dimensionless)": [0.9, 0.8, 0.7],
                "Absolute uncertainty in experimental transmission": [0.01, 0.01, 0.01],
                "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)": [0.89, 0.79, 0.69],
                "Final theoretical transmission as evaluated by SAMMY (dimensionless)": [0.91, 0.81, 0.71],
            }
        )

        sammy_data = SammyData()
        sammy_data.data = data

        sammy_data.plot_transmission(show_diff=True, show=True)

        mock_show.assert_called_once()
        plt.close("all")

    def test_plot_transmission_with_custom_parameters(self):
        """Test transmission plotting with custom parameters."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 10.0, 100.0],
                "Experimental transmission (dimensionless)": [0.9, 0.8, 0.7],
                "Final theoretical transmission as evaluated by SAMMY (dimensionless)": [0.91, 0.81, 0.71],
            }
        )

        sammy_data = SammyData()
        sammy_data.data = data

        fig = sammy_data.plot_transmission(
            show_diff=False,
            figsize=(10, 8),
            title="Test Plot",
            xscale="log",
            yscale="linear",
            data_color="blue",
            final_color="red",
            show=False,
        )

        assert fig is not None
        assert fig.get_size_inches()[0] == 10
        assert fig.get_size_inches()[1] == 8
        plt.close(fig)

    def test_plot_transmission_no_data_raises(self):
        """Test that plotting without data raises ValueError."""
        sammy_data = SammyData()

        with pytest.raises(ValueError, match="No data loaded to plot"):
            sammy_data.plot_transmission()

    @patch("matplotlib.pyplot.show")
    def test_plot_cross_section_basic(self, mock_show):
        """Test basic cross-section plotting."""
        data = pd.DataFrame(
            {
                "Energy": [1.0, 2.0, 3.0],
                "Experimental cross section (barns)": [10.0, 20.0, 30.0],
                "Final theoretical cross section as evaluated by SAMMY (barns)": [10.1, 20.1, 30.1],
            }
        )

        sammy_data = SammyData()
        sammy_data.data = data

        sammy_data.plot_cross_section()

        mock_show.assert_called_once()
        plt.close("all")

    def test_plot_cross_section_no_data_raises(self):
        """Test that plotting cross-section without data raises ValueError."""
        sammy_data = SammyData()

        with pytest.raises(ValueError, match="No data loaded to plot"):
            sammy_data.plot_cross_section()


class TestProperties:
    """Test property accessors."""

    def test_energy_property(self):
        """Test energy property accessor."""
        data = pd.DataFrame({"Energy": [1.0, 2.0, 3.0], "Other": [4.0, 5.0, 6.0]})

        sammy_data = SammyData()
        sammy_data.data = data

        energy = sammy_data.energy
        assert energy.tolist() == [1.0, 2.0, 3.0]

    def test_experimental_cross_section_property(self):
        """Test experimental_cross_section property."""
        data = pd.DataFrame({"Energy": [1.0, 2.0], "Experimental cross section (barns)": [10.0, 20.0]})

        sammy_data = SammyData()
        sammy_data.data = data

        cross_section = sammy_data.experimental_cross_section
        assert cross_section.tolist() == [10.0, 20.0]

    def test_theoretical_cross_section_property(self):
        """Test theoretical_cross_section property."""
        data = pd.DataFrame(
            {"Energy": [1.0, 2.0], "Final theoretical cross section as evaluated by SAMMY (barns)": [10.1, 20.1]}
        )

        sammy_data = SammyData()
        sammy_data.data = data

        cross_section = sammy_data.theoretical_cross_section
        assert cross_section.tolist() == [10.1, 20.1]

    def test_experimental_transmission_property(self):
        """Test experimental_transmission property."""
        data = pd.DataFrame({"Energy": [1.0, 2.0], "Experimental transmission (dimensionless)": [0.9, 0.8]})

        sammy_data = SammyData()
        sammy_data.data = data

        transmission = sammy_data.experimental_transmission
        assert transmission.tolist() == [0.9, 0.8]

    def test_theoretical_transmission_property(self):
        """Test theoretical_transmission property."""
        data = pd.DataFrame(
            {"Energy": [1.0, 2.0], "Final theoretical transmission as evaluated by SAMMY (dimensionless)": [0.91, 0.81]}
        )

        sammy_data = SammyData()
        sammy_data.data = data

        transmission = sammy_data.theoretical_transmission
        assert transmission.tolist() == [0.91, 0.81]

    def test_property_returns_none_for_missing_column(self):
        """Test that properties return None for missing columns."""
        data = pd.DataFrame({"Energy": [1.0, 2.0]})

        sammy_data = SammyData()
        sammy_data.data = data

        assert sammy_data.experimental_cross_section is None
        assert sammy_data.theoretical_transmission is None


class TestIntegrationScenarios:
    """Test complete workflows."""

    def test_full_workflow_transmission_data(self):
        """Test complete workflow with transmission data."""
        # Column order follows _all_column_names:
        # Energy, Exp_Cross, Unc_Cross, Zero_Cross, Final_Cross, Exp_Trans, Unc_Trans, Zero_Trans, Final_Trans
        csv_content = """# Column order follows SAMMY standard
1.0 0.0 0.0 0.0 0.0 0.95 0.01 0.94 0.96
2.0 0.0 0.0 0.0 0.0 0.85 0.02 0.84 0.86
3.0 0.0 0.0 0.0 0.0 0.75 0.02 0.74 0.76
4.0 0.0 0.0 0.0 0.0 0.65 0.03 0.64 0.66"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".lst", delete=False) as tmp:
            tmp.write(csv_content)
            tmp_path = Path(tmp.name)

        try:
            # Load and validate
            sammy_data = SammyData(data_file=tmp_path, data_type=DataTypeOptions.TRANSMISSION)

            # Check data loaded correctly
            assert len(sammy_data.data) == 4
            assert sammy_data.energy.tolist() == [1.0, 2.0, 3.0, 4.0]
            assert sammy_data.experimental_transmission.tolist() == [0.95, 0.85, 0.75, 0.65]

            # Test plotting doesn't crash
            fig = sammy_data.plot_transmission(show=False, show_diff=True)
            assert fig is not None
            plt.close(fig)

        finally:
            tmp_path.unlink()

    def test_constants_defined(self):
        """Test that module constants are properly defined."""
        assert RESIDUAL_YLIM == (-1, 1)
        assert HISTOGRAM_BIN_RANGE == (-1, 1, 0.01)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        sammy_data = SammyData()
        sammy_data.data = pd.DataFrame()

        # Properties should handle empty DataFrame
        assert sammy_data.energy is None
        assert sammy_data.experimental_transmission is None

    def test_validation_with_none_data(self):
        """Test validation with None data."""
        sammy_data = SammyData()

        # Should handle None data gracefully
        with pytest.raises(AttributeError):
            sammy_data.validate_columns()

    def test_plot_with_minimal_data(self):
        """Test plotting with minimal required columns."""
        data = pd.DataFrame(
            {
                "Energy": [1.0],
                "Experimental transmission (dimensionless)": [0.9],
                "Final theoretical transmission as evaluated by SAMMY (dimensionless)": [0.91],
            }
        )

        sammy_data = SammyData()
        sammy_data.data = data

        # Should not crash with single data point
        fig = sammy_data.plot_transmission(show=False)
        assert fig is not None
        plt.close(fig)

    @patch("pandas.read_csv")
    def test_load_with_io_error(self, mock_read_csv):
        """Test handling of I/O errors during load."""
        mock_read_csv.side_effect = IOError("Cannot read file")

        sammy_data = SammyData()
        sammy_data.data_file = Path("/test/file.lst")

        with pytest.raises(IOError, match="Cannot read file"):
            sammy_data.load()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
