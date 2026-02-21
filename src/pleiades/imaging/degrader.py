"""Hyperspectral data degrader for validation of recovery methods.

Provides ``DataDegrader`` to apply physically-motivated noise and degradation
to clean hyperspectral transmission data, enabling controlled benchmarking of
denoising and recovery algorithms.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np


class DataDegrader:
    """Degrade clean hyperspectral transmission data for validation of recovery methods.

    All operations are reproducible via ``random_seed``. The RNG state is
    consumed in call order, so calls must be made in the same order across
    runs to reproduce results.

    Args:
        random_seed: Seed for the internal NumPy random generator. Pass an
            integer for reproducible degradation, or ``None`` for a random seed.
    """

    def __init__(self, random_seed: Optional[int] = None) -> None:
        self.rng = np.random.default_rng(random_seed)

    def add_poisson_noise(self, data: np.ndarray, n_incident: float = 1000.0) -> np.ndarray:
        """Simulate photon-counting noise via a Poisson process.

        For each transmission value ``T``, the observed count is drawn from
        ``Poisson(n_incident * T)`` and then normalised back to transmission:
        ``T_obs = N_out / n_incident``.  The result is clipped to ``[0, 1]``.

        Args:
            data: Transmission array of any shape with values in ``[0, 1]``.
            n_incident: Mean number of incident photons per pixel per energy
                bin.  Higher values → less noise.  Must be positive.

        Returns:
            Noisy transmission array of the same shape, clipped to ``[0, 1]``.

        Raises:
            ValueError: If ``n_incident`` is not positive.
        """
        if n_incident <= 0:
            raise ValueError(f"n_incident must be positive, got {n_incident}")
        counts = self.rng.poisson(lam=n_incident * data)
        return np.clip(counts / n_incident, 0.0, 1.0)

    def add_dead_pixels(self, data: np.ndarray, dead_fraction: float = 0.05) -> Tuple[np.ndarray, np.ndarray]:
        """Randomly set whole-pixel spectra to 1.0 (open-beam / detector dead).

        A fraction ``dead_fraction`` of spatial pixels is selected uniformly at
        random.  Their full spectrum (all energy bins) is set to 1.0, which
        corresponds to a "dead" detector element that records only open-beam
        counts.

        Args:
            data: 3-D transmission array of shape ``(n_energy, height, width)``.
            dead_fraction: Fraction of spatial pixels to mark dead.  Must be
                in ``[0, 1)``.

        Returns:
            Tuple ``(degraded_data, dead_mask)`` where:
            - ``degraded_data`` is a copy of ``data`` with dead pixels set to 1.0.
            - ``dead_mask`` is a boolean array of shape ``(height, width)`` where
              ``True`` indicates a dead pixel.

        Raises:
            ValueError: If ``data`` is not 3-D or ``dead_fraction`` is out of range.
        """
        if data.ndim != 3:
            raise ValueError(f"data must be 3-D (n_energy, height, width), got {data.ndim}D")
        if not (0.0 <= dead_fraction < 1.0):
            raise ValueError(f"dead_fraction must be in [0, 1), got {dead_fraction}")

        _, height, width = data.shape
        n_pixels = height * width
        n_dead = int(round(dead_fraction * n_pixels))

        flat_indices = self.rng.choice(n_pixels, size=n_dead, replace=False)
        dead_mask = np.zeros(n_pixels, dtype=bool)
        dead_mask[flat_indices] = True
        dead_mask = dead_mask.reshape(height, width)

        degraded = data.copy()
        # Vectorised: set all energy bins to 1.0 for dead pixels.
        degraded[:, dead_mask] = 1.0
        return degraded, dead_mask

    def degrade_to_level(self, data: np.ndarray, target_level: int) -> np.ndarray:
        """Apply a preset degradation level to the data.

        Preset definitions:

        ====== ================ ============== =====================================
        Level  n_incident       Dead pixels    Description
        ====== ================ ============== =====================================
        L1     5 000            0%             Mild Poisson noise
        L2     500              0%             Moderate noise (SNR ~5)
        L3     100              5%             Heavy noise + sparse dead pixels
        L4     20               10%            Extreme noise + many dead pixels
        ====== ================ ============== =====================================

        For levels with dead pixels (L3, L4) the dead pixel mask is applied
        **after** Poisson noise so dead pixels always read exactly 1.0.

        Args:
            data: 3-D transmission array ``(n_energy, height, width)`` with
                values in ``[0, 1]``.
            target_level: Degradation level (1–4).

        Returns:
            Degraded transmission array of the same shape.

        Raises:
            ValueError: If ``target_level`` is not 1–4.
        """
        if target_level not in (1, 2, 3, 4):
            raise ValueError(f"target_level must be 1–4, got {target_level}")

        presets = {
            1: {"n_incident": 5000.0, "dead_fraction": 0.0},
            2: {"n_incident": 500.0, "dead_fraction": 0.0},
            3: {"n_incident": 100.0, "dead_fraction": 0.05},
            4: {"n_incident": 20.0, "dead_fraction": 0.10},
        }
        cfg = presets[target_level]
        degraded = self.add_poisson_noise(data, n_incident=cfg["n_incident"])
        if cfg["dead_fraction"] > 0.0:
            degraded, _ = self.add_dead_pixels(degraded, dead_fraction=cfg["dead_fraction"])
        return degraded
