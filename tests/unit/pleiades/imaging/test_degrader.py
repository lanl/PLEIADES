"""Unit tests for pleiades.imaging.degrader.DataDegrader.

Tests cover:
  - Poisson noise: shape, range, statistical expectation, reproducibility
  - Dead pixels: shape, fraction, mask semantics, open-beam value
  - degrade_to_level: correct preset application, shape preservation
  - Error handling: invalid parameters
"""

from __future__ import annotations

import numpy as np
import pytest

from pleiades.imaging.degrader import DataDegrader

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_3d():
    """3-D hyperspectral array (n_e=50, H=8, W=8) with uniform T=0.7."""
    return np.full((50, 8, 8), 0.7, dtype=np.float64)


@pytest.fixture
def clean_varied():
    """3-D array with varied transmission values in [0.2, 0.95]."""
    rng = np.random.default_rng(0)
    return rng.uniform(0.2, 0.95, (50, 8, 8))


@pytest.fixture
def degrader():
    """Seeded DataDegrader for reproducible tests."""
    return DataDegrader(random_seed=42)


# ---------------------------------------------------------------------------
# TestDataDegraderInit
# ---------------------------------------------------------------------------


class TestDataDegraderInit:
    def test_seeded_creates_rng(self):
        d = DataDegrader(random_seed=0)
        assert d.rng is not None

    def test_none_seed_creates_rng(self):
        d = DataDegrader(random_seed=None)
        assert d.rng is not None

    def test_two_same_seeds_produce_same_rng_output(self):
        d1 = DataDegrader(random_seed=7)
        d2 = DataDegrader(random_seed=7)
        data = np.full((5, 4, 4), 0.8)
        r1 = d1.add_poisson_noise(data, n_incident=500.0)
        r2 = d2.add_poisson_noise(data, n_incident=500.0)
        np.testing.assert_array_equal(r1, r2)

    def test_different_seeds_produce_different_output(self):
        d1 = DataDegrader(random_seed=1)
        d2 = DataDegrader(random_seed=2)
        data = np.full((50, 8, 8), 0.5)
        r1 = d1.add_poisson_noise(data, n_incident=100.0)
        r2 = d2.add_poisson_noise(data, n_incident=100.0)
        assert not np.allclose(r1, r2)


# ---------------------------------------------------------------------------
# TestAddPoissonNoise
# ---------------------------------------------------------------------------


class TestAddPoissonNoise:
    def test_output_shape_preserved(self, degrader, clean_3d):
        out = degrader.add_poisson_noise(clean_3d)
        assert out.shape == clean_3d.shape

    def test_output_clipped_to_zero_one(self, clean_varied):
        d = DataDegrader(random_seed=99)
        out = d.add_poisson_noise(clean_varied, n_incident=20.0)
        assert np.all(out >= 0.0)
        assert np.all(out <= 1.0)

    def test_high_n_incident_is_close_to_original(self, clean_3d):
        d = DataDegrader(random_seed=0)
        out = d.add_poisson_noise(clean_3d, n_incident=1e7)
        np.testing.assert_allclose(out, clean_3d, atol=5e-3)

    def test_low_n_incident_increases_variance(self, clean_3d):
        d_high = DataDegrader(random_seed=5)
        d_low = DataDegrader(random_seed=5)
        high = d_high.add_poisson_noise(clean_3d, n_incident=100_000.0)
        low = d_low.add_poisson_noise(clean_3d, n_incident=10.0)
        assert low.std() > high.std()

    def test_mean_close_to_original_for_large_n(self, clean_3d):
        d = DataDegrader(random_seed=3)
        out = d.add_poisson_noise(clean_3d, n_incident=1e6)
        np.testing.assert_allclose(out.mean(), 0.7, atol=1e-3)

    def test_works_on_1d_array(self, degrader):
        arr = np.array([0.5, 0.8, 0.2])
        out = degrader.add_poisson_noise(arr, n_incident=1000.0)
        assert out.shape == arr.shape
        assert np.all(out >= 0.0) and np.all(out <= 1.0)

    def test_works_on_2d_array(self, degrader):
        arr = np.full((4, 6), 0.6)
        out = degrader.add_poisson_noise(arr, n_incident=500.0)
        assert out.shape == arr.shape

    def test_invalid_n_incident_raises(self, degrader, clean_3d):
        with pytest.raises(ValueError, match="n_incident"):
            degrader.add_poisson_noise(clean_3d, n_incident=0.0)

    def test_negative_n_incident_raises(self, degrader, clean_3d):
        with pytest.raises(ValueError, match="n_incident"):
            degrader.add_poisson_noise(clean_3d, n_incident=-10.0)

    def test_zero_transmission_stays_zero(self, degrader):
        data = np.zeros((10, 4, 4))
        out = degrader.add_poisson_noise(data, n_incident=1000.0)
        np.testing.assert_array_equal(out, 0.0)

    def test_output_dtype_float(self, degrader, clean_3d):
        out = degrader.add_poisson_noise(clean_3d, n_incident=500.0)
        assert np.issubdtype(out.dtype, np.floating)


