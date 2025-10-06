"""
Router for facility-specific normalization implementations.

This module provides the main entry point for neutron imaging normalization,
delegating to appropriate facility-specific implementations based on the
facility parameter.
"""

from typing import List, Optional, Union

from pleiades.processing import Facility, Roi
from pleiades.processing.models_ornl import Transmission
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name="normalization")


def normalization(
    list_sample_folders: Union[List[str], str],
    list_obs_folders: Union[List[str], str],
    nexus_path: Optional[str] = None,
    roi: Optional[Roi] = None,
    facility: Facility = Facility.ornl,
    combine_mode: bool = False,
    output_folder: Optional[str] = None,
    **kwargs,
) -> List[Transmission]:
    """Main entry point for neutron imaging normalization.

    Routes to facility-specific implementations based on the facility parameter.

    Args:
        list_sample_folders: List of sample folders or single folder path
        list_obs_folders: List of open beam folders or single folder path
        nexus_path: Path to nexus directory (for ORNL)
        roi: Optional region of interest
        facility: Facility identifier (ornl, lanl, etc.)
        combine_mode: If True, combine all runs before processing
        output_folder: Optional folder to save results
        **kwargs: Additional facility-specific parameters

    Returns:
        List[Transmission]: Transmission objects containing normalized data

    Raises:
        NotImplementedError: If facility is not supported

    Example:
        >>> from pleiades.processing import normalization, Facility, Roi
        >>>
        >>> # Use ORNL implementation
        >>> results = normalization(
        ...     list_sample_folders=["sample1", "sample2"],
        ...     list_obs_folders=["ob1", "ob2"],
        ...     facility=Facility.ornl
        ... )
    """
    # Convert single strings to lists
    if isinstance(list_sample_folders, str):
        list_sample_folders = [list_sample_folders]
    if isinstance(list_obs_folders, str):
        list_obs_folders = [list_obs_folders]

    # Route to facility-specific implementation
    if facility == Facility.ornl:
        logger.info("Using ORNL-specific normalization")
        from pleiades.processing.normalization_ornl import normalization_ornl

        return normalization_ornl(
            sample_folders=list_sample_folders,
            ob_folders=list_obs_folders,
            nexus_dir=nexus_path,
            roi=roi,
            combine_mode=combine_mode,
            output_folder=output_folder,
            **kwargs,
        )

    elif facility == Facility.lanl:
        raise NotImplementedError(
            "LANL normalization not yet implemented. Use use_legacy=True for the old implementation."
        )

    else:
        raise NotImplementedError(
            f"Normalization for facility '{facility}' not implemented. "
            f"Supported facilities: {[Facility.ornl]}. "
            "Use use_legacy=True for the old implementation."
        )


# For backward compatibility, export the main function
__all__ = ["normalization"]
