"""
Simplified ORNL-specific helper functions for neutron imaging data processing.

This module provides ORNL-specific utilities that complement the generic
utilities in pleiades.utils, focusing on VENUS beamline conventions.
"""

import os
from glob import glob
from pathlib import Path
from typing import List, Optional

import numpy as np

from pleiades.core.constants import CONSTANTS
from pleiades.processing.models_ornl import Run
from pleiades.utils.files import retrieve_list_of_most_dominant_extension_from_folder
from pleiades.utils.load import load
from pleiades.utils.logger import loguru_logger
from pleiades.utils.nexus import get_proton_charge

logger = loguru_logger.bind(name="helper_ornl")


def load_spectra_file(directory_path: str, header: int = 1, sep: str = ",") -> Optional[np.ndarray]:
    """Load ORNL VENUS spectra file containing TOF information.

    Args:
        directory_path: Path to directory containing *_Spectra.txt file
        header: Number of header lines to skip (default: 1 for VENUS)
        sep: Column separator (default: "," for VENUS CSV format)

    Returns:
        Array of shape (n_tof, 2) with columns [TOF(s), Counts] or None if not found
    """
    spectra_files = glob(os.path.join(directory_path, "*_Spectra.txt"))
    if not spectra_files:
        logger.warning(f"No spectra files found in {directory_path}")
        return None

    file_path = spectra_files[0]
    logger.debug(f"Found spectra file: {os.path.basename(file_path)}")

    try:
        data = np.loadtxt(file_path, skiprows=header, delimiter=sep, usecols=(0, 1))
        return data
    except Exception as e:
        logger.error(f"Error loading spectra file: {e}")
        return None


def find_nexus_file(folder: str, nexus_dir: Optional[str] = None) -> Optional[str]:
    """Find the NeXus file for a given VENUS measurement.

    Args:
        folder: Path to measurement folder (e.g., Run_8022)
        nexus_dir: Optional path to nexus directory

    Returns:
        Path to NeXus file or None if not found
    """
    folder_path = Path(folder)
    # Extract run number from folder name (e.g., "Run_8022" -> "8022")
    run_number = folder_path.name.split("_")[1] if "_" in folder_path.name else folder_path.name

    # Determine search directory
    if nexus_dir:
        search_dir = Path(nexus_dir)
    else:
        # Default ORNL structure: look in parent's nexus subfolder
        parent = folder_path.parent.parent
        search_dir = parent / "nexus" if (parent / "nexus").exists() else parent

    # VENUS naming convention
    nexus_pattern = f"VENUS_{run_number}*.nxs.h5"
    matches = list(search_dir.glob(nexus_pattern))

    if matches:
        return str(matches[0])

    logger.warning(f"No NeXus file found for run {run_number} in {search_dir}")
    return None


def tof_to_energy(tof: np.ndarray, flight_path: float = 25.0) -> np.ndarray:
    """Convert time-of-flight to neutron energy.

    Args:
        tof: Time-of-flight values in seconds
        flight_path: Flight path length in meters (default 25m for VENUS)

    Returns:
        Neutron energy in eV
    """
    # Use constants from PLEIADES constants module
    m_n = CONSTANTS.neutron_mass_kg  # neutron mass in kg
    e_charge = CONSTANTS.elementary_charge  # J/eV conversion

    # Avoid division by zero
    tof_safe = np.where(tof > 0, tof, np.inf)

    v = flight_path / tof_safe  # velocity in m/s
    E_joule = 0.5 * m_n * v**2  # kinetic energy in joules
    E_eV = E_joule / e_charge  # convert to eV

    return E_eV


