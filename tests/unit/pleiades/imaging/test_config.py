"""Unit tests for pleiades.imaging.config."""

import pytest

from pleiades.imaging.config import ImagingConfig


class TestImagingConfig:
    """Test ImagingConfig model."""

    def test_get_material_properties_correct_keys(self):
        """Test that get_material_properties() emits correct dictionary keys."""
        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.948,
            min_energy_eV=1.0,
            max_energy_eV=200.0,
            temperature_K=293.6,
        )

        props = config.get_material_properties()

        # Verify correct key names (Issue #P1: min_energy_eV not min_energy)
        assert "min_energy_eV" in props
        assert "max_energy_eV" in props
        assert "min_energy" not in props  # Should NOT have this key

        # Verify values
        assert props["min_energy_eV"] == 1.0
        assert props["max_energy_eV"] == 200.0
        assert props["element"] == "Ta"
        assert props["mass_number"] == 181
        assert props["density_g_cm3"] == 16.6
        assert props["thickness_mm"] == 0.025
        assert props["atomic_mass_amu"] == 180.948
        assert props["temperature_K"] == 293.6
        assert props["abundance"] == 1.0

    def test_get_abundances_natural_single_isotope(self):
        """Test natural abundance lookup for single isotope."""
        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.948,
            natural_abundances=True,
        )

        abundances = config.get_abundances()

        # Ta-181 is 99.988% natural abundance
        assert len(abundances) == 1
        assert 0.999 < abundances[0] < 1.0  # ~0.99988 as fraction
        assert isinstance(abundances[0], float)

    def test_get_abundances_natural_multi_isotope(self):
        """Test natural abundance lookup for multiple isotopes (Issue #P1)."""
        config = ImagingConfig(
            isotopes=["Hf-174", "Hf-176", "Hf-177", "Hf-178", "Hf-179", "Hf-180"],
            element="Hf",
            mass_number=178,  # Most abundant
            density_g_cm3=13.3,
            thickness_mm=0.5,
            atomic_mass_amu=177.5,
            natural_abundances=True,
        )

        abundances = config.get_abundances()

        # Should return actual natural abundance fractions, not all 1.0s
        assert len(abundances) == 6
        assert all(isinstance(a, float) for a in abundances)
        assert all(0.0 < a < 1.0 for a in abundances)  # All should be fractions

        # Sum should be ≤ 1.0 (physically meaningful)
        total = sum(abundances)
        assert 0.99 < total <= 1.0  # Natural abundances should sum to ~100%

        # Should NOT be all 1.0s (the bug we're fixing)
        assert not all(a == 1.0 for a in abundances)

    def test_get_abundances_custom(self):
        """Test custom abundance specification."""
        custom = [0.3, 0.4, 0.3]
        config = ImagingConfig(
            isotopes=["W-182", "W-183", "W-184"],
            element="W",
            mass_number=184,
            density_g_cm3=19.3,
            thickness_mm=0.1,
            atomic_mass_amu=183.84,
            natural_abundances=False,
            custom_abundances=custom,
        )

        abundances = config.get_abundances()

        assert abundances == custom

    def test_get_abundances_custom_length_mismatch(self):
        """Test error when custom abundances length mismatches isotopes."""
        with pytest.raises(ValueError, match="custom_abundances length"):
            config = ImagingConfig(
                isotopes=["W-182", "W-183", "W-184"],
                element="W",
                mass_number=184,
                density_g_cm3=19.3,
                thickness_mm=0.1,
                atomic_mass_amu=183.84,
                natural_abundances=False,
                custom_abundances=[0.5, 0.5],  # Wrong length
            )
            config.get_abundances()

    def test_get_abundances_no_custom_when_required(self):
        """Test error when custom abundances not provided but required."""
        with pytest.raises(ValueError, match="Must specify custom_abundances"):
            config = ImagingConfig(
                isotopes=["W-182"],
                element="W",
                mass_number=182,
                density_g_cm3=19.3,
                thickness_mm=0.1,
                atomic_mass_amu=181.95,
                natural_abundances=False,
                # custom_abundances not provided
            )
            config.get_abundances()

    def test_get_abundances_natural_isotope_not_found(self):
        """Test error when natural abundance not available for isotope."""
        # IsotopeManager raises ValueError during mass data lookup for nonexistent isotopes
        with pytest.raises(ValueError, match="Mass data for Xx-999 not found"):
            config = ImagingConfig(
                isotopes=["Xx-999"],  # Nonexistent isotope
                element="Xx",
                mass_number=999,
                density_g_cm3=1.0,
                thickness_mm=1.0,
                atomic_mass_amu=999.0,
                natural_abundances=True,
            )
            config.get_abundances()

    def test_vary_flags_default_true(self):
        """Test that vary_* flags default to True (appropriate for real data)."""
        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.948,
        )
        assert config.vary_normalization is True
        assert config.vary_background is True
        assert config.vary_tzero is True
        assert config.vary_thickness is True

    def test_vary_flags_can_be_set_false(self):
        """Test that vary_* flags can be overridden to False (e.g. for clean synthetic data)."""
        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.948,
            vary_normalization=False,
            vary_background=False,
            vary_tzero=False,
            vary_thickness=False,
        )
        assert config.vary_normalization is False
        assert config.vary_background is False
        assert config.vary_tzero is False
        assert config.vary_thickness is False

    def test_to_dataset_metadata_populates_vary_flags(self):
        """Test that to_dataset_metadata() passes vary_* flags through."""
        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.948,
            vary_normalization=False,
            vary_background=False,
            vary_tzero=False,
            vary_thickness=False,
        )
        meta = config.to_dataset_metadata()
        assert meta.vary_normalization is False
        assert meta.vary_background is False
        assert meta.vary_tzero is False
        assert meta.vary_thickness is False

    def test_to_dataset_metadata_populates_vary_flags_true(self):
        """Test that to_dataset_metadata() passes True vary_* flags through."""
        config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.948,
            vary_normalization=True,
            vary_background=True,
            vary_tzero=True,
            vary_thickness=True,
        )
        meta = config.to_dataset_metadata()
        assert meta.vary_normalization is True
        assert meta.vary_background is True
        assert meta.vary_tzero is True
        assert meta.vary_thickness is True
