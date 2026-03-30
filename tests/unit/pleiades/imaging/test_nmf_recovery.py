"""Unit tests for pleiades.imaging.nmf_recovery.NMFRecovery.

Tests cover:
  - NMF decomposition on synthetic data with known ground truth
  - Component identification via reference spectra correlation
  - Denoising (reconstruction quality vs clean data)
  - Edge cases: single component, open-beam pixels, NaN handling
  - Integration with Imaging2DResults
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pleiades.imaging.models import HyperspectralData, Imaging2DResults

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hyperspectral(
    data: np.ndarray,
    energy: np.ndarray | None = None,
    uncertainty: np.ndarray | None = None,
) -> HyperspectralData:
    """Wrap a 3-D array in HyperspectralData with a synthetic source path."""
    n_e = data.shape[0]
    if energy is None:
        energy = np.linspace(1.0, 100.0, n_e)
    return HyperspectralData(
        data=data,
        energy=energy,
        uncertainty=uncertainty,
        source_file=Path("/tmp/test.tif"),
    )


def _make_two_component_data(n_energy=100, height=16, width=16, noise_level=0.0, seed=42):
    """Create synthetic hyperspectral data with two distinct absorption components.

    Component 0: peaks at energy indices ~25 and ~75
    Component 1: peaks at energy indices ~50

    Returns (data_3d, ground_truth_maps, basis_spectra) where:
    - data_3d: (n_energy, height, width) transmission
    - ground_truth_maps: (2, height, width) abundance fractions
    - basis_spectra: (2, n_energy) absorption profiles
    """
    rng = np.random.default_rng(seed)
    energy = np.linspace(1, 100, n_energy)

    # Create two distinct absorption profiles
    sigma = 3.0
    basis0 = 1.5 * np.exp(-0.5 * ((energy - 25) / sigma) ** 2) + 1.0 * np.exp(-0.5 * ((energy - 75) / sigma) ** 2)
    basis1 = 2.0 * np.exp(-0.5 * ((energy - 50) / sigma) ** 2)
    basis = np.stack([basis0, basis1])  # (2, n_energy)

    # Spatial abundance maps: component 0 in top half, component 1 in bottom half
    gt_maps = np.zeros((2, height, width))
    gt_maps[0, : height // 2, :] = 0.8
    gt_maps[0, height // 2 :, :] = 0.2
    gt_maps[1, : height // 2, :] = 0.2
    gt_maps[1, height // 2 :, :] = 0.8

    # Build attenuation cube and convert to transmission
    atten = np.zeros((n_energy, height, width))
    for r in range(height):
        for c in range(width):
            atten[:, r, c] = gt_maps[0, r, c] * basis0 + gt_maps[1, r, c] * basis1

    data = np.exp(-atten)

    # Add Poisson-like noise if requested
    if noise_level > 0:
        n_incident = 1.0 / noise_level
        counts = rng.poisson(n_incident * data)
        data = np.clip(counts / n_incident, 0.0, 1.0)

    return data, gt_maps, basis, energy


# ---------------------------------------------------------------------------
# TestNMFDecomposition
# ---------------------------------------------------------------------------


class TestNMFDecomposition:
    """Tests for NMFRecovery.decompose on synthetic data."""

    def test_returns_imaging2d_results(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data()
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2)
        result = nmf.decompose(hs)
        assert isinstance(result, Imaging2DResults)

    def test_abundance_maps_shape(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data(height=8, width=10)
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2)
        result = nmf.decompose(hs)
        assert result.abundance_maps.shape == (2, 8, 10)

    def test_abundance_maps_sum_to_one(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data()
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2)
        result = nmf.decompose(hs)
        sums = np.nansum(result.abundance_maps, axis=0)
        valid = sums[result.success_mask]
        np.testing.assert_allclose(valid, 1.0, atol=1e-6)

    def test_recovers_spatial_pattern_clean(self):
        """NMF should recover the spatial pattern on clean data."""
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, gt_maps, _, energy = _make_two_component_data(height=16, width=16)
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2, random_state=42)
        result = nmf.decompose(hs)

        # NMF component ordering is arbitrary — find the best match
        # by checking which component correlates with gt_maps[0]
        corr0 = np.corrcoef(result.abundance_maps[0].ravel(), gt_maps[0].ravel())[0, 1]
        corr1 = np.corrcoef(result.abundance_maps[1].ravel(), gt_maps[0].ravel())[0, 1]
        best_corr = max(abs(corr0), abs(corr1))
        assert best_corr > 0.9, f"Best correlation with ground truth = {best_corr:.3f}, expected > 0.9"

    def test_recovers_spatial_pattern_noisy(self):
        """NMF should recover spatial patterns even with moderate noise."""
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, gt_maps, _, energy = _make_two_component_data(height=16, width=16, noise_level=0.1)
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2, random_state=42)
        result = nmf.decompose(hs)

        corr0 = np.corrcoef(result.abundance_maps[0].ravel(), gt_maps[0].ravel())[0, 1]
        corr1 = np.corrcoef(result.abundance_maps[1].ravel(), gt_maps[0].ravel())[0, 1]
        best_corr = max(abs(corr0), abs(corr1))
        assert best_corr > 0.7, f"Best correlation = {best_corr:.3f}, expected > 0.7 for noisy data"

    def test_spectral_basis_has_correct_shape(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data(n_energy=50)
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2)
        result = nmf.decompose(hs)
        assert result.metadata["spectral_basis"].shape == (2, 50)

    def test_spectral_basis_non_negative(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data()
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2)
        result = nmf.decompose(hs)
        assert np.all(result.metadata["spectral_basis"] >= 0)

    def test_metadata_contains_method(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data()
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2)
        result = nmf.decompose(hs)
        assert result.metadata["method"] == "nmf_recovery"


# ---------------------------------------------------------------------------
# TestNMFDenoise
# ---------------------------------------------------------------------------


class TestNMFDenoise:
    """Tests for NMFRecovery.denoise."""

    def test_denoised_shape_matches_input(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data(noise_level=0.1)
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2)
        denoised = nmf.denoise(hs)
        assert denoised.shape == hs.shape

    def test_denoised_closer_to_clean_than_noisy(self):
        """NMF-denoised data should be closer to clean truth than the noisy input."""
        from pleiades.imaging.nmf_recovery import NMFRecovery

        clean_data, _, _, energy = _make_two_component_data(noise_level=0.0)
        noisy_data, _, _, _ = _make_two_component_data(noise_level=0.1)
        hs_noisy = _make_hyperspectral(noisy_data, energy=energy)

        nmf = NMFRecovery(n_components=2)
        denoised = nmf.denoise(hs_noisy)

        err_noisy = np.mean((noisy_data - clean_data) ** 2)
        err_denoised = np.mean((denoised.data - clean_data) ** 2)
        assert err_denoised < err_noisy, f"Denoised MSE {err_denoised:.6f} >= noisy MSE {err_noisy:.6f}"

    def test_denoised_values_in_valid_range(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data(noise_level=0.1)
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2)
        denoised = nmf.denoise(hs)
        # Transmission should be in (0, 1] after reconstruction
        assert np.all(denoised.data > 0)
        assert np.all(denoised.data <= 1.0 + 1e-6)


# ---------------------------------------------------------------------------
# TestComponentLabeling
# ---------------------------------------------------------------------------


class TestComponentLabeling:
    """Tests for labeling NMF components using reference spectra."""

    def test_label_components_reorders_maps(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery
        from pleiades.imaging.recovery import ReferenceSpectrum

        data, gt_maps, basis, energy = _make_two_component_data()
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2, random_state=42)
        result = nmf.decompose(hs)

        # Create reference spectra matching the known basis
        refs = [
            ReferenceSpectrum(isotope_name="Iso-A", energy=energy, transmission=np.exp(-basis[0]), absorption=basis[0]),
            ReferenceSpectrum(isotope_name="Iso-B", energy=energy, transmission=np.exp(-basis[1]), absorption=basis[1]),
        ]
        # label_components is a static method that reads basis from result.metadata
        labeled = NMFRecovery.label_components(result, refs)
        assert labeled.isotope_names == ["Iso-A", "Iso-B"]


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestNMFEdgeCases:
    """Edge case tests for NMF recovery."""

    def test_single_component(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data()
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=1)
        result = nmf.decompose(hs)
        assert result.abundance_maps.shape[0] == 1

    def test_open_beam_pixels_handled(self):
        """Pixels with T~1 everywhere should not crash NMF."""
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data(height=8, width=8)
        # Set some pixels to open beam
        data[:, 0, 0] = 1.0
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2)
        result = nmf.decompose(hs)
        assert isinstance(result, Imaging2DResults)

    def test_invalid_n_components_raises(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        with pytest.raises(ValueError, match="n_components"):
            NMFRecovery(n_components=0)

    def test_max_iter_respected(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data()
        hs = _make_hyperspectral(data, energy=energy)
        nmf = NMFRecovery(n_components=2, max_iter=5)
        result = nmf.decompose(hs)
        assert isinstance(result, Imaging2DResults)

    def test_reproducible_with_seed(self):
        from pleiades.imaging.nmf_recovery import NMFRecovery

        data, _, _, energy = _make_two_component_data()
        hs = _make_hyperspectral(data, energy=energy)

        nmf1 = NMFRecovery(n_components=2, random_state=42)
        r1 = nmf1.decompose(hs)
        nmf2 = NMFRecovery(n_components=2, random_state=42)
        r2 = nmf2.decompose(hs)
        np.testing.assert_array_equal(r1.abundance_maps, r2.abundance_maps)
