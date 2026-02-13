"""Unit tests for pleiades.imaging.orchestrator."""

import pickle
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pleiades.imaging.config import ImagingConfig
from pleiades.imaging.models import PixelFitResult, PixelSpectrum
from pleiades.imaging.orchestrator import BatchFittingOrchestrator, CheckpointData, _fit_pixel_worker
from pleiades.sammy.results.models import ChiSquaredResults, FitResults


@pytest.fixture
def imaging_config():
    """Create test imaging configuration."""
    return ImagingConfig(
        isotopes=["Ta-181"],
        element="Ta",
        mass_number=181,
        density_g_cm3=16.6,
        thickness_mm=0.025,
        atomic_mass_amu=180.9479958,
        natural_abundances=True,
        min_energy_eV=1.0,
        max_energy_eV=100.0,
    )


@pytest.fixture
def test_pixel():
    """Create test pixel spectrum."""
    energy = np.linspace(1, 100, 50)
    transmission = np.random.uniform(0.5, 1.0, 50)
    uncertainty = transmission * 0.01

    return PixelSpectrum(row=5, col=10, energy=energy, transmission=transmission, uncertainty=uncertainty)


@pytest.fixture
def mock_sammy_executable(tmp_path):
    """Create mock SAMMY executable."""
    sammy_exe = tmp_path / "sammy"
    sammy_exe.touch()
    sammy_exe.chmod(0o755)
    return sammy_exe


