"""Unit tests for ORNL-specific helper functions."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from pleiades.processing.helper_ornl import (
    combine_runs,
    detect_persistent_dead_pixels,
    find_nexus_file,
    load_multiple_runs,
    load_run_from_folder,
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


class TestFindNexusFile:
    """Test NeXus file discovery."""

    def test_find_nexus_in_parent_structure(self):
        """Test finding NeXus file in standard ORNL directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create ORNL-like structure: parent/nexus/VENUS_8022.nxs.h5
            parent = Path(tmpdir)
            nexus_dir = parent / "nexus"
            nexus_dir.mkdir()
            run_dir = parent / "measurements" / "Run_8022"
            run_dir.mkdir(parents=True)

            # Create mock NeXus file
            nexus_file = nexus_dir / "VENUS_8022.nxs.h5"
            nexus_file.touch()

            # Test finding from run folder
            result = find_nexus_file(str(run_dir))
            assert result == str(nexus_file)

    def test_find_nexus_with_custom_dir(self):
        """Test finding NeXus file with custom nexus directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create custom nexus directory
            custom_nexus = Path(tmpdir) / "custom_nexus"
            custom_nexus.mkdir()

            # Create NeXus file
            nexus_file = custom_nexus / "VENUS_9999.nxs.h5"
            nexus_file.touch()

            # Test finding with custom directory
            result = find_nexus_file("Run_9999", nexus_dir=str(custom_nexus))
            assert result == str(nexus_file)

    def test_find_nexus_multiple_matches(self):
        """Test that first match is returned when multiple files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nexus_dir = Path(tmpdir)

            # Create multiple matching files
            nexus1 = nexus_dir / "VENUS_8022.nxs.h5"
            nexus2 = nexus_dir / "VENUS_8022_corrected.nxs.h5"
            nexus1.touch()
            nexus2.touch()

            result = find_nexus_file("Run_8022", nexus_dir=str(nexus_dir))
            assert result in [str(nexus1), str(nexus2)]  # Should return one of them

    def test_find_nexus_not_found(self):
        """Test when NeXus file is not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = find_nexus_file("Run_9999", nexus_dir=tmpdir)
            assert result is None

    def test_extract_run_number_from_folder(self):
        """Test run number extraction from different folder name formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nexus_dir = Path(tmpdir)

            # Test with underscore format
            nexus_file = nexus_dir / "VENUS_1234.nxs.h5"
            nexus_file.touch()

            result = find_nexus_file("Run_1234", nexus_dir=str(nexus_dir))
            assert result == str(nexus_file)

            # Test with just number
            result = find_nexus_file("1234", nexus_dir=str(nexus_dir))
            assert result == str(nexus_file)


