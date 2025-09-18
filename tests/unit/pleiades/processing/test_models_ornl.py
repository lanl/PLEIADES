"""Unit tests for ORNL-specific data models."""

import numpy as np
import pytest
from pydantic import ValidationError

from pleiades.processing import Roi
from pleiades.processing.models_ornl import Run, Transmission


class TestRunModel:
    """Test the Run data model."""

    def test_valid_run_creation(self):
        """Test creating a valid Run object."""
        counts = np.random.rand(100, 256, 256)
        proton_charge = 1234.5

        run = Run(counts=counts, proton_charge=proton_charge, metadata={"run_number": "8022"})

        assert run.counts.shape == (100, 256, 256)
        assert run.proton_charge == 1234.5
        assert run.metadata["run_number"] == "8022"
        assert run.shutter_counts is None
        assert run.dead_pixel_mask is None

    def test_invalid_counts_shape(self):
        """Test that 2D counts array raises error."""
        counts = np.random.rand(256, 256)  # 2D instead of 3D

        with pytest.raises(ValidationError, match="counts must be 3D array"):
            Run(counts=counts, proton_charge=1.0)

    def test_invalid_proton_charge(self):
        """Test that negative proton charge raises error."""
        counts = np.random.rand(10, 256, 256)

        with pytest.raises(ValidationError, match="greater than 0"):
            Run(counts=counts, proton_charge=-1.0)

        with pytest.raises(ValidationError, match="greater than 0"):
            Run(counts=counts, proton_charge=0.0)

    def test_shutter_counts_validation(self):
        """Test shutter_counts must be 1D."""
        counts = np.random.rand(100, 256, 256)
        shutter_2d = np.random.rand(100, 2)  # 2D instead of 1D

        with pytest.raises(ValidationError, match="shutter_counts must be 1D"):
            Run(counts=counts, proton_charge=1.0, shutter_counts=shutter_2d)

        # Valid 1D shutter counts
        shutter_1d = np.random.rand(100)
        run = Run(counts=counts, proton_charge=1.0, shutter_counts=shutter_1d)
        assert run.shutter_counts.shape == (100,)

    def test_dead_pixel_mask_validation(self):
        """Test dead_pixel_mask must be 2D boolean."""
        counts = np.random.rand(100, 256, 256)

        # Test non-2D shape
        mask_3d = np.ones((100, 256, 256), dtype=bool)
        with pytest.raises(ValidationError, match="dead_pixel_mask must be 2D"):
            Run(counts=counts, proton_charge=1.0, dead_pixel_mask=mask_3d)

        # Test non-boolean dtype
        mask_float = np.ones((256, 256), dtype=float)
        with pytest.raises(ValidationError, match="dead_pixel_mask must be boolean"):
            Run(counts=counts, proton_charge=1.0, dead_pixel_mask=mask_float)

        # Valid boolean 2D mask
        mask_bool = np.ones((256, 256), dtype=bool)
        run = Run(counts=counts, proton_charge=1.0, dead_pixel_mask=mask_bool)
        assert run.dead_pixel_mask.shape == (256, 256)
        assert run.dead_pixel_mask.dtype == bool

    def test_get_tof_range(self):
        """Test getting shape information."""
        counts = np.random.rand(100, 256, 512)
        run = Run(counts=counts, proton_charge=1.0)

        shape = run.get_tof_range()
        assert shape == (100, 256, 512)


class TestTransmissionModel:
    """Test the Transmission data model."""

    def test_valid_transmission_creation(self):
        """Test creating a valid Transmission object."""
        n_points = 1000
        energy = np.logspace(0, 4, n_points)  # 1 eV to 10 keV
        transmission = np.random.rand(n_points) * 0.9 + 0.1  # 0.1 to 1.0
        uncertainty = np.random.rand(n_points) * 0.01

        trans = Transmission(
            energy=energy,
            transmission=transmission,
            uncertainty=uncertainty,
            roi_center=(256.0, 256.0),
            metadata={"processing": "Method2"},
        )

        assert trans.energy.shape == (n_points,)
        assert trans.transmission.shape == (n_points,)
        assert trans.uncertainty.shape == (n_points,)
        assert trans.roi_center == (256.0, 256.0)
        assert trans.roi is None

    def test_arrays_must_be_1d(self):
        """Test that arrays must be 1D."""
        energy_2d = np.ones((10, 2))
        trans_1d = np.ones(10)
        uncert_1d = np.ones(10)

        with pytest.raises(ValidationError, match="energy must be 1D array"):
            Transmission(energy=energy_2d, transmission=trans_1d, uncertainty=uncert_1d, roi_center=(0, 0))

    def test_array_length_consistency(self):
        """Test that all arrays must have same length."""
        energy = np.ones(100)
        transmission = np.ones(100)
        uncertainty = np.ones(50)  # Different length

        with pytest.raises(ValidationError, match="Array length mismatch"):
            Transmission(energy=energy, transmission=transmission, uncertainty=uncertainty, roi_center=(0, 0))

    def test_transmission_range_warning(self):
        """Test warning for unusual transmission values."""
        energy = np.ones(10)
        transmission = np.ones(10) * 2.0  # Unusually high
        uncertainty = np.ones(10) * 0.01

        with pytest.warns(UserWarning, match="outside typical range"):
            trans = Transmission(energy=energy, transmission=transmission, uncertainty=uncertainty, roi_center=(0, 0))

    def test_negative_uncertainty_rejected(self):
        """Test that negative uncertainties are rejected."""
        energy = np.ones(10)
        transmission = np.ones(10) * 0.5
        uncertainty = np.ones(10) * -0.01  # Negative

        with pytest.raises(ValidationError, match="must be non-negative"):
            Transmission(energy=energy, transmission=transmission, uncertainty=uncertainty, roi_center=(0, 0))

    def test_to_dat_format(self):
        """Test exporting to SAMMY .dat format."""
        energy = np.array([1.0, 2.0, 3.0])
        transmission = np.array([0.9, 0.8, 0.7])
        uncertainty = np.array([0.01, 0.02, 0.03])

        trans = Transmission(energy=energy, transmission=transmission, uncertainty=uncertainty, roi_center=(0, 0))

        dat_array = trans.to_dat_format()
        assert dat_array.shape == (3, 3)
        np.testing.assert_array_equal(dat_array[:, 0], energy)
        np.testing.assert_array_equal(dat_array[:, 1], transmission)
        np.testing.assert_array_equal(dat_array[:, 2], uncertainty)

    def test_with_roi(self):
        """Test Transmission with ROI specified."""
        energy = np.ones(10)
        transmission = np.ones(10) * 0.5
        uncertainty = np.ones(10) * 0.01
        roi = Roi(x1=100, y1=100, x2=200, y2=200)

        trans = Transmission(
            energy=energy, transmission=transmission, uncertainty=uncertainty, roi=roi, roi_center=(150.0, 150.0)
        )

        assert trans.roi == roi
        assert trans.roi_center == (150.0, 150.0)
