# sammyUtils.py
# Version: 1.0
# Authors:
#   - Alexander M. Long
#       - Los Alamos National Laboratory
#       - ORCID: 0000-0003-4300-9454
#   - Tsviki Hirsh
#       - Soreq Nuclear Research Center
#       - ORCID: 0000-0001-5889-4500
# About:
#   This file is part of the PLEIADES package and contains high level functions to setup the SAMMY fitting process.
# Functions:
#   - create_parFile_from_endf(config: SammyFitConfig, archive: bool = True, verbose_level: int = 0) -> None
#   - configure_sammy_run(config: SammyFitConfig, verbose_level: int = 0)
#   - run_sammy(config: SammyFitConfig, verbose_level: int = 0)
# How to use:
#   - Import the this class with 'from pleiades import sammyUtils'
#   Note:
#       also need to import SammyFitConfig from pleiades.sammyStructures
#       with 'from pleiades.sammyStructures import SammyFitConfig'

# General imports
from pathlib import Path
import pathlib
import os
import shutil
import numpy as np
import importlib.resources as pkg_resources

# PLEIADES imports
from pleiades.sammyStructures import SammyFitConfig, sammyRunConfig
from pleiades import sammyParFile, sammyInput, sammyRunner, nucData

print_header_check = "\033[1;34m<SAMMY Utilities>\033[0m "
print_header_good = "\033[1;32m<SAMMY Utilities>\033[0m "
print_header_bad = "\033[1;31m<SAMMY Utilities>\033[0m "


