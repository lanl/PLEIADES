import matplotlib.pyplot as plt
import numpy as np

from pleiades.sammy.results.models import RunResults
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


def plot_transmission(
    results: RunResults,
    ax: plt.Axes = None,
    residual: bool = False,
    plot_uncertainty: bool = False,
    override_data_type: bool = False,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Plot the transmission data from the run results.

    Args:
        results (RunResults): The results object containing the data to plot.
        residual (bool): If True, plot the residuals. Default is False.
        plot_uncertainty (bool): If True, plot the uncertainty. Default is False.
        override_data_type (bool): If True, override the data type check. Default is False.
        axis (matplotlib.axes.Axes): The axes to plot on. If None, create a new figure and axes. Default is None.

    Returns:
        tuple: (fig, ax) matplotlib figure and axes objects.
    """
    if not results:
        raise ValueError("No results available to plot.")

    if residual:
        if ax is not None:
            # Check if ax is array-like and has 2 axes (for 2x1 grid)
            if not isinstance(ax, (list, tuple, np.ndarray)) or len(ax) != 2:
                raise ValueError(
                    "When plotting residuals, 'ax' must be an array-like of 2 axes objects (for a 2x1 grid)."
                )
            fig = ax[0].figure
            ax = np.ravel(ax)
        else:
            fig, ax = plt.subplots(
                2,
                1,
                sharex=True,
                figsize=(8, 6),
                gridspec_kw={"height_ratios": [3, 1]},
            )
            ax = np.ravel(ax)
            fig.subplots_adjust(hspace=0)
    else:
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))
        else:
            fig = ax.figure
        # Always make ax a list for consistency
        ax = [ax] if not isinstance(ax, (list, np.ndarray)) else ax

    data = results.data
    data_color = "#433E3F"
    initial_color = "#003f5c"
    final_color = "#ff6361"

    # Column name mapping for compatibility
    col_exp = "Experimental transmission (dimensionless)"
    col_exp_unc = "Absolute uncertainty in experimental transmission"
    col_init = "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)"
    col_final = "Final theoretical transmission as evaluated by SAMMY (dimensionless)"

    # Check if the uncertainty data column is empty
    yerr = results.data[col_exp_unc] if col_exp_unc in results.data.columns else None

    # Plot experimental data
    results.data.plot.scatter(x="Energy", y=col_exp, yerr=yerr, ax=ax[0], zorder=-1, color=data_color, alpha=0.25, s=10)

    # Plot final theoretical transmission
    if col_final in results.data.columns:
        results.data.plot(x="Energy", y=col_final, ax=ax[0], alpha=1.0, color=final_color, lw=1)

    ax[0].set_xlabel("Energy (eV)")
    ax[0].set_xticks([])
    ax[0].legend(["data", "final fit"])
    ax[0].set_ylabel("transmission")
    ax[0].tick_params(axis="x", which="both", bottom=False, top=False, labelbottom=False)

    # Determine y-axis limits
    max_y_limit = results.data[col_exp].max() * 1.1
    min_y_limit = results.data[col_exp].min() - 0.01
    ax[0].set_ylim(min_y_limit, max_y_limit)

    # If residual is requested, plot residuals in ax[1]
    if residual:
        # Compute residuals if possible
        if col_final in results.data.columns:
            residuals = results.data[col_exp] - results.data[col_final]

            # Plot residuals: x and y must be arrays of the same length
            ax[1].scatter(results.data["Energy"].values, residuals.values, color=data_color, alpha=0.5, s=10)
            ax[1].axhline(0, color="red", linestyle="--", linewidth=1)
            ax[1].set_ylabel("residuals\n(fit-data)/err [σ]")
            ax[1].set_xlabel("energy [eV]")
            ax[1].grid(True)

            # find the min and max of the residuals
            max_residual = residuals.max()
            min_residual = residuals.min()
            # set the y limits to be 10% above and below the min and max of the residuals
            ax[1].set_ylim(min_residual - 0.1 * abs(min_residual), max_residual + 0.1 * abs(max_residual))
        else:
            ax[1].text(0.5, 0.5, "No final fit for residuals", ha="center", va="center")
            ax[1].set_axis_off()

    return fig, ax
