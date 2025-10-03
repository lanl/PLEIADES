from enum import Enum
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from pleiades.utils.logger import loguru_logger
from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions

logger = loguru_logger.bind(name=__name__)

# Plot constants
RESIDUAL_YLIM = (-1, 1)  # Y-axis limits for residual plots
HISTOGRAM_BIN_RANGE = (-1, 1, 0.01)  # Range and step for histogram bins


class DataTypeOptions(str, Enum):
    TRANSMISSION = "TRANSMISSION"
    TOTAL_CROSS_SECTION = "TOTAL CROSS SECTION"
    SCATTERING = "SCATTERING"
    ELASTIC = "ELASTIC"
    DIFFERENTIAL_ELASTIC = "DIFFERENTIAL ELASTIC"
    DIFFERENTIAL_REACTION = "DIFFERENTIAL REACTION"
    REACTION = "REACTION"
    INELASTIC_SCATTERING = "INELASTIC SCATTERING"
    FISSION = "FISSION"
    CAPTURE = "CAPTURE"
    SELF_INDICATION = "SELF INDICATION"
    INTEGRAL = "INTEGRAL"
    COMBINATION = "COMBINATION"


class SammyData(BaseModel):
    """
    Container for LST data, loaded from a SAMMY .LST file using pandas.

    Attributes:
        data_file: Path to the LST file.
        data: Pandas DataFrame holding the LST data.
    """

    model_config = {"arbitrary_types_allowed": True}

    data_file: Optional[Path] = Field(description="Path to the file containing the data", default=None)
    data_type: DataTypeOptions = Field(description="Type of the data", default=DataTypeOptions.TRANSMISSION)
    data_format: str = Field(description="Format of the data", default="LST")
    energy_units: EnergyUnitOptions = Field(description="Units of energy", default=EnergyUnitOptions.eV)
    cross_section_units: CrossSectionUnitOptions = Field(
        description="Units of cross-section", default=CrossSectionUnitOptions.barn
    )
    data: Optional[pd.DataFrame] = Field(default=None, exclude=True)

    # All possible columns in a SAMMY.LPT file (always in this order)
    _all_column_names = [
        "Energy",
        "Experimental cross section (barns)",
        "Absolute uncertainty in experimental cross section (barns)",
        "Zeroth-order theoretical cross section as evaluated by SAMMY (barns)",
        "Final theoretical cross section as evaluated by SAMMY (barns)",
        "Experimental transmission (dimensionless)",
        "Absolute uncertainty in experimental transmission",
        "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)",
        "Final theoretical transmission as evaluated by SAMMY (dimensionless)",
        "Theoretical uncertainty on Zeroth-order theoretical cross section or transmission",
        "Theoretical uncertainty on Final theoretical cross section or transmission",
        "Adjusted energy initially",
        "Adjusted energy finally",
    ]

    def model_post_init(self, __context):
        if self.data_file is not None:
            self.load()

    def load(self):
        """Load the LST file into a pandas DataFrame and validate columns."""
        self.data = pd.read_csv(self.data_file, sep=r"\s+", header=None, comment="#")
        n_cols = self.data.shape[1]
        self.data.columns = self._all_column_names[:n_cols]
        self.validate_columns()

    def validate_columns(self):
        """Validate columns based on data_type."""
        transmission_cols = [
            "Experimental transmission (dimensionless)",
            "Absolute uncertainty in experimental transmission",
            "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)",
            "Final theoretical transmission as evaluated by SAMMY (dimensionless)",
        ]
        cross_section_cols = [
            "Experimental cross section (barns)",
            "Absolute uncertainty in experimental cross section",
            "Zeroth-order theoretical cross section as evaluated by SAMMY (barns)",
            "Final theoretical cross section as evaluated by SAMMY (barns)",
        ]

        if self.data_type == DataTypeOptions.TRANSMISSION:
            # Transmission data must have all transmission columns
            for col in transmission_cols:
                if col not in self.data.columns:
                    raise ValueError(f"Missing required transmission column: {col}")

        elif self.data_type == DataTypeOptions.TOTAL_CROSS_SECTION or self.data_type == DataTypeOptions.SCATTERING:
            # Cross-section data must have all cross-section columns
            for col in cross_section_cols:
                if col not in self.data.columns:
                    raise ValueError(f"Missing required cross-section column: {col}")
            # Should not have transmission columns
            for col in transmission_cols:
                if col in self.data.columns:
                    raise ValueError(f"Unexpected transmission column for cross-section data: {col}")

    def plot_transmission(
        self,
        show_diff=False,
        plot_uncertainty=False,
        figsize=None,
        title=None,
        xscale="linear",
        yscale="linear",
        data_color="#433E3F",
        final_color="#ff6361",
        show=True,
    ):
        """
        Plot the transmission data and optionally the residuals.

        Args:
            show_diff (bool): If True, plot the residuals.
            plot_uncertainty (bool): (Unused, for compatibility)
            figsize (tuple): Figure size (width, height) in inches.
            title (str): Plot title.
            xscale (str): X-axis scale ('linear' or 'log').
            yscale (str): Y-axis scale ('linear' or 'log').
            data_color (str): Color for experimental data points.
            final_color (str): Color for fitted theoretical curve.
            show (bool): If True, display the plot. If False, return figure object.

        Returns:
            matplotlib.figure.Figure: The figure object if show=False, None otherwise.
        """
        if self.data is None:
            raise ValueError("No data loaded to plot.")

        data = self.data
        initial_color = "#003f5c"

        # Use provided figsize or default
        if figsize is None:
            figsize = (8, 6)

        # Column name mapping for compatibility
        col_exp = "Experimental transmission (dimensionless)"
        col_exp_unc = "Absolute uncertainty in experimental transmission"
        col_init = "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)"
        col_final = "Final theoretical transmission as evaluated by SAMMY (dimensionless)"

        if show_diff:
            fig, ax = plt.subplots(
                2,
                2,
                sharey=False,
                figsize=figsize,
                gridspec_kw={"width_ratios": [5, 1], "height_ratios": [5, 2]},
            )
            ax = np.ravel(ax)
        else:
            fig, ax = plt.subplots(figsize=figsize)
            ax = [ax]

        # Plot experimental transmission as scatter with error bars if available
        yerr = data[col_exp_unc] if col_exp_unc in data.columns else None
        data.plot.scatter(
            x="Energy",
            y=col_exp,
            yerr=yerr,
            ax=ax[0],
            zorder=-1,
            color=data_color,
            alpha=0.25,
            s=10,
        )
        # Plot final theoretical transmission
        if col_final in data.columns:
            data.plot(
                x="Energy",
                y=col_final,
                ax=ax[0],
                alpha=1.0,
                color=final_color,
                lw=1,
            )
        # Apply scale settings first
        ax[0].set_xscale(xscale)
        ax[0].set_yscale(yscale)

        # Then remove x-axis labels and ticks (for show_diff layout)
        ax[0].set_xlabel("")
        ax[0].set_xticks([])
        ax[0].legend(["data", "final fit"])
        ax[0].set_ylabel("transmission")

        # Apply title if provided
        if title:
            ax[0].set_title(title)

        # Determine y-axis limits
        max_y = data[col_exp].max()
        min_y = data[col_exp].min()
        ax[0].set_ylim(min_y, max_y)

        if show_diff:
            ax[1].spines["right"].set_visible(False)
            ax[1].spines["top"].set_visible(False)
            ax[1].spines["bottom"].set_visible(False)
            ax[1].spines["left"].set_visible(False)
            ax[1].set_xticks([])
            ax[1].set_yticks([], [])

            # Compute residuals
            if col_init in data.columns:
                data["residual_initial"] = data[col_init] - data[col_exp]
            data["residual_final"] = data[col_final] - data[col_exp]

            # Plot residuals (final fit)
            data.plot.scatter(
                x="Energy",
                y="residual_final",
                yerr=yerr,
                lw=0,
                ylim=(-10, 10),
                color=final_color,
                ax=ax[2],
                alpha=0.5,
                legend=False,
            )
            ax[2].set_ylabel("residuals\n(fit-data)/err [σ]")
            ax[2].set_xlabel("energy [eV]")
            ax[2].set_ylim(*RESIDUAL_YLIM)
            # Apply same x-scale to residual plot
            ax[2].set_xscale(xscale)

            # Plot histograms of residuals
            if "residual_initial" in data.columns:
                data.plot.hist(
                    y=["residual_initial"],
                    bins=np.arange(*HISTOGRAM_BIN_RANGE),
                    ax=ax[3],
                    orientation="horizontal",
                    legend=False,
                    alpha=0.8,
                    histtype="stepfilled",
                    color=initial_color,
                )
            data.plot.hist(
                y=["residual_final"],
                bins=np.arange(-1, 1, 0.01),
                ax=ax[3],
                orientation="horizontal",
                legend=False,
                alpha=0.8,
                histtype="stepfilled",
                color=final_color,
            )
            ax[3].set_xlabel("")
            ax[3].set_xticks([], [])
            ax[3].set_yticks([], [])
            ax[3].spines["right"].set_visible(False)
            ax[3].spines["top"].set_visible(False)
            ax[3].spines["bottom"].set_visible(False)
            ax[3].spines["left"].set_visible(False)

        plt.subplots_adjust(wspace=0.003, hspace=0.03)

        if show:
            plt.show()
            return None
        else:
            return fig

    def plot_cross_section(self, show_diff=False, plot_uncertainty=False):
        """Plot the cross-section data."""
        if self.data is not None:
            plt.figure(figsize=(10, 6))
            plt.plot(
                self.data["Energy"], self.data["Experimental cross section (barns)"], label="Experimental cross section"
            )
            plt.plot(
                self.data["Energy"],
                self.data["Final theoretical cross section as evaluated by SAMMY (barns)"],
                label="Final theoretical cross section",
            )
            plt.xlabel(f"Energy ({self.energy_units})")
            plt.ylabel(f"Cross section ({self.cross_section_units})")
            plt.title("Cross Section Data")
            plt.legend()
            plt.grid()
            plt.show()
        else:
            raise ValueError("No data loaded to plot.")

    @property
    def energy(self):
        return self.data.get("Energy")

    @property
    def experimental_cross_section(self):
        return self.data.get("Experimental cross section (barns)")

    @property
    def theoretical_cross_section(self):
        return self.data.get("Final theoretical cross section as evaluated by SAMMY (barns)")

    @property
    def experimental_transmission(self):
        return self.data.get("Experimental transmission (dimensionless)")

    @property
    def theoretical_transmission(self):
        return self.data.get("Final theoretical transmission as evaluated by SAMMY (dimensionless)")
