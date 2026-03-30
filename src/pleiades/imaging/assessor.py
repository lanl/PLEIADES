"""Sparsity assessor for hyperspectral neutron imaging data.

Provides ``SparsityAssessor`` which analyses a ``HyperspectralData`` cube and
returns ``SparsityMetrics`` characterising the signal-to-noise regime and
recommended processing strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from pleiades.imaging.models import HyperspectralData


@dataclass
class SparsityMetrics:
    """Quantitative sparsity characterisation of a hyperspectral dataset.

    Attributes:
        mean_transmission: Spatial and spectral mean of the transmission cube.
        min_transmission: Minimum of the spatial-mean transmission spectrum.
        resonance_depth: ``1 - min_transmission`` (depth of the deepest dip
            in the spatial-mean spectrum).
        snr_estimate: ``resonance_depth / noise_estimate`` where noise is the
            median absolute deviation across energy bins, normalised by 0.6745
            to convert MAD to an equivalent Gaussian standard deviation.
        zero_fraction: Fraction of transmission values below 0.01.
        severity_level: Integer 0–4 encoding the sparsity regime.
        severity_label: Human-readable label, e.g. ``"L0: Clean"``.
        recommendations: List of processing recommendations such as
            ``["direct_fitting"]`` or ``["bin_size=2", "increase_n_incident"]``.
    """

    mean_transmission: float
    min_transmission: float
    resonance_depth: float
    snr_estimate: float
    zero_fraction: float
    # NOTE: min_transmission and resonance_depth are derived from the
    # spatial-mean spectrum (not the global voxel minimum) so that the
    # SNR estimate is self-consistent with the MAD noise estimate.
    severity_level: int
    severity_label: str
    recommendations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Level definitions
# ---------------------------------------------------------------------------

_LEVEL_LABELS = {
    0: "L0: Clean",
    1: "L1: Mild noise",
    2: "L2: Moderate sparse",
    3: "L3: Heavy sparse",
    4: "L4: Extreme sparse",
}

_LEVEL_RECOMMENDATIONS = {
    0: ["direct_fitting"],
    1: ["direct_fitting"],
    2: ["bin_size=2"],
    3: ["bin_size=4"],
    4: ["bin_size=4", "physics_recovery"],
}


class SparsityAssessor:
    """Assess the sparsity level of a hyperspectral neutron imaging dataset.

    Estimates noise via the median absolute deviation (MAD) of the spatial
    mean spectrum across energy bins, then classifies the dataset into one of
    five severity levels (L0–L4) based on SNR and zero-fraction thresholds.

    Usage::

        assessor = SparsityAssessor()
        metrics = assessor.assess(hyperspectral)
        print(metrics.severity_label)   # e.g. "L2: Moderate sparse"
        print(metrics.recommendations)  # e.g. ["bin_size=2"]
    """

    def assess(self, hyperspectral: HyperspectralData) -> SparsityMetrics:
        """Assess sparsity of a hyperspectral dataset.

        The noise estimate is the MAD of the spatial-mean spectrum over energy
        bins, normalised to an equivalent Gaussian standard deviation
        (``noise = MAD / 0.6745``).  The spatial mean averages over H×W pixels
        for each energy bin so that pure spatial dead-pixel noise does not
        inflate the estimate.

        Severity classification rules (evaluated in order; first match wins):

        ====== ===== ============== =====================================
        Level  SNR   Zero fraction  Label
        ====== ===== ============== =====================================
        L0     >10   <1%            Clean
        L1     5–10  <5%            Mild noise
        L2     2–5   5–15%          Moderate sparse
        L3     1–2   15–40%         Heavy sparse
        L4     <1    >40%           Extreme sparse
        ====== ===== ============== =====================================

        When SNR and zero-fraction point to different levels, the *higher*
        (more severe) level is chosen.

        Args:
            hyperspectral: Loaded hyperspectral dataset with shape
                ``(n_energy, height, width)``.

        Returns:
            ``SparsityMetrics`` with all fields populated.
        """
        data = hyperspectral.data

        # --- Global scalar statistics ---
        mean_transmission = float(np.mean(data, dtype=np.float64))
        zero_fraction = float(np.mean(data < 0.01))

        # --- Noise & signal from the spatial-mean spectrum ---
        # spatial_mean_spectrum: shape (n_energy,)
        spatial_mean = np.mean(data, axis=(1, 2), dtype=np.float64)
        min_transmission = float(np.min(spatial_mean))
        resonance_depth = max(0.0, 1.0 - min_transmission)

        mad = float(np.median(np.abs(spatial_mean - np.median(spatial_mean))))
        noise_estimate = mad / 0.6745  # normalise MAD → Gaussian std equivalent
        if resonance_depth == 0.0:
            snr_estimate = 0.0
        elif noise_estimate == 0.0:
            snr_estimate = float("inf")
        else:
            snr_estimate = resonance_depth / noise_estimate

        # --- Classify severity ---
        severity_level = _classify_severity(snr_estimate, zero_fraction)
        severity_label = _LEVEL_LABELS[severity_level]
        recommendations = list(_LEVEL_RECOMMENDATIONS[severity_level])

        return SparsityMetrics(
            mean_transmission=mean_transmission,
            min_transmission=min_transmission,
            resonance_depth=resonance_depth,
            snr_estimate=snr_estimate,
            zero_fraction=zero_fraction,
            severity_level=severity_level,
            severity_label=severity_label,
            recommendations=recommendations,
        )


def _classify_severity(snr: float, zero_fraction: float) -> int:
    """Map (SNR, zero_fraction) to a severity level 0–4.

    Both axes are evaluated independently and the *more severe* (higher) level
    is returned.

    Args:
        snr: Signal-to-noise ratio (resonance_depth / noise_estimate).
        zero_fraction: Fraction of transmission values below 0.01.

    Returns:
        Severity level integer 0–4.
    """
    # SNR axis
    if snr > 10.0:
        snr_level = 0
    elif snr >= 5.0:
        snr_level = 1
    elif snr >= 2.0:
        snr_level = 2
    elif snr >= 1.0:
        snr_level = 3
    else:
        snr_level = 4

    # Zero-fraction axis
    if zero_fraction < 0.01:
        zf_level = 0
    elif zero_fraction < 0.05:
        zf_level = 1
    elif zero_fraction < 0.15:
        zf_level = 2
    elif zero_fraction <= 0.40:
        zf_level = 3
    else:
        zf_level = 4

    return max(snr_level, zf_level)
