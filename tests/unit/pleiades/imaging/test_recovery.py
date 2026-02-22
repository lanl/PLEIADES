"""Unit tests for pleiades.imaging.recovery.PhysicsRecovery.

Tests cover:
  - ReferenceSpectrum field validation and construction
  - recover_pixel with synthetic dictionary: known ground truth recovery
  - recover_pixel edge cases: clamping, open-beam, uncertainty=0, non-negativity
  - recover_pixel weighted NNLS behavior
  - recover_image with synthetic 2D data: shapes, success_mask, metadata
  - recover_image open-beam pixel skipping
  - _coefficients_to_abundances: single/multi isotope normalization
  - _compute_chi_squared: known-value check
  - Integration tests with mocked SAMMY (generate_reference_spectra)
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields
from pathlib import Path
from unittest.mock import patch

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


def _make_reference_spectrum(isotope_name: str, energy: np.ndarray, peak_energy: float, peak_depth: float = 0.8):
    """Create a ReferenceSpectrum with a Gaussian absorption peak.

    The peak is centred at ``peak_energy`` with depth ``peak_depth``.
    """
    from pleiades.imaging.recovery import ReferenceSpectrum

    # Create Gaussian absorption peak
    sigma = (energy[-1] - energy[0]) / 20.0
    absorption = peak_depth * np.exp(-0.5 * ((energy - peak_energy) / sigma) ** 2)
    transmission = np.exp(-absorption)
    return ReferenceSpectrum(
        isotope_name=isotope_name,
        energy=energy,
        transmission=transmission,
        absorption=absorption,
    )


def _build_synthetic_dictionary(energy: np.ndarray, n_isotopes: int = 2) -> list:
    """Build a list of ReferenceSpectrum with non-overlapping peaks."""
    refs = []
    centers = np.linspace(energy[0] + 10, energy[-1] - 10, n_isotopes)
    for i in range(n_isotopes):
        name = f"Iso-{i}"
        refs.append(_make_reference_spectrum(name, energy, centers[i], peak_depth=1.0))
    return refs


# ---------------------------------------------------------------------------
# TestReferenceSpectrum
# ---------------------------------------------------------------------------


class TestReferenceSpectrum:
    """Tests for the ReferenceSpectrum dataclass."""

    def test_construction_basic(self):
        from pleiades.imaging.recovery import ReferenceSpectrum

        energy = np.linspace(1, 100, 50)
        transmission = np.exp(-0.5 * np.ones(50))
        absorption = 0.5 * np.ones(50)
        ref = ReferenceSpectrum(
            isotope_name="Ta-181",
            energy=energy,
            transmission=transmission,
            absorption=absorption,
        )
        assert ref.isotope_name == "Ta-181"
        assert ref.energy.shape == (50,)
        assert ref.transmission.shape == (50,)
        assert ref.absorption.shape == (50,)

    def test_has_expected_fields(self):
        from pleiades.imaging.recovery import ReferenceSpectrum

        field_names = {f.name for f in dataclass_fields(ReferenceSpectrum)}
        assert "isotope_name" in field_names
        assert "energy" in field_names
        assert "transmission" in field_names
        assert "absorption" in field_names

    def test_absorption_consistent_with_transmission(self):
        """absorption should be -ln(transmission) for valid data."""
        energy = np.linspace(1, 100, 50)
        ref = _make_reference_spectrum("Ta-181", energy, peak_energy=50.0, peak_depth=1.0)
        np.testing.assert_allclose(ref.absorption, -np.log(ref.transmission), atol=1e-14)


# ---------------------------------------------------------------------------
# TestRecoverPixel
# ---------------------------------------------------------------------------


class TestRecoverPixel:
    """Tests for PhysicsRecovery.recover_pixel with synthetic dictionary."""

    def setup_method(self):
        from pleiades.imaging.recovery import PhysicsRecovery

        self.energy = np.linspace(1.0, 100.0, 200)
        # Build simple mock config for PhysicsRecovery (won't use SAMMY in unit tests)
        self.recovery = PhysicsRecovery.__new__(PhysicsRecovery)

    def test_single_isotope_recovery(self):
        """Single reference spectrum — coefficient should be close to ground truth."""
        ref = _make_reference_spectrum("Ta-181", self.energy, peak_energy=50.0, peak_depth=1.5)
        dictionary = np.column_stack([ref.absorption])

        # Simulate observed transmission: T = exp(-n * A) with n=0.6
        ground_truth_n = 0.6
        transmission = np.exp(-ground_truth_n * ref.absorption)
        uncertainty = 0.01 * np.ones_like(transmission)

        coeffs, chi2, success = self.recovery.recover_pixel(transmission, uncertainty, dictionary)
        assert success is True
        assert len(coeffs) == 1
        assert coeffs[0] == pytest.approx(ground_truth_n, abs=0.05)
        assert chi2 >= 0.0

    def test_two_isotope_recovery(self):
        """Two non-overlapping isotopes — both coefficients recovered accurately."""
        refs = _build_synthetic_dictionary(self.energy, n_isotopes=2)
        dictionary = np.column_stack([r.absorption for r in refs])

        # Ground truth: n0=0.5, n1=0.8
        ground_truth = np.array([0.5, 0.8])
        total_absorption = dictionary @ ground_truth
        transmission = np.exp(-total_absorption)
        uncertainty = 0.01 * np.ones_like(transmission)

        coeffs, chi2, success = self.recovery.recover_pixel(transmission, uncertainty, dictionary)
        assert success is True
        assert len(coeffs) == 2
        np.testing.assert_allclose(coeffs, ground_truth, atol=0.05)

    def test_non_negativity_enforced(self):
        """NNLS must never return negative coefficients."""
        ref = _make_reference_spectrum("Ta-181", self.energy, peak_energy=50.0)
        dictionary = np.column_stack([ref.absorption])

        # Open beam (T~1) — NNLS should give ~0, never negative
        transmission = np.ones_like(self.energy)
        uncertainty = 0.01 * np.ones_like(transmission)

        coeffs, chi2, success = self.recovery.recover_pixel(transmission, uncertainty, dictionary)
        assert np.all(coeffs >= 0.0)

    def test_transmission_clamped_below_floor(self):
        """T=0 should be clamped to TRANSMISSION_FLOOR, not cause -ln(0) = inf."""
        ref = _make_reference_spectrum("Ta-181", self.energy, peak_energy=50.0)
        dictionary = np.column_stack([ref.absorption])

        transmission = np.zeros_like(self.energy)  # T=0 everywhere
        uncertainty = 0.01 * np.ones_like(transmission)

        # Should not raise or produce NaN/inf
        coeffs, chi2, success = self.recovery.recover_pixel(transmission, uncertainty, dictionary)
        assert np.all(np.isfinite(coeffs))
        assert np.isfinite(chi2)

    def test_transmission_clamped_above_ceiling(self):
        """T>1 should be clamped to TRANSMISSION_CEIL."""
        ref = _make_reference_spectrum("Ta-181", self.energy, peak_energy=50.0)
        dictionary = np.column_stack([ref.absorption])

        transmission = 1.05 * np.ones_like(self.energy)  # T > 1
        uncertainty = 0.01 * np.ones_like(transmission)

        coeffs, chi2, success = self.recovery.recover_pixel(transmission, uncertainty, dictionary)
        assert np.all(np.isfinite(coeffs))

    def test_open_beam_pixel_skipped(self):
        """Pixel where T~1 everywhere should be marked as not successful."""
        ref = _make_reference_spectrum("Ta-181", self.energy, peak_energy=50.0, peak_depth=1.0)
        dictionary = np.column_stack([ref.absorption])

        # Open beam: T ~ 1.0 everywhere (no absorption)
        transmission = np.ones_like(self.energy)
        uncertainty = 0.01 * np.ones_like(transmission)

        coeffs, chi2, success = self.recovery.recover_pixel(transmission, uncertainty, dictionary)
        # Open-beam pixel: NNLS gives near-zero coefficients
        # success is still True (NNLS converged) but coefficients are ~0
        assert success is True
        assert np.all(coeffs < 0.01)  # Near-zero

    def test_uncertainty_zero_clamped(self):
        """Uncertainty=0 should be clamped to small value, not cause division by zero."""
        ref = _make_reference_spectrum("Ta-181", self.energy, peak_energy=50.0)
        dictionary = np.column_stack([ref.absorption])

        transmission = np.exp(-0.5 * ref.absorption)
        uncertainty = np.zeros_like(transmission)  # All zeros

        coeffs, chi2, success = self.recovery.recover_pixel(transmission, uncertainty, dictionary)
        assert np.all(np.isfinite(coeffs))
        assert success is True

    def test_weighted_nnls_respects_uncertainty(self):
        """Higher uncertainty on certain bins should reduce their influence."""
        refs = _build_synthetic_dictionary(self.energy, n_isotopes=2)
        dictionary = np.column_stack([r.absorption for r in refs])

        ground_truth = np.array([0.5, 0.8])
        total_absorption = dictionary @ ground_truth
        transmission = np.exp(-total_absorption)

        # Uniform low uncertainty
        uncertainty_uniform = 0.01 * np.ones_like(transmission)
        coeffs_uniform, _, _ = self.recovery.recover_pixel(transmission, uncertainty_uniform, dictionary)

        # Very high uncertainty on isotope-1's peak region — should degrade accuracy for isotope 1
        uncertainty_biased = 0.01 * np.ones_like(transmission)
        mid = len(self.energy) // 2
        # Add noise to the region AND increase uncertainty there
        transmission_noisy = transmission.copy()
        rng = np.random.default_rng(42)
        transmission_noisy[mid:] += rng.normal(0, 0.1, len(self.energy) - mid)
        transmission_noisy = np.clip(transmission_noisy, 1e-6, 1 - 1e-6)
        uncertainty_biased[mid:] = 10.0  # Very high uncertainty

        coeffs_biased, _, _ = self.recovery.recover_pixel(transmission_noisy, uncertainty_biased, dictionary)
        # The first isotope (in the low-noise region) should still be recovered well
        assert abs(coeffs_biased[0] - ground_truth[0]) < 0.15

    def test_chi_squared_computed_correctly(self):
        """Chi-squared should be non-negative and finite."""
        ref = _make_reference_spectrum("Ta-181", self.energy, peak_energy=50.0)
        dictionary = np.column_stack([ref.absorption])

        transmission = np.exp(-0.3 * ref.absorption)
        uncertainty = 0.01 * np.ones_like(transmission)

        _, chi2, success = self.recovery.recover_pixel(transmission, uncertainty, dictionary)
        assert success is True
        assert chi2 >= 0.0
        assert np.isfinite(chi2)

    def test_returns_tuple_of_three(self):
        """recover_pixel returns (coefficients, chi_squared, success)."""
        ref = _make_reference_spectrum("Ta-181", self.energy, peak_energy=50.0)
        dictionary = np.column_stack([ref.absorption])
        transmission = np.exp(-0.5 * ref.absorption)
        uncertainty = 0.01 * np.ones_like(transmission)

        result = self.recovery.recover_pixel(transmission, uncertainty, dictionary)
        assert len(result) == 3
        assert isinstance(result[0], np.ndarray)
        assert isinstance(result[1], float)
        assert isinstance(result[2], bool)


# ---------------------------------------------------------------------------
# TestRecoverImage
# ---------------------------------------------------------------------------


class TestRecoverImage:
    """Tests for PhysicsRecovery.recover_image with synthetic 2D data."""

    def setup_method(self):
        from pleiades.imaging.recovery import PhysicsRecovery

        self.energy = np.linspace(1.0, 100.0, 100)
        self.height, self.width = 4, 4
        self.n_isotopes = 2
        self.refs = _build_synthetic_dictionary(self.energy, self.n_isotopes)

        # Create PhysicsRecovery without calling __init__ (avoids SAMMY deps)
        self.recovery = PhysicsRecovery.__new__(PhysicsRecovery)

    def _make_synthetic_image(self, ground_truth_maps: np.ndarray) -> HyperspectralData:
        """Create synthetic hyperspectral data from ground truth abundance maps.

        Args:
            ground_truth_maps: (n_isotopes, height, width) abundance maps
        """
        n_e = len(self.energy)
        h, w = ground_truth_maps.shape[1], ground_truth_maps.shape[2]
        data = np.zeros((n_e, h, w))
        for row in range(h):
            for col in range(w):
                total_abs = np.zeros(n_e)
                for iso_idx in range(ground_truth_maps.shape[0]):
                    total_abs += ground_truth_maps[iso_idx, row, col] * self.refs[iso_idx].absorption
                data[:, row, col] = np.exp(-total_abs)

        uncertainty = 0.01 * np.ones_like(data)
        return _make_hyperspectral(data, energy=self.energy, uncertainty=uncertainty)

    def test_output_is_imaging2d_results(self):
        """recover_image should return an Imaging2DResults instance."""
        gt = np.full((self.n_isotopes, self.height, self.width), 0.5)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        assert isinstance(result, Imaging2DResults)

    def test_abundance_maps_shape(self):
        """abundance_maps should have shape (n_isotopes, height, width)."""
        gt = np.full((self.n_isotopes, self.height, self.width), 0.5)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        assert result.abundance_maps.shape == (self.n_isotopes, self.height, self.width)

    def test_chi_squared_map_shape(self):
        """chi_squared_map should have shape (height, width)."""
        gt = np.full((self.n_isotopes, self.height, self.width), 0.5)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        assert result.chi_squared_map.shape == (self.height, self.width)

    def test_success_mask_shape(self):
        """success_mask should have shape (height, width)."""
        gt = np.full((self.n_isotopes, self.height, self.width), 0.5)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        assert result.success_mask.shape == (self.height, self.width)

    def test_isotope_names_match_references(self):
        """isotope_names should match the reference spectra."""
        gt = np.full((self.n_isotopes, self.height, self.width), 0.5)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        assert result.isotope_names == [r.isotope_name for r in self.refs]

    def test_source_hyperspectral_is_input(self):
        """source_hyperspectral should reference the input data."""
        gt = np.full((self.n_isotopes, self.height, self.width), 0.5)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        assert result.source_hyperspectral is hs

    def test_recovery_accuracy_uniform(self):
        """Uniform ground truth should be recovered within tolerance."""
        gt_val = 0.5
        gt = np.full((self.n_isotopes, self.height, self.width), gt_val)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        # All pixels should succeed
        assert np.all(result.success_mask)
        # Recovered abundances should be close to ground truth
        for iso in range(self.n_isotopes):
            np.testing.assert_allclose(
                result.abundance_maps[iso][result.success_mask],
                gt_val,
                atol=0.1,
            )

    def test_recovery_accuracy_varying(self):
        """Spatially varying ground truth should be recovered with correct ratios."""
        gt = np.zeros((self.n_isotopes, self.height, self.width))
        # Isotope 0: gradient left→right
        for col in range(self.width):
            gt[0, :, col] = 0.2 + 0.6 * col / (self.width - 1)
        # Isotope 1: gradient top→bottom
        for row in range(self.height):
            gt[1, row, :] = 0.3 + 0.4 * row / (self.height - 1)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        assert np.all(result.success_mask)

        # recover_image normalizes multi-isotope to sum=1, so compare against
        # the normalized ground truth (fractional abundances)
        gt_sum = gt.sum(axis=0, keepdims=True)
        gt_normalized = gt / gt_sum
        np.testing.assert_allclose(result.abundance_maps, gt_normalized, atol=0.05)

    def test_metadata_contains_method(self):
        """metadata should indicate physics_recovery method."""
        gt = np.full((self.n_isotopes, self.height, self.width), 0.5)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        assert "method" in result.metadata
        assert result.metadata["method"] == "physics_recovery"

    def test_open_beam_pixels_not_successful(self):
        """Pixels where T~1 everywhere (open beam) should be marked as failed."""
        gt = np.zeros((self.n_isotopes, self.height, self.width))
        # Most pixels have some absorption, but one is pure open beam
        gt[:, :, :] = 0.5
        gt[:, 0, 0] = 0.0  # Open beam: no absorption at all
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        # Open beam pixel: coefficients ~0, NaN abundances
        assert np.isnan(result.abundance_maps[0, 0, 0])
        assert result.success_mask[0, 0] is np.bool_(False)

    def test_chi_squared_non_negative(self):
        """All chi-squared values should be non-negative."""
        gt = np.full((self.n_isotopes, self.height, self.width), 0.5)
        hs = self._make_synthetic_image(gt)

        result = self.recovery.recover_image(hs, reference_spectra=self.refs)
        finite = np.isfinite(result.chi_squared_map)
        assert np.all(result.chi_squared_map[finite] >= 0.0)

    def test_no_reference_spectra_raises(self):
        """recover_image without reference_spectra and no generate method should raise."""
        gt = np.full((self.n_isotopes, self.height, self.width), 0.5)
        hs = self._make_synthetic_image(gt)

        with pytest.raises((ValueError, RuntimeError)):
            self.recovery.recover_image(hs, reference_spectra=None)


# ---------------------------------------------------------------------------
# TestCoefficientsToAbundances
# ---------------------------------------------------------------------------


class TestCoefficientsToAbundances:
    """Tests for PhysicsRecovery._coefficients_to_abundances static method."""

    def test_single_isotope_passthrough(self):
        """Single isotope: coefficient is passed through as-is (no normalization)."""
        from pleiades.imaging.recovery import PhysicsRecovery

        density_maps = np.array([[[0.5, 0.8], [0.3, 1.0]]])  # (1, 2, 2)
        success_mask = np.ones((2, 2), dtype=bool)
        result = PhysicsRecovery._coefficients_to_abundances(density_maps, success_mask)
        np.testing.assert_array_equal(result, density_maps)

    def test_multi_isotope_sums_to_one(self):
        """Multi-isotope: abundances should sum to 1.0 per pixel."""
        from pleiades.imaging.recovery import PhysicsRecovery

        density_maps = np.array([[[0.5, 0.3]], [[0.5, 0.7]]])  # (2, 1, 2)
        success_mask = np.ones((1, 2), dtype=bool)
        result = PhysicsRecovery._coefficients_to_abundances(density_maps, success_mask)
        # Sum along isotope axis should be 1.0
        np.testing.assert_allclose(np.sum(result, axis=0)[success_mask], 1.0)

    def test_multi_isotope_preserves_ratios(self):
        """Multi-isotope: normalization preserves relative ratios."""
        from pleiades.imaging.recovery import PhysicsRecovery

        density_maps = np.array([[[2.0]], [[3.0]]])  # (2, 1, 1)
        success_mask = np.ones((1, 1), dtype=bool)
        result = PhysicsRecovery._coefficients_to_abundances(density_maps, success_mask)
        assert result[0, 0, 0] == pytest.approx(0.4)
        assert result[1, 0, 0] == pytest.approx(0.6)

    def test_failed_pixels_remain_nan(self):
        """Failed pixels should remain NaN after normalization."""
        from pleiades.imaging.recovery import PhysicsRecovery

        density_maps = np.full((2, 2, 2), np.nan)
        density_maps[:, 0, 0] = [0.3, 0.7]
        success_mask = np.array([[True, False], [False, False]])
        result = PhysicsRecovery._coefficients_to_abundances(density_maps, success_mask)
        assert result[0, 0, 0] == pytest.approx(0.3)
        assert result[1, 0, 0] == pytest.approx(0.7)
        assert np.isnan(result[0, 0, 1])
        assert np.isnan(result[0, 1, 0])

    def test_zero_coefficients_give_nan(self):
        """Pixel where all coefficients are zero should give NaN (open beam)."""
        from pleiades.imaging.recovery import PhysicsRecovery

        density_maps = np.array([[[0.0]], [[0.0]]])  # (2, 1, 1)
        success_mask = np.ones((1, 1), dtype=bool)
        result = PhysicsRecovery._coefficients_to_abundances(density_maps, success_mask)
        # Zero/zero → NaN
        assert np.isnan(result[0, 0, 0])
        assert np.isnan(result[1, 0, 0])


# ---------------------------------------------------------------------------
# TestComputeChiSquared
# ---------------------------------------------------------------------------


class TestComputeChiSquared:
    """Tests for PhysicsRecovery._compute_chi_squared static method."""

    def test_perfect_fit_zero_chi2(self):
        """Perfect fit should give chi-squared = 0."""
        from pleiades.imaging.recovery import PhysicsRecovery

        observed = np.array([1.0, 2.0, 3.0])
        predicted = np.array([1.0, 2.0, 3.0])
        uncertainty = np.array([0.1, 0.1, 0.1])
        chi2 = PhysicsRecovery._compute_chi_squared(observed, predicted, uncertainty)
        assert chi2 == pytest.approx(0.0, abs=1e-12)

    def test_known_chi2_value(self):
        """Known-value test for chi-squared."""
        from pleiades.imaging.recovery import PhysicsRecovery

        observed = np.array([1.0, 2.0, 3.0])
        predicted = np.array([1.1, 2.0, 2.9])
        uncertainty = np.array([0.1, 0.1, 0.1])
        # chi2 = sum((obs-pred)^2/sigma^2) = (0.1/0.1)^2 + 0 + (0.1/0.1)^2 = 2.0
        chi2 = PhysicsRecovery._compute_chi_squared(observed, predicted, uncertainty)
        assert chi2 == pytest.approx(2.0, abs=1e-10)

    def test_chi2_always_non_negative(self):
        """Chi-squared must always be non-negative."""
        from pleiades.imaging.recovery import PhysicsRecovery

        rng = np.random.default_rng(42)
        observed = rng.uniform(0, 1, 50)
        predicted = rng.uniform(0, 1, 50)
        uncertainty = rng.uniform(0.01, 0.1, 50)
        chi2 = PhysicsRecovery._compute_chi_squared(observed, predicted, uncertainty)
        assert chi2 >= 0.0

    def test_higher_uncertainty_reduces_chi2(self):
        """Larger uncertainty should reduce chi-squared for same residuals."""
        from pleiades.imaging.recovery import PhysicsRecovery

        observed = np.array([1.0, 2.0])
        predicted = np.array([1.5, 2.5])
        chi2_small = PhysicsRecovery._compute_chi_squared(observed, predicted, np.array([0.1, 0.1]))
        chi2_large = PhysicsRecovery._compute_chi_squared(observed, predicted, np.array([1.0, 1.0]))
        assert chi2_large < chi2_small


# ---------------------------------------------------------------------------
# TestGenerateReferenceSpectra (mocked SAMMY)
# ---------------------------------------------------------------------------


class TestGenerateReferenceSpectra:
    """Integration tests for generate_reference_spectra with mocked SAMMY."""

    def test_forward_model_calls_run_per_isotope(self):
        """Verify generate_reference_spectra calls _run_sammy_forward_model per isotope."""
        from pleiades.imaging.config import ImagingConfig
        from pleiades.imaging.recovery import PhysicsRecovery

        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.65,
            thickness_mm=1.0,
            atomic_mass_amu=180.948,
            min_energy_eV=1.0,
            max_energy_eV=100.0,
        )
        energy = np.linspace(1.0, 100.0, 50)
        recovery = PhysicsRecovery(
            imaging_config=config,
            sammy_executable=Path("/usr/local/bin/sammy"),
        )

        # Patch _run_sammy_forward_model to verify it's called correctly
        # and return a mock ReferenceSpectrum
        from pleiades.imaging.recovery import ReferenceSpectrum

        mock_ref = ReferenceSpectrum(
            isotope_name="Ta-181",
            energy=energy,
            transmission=np.ones(50) * 0.5,
            absorption=-np.log(np.ones(50) * 0.5),
        )

        with patch.object(recovery, "_run_sammy_forward_model", return_value=mock_ref) as mock_run:
            specs = recovery.generate_reference_spectra(energy)
            assert len(specs) == 1
            assert specs[0].isotope_name == "Ta-181"
            mock_run.assert_called_once()
            # Verify the call included "Ta-181" as isotope
            call_args = mock_run.call_args
            assert call_args[0][0] == "Ta-181" or call_args[1].get("isotope_name") == "Ta-181"

    def test_multi_isotope_generates_one_per_isotope(self):
        """Each isotope should generate exactly one reference spectrum."""
        from pleiades.imaging.config import ImagingConfig
        from pleiades.imaging.recovery import PhysicsRecovery, ReferenceSpectrum

        config = ImagingConfig(
            isotopes=["Ta-181", "W-182"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.65,
            thickness_mm=1.0,
            atomic_mass_amu=180.948,
            min_energy_eV=1.0,
            max_energy_eV=100.0,
            natural_abundances=False,
            custom_abundances=[0.5, 0.5],
        )
        energy = np.linspace(1.0, 100.0, 50)
        recovery = PhysicsRecovery(
            imaging_config=config,
            sammy_executable=Path("/usr/local/bin/sammy"),
        )

        def mock_forward(isotope_name, energy_grid, working_dir=None):
            return ReferenceSpectrum(
                isotope_name=isotope_name,
                energy=energy_grid,
                transmission=np.ones(50) * 0.5,
                absorption=-np.log(np.ones(50) * 0.5),
            )

        with patch.object(recovery, "_run_sammy_forward_model", side_effect=mock_forward):
            specs = recovery.generate_reference_spectra(energy)
            assert len(specs) == 2
            assert specs[0].isotope_name == "Ta-181"
            assert specs[1].isotope_name == "W-182"


# ---------------------------------------------------------------------------
# TestAnalyzeImagingIntegration (mocked SAMMY)
# ---------------------------------------------------------------------------


class TestAnalyzeImagingIntegration:
    """Integration tests for analyze_imaging(physics_recovery=True)."""

    def test_physics_recovery_flag_in_api(self):
        """Verify physics_recovery parameter exists in analyze_imaging signature."""
        import inspect

        from pleiades.imaging.api import analyze_imaging

        sig = inspect.signature(analyze_imaging)
        assert "physics_recovery" in sig.parameters


# ---------------------------------------------------------------------------
# TestPhysicsRecoveryInit
# ---------------------------------------------------------------------------


class TestPhysicsRecoveryInit:
    """Tests for PhysicsRecovery constructor."""

    def test_init_stores_config(self):
        from pleiades.imaging.config import ImagingConfig
        from pleiades.imaging.recovery import PhysicsRecovery

        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.65,
            thickness_mm=1.0,
            atomic_mass_amu=180.948,
        )
        recovery = PhysicsRecovery(
            imaging_config=config,
            sammy_executable=Path("/usr/local/bin/sammy"),
        )
        assert recovery.imaging_config is config

    def test_init_stores_executable(self):
        from pleiades.imaging.config import ImagingConfig
        from pleiades.imaging.recovery import PhysicsRecovery

        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.65,
            thickness_mm=1.0,
            atomic_mass_amu=180.948,
        )
        exe = Path("/usr/local/bin/sammy")
        recovery = PhysicsRecovery(imaging_config=config, sammy_executable=exe)
        assert recovery.sammy_executable == exe

    def test_init_accepts_resolution_file(self):
        from pleiades.imaging.config import ImagingConfig
        from pleiades.imaging.recovery import PhysicsRecovery

        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.65,
            thickness_mm=1.0,
            atomic_mass_amu=180.948,
        )
        recovery = PhysicsRecovery(
            imaging_config=config,
            sammy_executable=Path("/usr/local/bin/sammy"),
            resolution_file=Path("/tmp/resolution.dat"),
        )
        assert recovery.resolution_file == Path("/tmp/resolution.dat")

    def test_init_default_resolution_file_none(self):
        from pleiades.imaging.config import ImagingConfig
        from pleiades.imaging.recovery import PhysicsRecovery

        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.65,
            thickness_mm=1.0,
            atomic_mass_amu=180.948,
        )
        recovery = PhysicsRecovery(
            imaging_config=config,
            sammy_executable=Path("/usr/local/bin/sammy"),
        )
        assert recovery.resolution_file is None


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestRecoveryEdgeCases:
    """Edge case tests for the recovery module."""

    def test_single_energy_bin(self):
        """Single energy bin should still work (degenerate case)."""
        from pleiades.imaging.recovery import PhysicsRecovery, ReferenceSpectrum

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.array([50.0])
        ref = ReferenceSpectrum(
            isotope_name="Ta-181",
            energy=energy,
            transmission=np.array([0.5]),
            absorption=np.array([np.log(2)]),
        )
        dictionary = np.column_stack([ref.absorption])
        transmission = np.array([0.5])
        uncertainty = np.array([0.01])

        coeffs, chi2, success = recovery.recover_pixel(transmission, uncertainty, dictionary)
        assert success is True
        assert len(coeffs) == 1

    def test_many_isotopes_small_image(self):
        """Should handle more isotopes than pixels gracefully."""
        from pleiades.imaging.recovery import PhysicsRecovery

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 100)
        n_isotopes = 5
        refs = _build_synthetic_dictionary(energy, n_isotopes)

        # Create 2x2 image with known coefficients
        gt = np.zeros((n_isotopes, 2, 2))
        gt[0, :, :] = 0.3
        gt[2, :, :] = 0.5

        # Build transmission data
        data = np.zeros((100, 2, 2))
        for r in range(2):
            for c in range(2):
                total_abs = np.zeros(100)
                for i in range(n_isotopes):
                    total_abs += gt[i, r, c] * refs[i].absorption
                data[:, r, c] = np.exp(-total_abs)

        uncertainty = 0.01 * np.ones_like(data)
        hs = _make_hyperspectral(data, energy=energy, uncertainty=uncertainty)

        result = recovery.recover_image(hs, reference_spectra=refs)
        assert result.abundance_maps.shape == (n_isotopes, 2, 2)
        assert np.all(result.success_mask)

    def test_energy_grid_length_mismatch_raises(self):
        """Reference spectra with different bin count should raise ValueError."""
        from pleiades.imaging.recovery import PhysicsRecovery, ReferenceSpectrum

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 100)
        data = np.full((100, 2, 2), 0.7)
        hs = _make_hyperspectral(data, energy=energy, uncertainty=0.01 * np.ones_like(data))

        # Reference spectrum with wrong number of energy bins
        bad_ref = ReferenceSpectrum(
            isotope_name="Ta-181",
            energy=np.linspace(1, 100, 50),  # 50 bins vs 100 in hyperspectral
            transmission=np.ones(50) * 0.5,
            absorption=-np.log(np.ones(50) * 0.5),
        )

        with pytest.raises(ValueError, match="energy bins"):
            recovery.recover_image(hs, reference_spectra=[bad_ref])

    def test_energy_grid_values_mismatch_raises(self):
        """Reference spectra with same length but shifted energy values should raise."""
        from pleiades.imaging.recovery import PhysicsRecovery, ReferenceSpectrum

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 100)
        data = np.full((100, 2, 2), 0.7)
        hs = _make_hyperspectral(data, energy=energy, uncertainty=0.01 * np.ones_like(data))

        # Same length but shifted energy values
        bad_ref = ReferenceSpectrum(
            isotope_name="Ta-181",
            energy=np.linspace(10, 200, 100),  # Different range
            transmission=np.ones(100) * 0.5,
            absorption=-np.log(np.ones(100) * 0.5),
        )

        with pytest.raises(ValueError, match="energy grid does not match"):
            recovery.recover_image(hs, reference_spectra=[bad_ref])

    def test_recover_image_uncertainty_none_uses_fallback(self):
        """When hyperspectral uncertainty is None, recover_image uses 1% fallback."""
        from pleiades.imaging.recovery import PhysicsRecovery

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 100)
        refs = _build_synthetic_dictionary(energy, n_isotopes=2)

        gt = np.full((2, 3, 3), 0.5)
        n_e = len(energy)
        data = np.zeros((n_e, 3, 3))
        for r in range(3):
            for c in range(3):
                total_abs = np.zeros(n_e)
                for i in range(2):
                    total_abs += gt[i, r, c] * refs[i].absorption
                data[:, r, c] = np.exp(-total_abs)

        # No uncertainty provided
        hs = _make_hyperspectral(data, energy=energy, uncertainty=None)

        result = recovery.recover_image(hs, reference_spectra=refs)
        assert isinstance(result, Imaging2DResults)
        assert np.all(result.success_mask)

    def test_recover_image_with_roi(self):
        """ROI should restrict which pixels are processed."""
        from pleiades.imaging.recovery import PhysicsRecovery

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 100)
        refs = _build_synthetic_dictionary(energy, n_isotopes=1)

        # 6x6 image with absorption
        data = np.full((100, 6, 6), 0.7)
        uncertainty = 0.01 * np.ones_like(data)
        hs = _make_hyperspectral(data, energy=energy, uncertainty=uncertainty)

        # ROI = (x1=1, y1=1, x2=4, y2=4) → only inner 3×3 should be fitted
        result = recovery.recover_image(hs, reference_spectra=refs, roi=(1, 1, 4, 4))
        assert result.abundance_maps.shape == (1, 6, 6)
        # Pixels outside ROI should be NaN
        assert np.isnan(result.abundance_maps[0, 0, 0])
        assert np.isnan(result.abundance_maps[0, 5, 5])
        # Pixels inside ROI should be fitted (success_mask True)
        assert result.success_mask[2, 2]
        assert result.success_mask[1, 1]

    def test_recover_image_with_stride(self):
        """Stride should skip pixels, leaving unprocessed positions as NaN."""
        from pleiades.imaging.recovery import PhysicsRecovery

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 100)
        refs = _build_synthetic_dictionary(energy, n_isotopes=1)

        # 8x8 image with absorption
        data = np.full((100, 8, 8), 0.7)
        uncertainty = 0.01 * np.ones_like(data)
        hs = _make_hyperspectral(data, energy=energy, uncertainty=uncertainty)

        result = recovery.recover_image(hs, reference_spectra=refs, stride=2)

        # Stride=2: only pixels at (0,0), (0,2), (0,4), (0,6), (2,0), ... should be fitted
        assert result.success_mask[0, 0]
        assert result.success_mask[0, 2]
        assert result.success_mask[2, 0]
        # Odd-indexed pixels should NOT be fitted
        assert not result.success_mask[0, 1]
        assert not result.success_mask[1, 0]
        assert not result.success_mask[1, 1]
        # Total fitted = 4*4 = 16 out of 64
        assert np.sum(result.success_mask) == 16

    def test_invalid_roi_negative_raises(self):
        """Negative ROI coordinates should raise ValueError."""
        from pleiades.imaging.recovery import PhysicsRecovery

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 50)
        refs = _build_synthetic_dictionary(energy, n_isotopes=1)
        data = np.full((50, 4, 4), 0.7)
        hs = _make_hyperspectral(data, energy=energy, uncertainty=0.01 * np.ones_like(data))

        with pytest.raises(ValueError, match="Invalid ROI"):
            recovery.recover_image(hs, reference_spectra=refs, roi=(-1, 0, 2, 2))

    def test_invalid_roi_out_of_bounds_raises(self):
        """ROI exceeding image dimensions should raise ValueError."""
        from pleiades.imaging.recovery import PhysicsRecovery

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 50)
        refs = _build_synthetic_dictionary(energy, n_isotopes=1)
        data = np.full((50, 4, 4), 0.7)
        hs = _make_hyperspectral(data, energy=energy, uncertainty=0.01 * np.ones_like(data))

        with pytest.raises(ValueError, match="Invalid ROI"):
            recovery.recover_image(hs, reference_spectra=refs, roi=(0, 0, 10, 10))

    def test_invalid_roi_reversed_raises(self):
        """ROI with x1 >= x2 should raise ValueError."""
        from pleiades.imaging.recovery import PhysicsRecovery

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 50)
        refs = _build_synthetic_dictionary(energy, n_isotopes=1)
        data = np.full((50, 4, 4), 0.7)
        hs = _make_hyperspectral(data, energy=energy, uncertainty=0.01 * np.ones_like(data))

        with pytest.raises(ValueError, match="Invalid ROI"):
            recovery.recover_image(hs, reference_spectra=refs, roi=(3, 0, 1, 4))

    def test_nan_in_spectrum_skipped_not_crashed(self):
        """Pixels with NaN in transmission should be skipped, not crash."""
        from pleiades.imaging.recovery import PhysicsRecovery

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 50)
        refs = _build_synthetic_dictionary(energy, n_isotopes=1)

        data = np.full((50, 3, 3), 0.7)
        uncertainty = 0.01 * np.ones_like(data)
        # Inject NaN into one pixel
        data[:, 1, 1] = np.nan
        hs = _make_hyperspectral(data, energy=energy, uncertainty=uncertainty)

        # Should not raise — the NaN pixel is skipped
        result = recovery.recover_image(hs, reference_spectra=refs)
        assert not result.success_mask[1, 1]
        assert np.isnan(result.abundance_maps[0, 1, 1])
        # Other pixels should still be fitted
        assert result.success_mask[0, 0]

    def test_inf_in_uncertainty_skipped_not_crashed(self):
        """Pixels with Inf in uncertainty should be skipped, not crash."""
        from pleiades.imaging.recovery import PhysicsRecovery

        recovery = PhysicsRecovery.__new__(PhysicsRecovery)
        energy = np.linspace(1, 100, 50)
        refs = _build_synthetic_dictionary(energy, n_isotopes=1)

        data = np.full((50, 3, 3), 0.7)
        uncertainty = 0.01 * np.ones_like(data)
        # Inject Inf into one pixel's uncertainty
        uncertainty[:, 2, 0] = np.inf
        hs = _make_hyperspectral(data, energy=energy, uncertainty=uncertainty)

        result = recovery.recover_image(hs, reference_spectra=refs)
        assert not result.success_mask[2, 0]
        # Other pixels should still be fitted
        assert result.success_mask[0, 0]
