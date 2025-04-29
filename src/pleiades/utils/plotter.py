import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def process_and_plot_lst_file(filename, residual=False, quantity="cross-section"):
    """
    Reads an LST file, determines the number of columns, processes the data based on plot_type, and plots the data.

    Args:
        filename (str): The path to the LST file.
        plot_type (str): Type of plot. Options: 'cross-section', 'Transmission'
    """
    # Define all possible column names
    all_column_names = [
        "Energy",
        "Experimental cross section",
        "Absolute uncertainty in experimental cross section",
        "Zeroth-order theoretical cross section",
        "Final theoretical cross section",
        "Experimental transmission",
        "Absolute uncertainty in experimental transmission",
        "Zeroth-order theoretical transmission",
        "Final theoretical transmission",
        "Theoretical uncertainty on section 4 or 8",
        "Theoretical uncertainty on section 5 or 9",
        "Adjusted energy initially",
        "Adjusted energy",
    ]

    # Read the file with pandas without column names
    data = pd.read_csv(filename, header=None, comment="#", sep=r"\s+")

    # Get the number of columns in the data
    num_columns = data.shape[1]

    # Assign only as many column names as there are columns in the data
    data.columns = all_column_names[:num_columns]

    if quantity == "cross-section" and num_columns >= 5:
        plot_cross_section(data, residual=residual)

    elif quantity == "transmission":
        plot_transmission(data, residual=residual)


def plot_cross_section(data, residual=False):
    """
    Plots the cross section data from the LST file.

    Args:
        data (DataFrame): The DataFrame containing the LST file data.
        residual (bool): If True, the difference between the theoretical and experimental cross sections will be plotted.
    """
    energy = data.iloc[:, 0]
    exp_cs = data.iloc[:, 2]
    theo_cs_initial = data.iloc[:, 4]
    theo_cs_final = data.iloc[:, 5]

    if residual:
        diff_initial = exp_cs - theo_cs_initial
        diff_final = exp_cs - theo_cs_final

        fig, ax = plt.subplots(
            2,
            2,
            sharey=False,
            figsize=(8, 6),
            gridspec_kw={"width_ratios": [5, 1], "height_ratios": [5, 2]},
        )
        ax = np.ravel(ax)
        ax[0].plot(
            energy,
            exp_cs,
            label="Experimental Cross Section",
            marker="o",
            linestyle="-",
        )
        ax[0].plot(
            energy,
            theo_cs_initial,
            label="Theoretical Cross Section (Initial)",
            marker="x",
            linestyle="--",
        )
        ax[0].plot(
            energy,
            theo_cs_final,
            label="Theoretical Cross Section (Final)",
            marker="x",
            linestyle="--",
        )
        ax[0].set_ylabel("Cross Section (barns)")
        ax[0].legend()

        plt.plot(
            energy, diff_initial, label="Difference Initial", marker="o", linestyle="-"
        )
        plt.plot(
            energy, diff_final, label="Difference Final", marker="o", linestyle="-"
        )
        plt.ylabel("Difference (barns)")

    else:
        fig, ax = plt.subplots(1, 1, figsize=(6, 6))
        ax.plot(
            energy,
            exp_cs,
            label="Experimental Cross Section",
            marker="o",
            linestyle="-",
        )
        ax.plot(
            energy,
            theo_cs_initial,
            label="Theoretical Cross Section (Initial)",
            marker="x",
            linestyle="--",
        )
        ax.plot(
            energy,
            theo_cs_final,
            label="Theoretical Cross Section (Final)",
            marker="x",
            linestyle="--",
        )
        ax.set_ylabel("Cross Section (barns)")
        ax.legend()
        plt.show()


