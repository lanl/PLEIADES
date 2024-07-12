import numpy as np

SPEED_OF_LIGHT = 299792458  # m/s
MASS_OF_NEUTRON = 939.56542052 * 1e6 / (SPEED_OF_LIGHT) ** 2  # [eV s²/m²]  
TOF_LABEL = "Time-of-flight [μs]"
ENERGY_LABEL = "Energy [eV]"

def time2energy(time, flight_path_length):
    r"""Convert time-of-flight to energy of the neutron.

    .. math::
        E = \left( \gamma - 1 \right) m c^2 \; ,
        \gamma = \frac{1}{\sqrt{1 - \left(\frac{L}{c \cdot t} \right)^2}} \; ,

    where :math:`E` is the energy, :math:`m` is the mass, :math:`c` is
    the speed of light, :math:`t` is the time-of-flight of the neutron,
    and :math:`L` is the flight path length.

    Args:
        time: Time-of-flight in :math:`\mathrm{s}`.
        flight_path_length: flight path length in :math:`\mathrm{m}`.

    Returns:
        Energy of the neutron in :math:`\mathrm{eV}`.
    """
    m = MASS_OF_NEUTRON  # [eV s²/m²]
    c = SPEED_OF_LIGHT  # m/s
    L = flight_path_length  # m
    t = time  # s
    γ = 1 / np.sqrt(1 - (L / t) ** 2 / c**2)
    return (γ - 1) * m * c**2  # eV


def energy2time(energy, flight_path_length):
    r"""Convert energy to time-of-flight of the neutron.

    .. math::
        t = \frac{L}{c} \sqrt{ \frac{\gamma^2}{\gamma^2 - 1 }} \; ,
        \gamma = 1 + \frac{E}{mc^2}

    where :math:`E` is the energy, :math:`m` is the mass, :math:`c`
    is the speed of light, :math:`t` is the time-of-flight of the neutron,
    and :math:`L` is the flight path length.

    Args:
        energy:  Energy of the neutron in :math:`\mathrm{eV}`.
        flight_path_length: flight path length in :math:`\mathrm{m}`.

    Returns:
        Time-of-flight in :math:`\mathrm{s}`.

    """
    L = flight_path_length  # m
    m = MASS_OF_NEUTRON  # eV s²/m²
    c = SPEED_OF_LIGHT  # m/s
    E = energy  # eV
    γ = 1 + E / m / c**2
    t = L / c * np.sqrt(γ**2 / (γ**2 - 1))  # s
    return t  # ns

def sammy_background(
    energy: np.ndarray,
    normalization: float = 1.0,
    constant_bg: float = 0.0,
    one_over_v_bg: float = 0.0,
    sqrt_energy_bg: float = 0.0,
    exponential_bg: float = 0.0,
    exp_decay_bg: float = 0.0,
) -> np.ndarray:
    """Calculates the Sammy background function for a given energy array.

    This function implements the background parametrization used by the
    SAMMY code for neutron spectroscopy.

    Args:
        energy (np.ndarray): Array of energy bins in eV.
        normalization (float, optional): Overall normalization factor for the background (default: 1.0).
        constant_bg (float, optional): Constant background term (default: 0.0).
        one_over_v_bg (float, optional): Coefficient for the 1/v term (default: 0.0).
        sqrt_energy_bg (float, optional): Coefficient for the sqrt(E) term (default: 0.0).
        exponential_bg (float, optional): Pre-exponential factor for the exponential term (default: 0.0).
        exp_decay_bg (float, optional): Decay constant for the exponential term (default: 0.0).

    Returns:
        np.ndarray: The calculated background array with the same shape as the input energy array.
    """

    bg = (
        constant_bg
        + one_over_v_bg / np.sqrt(energy)
        + sqrt_energy_bg * np.sqrt(energy)
        + exponential_bg * np.exp(-exp_decay_bg / np.sqrt(energy))
    )
    return bg * normalization