# ---------------------------------------------------------------------------
# TestAddDeadPixels
# ---------------------------------------------------------------------------


class TestAddDeadPixels:
    def test_output_shape_preserved(self, degrader, clean_3d):
        degraded, mask = degrader.add_dead_pixels(clean_3d, dead_fraction=0.1)
        assert degraded.shape == clean_3d.shape
        assert mask.shape == (8, 8)

    def test_mask_is_boolean(self, degrader, clean_3d):
        _, mask = degrader.add_dead_pixels(clean_3d, dead_fraction=0.1)
        assert mask.dtype == bool

    def test_dead_pixels_set_to_one(self, degrader, clean_3d):
        degraded, mask = degrader.add_dead_pixels(clean_3d, dead_fraction=0.25)
        # All energy bins at dead pixels must be exactly 1.0
        assert np.all(degraded[:, mask] == 1.0)

    def test_live_pixels_unchanged(self, degrader, clean_3d):
        degraded, mask = degrader.add_dead_pixels(clean_3d, dead_fraction=0.25)
        live = ~mask
        np.testing.assert_array_equal(degraded[:, live], clean_3d[:, live])

    def test_dead_fraction_approximately_correct(self, clean_3d):
        d = DataDegrader(random_seed=0)
        _, mask = d.add_dead_pixels(clean_3d, dead_fraction=0.1)
        actual_fraction = mask.sum() / mask.size
        assert abs(actual_fraction - 0.1) <= 0.02  # within 2 percentage points

    def test_zero_fraction_no_dead_pixels(self, degrader, clean_3d):
        degraded, mask = degrader.add_dead_pixels(clean_3d, dead_fraction=0.0)
        assert not mask.any()
        np.testing.assert_array_equal(degraded, clean_3d)

    def test_non_3d_raises(self, degrader):
        with pytest.raises(ValueError, match="3-D"):
            degrader.add_dead_pixels(np.ones((4, 4)), dead_fraction=0.1)

    def test_negative_fraction_raises(self, degrader, clean_3d):
        with pytest.raises(ValueError, match="dead_fraction"):
            degrader.add_dead_pixels(clean_3d, dead_fraction=-0.1)

    def test_fraction_one_raises(self, degrader, clean_3d):
        with pytest.raises(ValueError, match="dead_fraction"):
            degrader.add_dead_pixels(clean_3d, dead_fraction=1.0)

    def test_returns_copy_not_in_place(self, degrader, clean_3d):
        original = clean_3d.copy()
        degrader.add_dead_pixels(clean_3d, dead_fraction=0.2)
        np.testing.assert_array_equal(clean_3d, original)

    def test_reproducible_with_same_seed(self, clean_3d):
        d1 = DataDegrader(random_seed=77)
        d2 = DataDegrader(random_seed=77)
        _, mask1 = d1.add_dead_pixels(clean_3d, dead_fraction=0.15)
        _, mask2 = d2.add_dead_pixels(clean_3d, dead_fraction=0.15)
        np.testing.assert_array_equal(mask1, mask2)


