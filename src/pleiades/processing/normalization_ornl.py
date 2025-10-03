"""
ORNL-specific normalization pipeline for neutron imaging at VENUS.

This module implements the Method 2 normalization approach (sum-then-divide)
for processing neutron imaging data from the VENUS beamline at ORNL.
"""

from typing import List, Optional

import numpy as np

from pleiades.processing import Roi
from pleiades.processing.helper_ornl import (
    combine_runs,
    detect_persistent_dead_pixels,
    load_multiple_runs,
    tof_to_energy,
)
from pleiades.processing.models_ornl import Run, Transmission
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="normalization_ornl")


def calculate_transmission(
    sample_run: Run,
    ob_run: Run,
    roi: Optional[Roi] = None,
    pc_uncertainty_sample: float = 0.005,  # 0.5% relative
    pc_uncertainty_ob: float = 0.005,
) -> Transmission:
    """Calculate transmission using Method 2 (sum-then-divide).

    Args:
        sample_run: Sample measurement run
        ob_run: Open beam measurement run
        roi: Optional region of interest for spatial selection
        pc_uncertainty_sample: Relative uncertainty in sample proton charge
        pc_uncertainty_ob: Relative uncertainty in OB proton charge

    Returns:
        Transmission object with calculated spectrum and uncertainties
    """
    # Step 1: Detect dead pixels on BOTH runs
    dead_sample = detect_persistent_dead_pixels(sample_run.counts)
    dead_ob = detect_persistent_dead_pixels(ob_run.counts)

    # Step 2: Combine dead masks
    dead_total = dead_sample | dead_ob

    # Step 3: Create ROI mask if provided
    height, width = sample_run.counts.shape[1:]
    roi_mask = np.ones((height, width), dtype=bool)
    roi_center = (width / 2, height / 2)  # Default center

    if roi is not None:
        roi_mask[:] = False
        roi_mask[roi.y1 : roi.y2, roi.x1 : roi.x2] = True
        roi_center = ((roi.x1 + roi.x2) / 2, (roi.y1 + roi.y2) / 2)

    # Step 4: Create valid pixel mask
    valid_mask = roi_mask & ~dead_total

    # Step 5: Sum counts spatially (Method 2)
    # Expand valid_mask to 3D for broadcasting
    valid_mask_3d = valid_mask[np.newaxis, :, :]

    # Sum over spatial dimensions
    C_s = np.sum(sample_run.counts * valid_mask_3d, axis=(1, 2))
    C_o = np.sum(ob_run.counts * valid_mask_3d, axis=(1, 2))

    # Step 6: Calculate transmission with proton charge correction
    # Avoid division by zero
    C_o_safe = np.where(C_o > 0, C_o, np.inf)
    T = (C_s / C_o_safe) * (ob_run.proton_charge / sample_run.proton_charge)

    # Step 7: Calculate uncertainty (Poisson + systematic)
    # σ/T = sqrt(1/C_s + 1/C_o + ε_s² + ε_o²)
    C_s_safe = np.where(C_s > 0, C_s, np.inf)
    relative_uncertainty = np.sqrt(1 / C_s_safe + 1 / C_o_safe + pc_uncertainty_sample**2 + pc_uncertainty_ob**2)
    uncertainty = T * relative_uncertainty

    # Step 8: Convert TOF to energy if available
    tof_values = sample_run.metadata.get("tof_values")
    if tof_values is not None:
        energy = tof_to_energy(tof_values)
    else:
        # Use bin indices as placeholder
        energy = np.arange(len(T))

    # Build metadata
    metadata = {
        "n_dead_pixels": int(np.sum(dead_total)),
        "n_valid_pixels": int(np.sum(valid_mask)),
        "sample_proton_charge": sample_run.proton_charge,
        "ob_proton_charge": ob_run.proton_charge,
        "pc_uncertainty_sample": pc_uncertainty_sample,
        "pc_uncertainty_ob": pc_uncertainty_ob,
        "method": "Method2_sum_then_divide",
    }

    return Transmission(
        energy=energy, transmission=T, uncertainty=uncertainty, roi=roi, roi_center=roi_center, metadata=metadata
    )


