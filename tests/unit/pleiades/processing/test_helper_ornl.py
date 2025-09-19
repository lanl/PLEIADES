"""Unit tests for ORNL-specific helper functions."""

import os
import tempfile

import numpy as np
import pytest

from pleiades.processing.helper_ornl import (
    combine_runs,
    detect_persistent_dead_pixels,
    load_spectra_file,
    tof_to_energy,
)
from pleiades.processing.models_ornl import Run


class TestDeadPixelDetection:
    """Test dead pixel detection function."""

    def test_no_dead_pixels(self):
        """Test with no dead pixels."""
        data = np.ones((100, 256, 256))  # All pixels have counts
        dead_mask = detect_persistent_dead_pixels(data)

        assert dead_mask.shape == (256, 256)
        assert not np.any(dead_mask)  # No dead pixels

    def test_some_dead_pixels(self):
        """Test with some persistent dead pixels."""
        data = np.ones((100, 256, 256))
        # Make some pixels dead across all frames
        data[:, 10:20, 30:40] = 0

        dead_mask = detect_persistent_dead_pixels(data)

        assert dead_mask.shape == (256, 256)
        assert np.sum(dead_mask) == 10 * 10  # 100 dead pixels
        assert np.all(dead_mask[10:20, 30:40])  # These should be marked dead

    def test_transient_zeros_not_dead(self):
        """Test that transient zeros are not marked as dead."""
        data = np.ones((100, 256, 256))
        # Make pixel zero in only some frames (transient)
        data[0:50, 100, 100] = 0  # Zero in first 50 frames only

        dead_mask = detect_persistent_dead_pixels(data)

        assert not dead_mask[100, 100]  # Should not be marked as dead


class TestCombineRuns:
    """Test run combination function."""

    def test_combine_single_run(self):
        """Test that combining single run returns the same run."""
        run = Run(counts=np.ones((100, 256, 256)), proton_charge=1234.5, metadata={"run_number": "8022"})

        combined = combine_runs([run])
        assert combined == run

    def test_combine_multiple_runs(self):
        """Test combining multiple runs."""
        run1 = Run(
            counts=np.ones((100, 256, 256)) * 2,
            proton_charge=1000.0,
            metadata={"run_number": "8022", "folder": "/path/8022"},
        )
        run2 = Run(
            counts=np.ones((100, 256, 256)) * 3,
            proton_charge=1500.0,
            metadata={"run_number": "8023", "folder": "/path/8023"},
        )

        combined = combine_runs([run1, run2])

        # Check counts are summed
        expected_counts = np.ones((100, 256, 256)) * 5
        np.testing.assert_array_equal(combined.counts, expected_counts)

        # Check proton charges are summed
        assert combined.proton_charge == 2500.0

        # Check metadata
        assert combined.metadata["n_runs_combined"] == 2
        assert combined.metadata["source_run_numbers"] == ["8022", "8023"]
        assert combined.metadata["individual_proton_charges"] == [1000.0, 1500.0]

    def test_combine_incompatible_shapes(self):
        """Test that incompatible shapes raise error."""
        run1 = Run(counts=np.ones((100, 256, 256)), proton_charge=1000.0)
        run2 = Run(
            counts=np.ones((100, 512, 512)),  # Different shape
            proton_charge=1500.0,
        )

        with pytest.raises(ValueError, match="shape mismatch"):
            combine_runs([run1, run2])

    def test_combine_empty_list(self):
        """Test that empty list raises error."""
        with pytest.raises(ValueError, match="Cannot combine empty"):
            combine_runs([])


class TestTofToEnergy:
    """Test TOF to energy conversion."""

    def test_known_conversion(self):
        """Test with known TOF-energy pairs."""
        # For 25m flight path, 1 meV neutron:
        # v = sqrt(2E/m) = sqrt(2 * 1e-3 * 1.602e-19 / 1.675e-27) = 437.4 m/s
        # t = L/v = 25/437.4 = 0.0571 s
        tof = np.array([0.0571])
        energy = tof_to_energy(tof, flight_path=25.0)

        # Should be approximately 1 meV (0.001 eV)
        assert np.abs(energy[0] - 0.001) < 0.00001  # Within 10 neV

    def test_zero_tof_handling(self):
        """Test that zero TOF is handled gracefully."""
        tof = np.array([0.0, 0.001, 0.01])
        energy = tof_to_energy(tof, flight_path=25.0)

        # Our implementation sets tof=0 to inf, so v=L/inf=0, E=0
        assert energy[0] == 0.0  # Zero TOF -> zero energy (handled safely)
        assert energy[1] > 0  # Non-zero TOF -> finite energy
        assert energy[2] > 0

    def test_array_shape_preserved(self):
        """Test that array shape is preserved."""
        tof = np.random.rand(100) * 0.1 + 0.001  # 1ms to 100ms
        energy = tof_to_energy(tof)

        assert energy.shape == tof.shape


class TestLoadSpectraFile:
    """Test spectra file loading."""

    def test_load_valid_spectra_file(self):
        """Test loading a valid spectra file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test spectra file
            spectra_path = os.path.join(tmpdir, "Run_8022_Spectra.txt")
            with open(spectra_path, "w") as f:
                f.write("# Header line\n")
                f.write("0.001,100\n")
                f.write("0.002,200\n")
                f.write("0.003,150\n")

            data = load_spectra_file(tmpdir, header=1, sep=",")

            assert data is not None
            assert data.shape == (3, 2)
            np.testing.assert_array_equal(data[:, 0], [0.001, 0.002, 0.003])
            np.testing.assert_array_equal(data[:, 1], [100, 200, 150])

    def test_no_spectra_file(self):
        """Test when no spectra file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = load_spectra_file(tmpdir)
            assert data is None

    def test_corrupted_spectra_file(self):
        """Test handling of corrupted spectra file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spectra_path = os.path.join(tmpdir, "Run_8022_Spectra.txt")
            with open(spectra_path, "w") as f:
                f.write("This is not valid CSV data\n")
                f.write("No numbers here!\n")

            data = load_spectra_file(tmpdir, header=0, sep=",")
            assert data is None  # Should return None on error