class TestLoadRunFromFolder:
    """Test loading run data from folder."""

    @patch("pleiades.processing.helper_ornl.retrieve_list_of_most_dominant_extension_from_folder")
    @patch("pleiades.processing.helper_ornl.load")
    @patch("pleiades.processing.helper_ornl.load_spectra_file")
    @patch("pleiades.processing.helper_ornl.find_nexus_file")
    @patch("pleiades.processing.helper_ornl.get_proton_charge")
    def test_load_run_complete(self, mock_get_pc, mock_find_nexus, mock_load_spectra, mock_load, mock_retrieve):
        """Test loading a complete run with all data available."""
        # Setup mocks
        mock_retrieve.return_value = (["img1.tiff", "img2.tiff"], ".tiff")
        mock_load.return_value = np.ones((100, 256, 256))
        mock_load_spectra.return_value = np.column_stack([np.arange(100) * 0.001, np.ones(100)])
        mock_find_nexus.return_value = "/path/to/nexus.h5"
        mock_get_pc.return_value = 1234567.0  # in pC

        # Load run
        run = load_run_from_folder("/path/to/Run_8022")

        # Verify calls
        mock_retrieve.assert_called_once_with("/path/to/Run_8022")
        mock_load.assert_called_once_with(["img1.tiff", "img2.tiff"], ".tiff")
        mock_load_spectra.assert_called_once_with("/path/to/Run_8022")
        mock_find_nexus.assert_called_once_with("/path/to/Run_8022", None)
        mock_get_pc.assert_called_once_with("/path/to/nexus.h5", units="pc")

        # Check run object
        assert run.counts.shape == (100, 256, 256)
        assert run.proton_charge == pytest.approx(1.234567)  # 1234567 pC / 1e6 = 1.234567 μC
        assert run.metadata["folder"] == "/path/to/Run_8022"
        assert run.metadata["nexus_path"] == "/path/to/nexus.h5"
        assert run.metadata["n_tof"] == 100
        assert len(run.metadata["tof_values"]) == 100

    @patch("pleiades.processing.helper_ornl.retrieve_list_of_most_dominant_extension_from_folder")
    def test_load_run_no_files(self, mock_retrieve):
        """Test error when no image files found."""
        mock_retrieve.return_value = ([], "")

        with pytest.raises(ValueError, match="No image files found"):
            load_run_from_folder("/empty/folder")

    @patch("pleiades.processing.helper_ornl.retrieve_list_of_most_dominant_extension_from_folder")
    @patch("pleiades.processing.helper_ornl.load")
    @patch("pleiades.processing.helper_ornl.load_spectra_file")
    @patch("pleiades.processing.helper_ornl.find_nexus_file")
    def test_load_run_tof_mismatch(self, mock_find_nexus, mock_load_spectra, mock_load, mock_retrieve):
        """Test handling of TOF length mismatch."""
        mock_retrieve.return_value = (["img1.tiff"], ".tiff")
        mock_load.return_value = np.ones((100, 256, 256))
        # Return wrong number of TOF values
        mock_load_spectra.return_value = np.column_stack([np.arange(50) * 0.001, np.ones(50)])
        mock_find_nexus.return_value = None

        run = load_run_from_folder("/path/to/Run_8022")

        # TOF values should be None due to mismatch
        assert run.metadata["tof_values"] is None
        assert run.metadata["n_tof"] == 100

    @patch("pleiades.processing.helper_ornl.retrieve_list_of_most_dominant_extension_from_folder")
    @patch("pleiades.processing.helper_ornl.load")
    @patch("pleiades.processing.helper_ornl.load_spectra_file")
    @patch("pleiades.processing.helper_ornl.find_nexus_file")
    @patch("pleiades.processing.helper_ornl.get_proton_charge")
    def test_load_run_with_custom_nexus_path(
        self, mock_get_pc, mock_find_nexus, mock_load_spectra, mock_load, mock_retrieve
    ):
        """Test loading run with explicitly provided nexus path."""
        mock_retrieve.return_value = (["img1.tiff"], ".tiff")
        mock_load.return_value = np.ones((10, 128, 128))
        mock_load_spectra.return_value = None
        mock_get_pc.return_value = 5000000.0  # in pC

        # Load with custom nexus path
        run = load_run_from_folder("/path/to/Run", nexus_path="/custom/nexus.h5")

        # find_nexus_file should not be called
        mock_find_nexus.assert_not_called()
        mock_get_pc.assert_called_once_with("/custom/nexus.h5", units="pc")

        assert run.proton_charge == pytest.approx(5.0)  # 5000000 pC / 1e6 = 5.0 μC
        assert run.metadata["nexus_path"] == "/custom/nexus.h5"

    @patch("pleiades.processing.helper_ornl.retrieve_list_of_most_dominant_extension_from_folder")
    @patch("pleiades.processing.helper_ornl.load")
    @patch("pleiades.processing.helper_ornl.load_spectra_file")
    @patch("pleiades.processing.helper_ornl.find_nexus_file")
    @patch("pleiades.processing.helper_ornl.get_proton_charge")
    def test_load_run_no_proton_charge(self, mock_get_pc, mock_find_nexus, mock_load_spectra, mock_load, mock_retrieve):
        """Test loading run when proton charge is not available."""
        mock_retrieve.return_value = (["img1.tiff"], ".tiff")
        mock_load.return_value = np.ones((10, 128, 128))
        mock_load_spectra.return_value = None
        mock_find_nexus.return_value = None
        mock_get_pc.return_value = None  # No proton charge available

        run = load_run_from_folder("/path/to/Run")

        # Should use default proton charge of 1.0
        assert run.proton_charge == 1.0
        assert run.metadata["nexus_path"] is None