class TestBatchFittingOrchestrator:
    """Test BatchFittingOrchestrator class."""

    def test_orchestrator_init_valid(self, imaging_config, mock_sammy_executable):
        """Test orchestrator initialization with valid config."""
        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=4
        )

        assert orchestrator.imaging_config == imaging_config
        assert orchestrator.sammy_executable == mock_sammy_executable
        assert orchestrator.n_workers == 4
        assert orchestrator.resolution_file is None

    def test_orchestrator_init_missing_executable(self, imaging_config):
        """Test orchestrator initialization with missing SAMMY executable."""
        with pytest.raises(FileNotFoundError, match="SAMMY executable not found"):
            BatchFittingOrchestrator(
                imaging_config=imaging_config, sammy_executable=Path("/nonexistent/sammy"), n_workers=4
            )

    def test_orchestrator_init_with_resolution_file(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test orchestrator initialization with resolution file."""
        resolution_file = tmp_path / "resolution.dat"
        resolution_file.touch()

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config,
            sammy_executable=mock_sammy_executable,
            n_workers=4,
            resolution_file=resolution_file,
        )

        assert orchestrator.resolution_file == resolution_file

    def test_orchestrator_init_missing_resolution_file(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test orchestrator initialization with missing resolution file."""
        resolution_file = tmp_path / "nonexistent_resolution.dat"

        with pytest.raises(FileNotFoundError, match="Resolution file not found"):
            BatchFittingOrchestrator(
                imaging_config=imaging_config,
                sammy_executable=mock_sammy_executable,
                n_workers=4,
                resolution_file=resolution_file,
            )

    @pytest.mark.skip(reason="ProcessPoolExecutor cannot pickle mocked functions. Worker function tested separately.")
    @patch("pleiades.imaging.orchestrator._fit_pixel_worker")
    def test_fit_pixels_single_success(self, mock_worker, imaging_config, mock_sammy_executable, test_pixel):
        """Test fitting single pixel with success."""
        # Mock successful fit result with mock FitResults
        mock_fit_results = MagicMock(spec=FitResults)
        mock_fit_result = PixelFitResult(
            row=5, col=10, fit_results=mock_fit_results, success=True, error_message=None, chi_squared=1.234
        )
        mock_worker.return_value = mock_fit_result

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels([test_pixel])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].chi_squared == 1.234
        mock_worker.assert_called_once()

    @pytest.mark.skip(reason="ProcessPoolExecutor cannot pickle mocked functions. Worker function tested separately.")
    @patch("pleiades.imaging.orchestrator._fit_pixel_worker")
    def test_fit_pixels_single_failure(self, mock_worker, imaging_config, mock_sammy_executable, test_pixel):
        """Test fitting single pixel with failure."""
        # Mock failed fit result
        mock_fit_result = PixelFitResult(
            row=5, col=10, fit_results=None, success=False, error_message="SAMMY execution failed", chi_squared=None
        )
        mock_worker.return_value = mock_fit_result

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels([test_pixel])

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error_message == "SAMMY execution failed"
        assert results[0].chi_squared is None

    @pytest.mark.skip(reason="ProcessPoolExecutor cannot pickle mocked functions. Worker function tested separately.")
    @patch("pleiades.imaging.orchestrator._fit_pixel_worker")
    def test_fit_pixels_multiple_parallel(self, mock_worker, imaging_config, mock_sammy_executable):
        """Test fitting multiple pixels in parallel."""
        # Create multiple test pixels
        pixels = [
            PixelSpectrum(
                row=i,
                col=j,
                energy=np.linspace(1, 100, 50),
                transmission=np.random.uniform(0.5, 1.0, 50),
                uncertainty=np.full(50, 0.01),
            )
            for i in range(2)
            for j in range(2)
        ]

        # Mock successful results
        def mock_fit(pixel, *args, **kwargs):
            mock_fit_results = MagicMock(spec=FitResults)
            return PixelFitResult(
                row=pixel.row,
                col=pixel.col,
                fit_results=mock_fit_results,
                success=True,
                error_message=None,
                chi_squared=1.0,
            )

        mock_worker.side_effect = mock_fit

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=2
        )

        results = orchestrator.fit_pixels(pixels)

        assert len(results) == 4
        assert all(r.success for r in results)
        assert mock_worker.call_count == 4

    @pytest.mark.skip(reason="ProcessPoolExecutor cannot pickle mocked functions. Checkpoint logic tested separately.")
    @patch("pleiades.imaging.orchestrator._fit_pixel_worker")
    def test_fit_pixels_checkpoint_save(self, mock_worker, imaging_config, mock_sammy_executable, test_pixel, tmp_path):
        """Test checkpoint saving during execution."""
        mock_fit_results = MagicMock(spec=FitResults)
        mock_fit_result = PixelFitResult(
            row=5, col=10, fit_results=mock_fit_results, success=True, error_message=None, chi_squared=1.234
        )
        mock_worker.return_value = mock_fit_result

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        checkpoint_file = tmp_path / "checkpoint.pkl"
        results = orchestrator.fit_pixels([test_pixel], checkpoint_file=checkpoint_file, checkpoint_interval=1)

        # Verify checkpoint file was created
        assert checkpoint_file.exists()

        # Load and verify checkpoint
        with open(checkpoint_file, "rb") as f:
            checkpoint = pickle.load(f)

        assert isinstance(checkpoint, CheckpointData)
        assert len(checkpoint.completed_pixels) == 1
        assert checkpoint.total_pixels == 1
        assert (5, 10) in checkpoint.completed_pixels

    @pytest.mark.skip(reason="ProcessPoolExecutor cannot pickle mocked functions. Checkpoint logic tested separately.")
    @patch("pleiades.imaging.orchestrator._fit_pixel_worker")
    def test_fit_pixels_resume_from_checkpoint(self, mock_worker, imaging_config, mock_sammy_executable, tmp_path):
        """Test resuming from checkpoint."""
        # Create test pixels
        pixels = [
            PixelSpectrum(
                row=i,
                col=0,
                energy=np.linspace(1, 100, 50),
                transmission=np.random.uniform(0.5, 1.0, 50),
                uncertainty=np.full(50, 0.01),
            )
            for i in range(3)
        ]

        # Create checkpoint with first pixel already completed
        mock_fit_results_1 = MagicMock(spec=FitResults)
        completed = {
            (0, 0): PixelFitResult(
                row=0, col=0, fit_results=mock_fit_results_1, success=True, error_message=None, chi_squared=1.0
            )
        }
        checkpoint = CheckpointData(completed_pixels=completed, total_pixels=3, config=imaging_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        # Mock worker for remaining pixels
        def mock_fit(pixel, *args, **kwargs):
            mock_fit_results = MagicMock(spec=FitResults)
            return PixelFitResult(
                row=pixel.row,
                col=pixel.col,
                fit_results=mock_fit_results,
                success=True,
                error_message=None,
                chi_squared=2.0,
            )

        mock_worker.side_effect = mock_fit

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        # Resume from checkpoint
        results = orchestrator.fit_pixels(pixels, checkpoint_file=checkpoint_file, resume=True)

        # Verify results
        assert len(results) == 3
        assert all(r.success for r in results)

        # First pixel should have chi_squared = 1.0 (from checkpoint)
        assert results[0].chi_squared == 1.0

        # Other pixels should have chi_squared = 2.0 (from mock)
        assert results[1].chi_squared == 2.0
        assert results[2].chi_squared == 2.0

        # Worker should only be called for remaining 2 pixels
        assert mock_worker.call_count == 2

    def test_fit_pixels_resume_missing_checkpoint(self, imaging_config, mock_sammy_executable, test_pixel, tmp_path):
        """Test resume with missing checkpoint file raises error."""
        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        checkpoint_file = tmp_path / "nonexistent.pkl"

        with pytest.raises(FileNotFoundError, match="Checkpoint file not found"):
            orchestrator.fit_pixels([test_pixel], checkpoint_file=checkpoint_file, resume=True)

    def test_fit_pixels_resume_total_pixels_mismatch(self, imaging_config, mock_sammy_executable, test_pixel, tmp_path):
        """Test resume rejects checkpoint created for different batch size."""
        checkpoint = CheckpointData(completed_pixels={}, total_pixels=2, config=imaging_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="total_pixels=.*does not match current batch size=.*"):
            orchestrator.fit_pixels([test_pixel], checkpoint_file=checkpoint_file, resume=True)

    def test_fit_pixels_resume_pixel_set_mismatch(self, imaging_config, mock_sammy_executable, test_pixel, tmp_path):
        """Test resume rejects checkpoint containing pixels outside current batch."""
        completed = {
            (99, 99): PixelFitResult(
                row=99,
                col=99,
                fit_results=None,
                success=False,
                error_message="Previous failed fit",
                chi_squared=None,
            )
        }
        checkpoint = CheckpointData(completed_pixels=completed, total_pixels=1, config=imaging_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint contains pixel .* not present in current batch"):
            orchestrator.fit_pixels([test_pixel], checkpoint_file=checkpoint_file, resume=True)

    def test_load_checkpoint_config_mismatch(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test loading checkpoint with mismatched config raises error."""
        # Create checkpoint with different isotopes
        different_config = ImagingConfig(
            isotopes=["Au-197"],  # Different isotope
            element="Au",
            mass_number=197,
            density_g_cm3=19.32,
            thickness_mm=0.025,
            atomic_mass_amu=196.966569,
        )

        checkpoint = CheckpointData(completed_pixels={}, total_pixels=1, config=different_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint isotopes .* != current"):
            orchestrator._load_checkpoint(checkpoint_file)

    def test_load_checkpoint_density_mismatch(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test loading checkpoint with mismatched density raises error."""
        # Create checkpoint with different density
        different_config = ImagingConfig(
            isotopes=["Ta-181"],  # Same isotope
            element="Ta",
            mass_number=181,
            density_g_cm3=19.32,  # Different density
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
        )

        checkpoint = CheckpointData(completed_pixels={}, total_pixels=1, config=different_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint density .* g/cm³ != current"):
            orchestrator._load_checkpoint(checkpoint_file)

    def test_load_checkpoint_thickness_mismatch(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test loading checkpoint with mismatched thickness raises error."""
        # Create checkpoint with different thickness
        different_config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.1,  # Different thickness
            atomic_mass_amu=180.9479958,
        )

        checkpoint = CheckpointData(completed_pixels={}, total_pixels=1, config=different_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint thickness .* mm != current"):
            orchestrator._load_checkpoint(checkpoint_file)

    def test_load_checkpoint_atomic_mass_mismatch(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test loading checkpoint with mismatched atomic mass raises error."""
        # Create checkpoint with different atomic mass
        different_config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.0,  # Different atomic mass
        )

        checkpoint = CheckpointData(completed_pixels={}, total_pixels=1, config=different_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint atomic mass .* amu != current"):
            orchestrator._load_checkpoint(checkpoint_file)

    def test_load_checkpoint_temperature_mismatch(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test loading checkpoint with mismatched temperature raises error."""
        # Create checkpoint with different temperature
        different_config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
            temperature_K=500.0,  # Different temperature
        )

        checkpoint = CheckpointData(completed_pixels={}, total_pixels=1, config=different_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint temperature .* K != current"):
            orchestrator._load_checkpoint(checkpoint_file)

    def test_fit_pixels_empty_list(self, imaging_config, mock_sammy_executable):
        """Test fitting empty pixel list."""
        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        results = orchestrator.fit_pixels([])

        assert len(results) == 0

    def test_fit_pixels_resume_without_checkpoint(self, imaging_config, mock_sammy_executable, test_pixel):
        """Test resume=True without checkpoint_file raises error."""
        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Cannot resume without checkpoint_file"):
            orchestrator.fit_pixels([test_pixel], resume=True, checkpoint_file=None)

    def test_load_checkpoint_min_energy_mismatch(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test loading checkpoint with mismatched min_energy raises error."""
        # Create checkpoint with different min_energy
        different_config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
            min_energy_eV=0.5,  # Different min_energy
            max_energy_eV=100.0,
        )

        checkpoint = CheckpointData(completed_pixels={}, total_pixels=1, config=different_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint min_energy .* eV != current"):
            orchestrator._load_checkpoint(checkpoint_file)

    def test_load_checkpoint_max_energy_mismatch(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test loading checkpoint with mismatched max_energy raises error."""
        # Create checkpoint with different max_energy
        different_config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
            min_energy_eV=1.0,
            max_energy_eV=200.0,  # Different max_energy
        )

        checkpoint = CheckpointData(completed_pixels={}, total_pixels=1, config=different_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint max_energy .* eV != current"):
            orchestrator._load_checkpoint(checkpoint_file)

    def test_load_checkpoint_natural_abundances_mismatch(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test loading checkpoint with mismatched natural_abundances raises error."""
        # Create checkpoint with different natural_abundances setting
        different_config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
            natural_abundances=False,  # Different abundance setting
            custom_abundances=[1.0],
        )

        checkpoint = CheckpointData(completed_pixels={}, total_pixels=1, config=different_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint natural_abundances .* != current"):
            orchestrator._load_checkpoint(checkpoint_file)

    def test_load_checkpoint_custom_abundances_mismatch(self, imaging_config, mock_sammy_executable, tmp_path):
        """Test loading checkpoint with mismatched custom_abundances raises error."""
        # Create checkpoint with different custom_abundances
        different_config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
            natural_abundances=False,
            custom_abundances=[0.5],  # Different custom abundance
        )

        checkpoint = CheckpointData(completed_pixels={}, total_pixels=1, config=different_config)

        checkpoint_file = tmp_path / "checkpoint.pkl"
        with open(checkpoint_file, "wb") as f:
            pickle.dump(checkpoint, f)

        # Create orchestrator with matching natural_abundances=False but different custom_abundances
        different_current_config = ImagingConfig(
            isotopes=["Ta-181"],
            element="Ta",
            mass_number=181,
            density_g_cm3=16.6,
            thickness_mm=0.025,
            atomic_mass_amu=180.9479958,
            natural_abundances=False,
            custom_abundances=[1.0],  # Different value
        )

        orchestrator = BatchFittingOrchestrator(
            imaging_config=different_current_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Checkpoint custom_abundances .* != current"):
            orchestrator._load_checkpoint(checkpoint_file)


class TestFitPixelWorker:
    """Test _fit_pixel_worker function."""

    @patch("pleiades.imaging.orchestrator.ResultsManager")
    @patch("pleiades.imaging.orchestrator.LocalSammyRunner")
    @patch("pleiades.imaging.orchestrator.JsonManager")
    def test_fit_pixel_worker_success(self, mock_json_mgr, mock_runner_cls, mock_results_mgr_cls, imaging_config):
        """Test worker function with successful SAMMY execution."""
        # Create test pixel
        pixel = PixelSpectrum(
            row=1,
            col=2,
            energy=np.linspace(1, 100, 50),
            transmission=np.random.uniform(0.5, 1.0, 50),
            uncertainty=np.full(50, 0.01),
        )

        # Mock JSON manager
        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.return_value = Path("/tmp/config.json")
        mock_json_mgr.return_value = mock_json_instance

        # Mock SAMMY runner
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error_message = None
        mock_runner.execute_sammy.return_value = mock_result
        mock_runner_cls.return_value = mock_runner

        # Mock results manager with fit results
        mock_fit_result = MagicMock(spec=FitResults)
        mock_chi_sq = ChiSquaredResults(chi_squared=1.234, dof=50, reduced_chi_squared=0.025)
        mock_fit_result.get_chi_squared_results.return_value = mock_chi_sq

        mock_results_mgr = MagicMock()
        mock_results_mgr.run_results.fit_results = [mock_fit_result]
        mock_results_mgr_cls.return_value = mock_results_mgr

        # Mock SAMMY executable
        with tempfile.TemporaryDirectory() as temp_dir:
            sammy_exe = Path(temp_dir) / "sammy"
            sammy_exe.touch()

            result = _fit_pixel_worker(pixel, imaging_config, sammy_exe)

        assert result.row == 1
        assert result.col == 2
        assert result.success is True
        assert result.chi_squared == 1.234
        assert result.error_message is None
        mock_runner.validate_config.assert_called_once()

    @patch("pleiades.imaging.orchestrator.LocalSammyRunner")
    @patch("pleiades.imaging.orchestrator.JsonManager")
    def test_fit_pixel_worker_sammy_failure(self, mock_json_mgr, mock_runner_cls, imaging_config):
        """Test worker function with SAMMY execution failure."""
        # Create test pixel
        pixel = PixelSpectrum(
            row=3,
            col=4,
            energy=np.linspace(1, 100, 50),
            transmission=np.random.uniform(0.5, 1.0, 50),
            uncertainty=np.full(50, 0.01),
        )

        # Mock JSON manager
        mock_json_instance = MagicMock()
        mock_json_instance.create_json_config.return_value = Path("/tmp/config.json")
        mock_json_mgr.return_value = mock_json_instance

        # Mock SAMMY runner with failure
        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "SAMMY crashed"
        mock_runner.execute_sammy.return_value = mock_result
        mock_runner_cls.return_value = mock_runner

        # Mock SAMMY executable
        with tempfile.TemporaryDirectory() as temp_dir:
            sammy_exe = Path(temp_dir) / "sammy"
            sammy_exe.touch()

            result = _fit_pixel_worker(pixel, imaging_config, sammy_exe)

        assert result.row == 3
        assert result.col == 4
        assert result.success is False
        assert "SAMMY execution failed" in result.error_message
        assert result.chi_squared is None
        mock_runner.validate_config.assert_called_once()

    @patch("pleiades.imaging.orchestrator.JsonManager")
    def test_fit_pixel_worker_exception_handling(self, mock_json_mgr, imaging_config):
        """Test worker function handles exceptions gracefully."""
        # Create test pixel
        pixel = PixelSpectrum(
            row=5,
            col=6,
            energy=np.linspace(1, 100, 50),
            transmission=np.random.uniform(0.5, 1.0, 50),
            uncertainty=np.full(50, 0.01),
        )

        # Mock JSON manager to raise exception
        mock_json_mgr.side_effect = RuntimeError("JSON creation failed")

        # Mock SAMMY executable
        with tempfile.TemporaryDirectory() as temp_dir:
            sammy_exe = Path(temp_dir) / "sammy"
            sammy_exe.touch()

            result = _fit_pixel_worker(pixel, imaging_config, sammy_exe)

        assert result.row == 5
        assert result.col == 6
        assert result.success is False
        assert "Exception:" in result.error_message
        assert result.chi_squared is None