def create_parFile_from_endf(
    config: SammyFitConfig, archive: bool = True, verbose_level: int = 0
) -> None:
    """
    Takes a SammyFitConfig object and creates SAMMY parFiles from ENDF data based on the isotopes specified in the configuration.


    This function creates a SAMMY input file based on a configuration file, modifies relevant
    cards for the target isotope, saves the input file, and then runs SAMMY with ENDF data
    to generate the corresponding `.par` file.

    Args:
        config (SammyFitConfig): SammyFitConfig object containing the configuration parameters.
        archive (bool, optional): Flag for storing sammy files. Defaults to False.
        verbose_level (int, optional): 0: no printing, 1: prints general info, 2: prints data. Defaults to 0.

    Notes:
        #TODO: Need to figure out a better way to deal with commands in card3.
        #TODO: Need to add a check to see if the .par file was created successfully and print a message if not.
    """

    # Grab the directory from which the pleiades script was called.
    # note: pleiades_call_dir is not used in this function
    pleiades_call_dir = pathlib.Path.cwd()  # noqa: F841

    # first check to see if the SAMMY environment is set up correctly
    if not sammyRunner.check_sammy_environment(config, verbose_level):
        raise FileNotFoundError(
            f"{print_header_bad} SAMMY executable not found in the path"
        )
    else:
        if verbose_level > 0:
            print(f"{print_header_good} SAMMY executable found in the path")

    # First grab the isotopes from the configuration class
    isotopes = config.params["isotopes"]["names"]
    if verbose_level > 1:
        print(f"{print_header_check} Isotopes: {isotopes}")

    # Then Grab the rest of the necessary parameters from the configuration class
    # note: flight_path_length is not used in this function
    flight_path_length = config.params["flight_path_length"]  # noqa: F841

    # Print a header if verbose_level > 0
    if verbose_level > 0:
        print(
            f"\n{print_header_check} ================================================"
        )
        print(
            f"{print_header_check} Creating SAMMY parFile files from ENDF data for isotopes: {isotopes}"
        )

    # Set the ENDF directory path
    endf_dir_path = pathlib.Path(config.params["directories"]["endf_dir"]).resolve()

    # Check to see if the endf_dir exists and create it if it doesn't
    if not os.path.exists(endf_dir_path):
        os.makedirs(endf_dir_path)
        if verbose_level > 0:
            print(f"{print_header_check} ENDF directory created at {endf_dir_path}")
    else:
        if verbose_level > 0:
            print(
                f"{print_header_check} ENDF directory at {endf_dir_path} already exists"
            )

    # Set the res_endf8.endf file path to be in the endf directory
    destination_res_endf = endf_dir_path / "res_endf8.endf"

    # Now check to see if the res_endf8.endf file exists in the endf dir. If not, copy it there.
    if not os.path.exists(destination_res_endf):
        source_res_endf = pkg_resources.files("pleiades").joinpath(
            "../../nucDataLibs/resonanceTables/res_endf8.endf"
        )
        # Copy the res_endf8.endf file to the endf directory
        shutil.copy(source_res_endf, destination_res_endf)
        if verbose_level > 0:
            print(
                f"{print_header_check} Copied {source_res_endf} to {destination_res_endf}"
            )
    else:
        if verbose_level > 0:
            print(
                f"{print_header_check} res_endf8.endf file already exists at {destination_res_endf}\n"
            )

    # Loop through the isotope list:
    #   1. Create a SAMMY input, data, and params file,
    #   2. then run SAMMY with ENDF data to generate .par file
    for isotope in isotopes:
        # Set the isotope directory path
        isotope_dir_path = endf_dir_path / Path(isotope)
        fit_results_dir = isotope_dir_path / Path("results")

        # Check to see if the isotope directory exists and create it if it doesn't
        if not os.path.exists(isotope_dir_path):
            os.makedirs(isotope_dir_path)
            if verbose_level > 0:
                print(
                    f"{print_header_check} Isotope directory created at {isotope_dir_path}"
                )
        else:
            if verbose_level > 0:
                print(
                    f"{print_header_check} Isotope directory at {isotope_dir_path} already exists"
                )

            # Check to see if the par file already exists in the isotope directory
            par_file = fit_results_dir / Path("SAMNDF.PAR")
            if os.path.exists(par_file):
                if verbose_level > 0:
                    print(
                        f"{print_header_check} SAMMY parFile already exists at {par_file}"
                    )
                    print(
                        f"{print_header_check} Skipping SAMMY ENDF run for isotope: {isotope}"
                    )
                continue
            else:
                if verbose_level > 0:
                    print(
                        f"{print_header_check} A SAMMY parFile does not exist at {par_file}"
                    )

        # Print a header if verbose_level > 0
        if verbose_level > 0:
            print(
                f"{print_header_check} Now Creating SAMMY input.inp and params.par for isotope: {isotope}"
            )

        # Create and update SAMMY input file data structure
        inp = sammyInput.InputFile()
        inp.update_with_config(config, isotope=isotope, for_endf=True)

        # Create a SAMMY input file in the isotope directory
        sammy_input_file = (
            isotope_dir_path / (config.params["filenames"]["input_file_name"])
        )

        # Write the SAMMY input file to the specified location.
        inp.process().write(sammy_input_file)
        if verbose_level > 0:
            print(
                f"{print_header_check} SAMMY input file created at {sammy_input_file}"
            )

        # Print the input data structure if desired
        if verbose_level > 1:
            print(f"{print_header_check} SAMMY input data for isotope {isotope}:")
            print(inp.data)
            print(f"{print_header_check} -------------------------------")

        # Need to create a fake data file with only Emin and Emax data points
        data_file = isotope_dir_path / ("data.twenty")

        # Determine the number of points (at least 100) and create a list of energies
        energy_values = np.linspace(
            config.params["fit_energy_max"], config.params["fit_energy_min"], 100
        )

        # Open the data file and write the energy, transmission, and error values
        # Note: this is the twenty character format that SAMMY expects with the TWENTY command
        with open(data_file, "w") as fid:
            for energy in energy_values:
                transmission = 1.0
                error = 0.1
                # Write each line with 20 characters width, right justified
                fid.write(f"{energy:>20.8f}{transmission:>20.8f}{error:>20.8f}\n")

        if verbose_level > 0:
            print(
                f"{print_header_check} Created an ENDF dummy data file at {data_file}"
            )

        # Creating a par file based on ENDF file
        endf_res_file_name = "res_endf8.endf"
        symlink_path = isotope_dir_path / endf_res_file_name
        # First check if file already exists

        if os.path.islink(symlink_path):
            endf_par_file = symlink_path
        else:
            # Create a symbolic link to the original endf file
            original_endf_file = "../res_endf8.endf"
            os.symlink(original_endf_file, symlink_path)
            endf_par_file = isotope_dir_path / "res_endf8.endf"

        if verbose_level > 0:
            print(f"{print_header_check} ENDF file: {endf_par_file}")

        # Create a sammy run configuration object
        isotope_run_config = sammyRunConfig()

        # configure run_config for an ENDF SAMMY run
        isotope_run_config.params["sammy_run_method"] = config.params[
            "sammy_run_method"
        ]
        isotope_run_config.params["sammy_command"] = config.params["sammy_command"]
        isotope_run_config.params["sammy_fit_name"] = isotope
        isotope_run_config.params["run_endf_for_par"] = True
        isotope_run_config.params["directories"]["sammy_fit_dir"] = str(
            isotope_dir_path
        )
        isotope_run_config.params["directories"]["input_dir"] = str(isotope_dir_path)
        isotope_run_config.params["directories"]["params_dir"] = str(endf_dir_path)
        isotope_run_config.params["directories"]["data_dir"] = str(isotope_dir_path)
        isotope_run_config.params["filenames"]["params_file_name"] = str(
            endf_res_file_name
        )

        sammyRunner.run_sammy_fit(isotope_run_config, verbose_level=verbose_level)

        if verbose_level > 0:
            print("\r")


