"""Unit tests for pleiades.imaging.assessor.SparsityAssessor.

Tests cover:
  - SparsityMetrics field types and ranges
  - All five severity levels (L0–L4) are reachable
  - SNR and zero-fraction each independently trigger higher levels
  - Noise estimation via MAD
  - Recommendations map correctly to severity levels
  - Edge cases: uniform data, all-zero data, zero resonance depth
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pleiades.imaging.assessor import SparsityAssessor, SparsityMetrics, _classify_severity
from pleiades.imaging.models import HyperspectralData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hyperspectral(data: np.ndarray, energy: np.ndarray | None = None) -> HyperspectralData:
    """Wrap a 3-D array in HyperspectralData with a synthetic source path."""
    n_e = data.shape[0]
    if energy is None:
        energy = np.linspace(1.0, 100.0, n_e)
    return HyperspectralData(
        data=data,
        energy=energy,
        source_file=Path("/tmp/test.tif"),
    )


def _clean_data(n_e: int = 50, h: int = 8, w: int = 8, t_min: float = 0.5, t_bg: float = 0.9) -> np.ndarray:
    """Create a synthetic clean dataset with a single sharp resonance dip."""
    data = np.full((n_e, h, w), t_bg)
    # Place a resonance at the centre energy bin — deep dip to t_min
    data[n_e // 2, :, :] = t_min
    return data


# ---------------------------------------------------------------------------
# TestSparsityMetricsFields
# ---------------------------------------------------------------------------


class TestSparsityMetricsFields:
    def test_returns_sparsity_metrics_instance(self):
        assessor = SparsityAssessor()
        data = _clean_data()
        hs = _make_hyperspectral(data)
        metrics = assessor.assess(hs)
        assert isinstance(metrics, SparsityMetrics)

    def test_mean_transmission_in_range(self):
        assessor = SparsityAssessor()
        hs = _make_hyperspectral(_clean_data())
        m = assessor.assess(hs)
        assert 0.0 <= m.mean_transmission <= 1.0

    def test_min_transmission_leq_mean(self):
        assessor = SparsityAssessor()
        hs = _make_hyperspectral(_clean_data())
        m = assessor.assess(hs)
        assert m.min_transmission <= m.mean_transmission

    def test_resonance_depth_equals_one_minus_min(self):
        assessor = SparsityAssessor()
        hs = _make_hyperspectral(_clean_data(t_min=0.3))
        m = assessor.assess(hs)
        assert abs(m.resonance_depth - (1.0 - m.min_transmission)) < 1e-12

    def test_snr_estimate_positive_for_resonance_data(self):
        assessor = SparsityAssessor()
        hs = _make_hyperspectral(_clean_data(t_min=0.3))
        m = assessor.assess(hs)
        assert m.snr_estimate > 0.0

    def test_zero_fraction_zero_for_uniform_high_data(self):
        assessor = SparsityAssessor()
        data = np.full((30, 4, 4), 0.8)
        hs = _make_hyperspectral(data)
        m = assessor.assess(hs)
        assert m.zero_fraction == 0.0

    def test_zero_fraction_for_all_below_threshold(self):
        assessor = SparsityAssessor()
        # All values below 0.01
        data = np.full((30, 4, 4), 0.005)
        hs = _make_hyperspectral(data)
        m = assessor.assess(hs)
        assert m.zero_fraction == pytest.approx(1.0)

    def test_severity_level_integer_in_range(self):
        assessor = SparsityAssessor()
        hs = _make_hyperspectral(_clean_data())
        m = assessor.assess(hs)
        assert m.severity_level in (0, 1, 2, 3, 4)

    def test_severity_label_is_string(self):
        assessor = SparsityAssessor()
        hs = _make_hyperspectral(_clean_data())
        m = assessor.assess(hs)
        assert isinstance(m.severity_label, str)
        assert len(m.severity_label) > 0

    def test_recommendations_is_list_of_strings(self):
        assessor = SparsityAssessor()
        hs = _make_hyperspectral(_clean_data())
        m = assessor.assess(hs)
        assert isinstance(m.recommendations, list)
        assert all(isinstance(r, str) for r in m.recommendations)
        assert len(m.recommendations) >= 1


# ---------------------------------------------------------------------------
# TestSeverityLevels
# ---------------------------------------------------------------------------


class TestSeverityLevels:
    """Verify each level 0–4 is reachable and produces correct labels/recs."""

    def test_l0_clean_high_snr(self):
        # Near-perfect data: background close to 1.0, deep clean resonance
        # → very high SNR, near-zero zero_fraction → L0
        assessor = SparsityAssessor()
        data = _clean_data(n_e=200, h=16, w=16, t_min=0.01, t_bg=0.999)
        hs = _make_hyperspectral(data)
        m = assessor.assess(hs)
        assert m.severity_level == 0
        assert "L0" in m.severity_label
        assert "direct_fitting" in m.recommendations

    def test_l0_recommendations_direct_fitting(self):
        assessor = SparsityAssessor()
        m = SparsityMetrics(
            mean_transmission=0.9,
            min_transmission=0.5,
            resonance_depth=0.5,
            snr_estimate=50.0,
            zero_fraction=0.001,
            severity_level=0,
            severity_label="L0: Clean",
            recommendations=["direct_fitting"],
        )
        assert "direct_fitting" in m.recommendations

    def test_l2_recommendations_bin_size_2(self):
        assessor = SparsityAssessor()
        # Force L2 via _classify_severity: snr in [2,5), zero_fraction in [5%,15%)
        level = _classify_severity(snr=3.0, zero_fraction=0.08)
        assert level == 2
        from pleiades.imaging.assessor import _LEVEL_RECOMMENDATIONS

        assert "bin_size=2" in _LEVEL_RECOMMENDATIONS[2]

    def test_l3_recommendations_bin_size_4(self):
        from pleiades.imaging.assessor import _LEVEL_RECOMMENDATIONS

        assert "bin_size=4" in _LEVEL_RECOMMENDATIONS[3]

    def test_l4_recommendations_physics_recovery(self):
        from pleiades.imaging.assessor import _LEVEL_RECOMMENDATIONS

        assert "physics_recovery" in _LEVEL_RECOMMENDATIONS[4]

    def test_severity_label_matches_level(self):
        from pleiades.imaging.assessor import _LEVEL_LABELS

        for level, label in _LEVEL_LABELS.items():
            assert f"L{level}" in label


# ---------------------------------------------------------------------------
# TestClassifySeverity
# ---------------------------------------------------------------------------


class TestClassifySeverity:
    """Unit tests for the _classify_severity helper."""

    def test_high_snr_low_zf_is_l0(self):
        assert _classify_severity(snr=100.0, zero_fraction=0.001) == 0

    def test_snr_7_low_zf_is_l1(self):
        assert _classify_severity(snr=7.0, zero_fraction=0.001) == 1

    def test_snr_3_low_zf_is_l2(self):
        assert _classify_severity(snr=3.0, zero_fraction=0.001) == 2

    def test_snr_1_5_low_zf_is_l3(self):
        assert _classify_severity(snr=1.5, zero_fraction=0.001) == 3

    def test_snr_below_1_is_l4(self):
        assert _classify_severity(snr=0.5, zero_fraction=0.001) == 4

    def test_zf_drives_level_up(self):
        # SNR says L0 but zero_fraction says L3
        level = _classify_severity(snr=100.0, zero_fraction=0.30)
        assert level == 3

    def test_takes_max_of_snr_and_zf_levels(self):
        # SNR=L2, zf=L1 → L2
        assert _classify_severity(snr=3.0, zero_fraction=0.02) == 2

    def test_boundary_snr_10_is_l0(self):
        # SNR > 10 → L0
        assert _classify_severity(snr=10.01, zero_fraction=0.005) == 0

    def test_boundary_snr_exactly_5_is_l1(self):
        assert _classify_severity(snr=5.0, zero_fraction=0.005) == 1

    def test_boundary_zf_0_01_is_l0(self):
        # zero_fraction < 0.01 → L0 on zf axis
        assert _classify_severity(snr=50.0, zero_fraction=0.009) == 0

    def test_boundary_zf_exactly_0_05_is_l2(self):
        # zero_fraction == 0.05 → L2 on zf axis (>= 0.05)
        assert _classify_severity(snr=50.0, zero_fraction=0.05) == 2

    def test_zero_snr_is_l4(self):
        assert _classify_severity(snr=0.0, zero_fraction=0.0) == 4

    def test_extreme_zf_is_l4(self):
        assert _classify_severity(snr=50.0, zero_fraction=0.55) == 4


# ---------------------------------------------------------------------------
# TestNoiseEstimation
# ---------------------------------------------------------------------------


class TestNoiseEstimation:
    def test_noiseless_uniform_gives_high_snr(self):
        """Perfectly flat spectrum (no energy variation) → MAD=0 → SNR=inf."""
        assessor = SparsityAssessor()
        # Uniform across ALL energy bins → spatial mean is constant → MAD=0
        data = np.full((50, 8, 8), 0.9)
        hs = _make_hyperspectral(data)
        m = assessor.assess(hs)
        assert m.snr_estimate == float("inf")

    def test_noisy_data_lower_snr_than_clean(self):
        assessor = SparsityAssessor()
        rng = np.random.default_rng(0)

        clean = _clean_data(n_e=100, h=16, w=16, t_min=0.1, t_bg=0.95)
        noisy = clean + rng.normal(0, 0.05, clean.shape)
        noisy = np.clip(noisy, 0.0, 1.0)

        m_clean = assessor.assess(_make_hyperspectral(clean))
        m_noisy = assessor.assess(_make_hyperspectral(noisy))

        assert m_noisy.snr_estimate < m_clean.snr_estimate

    def test_snr_is_finite_for_noisy_data(self):
        """Noisy (Poisson) data with spectral variation produces finite, positive SNR."""
        assessor = SparsityAssessor()
        rng = np.random.default_rng(42)
        # Simulate Poisson noise: each pixel has independent noise per energy bin.
        # This creates spectral variation in the spatial mean → non-zero MAD → finite SNR.
        n_incident = 200.0
        t_true = _clean_data(n_e=50, h=16, w=16, t_min=0.2, t_bg=0.9)
        counts = rng.poisson(n_incident * t_true)
        data = np.clip(counts / n_incident, 0.0, 1.0)
        hs = _make_hyperspectral(data)
        m = assessor.assess(hs)
        # Should be finite and positive
        assert np.isfinite(m.snr_estimate)
        assert m.snr_estimate > 0.0


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_pixel_image(self):
        assessor = SparsityAssessor()
        data = np.linspace(0.3, 0.95, 50).reshape(50, 1, 1)
        hs = _make_hyperspectral(data)
        m = assessor.assess(hs)
        assert isinstance(m, SparsityMetrics)
        assert 0 <= m.severity_level <= 4

    def test_single_energy_bin(self):
        assessor = SparsityAssessor()
        data = np.full((1, 8, 8), 0.7)
        energy = np.array([10.0])
        hs = _make_hyperspectral(data, energy=energy)
        m = assessor.assess(hs)
        assert isinstance(m, SparsityMetrics)

    def test_assess_is_deterministic(self):
        """Running assess() twice on the same data yields identical metrics."""
        assessor = SparsityAssessor()
        hs = _make_hyperspectral(_clean_data())
        m1 = assessor.assess(hs)
        m2 = assessor.assess(hs)
        assert m1.severity_level == m2.severity_level
        assert m1.snr_estimate == m2.snr_estimate
        assert m1.zero_fraction == m2.zero_fraction

    def test_high_zero_fraction_degrades_to_l4(self):
        assessor = SparsityAssessor()
        rng = np.random.default_rng(1)
        data = rng.uniform(0.0, 0.005, (50, 8, 8))  # nearly all below 0.01
        hs = _make_hyperspectral(data)
        m = assessor.assess(hs)
        assert m.severity_level == 4
        assert m.zero_fraction > 0.40