def load_run_from_folder(folder: str, nexus_path: Optional[str] = None, nexus_dir: Optional[str] = None) -> Run:
    """Load a single VENUS run from folder.

    Args:
        folder: Path to folder containing images
        nexus_path: Direct path to NeXus file (overrides search)
        nexus_dir: Directory to search for NeXus files

    Returns:
        Run object with counts, proton charge, and metadata
    """
    # Determine file type and load images
    file_list, file_extension = retrieve_list_of_most_dominant_extension_from_folder(folder)
    if not file_list:
        raise ValueError(f"No image files found in {folder}")

    counts = load(file_list, file_extension)

    # Load TOF values from spectra file
    spectra_data = load_spectra_file(folder)
    tof_values = None
    if spectra_data is not None:
        tof_values = spectra_data[:, 0]  # First column is TOF
        if len(tof_values) != counts.shape[0]:
            logger.warning(f"TOF length mismatch: {len(tof_values)} vs {counts.shape[0]} images")
            tof_values = None

    # Find NeXus file and extract proton charge
    if nexus_path is None:
        nexus_path = find_nexus_file(folder, nexus_dir)

    proton_charge = 1.0  # Default
    if nexus_path:
        pc = get_proton_charge(nexus_path, units="pc")
        if pc is not None:
            proton_charge = pc / 1e6  # Convert pC to μC

    # Build metadata
    metadata = {
        "folder": folder,
        "nexus_path": nexus_path,
        "run_number": Path(folder).name,
        "n_tof": counts.shape[0],
        "tof_values": tof_values,
    }

    return Run(counts=counts, proton_charge=proton_charge, metadata=metadata)


def load_multiple_runs(folders: List[str], nexus_dir: Optional[str] = None) -> List[Run]:
    """Load multiple VENUS runs.

    Args:
        folders: List of folder paths
        nexus_dir: Optional directory containing NeXus files

    Returns:
        List of Run objects
    """
    runs = []
    for folder in folders:
        try:
            run = load_run_from_folder(folder, nexus_dir=nexus_dir)
            runs.append(run)
        except Exception as e:
            logger.error(f"Failed to load run from {folder}: {e}")
            raise

    logger.info(f"Loaded {len(runs)} runs")
    return runs


def detect_persistent_dead_pixels(data: np.ndarray) -> np.ndarray:
    """Detect pixels that are zero across ALL time frames.

    Args:
        data: 3D array with shape (tof, y, x)

    Returns:
        2D boolean mask where True = dead pixel
    """
    dead_mask = np.all(data == 0, axis=0)
    n_dead = np.sum(dead_mask)
    n_total = dead_mask.size
    logger.debug(f"Found {n_dead}/{n_total} dead pixels ({100 * n_dead / n_total:.1f}%)")
    return dead_mask


def combine_runs(runs: List[Run]) -> Run:
    """Combine multiple runs into one effective run.

    Args:
        runs: List of Run objects to combine

    Returns:
        Combined Run object
    """
    if not runs:
        raise ValueError("Cannot combine empty list of runs")
    if len(runs) == 1:
        return runs[0]

    # Verify shape compatibility
    reference_shape = runs[0].counts.shape
    for i, run in enumerate(runs[1:], start=1):
        if run.counts.shape != reference_shape:
            raise ValueError(f"Run {i} shape mismatch: {run.counts.shape} vs {reference_shape}")

    # Combine data
    combined_counts = np.sum([run.counts for run in runs], axis=0)
    combined_pc = sum(run.proton_charge for run in runs)

    # Merge metadata
    combined_metadata = {
        "n_runs_combined": len(runs),
        "source_folders": [run.metadata.get("folder", "") for run in runs],
        "source_run_numbers": [run.metadata.get("run_number", "") for run in runs],
        "individual_proton_charges": [run.proton_charge for run in runs],
        "tof_values": runs[0].metadata.get("tof_values"),
        "n_tof": runs[0].metadata.get("n_tof"),
    }

    logger.info(f"Combined {len(runs)} runs, total PC: {combined_pc:.2f} μC")

    return Run(counts=combined_counts, proton_charge=combined_pc, metadata=combined_metadata)
