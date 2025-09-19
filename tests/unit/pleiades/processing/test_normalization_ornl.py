"""Unit tests for ORNL-specific normalization pipeline."""

import numpy as np

from pleiades.processing import Roi
from pleiades.processing.models_ornl import Run, Transmission


class TestCalculateTransmission:
    """Test the core transmission calculation."""

    def test_method2_calculation(self):
        """Test Method 2 transmission calculation."""
        # Create sample and OB runs with known values
        sample_counts = np.ones((100, 256, 256)) * 10
        ob_counts = np.ones((100, 256, 256)) * 20

        sample_run = Run(counts=sample_counts, proton_charge=1000.0)
        ob_run = Run(counts=ob_counts, proton_charge=1000.0)

        # Import function (will fail until implemented)
        from pleiades.processing.normalization_ornl import calculate_transmission

        result = calculate_transmission(sample_run, ob_run)

        # Check result type
        assert isinstance(result, Transmission)

        # Check transmission values (10/20 = 0.5)
        expected_transmission = 0.5
        np.testing.assert_allclose(result.transmission, expected_transmission, rtol=1e-6)

        # Check uncertainty calculation
        # σ/T = sqrt(1/C_s + 1/C_o + ε_s² + ε_o²) with PC uncertainty
        C_s = 10 * 256 * 256  # Total counts per frame
        C_o = 20 * 256 * 256
        # Default PC uncertainties are 0.005 each
        expected_uncertainty = 0.5 * np.sqrt(1 / C_s + 1 / C_o + 0.005**2 + 0.005**2)
        np.testing.assert_allclose(result.uncertainty[0], expected_uncertainty, rtol=1e-6)

    def test_with_proton_charge_correction(self):
        """Test transmission with different proton charges."""
        sample_counts = np.ones((100, 256, 256)) * 10
        ob_counts = np.ones((100, 256, 256)) * 20

        # Different proton charges
        sample_run = Run(counts=sample_counts, proton_charge=900.0)
        ob_run = Run(counts=ob_counts, proton_charge=1100.0)

        from pleiades.processing.normalization_ornl import calculate_transmission

        result = calculate_transmission(sample_run, ob_run)

        # T = (C_s/C_o) * (PC_o/PC_s) = 0.5 * (1100/900)
        expected_transmission = 0.5 * (1100.0 / 900.0)
        np.testing.assert_allclose(result.transmission, expected_transmission, rtol=1e-6)

    def test_with_dead_pixels(self):
        """Test that dead pixels are properly excluded."""
        sample_counts = np.ones((10, 100, 100)) * 10
        ob_counts = np.ones((10, 100, 100)) * 20

        # Add some dead pixels
        sample_counts[:, 10:20, 10:20] = 0
        ob_counts[:, 30:40, 30:40] = 0

        sample_run = Run(counts=sample_counts, proton_charge=1000.0)
        ob_run = Run(counts=ob_counts, proton_charge=1000.0)

        from pleiades.processing.normalization_ornl import calculate_transmission

        result = calculate_transmission(sample_run, ob_run)

        # Dead pixels should be detected and excluded
        # Valid pixels: 10000 - 100 (sample dead) - 100 (ob dead) = 9800
        assert result.metadata.get("n_dead_pixels") == 200
        assert result.metadata.get("n_valid_pixels") == 9800

    def test_with_roi(self):
        """Test transmission calculation with ROI."""
        sample_counts = np.ones((10, 100, 100))
        ob_counts = np.ones((10, 100, 100)) * 2

        # Make ROI region different
        sample_counts[:, 40:60, 40:60] = 10
        ob_counts[:, 40:60, 40:60] = 20

        sample_run = Run(counts=sample_counts, proton_charge=1000.0)
        ob_run = Run(counts=ob_counts, proton_charge=1000.0)

        roi = Roi(x1=40, y1=40, x2=60, y2=60)

        from pleiades.processing.normalization_ornl import calculate_transmission

        result = calculate_transmission(sample_run, ob_run, roi=roi)

        # Should use only ROI region (10/20 = 0.5)
        np.testing.assert_allclose(result.transmission, 0.5, rtol=1e-6)
        assert result.roi == roi
        assert result.roi_center == (50.0, 50.0)


class TestProcessingModes:
    """Test different processing modes."""

    def test_process_individual_mode(self):
        """Test processing runs individually."""
        # Create multiple sample runs
        sample_runs = [Run(counts=np.ones((10, 100, 100)) * i, proton_charge=1000.0) for i in [10, 20, 30]]
        ob_runs = [Run(counts=np.ones((10, 100, 100)) * 100, proton_charge=1000.0)]

        from pleiades.processing.normalization_ornl import process_individual_mode

        results = process_individual_mode(sample_runs, ob_runs)

        # Should get one result per sample run
        assert len(results) == 3

        # Check transmission values
        np.testing.assert_allclose(results[0].transmission[0], 0.1, rtol=1e-6)
        np.testing.assert_allclose(results[1].transmission[0], 0.2, rtol=1e-6)
        np.testing.assert_allclose(results[2].transmission[0], 0.3, rtol=1e-6)

    def test_process_combined_mode(self):
        """Test processing with all runs combined."""
        sample_runs = [
            Run(counts=np.ones((10, 100, 100)) * 10, proton_charge=500.0),
            Run(counts=np.ones((10, 100, 100)) * 20, proton_charge=500.0),
        ]
        ob_runs = [
            Run(counts=np.ones((10, 100, 100)) * 50, proton_charge=500.0),
            Run(counts=np.ones((10, 100, 100)) * 50, proton_charge=500.0),
        ]

        from pleiades.processing.normalization_ornl import process_combined_mode

        results = process_combined_mode(sample_runs, ob_runs)

        # Should get single result
        assert len(results) == 1

        # Combined: (10+20)/(50+50) = 30/100 = 0.3
        np.testing.assert_allclose(results[0].transmission[0], 0.3, rtol=1e-6)

        # Check metadata
        assert results[0].metadata.get("n_sample_runs") == 2
        assert results[0].metadata.get("n_ob_runs") == 2


class TestNormalizationOrnl:
    """Test the main ORNL normalization function."""

    def test_basic_normalization(self):
        """Test basic normalization with folders."""

        # This test would require actual folders with data
        # For unit test, we'll mock the data loading
        pass  # Placeholder for integration test

    def test_with_tof_to_energy_conversion(self):
        """Test that TOF is properly converted to energy."""
        # Create run with TOF metadata
        sample_counts = np.ones((100, 256, 256))
        tof_values = np.linspace(0.001, 0.01, 100)  # 1ms to 10ms

        sample_run = Run(counts=sample_counts, proton_charge=1000.0, metadata={"tof_values": tof_values})
        ob_run = Run(counts=sample_counts * 2, proton_charge=1000.0, metadata={"tof_values": tof_values})

        from pleiades.processing.normalization_ornl import calculate_transmission

        result = calculate_transmission(sample_run, ob_run)

        # Energy should be calculated from TOF
        assert len(result.energy) == 100
        assert result.energy[0] > result.energy[-1]  # Energy decreases with increasing TOF

        # Check rough energy range (should be eV range for these TOFs)
        assert 0.01 < result.energy[-1] < 1  # Last point (10ms) ~ 0.033 eV
        assert 1 < result.energy[0] < 100  # First point (1ms) ~ 3.3 eV