def save_transmission_spectrum(
    archivename: str = "UMo",
    signal: np.ndarray = np.array([]),
    openbeam: np.ndarray = np.array([]),
    flight_path_length: float = 10.7,
    Δt: float = 1.0,
    t_zero: float = 0.0,
    uncertainty_rank: float = 0.0,
    k: float = 1.0,
    ϵ: float = 1.0,
    plot_label: str = "",
    N: np.ndarray = np.array([1.0]),
    scale_bg: float = 1.0,
    bg_type: str = "",
    bg_params: dict = {},
    data_threshold: float = -999,
    resolution_file: str = "FP5_resolution.udp",
) -> None:
    """
    Calculates and saves transmission data from signal and open-beam spectra.

    This function processes signal and open-beam spectra (assumed to be numpy arrays)
    to generate a transmission spectrum with uncertainties. It can then save the
    transmission data to a `.dat` file and optionally create a plot.

    Args:
        archivename (str, optional): Name or path for the output `.dat` file
            (default: "UMo").
        signal (np.ndarray): Array containing the signal spectrum.
        openbeam (np.ndarray): Array containing the open-beam spectrum.
        flight_path_length (float, optional): Flight path length in meters (default: 10.7).
        Δt (float, optional): Time step between data points in microseconds (default: 1.0).
        t_zero (float, optional): Time delay to apply to the data (default: 0.0).
        uncertainty_rank (float, optional): Exponent for uncertainty correction (default: 0.0).
        k (float, optional): Ratio of sample and open-beam background (default: 1.0).
        ϵ (float, optional): Factor for systematic background uncertainty (default: 1.0).
        plot_label (str, optional): Label for the plot (default: "").
        N (np.ndarray, optional): Transmission normalization factor (default: 1.0).
        scale_bg (float, optional): Background scaling factor (default: 1.0).
        bg_type (str, optional): Background function type ("trinidi", "sammy", etc.)
            (default: "sammy").
        bg_params (dict, optional): Parameters for the background function (default: {}).
        data_threshold (float, optional): Minimum value for data points (default: -999). Useful to exclude saturation resonances below threshold
        resolution_file (str, optional): Name of the resolution file (default: "FP5_resolution.udp").
    """
    # Create output filename with proper extension
    output_filename = (
        Path("archive") / Path(archivename) / Path(archivename).with_suffix(".dat")
    )

    # Calculate time of flight (TOF) with center bins
    tof = t_zero * Δt + np.arange(len(signal)) * Δt + 0.5 * Δt

    # Convert TOF to energy
    energy = time2energy(tof * 1e-6, flight_path_length)

    # Calculate background based on type
    if bg_type == "sammy":
        background = scale_bg * sammy_background(energy, **bg_params)
    else:
        background = scale_bg * np.ones_like(
            energy
        )  # Assume zero background for other types

    # Calculate transmission
    transmission = N * (signal - k * background) / (openbeam - background)

    # Calculate transmission uncertainty
    uncertainty = (
        transmission
        / (openbeam - background)
        * np.sqrt(
            np.abs(signal) / transmission**2
            + np.abs(openbeam + (1.0 - k / transmission) ** 2 * ϵ**2 * background)
        )
    )

    # Apply uncertainty rank if specified
    if uncertainty_rank:
        uncertainty /= transmission**uncertainty_rank

    # Ensure positive uncertainty values
    uncertainty = np.abs(uncertainty)

    # Create pandas DataFrame with filtered and formatted data
    data = pandas.DataFrame(
        {"data": transmission[::-1], "err": uncertainty[::-1], "tof": tof[::-1]},
        index=energy[::-1],
    )
    filtered_data = data.query("tof > 0 and data > @data_threshold")[["data", "err"]]

    # Create directory for output file (if needed)
    output_filename.parent.mkdir(parents=True, exist_ok=True)

    # Save filtered data to .dat file
    np.savetxt(
        output_filename,
        filtered_data.reset_index().values,
        fmt="%19.12f",
        newline="\n ",
        header="W data (twenty format)",
    )

    # Remove the first line (header) using system call (consider alternative)
    os.system(f"sed -i '1d' {output_filename}")

    if resolution_file:
        # Create symbolic link to resolution file (consider alternative)
        resolution_file_path = Path.cwd() / "sammy_files" / resolution_file
        resolution_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(resolution_file_path, output_filename.with_name("FP5.udp"))
        except FileNotFoundError:
            print(
                f"Put the .udp resolution file in this directory {resolution_file_path.parent}"
            )
        except:
            pass

    # Plot data if label provided
    if plot_label:
        filtered_data.plot(
            y="data",
            xlim=(0, 50),
            lw=1,
            xlabel="energy [eV]",
            ylabel="average transmission",
            title=output_filename.stem,
            label=plot_label,
        )
        plt.show()  # Explicitly show the plot