def plot_transmission(data, residual=False):
    """
    Plot the transmission data and optionally the residuals.

    Args:
        data (DataFrame): The data to plot. It should have columns "energy", "Zeroth-order theoretical transmission", "Zeroth-order theoretical transmission", "Final theoretical transmission", and optionally "Absolute uncertainty in experimental transmission" if residual is True.
        residual (bool, optional): If True, plot the residuals. Defaults to False.
    """
    data_color = "#433E3F"
    initial_color = "#003f5c"
    final_color = "#ff6361"

    if residual:
        fig, ax = plt.subplots(
            2,
            2,
            sharey=False,
            figsize=(8, 6),
            gridspec_kw={"width_ratios": [5, 1], "height_ratios": [5, 2]},
        )
        ax = np.ravel(ax)
    else:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax = [ax]

    # Plot the Experimental transmission as scattering plot with Energy vs. Experimental transmission with Absolute uncertainty in experimental transmission
    data.plot.scatter(
        x="Energy",
        y="Experimental transmission",
        yerr="Absolute uncertainty in experimental transmission",
        ax=ax[0],
        zorder=-1,
        color=data_color,
        alpha=0.25,
        s=10,
    )
    # data.plot(x="Energy",y=["Zeroth-order theoretical transmission"],ax=ax[0],alpha=0.8, color=initial_color,lw=1)
    data.plot(
        x="Energy",
        y=["Final theoretical transmission"],
        ax=ax[0],
        alpha=1.0,
        color=final_color,
        lw=1,
    )
    ax[0].set_xlabel("")
    ax[0].set_xticks([])
    ax[0].legend(["data", "final fit"])
    ax[0].set_ylabel("transmission")
    ax[0].set_ylim(0, 1.2)

    if residual:
        ax[1].spines["right"].set_visible(False)
        ax[1].spines["top"].set_visible(False)
        ax[1].spines["bottom"].set_visible(False)
        ax[1].spines["left"].set_visible(False)
        ax[1].set_xticks([])
        ax[1].set_yticks([], [])

        data["residual_initial"] = (
            data["Zeroth-order theoretical transmission"]
            - data["Experimental transmission"]
        )
        data["residual_final"] = (
            data["Final theoretical transmission"] - data["Experimental transmission"]
        )

        # data.plot.scatter(x="Energy",y="residual_initial",yerr="Absolute uncertainty in experimental transmission",lw=0,ylim=(-10,10),color=initial_color,ax=ax[2],alpha=0.5,legend=False)
        data.plot.scatter(
            x="Energy",
            y="residual_final",
            yerr="Absolute uncertainty in experimental transmission",
            lw=0,
            ylim=(-10, 10),
            color=final_color,
            ax=ax[2],
            alpha=0.5,
            legend=False,
        )
        ax[2].set_ylabel("residuals\n(fit-data)/err [σ]")
        ax[2].set_xlabel("energy [eV]")
        ax[2].set_ylim(-1, 1)

        data.plot.hist(
            y=["residual_initial"],
            bins=np.arange(-1, 1, 0.01),
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
    plt.show()


def read_data(filename):
    # Load the data
    data = np.loadtxt(
        filename, delimiter=" ", skiprows=1
    )  # Assuming space delimited and one header row

    # Check number of columns
    num_cols = data.shape[1]
    if num_cols != 13:
        raise ValueError(
            "Incorrect number of columns. Expected 13 but got {}".format(num_cols)
        )

    return data


def plot_data(data):
    # Extract necessary columns
    energy = data[:, 0]
    experimental_cross_section = data[:, 1]
    final_theoretical_cross_section = data[:, 4]

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(
        energy,
        experimental_cross_section,
        label="Experimental Cross Section",
        marker="o",
        linestyle="-",
    )
    plt.plot(
        energy,
        final_theoretical_cross_section,
        label="SAMMY Cross Section",
        marker="x",
        linestyle="--",
    )

    plt.xlabel("Energy")
    plt.ylabel("Cross Section (barns)")
    plt.title("Experimental vs. Final Theoretical Cross Section")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    filename = input("Enter the filename: ")
    data = read_data(filename)
    plot_data(data)