class TestLoadMultipleRuns:
    """Test loading multiple runs."""

    @patch("pleiades.processing.helper_ornl.load_run_from_folder")
    def test_load_multiple_runs_success(self, mock_load_run):
        """Test successfully loading multiple runs."""
        # Create mock runs
        run1 = Run(
            counts=np.ones((100, 256, 256)),
            proton_charge=1000.0,
            metadata={"run_number": "8022"},
        )
        run2 = Run(
            counts=np.ones((100, 256, 256)) * 2,
            proton_charge=1500.0,
            metadata={"run_number": "8023"},
        )
        run3 = Run(
            counts=np.ones((100, 256, 256)) * 3,
            proton_charge=2000.0,
            metadata={"run_number": "8024"},
        )

        mock_load_run.side_effect = [run1, run2, run3]

        folders = ["/path/Run_8022", "/path/Run_8023", "/path/Run_8024"]
        runs = load_multiple_runs(folders)

        assert len(runs) == 3
        assert runs[0] == run1
        assert runs[1] == run2
        assert runs[2] == run3

        # Check that each folder was loaded
        assert mock_load_run.call_count == 3

    @patch("pleiades.processing.helper_ornl.load_run_from_folder")
    def test_load_multiple_runs_with_nexus_dir(self, mock_load_run):
        """Test loading multiple runs with custom nexus directory."""
        run1 = Run(counts=np.ones((10, 10, 10)), proton_charge=100.0)
        mock_load_run.return_value = run1

        folders = ["/path/Run_8022"]
        runs = load_multiple_runs(folders, nexus_dir="/custom/nexus")

        mock_load_run.assert_called_once_with("/path/Run_8022", nexus_dir="/custom/nexus")
        assert len(runs) == 1

    @patch("pleiades.processing.helper_ornl.load_run_from_folder")
    def test_load_multiple_runs_with_failure(self, mock_load_run):
        """Test that failure in one run propagates."""
        mock_load_run.side_effect = ValueError("Failed to load run")

        with pytest.raises(ValueError, match="Failed to load run"):
            load_multiple_runs(["/path/Run_8022"])

    @patch("pleiades.processing.helper_ornl.load_run_from_folder")
    def test_load_multiple_runs_empty_list(self, mock_load_run):
        """Test loading empty list of runs."""
        runs = load_multiple_runs([])

        assert len(runs) == 0
        mock_load_run.assert_not_called()


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple functions."""

    def test_tof_energy_conversion_roundtrip(self):
        """Test TOF to energy conversion consistency."""
        # Create a range of TOF values
        tof_original = np.logspace(-4, -1, 100)  # 0.1ms to 100ms

        # Convert to energy
        energy = tof_to_energy(tof_original, flight_path=25.0)

        # Energy should decrease as TOF increases (slower neutrons)
        assert np.all(np.diff(energy) < 0)

        # All energies should be positive (except for zero TOF)
        assert np.all(energy[tof_original > 0] > 0)

    def test_dead_pixel_detection_with_noise(self):
        """Test dead pixel detection with noisy data."""
        np.random.seed(42)

        # Create data with noise
        data = np.random.poisson(10, size=(100, 256, 256)).astype(float)

        # Add some dead pixels
        dead_regions = [(10, 20, 30, 40), (100, 110, 150, 160)]
        for y1, y2, x1, x2 in dead_regions:
            data[:, y1:y2, x1:x2] = 0

        dead_mask = detect_persistent_dead_pixels(data)

        # Check dead regions are detected
        for y1, y2, x1, x2 in dead_regions:
            assert np.all(dead_mask[y1:y2, x1:x2])

        # Check non-dead regions are not marked
        assert not np.all(dead_mask)

    def test_combine_runs_preserves_metadata(self):
        """Test that combining runs preserves important metadata."""
        tof_values = np.arange(50) * 0.001

        runs = [
            Run(
                counts=np.ones((50, 128, 128)) * i,
                proton_charge=100.0 * i,
                metadata={
                    "run_number": f"802{i}",
                    "folder": f"/path/Run_802{i}",
                    "tof_values": tof_values,
                    "n_tof": 50,
                },
            )
            for i in range(1, 4)
        ]

        combined = combine_runs(runs)

        # Check metadata preservation
        assert combined.metadata["n_runs_combined"] == 3
        assert combined.metadata["source_run_numbers"] == ["8021", "8022", "8023"]
        assert np.array_equal(combined.metadata["tof_values"], tof_values)
        assert combined.metadata["n_tof"] == 50

        # Check numerical accuracy
        assert combined.proton_charge == 600.0  # 100 + 200 + 300
        assert np.all(combined.counts == 6.0)  # 1 + 2 + 3