def process_individual_mode(
    sample_runs: List[Run], ob_runs: List[Run], roi: Optional[Roi] = None, pc_uncertainty: float = 0.005
) -> List[Transmission]:
    """Process each sample run individually against combined OB.

    Args:
        sample_runs: List of sample measurement runs
        ob_runs: List of open beam measurement runs
        roi: Optional region of interest
        pc_uncertainty: Relative proton charge uncertainty

    Returns:
        List of Transmission objects, one per sample run
    """
    # Step 1: Combine OB runs
    effective_ob = combine_runs(ob_runs)
    logger.info(f"Combined {len(ob_runs)} OB runs")

    # Step 2: Process each sample run
    results = []
    for i, sample_run in enumerate(sample_runs):
        logger.debug(f"Processing sample run {i + 1}/{len(sample_runs)}")
        transmission = calculate_transmission(sample_run, effective_ob, roi, pc_uncertainty, pc_uncertainty)
        # Add source info to metadata
        transmission.metadata["sample_run_index"] = i
        transmission.metadata["sample_folder"] = sample_run.metadata.get("folder", "")
        transmission.metadata["ob_folders"] = [run.metadata.get("folder", "") for run in ob_runs]
        results.append(transmission)

    return results


def process_combined_mode(
    sample_runs: List[Run], ob_runs: List[Run], roi: Optional[Roi] = None, pc_uncertainty: float = 0.005
) -> List[Transmission]:
    """Combine all runs before processing.

    Args:
        sample_runs: List of sample measurement runs
        ob_runs: List of open beam measurement runs
        roi: Optional region of interest
        pc_uncertainty: Relative proton charge uncertainty

    Returns:
        List with single Transmission object
    """
    # Step 1: Combine OB runs
    effective_ob = combine_runs(ob_runs)
    logger.info(f"Combined {len(ob_runs)} OB runs")

    # Step 2: Combine sample runs
    effective_sample = combine_runs(sample_runs)
    logger.info(f"Combined {len(sample_runs)} sample runs")

    # Step 3: Calculate transmission
    transmission = calculate_transmission(effective_sample, effective_ob, roi, pc_uncertainty, pc_uncertainty)

    # Add combined run info to metadata
    transmission.metadata["n_sample_runs"] = len(sample_runs)
    transmission.metadata["n_ob_runs"] = len(ob_runs)
    transmission.metadata["sample_folders"] = [run.metadata.get("folder", "") for run in sample_runs]
    transmission.metadata["ob_folders"] = [run.metadata.get("folder", "") for run in ob_runs]

    return [transmission]


def normalization_ornl(
    sample_folders: List[str],
    ob_folders: List[str],
    nexus_dir: Optional[str] = None,
    roi: Optional[Roi] = None,
    combine_mode: bool = False,
    pc_uncertainty: float = 0.005,
    output_folder: Optional[str] = None,
    **kwargs,
) -> List[Transmission]:
    """ORNL-specific normalization implementation.

    Args:
        sample_folders: List of sample measurement folders
        ob_folders: List of open beam measurement folders
        nexus_dir: Directory containing NeXus files
        roi: Optional region of interest
        combine_mode: If True, combine all runs before processing
        pc_uncertainty: Relative proton charge uncertainty
        output_folder: Optional folder to save results
        **kwargs: Additional parameters (ignored)

    Returns:
        List of Transmission objects
    """
    # Step 1: Load data
    logger.info(f"Loading {len(sample_folders)} sample folders")
    sample_runs = load_multiple_runs(sample_folders, nexus_dir)

    logger.info(f"Loading {len(ob_folders)} OB folders")
    ob_runs = load_multiple_runs(ob_folders, nexus_dir)

    # Step 2: Process based on mode
    if combine_mode:
        logger.info("Using combined mode")
        results = process_combined_mode(sample_runs, ob_runs, roi, pc_uncertainty)
    else:
        logger.info("Using individual mode")
        results = process_individual_mode(sample_runs, ob_runs, roi, pc_uncertainty)

    # Step 3: Optionally save results
    if output_folder:
        import os
        from pathlib import Path

        os.makedirs(output_folder, exist_ok=True)
        for i, trans in enumerate(results):
            # Extract run numbers from folder paths
            if combine_mode:
                # Combined mode: use all sample run numbers
                sample_folders = trans.metadata.get("sample_folders", [])
                run_numbers = []
                for folder in sample_folders:
                    folder_name = Path(folder).name
                    # Extract run number from folder name (e.g., "Run_8022" -> "8022")
                    if "_" in folder_name:
                        run_numbers.append(folder_name.split("_")[1])
                    else:
                        run_numbers.append(folder_name)

                if run_numbers:
                    filename = f"Combined_Runs_{'_'.join(run_numbers)}_transmission.txt"
                else:
                    filename = f"transmission_{i:04d}.dat"
            else:
                # Individual mode: use single sample run number
                sample_folder = trans.metadata.get("sample_folder", "")
                if sample_folder:
                    folder_name = Path(sample_folder).name
                    # Match normalization_v1 naming: "Run_8022_transmission.txt"
                    filename = f"{folder_name}_transmission.txt"
                else:
                    filename = f"transmission_{i:04d}.dat"

            filepath = os.path.join(output_folder, filename)
            trans.save_dat(filepath)
            logger.info(f"Saved transmission to {filepath}")

    return results