# ---------------------------------------------------------------------------
# TestDegradeToLevel
# ---------------------------------------------------------------------------


class TestDegradeToLevel:
    def test_output_shape_preserved_all_levels(self, clean_3d):
        for level in (1, 2, 3, 4):
            d = DataDegrader(random_seed=level)
            out = d.degrade_to_level(clean_3d, target_level=level)
            assert out.shape == clean_3d.shape, f"Shape mismatch at level {level}"

    def test_output_clipped_to_zero_one(self, clean_3d):
        for level in (1, 2, 3, 4):
            d = DataDegrader(random_seed=level)
            out = d.degrade_to_level(clean_3d, target_level=level)
            assert np.all(out >= 0.0) and np.all(out <= 1.0), f"Range violation at level {level}"

    def test_l1_lower_variance_than_l4(self, clean_3d):
        d1 = DataDegrader(random_seed=0)
        d4 = DataDegrader(random_seed=0)
        out1 = d1.degrade_to_level(clean_3d, target_level=1)
        out4 = d4.degrade_to_level(clean_3d, target_level=4)
        assert out4.std() > out1.std()

    def test_l3_has_some_exactly_one_pixels(self, clean_3d):
        # L3 applies 5% dead pixels, so there should be pixels at exactly 1.0
        # even if original data < 1.0.
        d = DataDegrader(random_seed=0)
        out = d.degrade_to_level(clean_3d, target_level=3)
        # At least some pixels should be exactly 1.0 from dead pixel injection
        # (any column of the output where all values == 1.0 indicates dead pixel)
        any_dead = np.any(np.all(out == 1.0, axis=0))
        assert any_dead, "L3 should produce dead pixels (all-1.0 columns)"

    def test_l4_has_some_exactly_one_pixels(self, clean_3d):
        d = DataDegrader(random_seed=0)
        out = d.degrade_to_level(clean_3d, target_level=4)
        any_dead = np.any(np.all(out == 1.0, axis=0))
        assert any_dead, "L4 should produce dead pixels (all-1.0 columns)"

    def test_l1_preserves_mean_approximately(self, clean_3d):
        # L1 is mild noise (n_incident=5000); mean should be close to 0.7
        d = DataDegrader(random_seed=0)
        out = d.degrade_to_level(clean_3d, target_level=1)
        np.testing.assert_allclose(out.mean(), 0.7, atol=0.02)

    def test_invalid_level_raises(self, clean_3d):
        d = DataDegrader(random_seed=0)
        with pytest.raises(ValueError, match="target_level"):
            d.degrade_to_level(clean_3d, target_level=0)

    def test_level_5_raises(self, clean_3d):
        d = DataDegrader(random_seed=0)
        with pytest.raises(ValueError, match="target_level"):
            d.degrade_to_level(clean_3d, target_level=5)

    def test_reproducible_with_same_seed(self, clean_3d):
        d1 = DataDegrader(random_seed=55)
        d2 = DataDegrader(random_seed=55)
        np.testing.assert_array_equal(
            d1.degrade_to_level(clean_3d, target_level=3),
            d2.degrade_to_level(clean_3d, target_level=3),
        )

    def test_level2_no_dead_pixels(self, clean_3d):
        """L2 uses only Poisson noise, no dead pixels."""
        # Data values of 0.7 should not all be pushed to exactly 1.0
        d = DataDegrader(random_seed=0)
        out = d.degrade_to_level(clean_3d, target_level=2)
        # There should be substantial variation (not all 1.0)
        assert out.std() > 0.0
        # The output should not be entirely 1.0
        assert not np.all(out == 1.0)