def configure_sammy_run(config: SammyFitConfig, verbose_level: int = 0):
    """
    Configures SAMMY based on a SammyFitConfig object.

    This function takes a SammyFitConfig object and uses the parameters to
    configure the files needed to run SAMMY. It creates a SAMMY input file, modifies the
    relevant cards based on the configuration, saves the input file. It then creates a SAMMY
    parameter file by summing the par files for the isotopes specified in the configuration.
    Finally, it creates a symlink for the data file into the sammy_fit_dir.

    Args:
        config (SammyFitConfig): SammyFitConfig object containing the configuration parameters.

    Notes:
        - TODO: This assumes that parfiles were created via ENDF data. This might not always be the case.
    """
    isotopeParFiles = []

    # setting up the directories that we will need to use
    # note: fit_dir is not used in this function
    fit_dir = config.params["directories"]["sammy_fit_dir"]  # noqa: F841
    endf_dir = config.params["directories"]["endf_dir"]
    sammy_fit_dir = config.params["directories"]["sammy_fit_dir"]
    data_dir = config.params["directories"]["data_dir"]

    # Grabbing the isotopes, abundances, and fudge factor from the config file
    isotopes = config.params["isotopes"]["names"]
    abundances = config.params["isotopes"]["abundances"]
    fudge_factor = config.params["fudge_factor"]

    # If using ENDF generated param files, then we need process them into a single parFile
    if config.params["use_endf_par_file"] is True:
        # setting the resonance energy min and max, this will clip the resonances in the parFile to the specified energy range
        res_emin = config.params["resonances"]["resonance_energy_min"]
        res_emax = config.params["resonances"]["resonance_energy_max"]

        # Create a SAMMY parFile for each isotope
        if verbose_level > 0:
            print(
                f"\n{print_header_check} Merging SAMMY parameter files for isotopes: {isotopes}, with abundances: {abundances}"
            )

        # TODO: This assumes that parfiles were created via ENDF data. This might not always be the case.
        # I think I can use the run_with_endf flag to determine if the par file was created with ENDF data
        for isotope, abundance in zip(isotopes, abundances):
            # turn the abundance into a float
            abundance = float(abundance)
            # Append sammy parFiles using sammyParFile in the ParFile class
            isotopeParFiles.append(
                sammyParFile.ParFile(
                    filename=f"{endf_dir}/{isotope}/results/SAMNDF.PAR",
                    name=isotope,
                    weight=abundance,
                    emin=res_emin,
                    emax=res_emax,
                ).read()
            )

        # Create a output parFile by summing the isotope parFiles
        outputParFile = isotopeParFiles[0]  # set the first isotope as the output

        # loop through the rest of the isotopes and add them to the output
        for isotopeParFile in isotopeParFiles[1:]:
            outputParFile = outputParFile + isotopeParFile

        # we want to fit abundances in this case
        # TODO: Need to implement a method to toggle the vary flag for all abundances
        outputParFile.update.toggle_vary_abundances(vary=True)

        # change the fudge-factor that essentially responsible for the fit step-size
        # it only has a minor effect on results
        outputParFile.data["info"]["fudge_factor"] = fudge_factor

        # Set broadening parameters based on the configuration
        broadening_args = {
            "match_radius": config.params["broadening"]["match_radius"],
            "temperature": config.params["broadening"]["temperature"],
            "thickness": config.params["broadening"]["thickness"],
            "flight_path_spread": config.params["broadening"]["flight_path_spread"],
            "deltag_fwhm": config.params["broadening"]["deltag_fwhm"],
            "deltae_us": config.params["broadening"]["deltae_us"],
            "vary_match_radius": int(
                config.params["broadening"]["vary_match_radius"] is True
            ),
            "vary_thickness": int(
                config.params["broadening"]["vary_thickness"] is True
            ),
            "vary_temperature": int(
                config.params["broadening"]["vary_temperature"] is True
            ),
            "vary_flight_path_spread": int(
                config.params["broadening"]["vary_flight_path_spread"] is True
            ),
            "vary_deltag_fwhm": int(
                config.params["broadening"]["vary_deltag_fwhm"] is True
            ),
            "vary_deltae_us": int(
                config.params["broadening"]["vary_deltae_us"] is True
            ),
        }
        outputParFile.update.broadening(**broadening_args)

        # Set normalization parameters based on the configuration
        normalization_args = {
            "normalization": float(config.params["normalization"]["normalization"]),
            "constant_bg": float(config.params["normalization"]["constant_bg"]),
            "one_over_v_bg": float(config.params["normalization"]["one_over_v_bg"]),
            "sqrt_energy_bg": float(config.params["normalization"]["sqrt_energy_bg"]),
            "exponential_bg": float(config.params["normalization"]["exponential_bg"]),
            "exp_decay_bg": float(config.params["normalization"]["exp_decay_bg"]),
            "vary_normalization": int(
                config.params["normalization"]["vary_normalization"] is True
            ),
            "vary_constant_bg": int(
                config.params["normalization"]["vary_constant_bg"] is True
            ),
            "vary_one_over_v_bg": int(
                config.params["normalization"]["vary_one_over_v_bg"] is True
            ),
            "vary_sqrt_energy_bg": int(
                config.params["normalization"]["vary_sqrt_energy_bg"] is True
            ),
            "vary_exponential_bg": int(
                config.params["normalization"]["vary_exponential_bg"] is True
            ),
            "vary_exp_decay_bg": int(
                config.params["normalization"]["vary_exp_decay_bg"] is True
            ),
        }
        outputParFile.update.normalization(**normalization_args)

        # write out the output par file
        output_par_file = Path(sammy_fit_dir) / Path("params").with_suffix(".par")
        if verbose_level > 0:
            print(f"{print_header_check} Writing output parFile: {output_par_file}")
        outputParFile.write(output_par_file)

        # Now create a SAMMY input file
        if verbose_level > 0:
            print(
                f"{print_header_check} Creating SAMMY inpFile files for isotopes: {isotopes} with abundances: {abundances}"
            )

        # Create an inpFile from
        inp = sammyInput.InputFile(verbose_level=verbose_level)

        # find the lowest atomic number isotope and set it as the element
        lowest_atomic_isotope = min(
            isotopes, key=lambda isotope: nucData.get_mass_from_ame(isotope)
        )

        # Update input data with isotope-specific information
        inp.data["Card2"]["elmnt"] = lowest_atomic_isotope
        inp.data["Card2"]["aw"] = "auto"
        inp.data["Card2"]["emin"] = config.params["fit_energy_min"]
        inp.data["Card2"]["emax"] = config.params["fit_energy_max"]
        inp.data["Card5"]["dist"] = config.params["flight_path_length"]
        inp.data["Card5"]["deltag"] = 0.001
        inp.data["Card5"]["deltae"] = 0.001
        inp.data["Card7"]["crfn"] = 0.001

        # TODO: Need to figure out a better way to deal with commands in card3.
        # Resetting the commands for running SAMMY to generate output par files based on ENDF.
        inp.data["Card3"]["commands"] = (
            "CHI_SQUARED,TWENTY,SOLVE_BAYES,QUANTUM_NUMBERS,REICH-MOORE FORMALISm is wanted,GENERATE ODF FILE AUTOMATICALLY,USE I4 FORMAT TO READ SPIN GROUP NUMBER"
        )

        # Print the input data structure if desired
        if verbose_level > 1:
            print(inp.data)

        # Create a run name or handle for the compound inpFile
        # TODO: fix hard coding of inpFile name
        output_inp_file = Path(sammy_fit_dir) / Path("input").with_suffix(".inp")

        # Write the SAMMY input file to the specified location.
        inp.process().write(output_inp_file)
        if verbose_level > 0:
            print(
                f"{print_header_check} Created compound input file: {output_inp_file}"
            )

        # Create a symbolic link inside the sammy_fit_dir that points to the data file
        data_file = os.path.join(data_dir, config.params["filenames"]["data_file_name"])
        data_file_name = pathlib.Path(data_file).name

        if verbose_level > 0:
            print(
                f"{print_header_check} Symlinking data file: {data_file} into {sammy_fit_dir}"
            )

        # Check if the symbolic link already exists
        symlink_path = pathlib.Path(sammy_fit_dir) / data_file_name
        if os.path.islink(symlink_path):
            os.unlink(symlink_path)  # unlink old symlink

        os.symlink(
            data_file, pathlib.Path(sammy_fit_dir) / data_file_name
        )  # create new symlink

        # Create a sammy run configuration object
        sammy_run_config = sammyRunConfig()

        # configure run_config for an ENDF SAMMY run
        sammy_run_config.params["sammy_run_method"] = config.params["sammy_run_method"]
        sammy_run_config.params["sammy_command"] = config.params["sammy_command"]
        sammy_run_config.params["run_endf_for_par"] = False
        sammy_run_config.params["directories"]["sammy_fit_dir"] = config.params[
            "directories"
        ]["sammy_fit_dir"]
        sammy_run_config.params["directories"]["input_dir"] = config.params[
            "directories"
        ]["sammy_fit_dir"]
        sammy_run_config.params["directories"]["params_dir"] = config.params[
            "directories"
        ]["sammy_fit_dir"]
        sammy_run_config.params["directories"]["data_dir"] = config.params[
            "directories"
        ]["data_dir"]
        sammy_run_config.params["filenames"]["params_file_name"] = config.params[
            "filenames"
        ]["params_file_name"]
        sammy_run_config.params["filenames"]["input_file_name"] = config.params[
            "filenames"
        ]["input_file_name"]
        sammy_run_config.params["filenames"]["data_file_name"] = config.params[
            "filenames"
        ]["data_file_name"]

        return sammy_run_config

    else:
        return config


def run_sammy(config: SammyFitConfig, verbose_level: int = 0):
    """
    Runs SAMMY based on a SammyFitConfig object.

    This function takes a SammyFitConfig object and uses it to run sammy.

    Args:
        config (SammyFitConfig): SammyFitConfig object containing the configuration parameters.
    """

    # Run SAMMY
    sammyRunner.run_sammy_fit(config, verbose_level=verbose_level)
