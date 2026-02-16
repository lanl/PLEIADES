"""
2D resonance imaging module for PLEIADES.

This module provides tools for spatially-resolved neutron resonance fitting
from hyperspectral imaging data. It orchestrates batch SAMMY fitting across
detector pixels to generate isotope abundance maps.

Main components:
- HyperspectralLoader: Load and manage hyperspectral TIFF data
- BatchFittingOrchestrator: Parallel SAMMY fitting across pixels
- ResultsAggregator: Build 2D abundance maps from pixel results

Example:
    >>> from pleiades.imaging import HyperspectralLoader
    >>> loader = HyperspectralLoader("data.tif", energy=energy_array)
    >>> hyperspectral = loader.load()
    >>> for pixel in loader.iter_pixels():
    ...     # Process each PixelSpectrum
    ...     pass
"""

from pleiades.imaging.aggregator import ResultsAggregator
from pleiades.imaging.loader import HyperspectralLoader
from pleiades.imaging.models import HyperspectralData, Imaging2DResults, PixelFitResult, PixelSpectrum

__all__ = [
    "HyperspectralLoader",
    "HyperspectralData",
    "PixelSpectrum",
    "PixelFitResult",
    "Imaging2DResults",
    "ResultsAggregator",
]
