"""NMF-based spectral decomposition and denoising for 2D imaging.

Applies non-negative matrix factorisation (NMF) to the attenuation domain
``A = -ln(T)`` of hyperspectral neutron transmission data.  The low-rank
decomposition simultaneously decomposes the image into isotopic abundance
maps and filters spectral noise.

The approach follows the Fast Hyperspectral Reconstruction (FHR) method
described in `Venkatakrishnan et al., IEEE 2025
<https://arxiv.org/html/2410.22500>`_.

Mathematical formulation::

    A  ≈  W @ H

where ``A`` has shape ``(n_pixels, n_energy)``, ``W`` has shape
``(n_pixels, n_components)`` (spatial coefficients), and ``H`` has shape
``(n_components, n_energy)`` (spectral basis functions).  Both ``W`` and
``H`` are constrained to be non-negative.
"""

from __future__ import annotations

import numpy as np

from pleiades.imaging.models import HyperspectralData, Imaging2DResults
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


class NMFRecovery:
    """NMF-based isotopic decomposition and spectral denoising.

    Decomposes hyperspectral transmission data into a small number of
    non-negative spectral components and their spatial abundance maps.
    Works in the attenuation domain ``A = -ln(T)`` where the Beer-Lambert
    law gives a linear mixing model.

    Args:
        n_components: Number of spectral components to extract (typically
            the number of isotopes).  Must be >= 1.
        max_iter: Maximum number of multiplicative-update iterations.
        random_state: Seed for reproducible initialisation.

    Example::

        nmf = NMFRecovery(n_components=2)
        result = nmf.decompose(hyperspectral)  # → Imaging2DResults
        denoised = nmf.denoise(hyperspectral)  # → HyperspectralData
    """

    TRANSMISSION_FLOOR = 1e-6
    TRANSMISSION_CEIL = 1.0 - 1e-6

    def __init__(
        self,
        n_components: int = 2,
        max_iter: int = 200,
        random_state: int | None = None,
    ) -> None:
        if n_components < 1:
            raise ValueError(f"n_components must be >= 1, got {n_components}")
        self.n_components = n_components
        self.max_iter = max_iter
        self.random_state = random_state
        self.spectral_basis_: np.ndarray | None = None
        self.spatial_coefficients_: np.ndarray | None = None

    # ------------------------------------------------------------------
    # Core NMF
    # ------------------------------------------------------------------

    def _nmf_multiplicative_updates(
        self,
        V: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run NMF via multiplicative updates (Frobenius norm).

        Solves ``min_{W>=0, H>=0} ||V - W @ H||_F^2``.

        Args:
            V: Non-negative data matrix, shape ``(n_samples, n_features)``.

        Returns:
            ``(W, H)`` where ``W`` is ``(n_samples, n_components)`` and
            ``H`` is ``(n_components, n_features)``.
        """
        n_samples, n_features = V.shape
        k = self.n_components
        rng = np.random.default_rng(self.random_state)

        # NNDSVD-like initialisation: small positive random values
        avg = np.sqrt(V.mean() / k)
        W = np.abs(rng.normal(0, avg, (n_samples, k))) + 1e-10
        H = np.abs(rng.normal(0, avg, (k, n_features))) + 1e-10

        eps = 1e-10
        for i in range(self.max_iter):
            # Update W: W *= (V @ H^T) / (W @ H @ H^T + eps)
            W *= (V @ H.T) / (W @ (H @ H.T) + eps)

            # Update H: H *= (W^T @ V) / (W^T @ W @ H + eps)
            H *= (W.T @ V) / ((W.T @ W) @ H + eps)

        return W, H

    def _to_attenuation_matrix(self, hyperspectral: HyperspectralData) -> np.ndarray:
        """Convert hyperspectral transmission cube to 2-D attenuation matrix.

        Args:
            hyperspectral: Input data with shape ``(n_energy, height, width)``.

        Returns:
            Attenuation matrix of shape ``(n_pixels, n_energy)`` where
            ``n_pixels = height * width``.
        """
        T = np.clip(hyperspectral.data, self.TRANSMISSION_FLOOR, self.TRANSMISSION_CEIL)
        A = -np.log(T)  # (n_energy, height, width)
        n_e, h, w = A.shape
        return A.reshape(n_e, h * w).T  # (n_pixels, n_energy)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decompose(self, hyperspectral: HyperspectralData) -> Imaging2DResults:
        """Decompose hyperspectral data into abundance maps via NMF.

        Converts transmission to attenuation, runs NMF, and normalises
        the spatial coefficients to fractional abundances (sum-to-one per
        pixel).

        Args:
            hyperspectral: Input hyperspectral data.

        Returns:
            :class:`Imaging2DResults` with ``n_components`` abundance maps.
            The ``isotope_names`` field contains generic labels
            ``["NMF-0", "NMF-1", ...]``; use :meth:`label_components`
            to assign isotope names from reference spectra.
        """
        n_e, height, width = hyperspectral.shape
        logger.info(f"NMF decomposition: {height}x{width} pixels, {n_e} energy bins, {self.n_components} components")

        V = self._to_attenuation_matrix(hyperspectral)
        W, H = self._nmf_multiplicative_updates(V)

        # Store learned basis for denoise() and label_components()
        self.spectral_basis_ = H  # (n_components, n_energy)
        self.spatial_coefficients_ = W  # (n_pixels, n_components)

        # Reshape to spatial maps
        spatial_maps = W.T.reshape(self.n_components, height, width)

        # Normalise to fractional abundances
        coeff_sum = spatial_maps.sum(axis=0, keepdims=True)
        abundance_maps = np.where(coeff_sum > 1e-10, spatial_maps / coeff_sum, np.nan)

        success_mask = np.isfinite(abundance_maps[0])

        # Chi-squared: reconstruction quality per pixel
        recon = W @ H  # (n_pixels, n_energy)
        residuals = V - recon
        chi_squared_flat = np.sum(residuals**2, axis=1)  # (n_pixels,)
        chi_squared_map = chi_squared_flat.reshape(height, width)

        isotope_names = [f"NMF-{i}" for i in range(self.n_components)]

        logger.info(
            f"NMF complete: {np.sum(success_mask)} pixels decomposed, "
            f"mean reconstruction error = {np.sqrt(np.mean(chi_squared_flat)):.4f}"
        )

        return Imaging2DResults(
            abundance_maps=abundance_maps,
            isotope_names=isotope_names,
            chi_squared_map=chi_squared_map,
            success_mask=success_mask,
            source_hyperspectral=hyperspectral,
            metadata={
                "method": "nmf_recovery",
                "n_components": self.n_components,
                "max_iter": self.max_iter,
            },
        )

    def denoise(self, hyperspectral: HyperspectralData) -> HyperspectralData:
        """Denoise hyperspectral data by projecting onto the NMF subspace.

        Decomposes the data via NMF, then reconstructs ``A_denoised = W @ H``
        and converts back to transmission domain.  The low-rank constraint
        filters spectral noise while preserving resonance structure.

        Args:
            hyperspectral: Noisy input data.

        Returns:
            Denoised :class:`HyperspectralData` with the same shape and
            energy grid as the input.
        """
        n_e, height, width = hyperspectral.shape

        V = self._to_attenuation_matrix(hyperspectral)
        W, H = self._nmf_multiplicative_updates(V)

        self.spectral_basis_ = H
        self.spatial_coefficients_ = W

        # Reconstruct and convert back to transmission
        recon_A = W @ H  # (n_pixels, n_energy)
        recon_T = np.exp(-recon_A)  # back to transmission
        recon_T = np.clip(recon_T, 0.0, 1.0)
        recon_3d = recon_T.T.reshape(n_e, height, width)

        return HyperspectralData(
            data=recon_3d.astype(np.float32),
            energy=hyperspectral.energy,
            uncertainty=hyperspectral.uncertainty,
            source_file=hyperspectral.source_file,
            metadata={**hyperspectral.metadata, "nmf_denoised": True},
        )

    def label_components(
        self,
        result: Imaging2DResults,
        reference_spectra: list,
    ) -> Imaging2DResults:
        """Assign isotope names to NMF components by matching reference spectra.

        Computes the correlation between each NMF spectral basis vector and
        each reference absorption profile, then assigns isotope names via
        the Hungarian algorithm (best overall matching).

        Args:
            result: :class:`Imaging2DResults` from :meth:`decompose`.
            reference_spectra: List of :class:`ReferenceSpectrum` with
                known isotope names and absorption profiles.

        Returns:
            New :class:`Imaging2DResults` with reordered abundance maps
            and correct ``isotope_names``.
        """
        if self.spectral_basis_ is None:
            raise RuntimeError("Must call decompose() before label_components()")

        n_comp = self.spectral_basis_.shape[0]
        n_ref = len(reference_spectra)

        # Build correlation matrix
        corr = np.zeros((n_comp, n_ref))
        for i in range(n_comp):
            for j in range(n_ref):
                corr[i, j] = np.corrcoef(self.spectral_basis_[i], reference_spectra[j].absorption)[0, 1]

        # Greedy assignment: for each reference, find the best-matching component
        used_comps: set[int] = set()
        assignments: list[tuple[int, int]] = []  # (component_idx, ref_idx)
        for ref_idx in range(n_ref):
            best_comp = -1
            best_val = -1.0
            for comp_idx in range(n_comp):
                if comp_idx not in used_comps and corr[comp_idx, ref_idx] > best_val:
                    best_val = corr[comp_idx, ref_idx]
                    best_comp = comp_idx
            if best_comp >= 0:
                assignments.append((best_comp, ref_idx))
                used_comps.add(best_comp)

        # Reorder abundance maps and assign names
        new_order = [a[0] for a in assignments]
        # Add any unmatched components at the end
        for i in range(n_comp):
            if i not in used_comps:
                new_order.append(i)

        reordered_maps = result.abundance_maps[new_order]
        isotope_names = []
        for comp_idx, ref_idx in assignments:
            isotope_names.append(reference_spectra[ref_idx].isotope_name)
        for i in range(n_comp):
            if i not in used_comps:
                isotope_names.append(f"NMF-{i}")

        return Imaging2DResults(
            abundance_maps=reordered_maps,
            isotope_names=isotope_names,
            chi_squared_map=result.chi_squared_map,
            success_mask=result.success_mask,
            source_hyperspectral=result.source_hyperspectral,
            metadata={**result.metadata, "labeled": True},
        )
