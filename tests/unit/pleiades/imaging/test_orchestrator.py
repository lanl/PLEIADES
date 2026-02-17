"""Unit tests for pleiades.imaging.orchestrator."""

import os
import pickle
import signal
import tempfile
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import numpy as np
import pytest

from pleiades.imaging.config import ImagingConfig
from pleiades.imaging.models import PixelFitResult, PixelSpectrum
from pleiades.imaging.orchestrator import (
    BatchFittingOrchestrator,
    CheckpointData,
    GracefulShutdownHandler,
    ProgressReporter,
    _fit_pixel_worker,
    _worker_initializer,
)
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

        with pytest.raises(ValueError, match="Mismatched fields:.*isotopes"):
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

        with pytest.raises(ValueError, match="Mismatched fields:.*density_g_cm3"):
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

        with pytest.raises(ValueError, match="Mismatched fields:.*thickness_mm"):
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

        with pytest.raises(ValueError, match="Mismatched fields:.*atomic_mass_amu"):
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

        with pytest.raises(ValueError, match="Mismatched fields:.*temperature_K"):
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

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_fit_pixels_stages_shared_inputs_once(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable
    ):
        """Test ENDF/JSON inputs are staged once and reused across submitted pixels."""
        pixels = [
            PixelSpectrum(
                row=i,
                col=0,
                energy=np.linspace(1, 100, 50),
                transmission=np.random.uniform(0.5, 1.0, 50),
                uncertainty=np.full(50, 0.01),
            )
            for i in range(2)
        ]

        # Mock shared JSON staging
        mock_json_instance = MagicMock()

        def create_json_side_effect(isotopes, abundances, working_dir):
            working_dir.mkdir(parents=True, exist_ok=True)
            shared_json = working_dir / "config.json"
            shared_json.write_text("{}", encoding="utf-8")
            return shared_json

        mock_json_instance.create_json_config.side_effect = create_json_side_effect
        mock_json_mgr.return_value = mock_json_instance

        # Mock executor to avoid subprocesses while preserving Future/as_completed behavior
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        submitted_shared_json = []
        submitted_shared_endf = []

        def submit_side_effect(
            fn, pixel, imaging_cfg, sammy_exe, resolution_file, shared_json, shared_endf, *args, **kwargs
        ):
            submitted_shared_json.append(shared_json)
            submitted_shared_endf.append(shared_endf)
            mock_fit_results = MagicMock(spec=FitResults)
            future = Future()
            future.set_result(
                PixelFitResult(
                    row=pixel.row,
                    col=pixel.col,
                    fit_results=mock_fit_results,
                    success=True,
                    error_message=None,
                    chi_squared=1.0,
                )
            )
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=2
        )
        results = orchestrator.fit_pixels(pixels)

        assert len(results) == 2
        assert all(r.success for r in results)
        mock_json_instance.create_json_config.assert_called_once()
        assert len(submitted_shared_json) == 2
        assert submitted_shared_json[0] == submitted_shared_json[1]
        assert submitted_shared_endf[0] == submitted_shared_endf[1]

    def test_fit_pixels_rejects_duplicate_coordinates(self, imaging_config, mock_sammy_executable, test_pixel):
        """Test duplicate pixel coordinates are rejected to avoid result overwrite."""
        duplicate_pixel = PixelSpectrum(
            row=test_pixel.row,
            col=test_pixel.col,
            energy=test_pixel.energy.copy(),
            transmission=test_pixel.transmission.copy(),
            uncertainty=test_pixel.uncertainty.copy(),
        )

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        with pytest.raises(ValueError, match="Duplicate pixel coordinates detected"):
            orchestrator.fit_pixels([test_pixel, duplicate_pixel])

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

        with pytest.raises(ValueError, match="Mismatched fields:.*min_energy_eV"):
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

        with pytest.raises(ValueError, match="Mismatched fields:.*max_energy_eV"):
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

        with pytest.raises(ValueError, match="Mismatched fields:.*natural_abundances"):
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

        with pytest.raises(ValueError, match="Mismatched fields:.*custom_abundances"):
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

    @patch("pleiades.imaging.orchestrator.ResultsManager")
    @patch("pleiades.imaging.orchestrator.LocalSammyRunner")
    @patch("pleiades.imaging.orchestrator.JsonManager")
    def test_fit_pixel_worker_uses_shared_inputs(
        self, mock_json_mgr, mock_runner_cls, mock_results_mgr_cls, imaging_config
    ):
        """Test worker uses shared staged JSON/ENDF inputs without restaging."""
        pixel = PixelSpectrum(
            row=7,
            col=8,
            energy=np.linspace(1, 100, 50),
            transmission=np.random.uniform(0.5, 1.0, 50),
            uncertainty=np.full(50, 0.01),
        )

        mock_runner = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.error_message = None
        mock_runner.execute_sammy.return_value = mock_result
        mock_runner_cls.return_value = mock_runner

        mock_fit_result = MagicMock(spec=FitResults)
        mock_chi_sq = ChiSquaredResults(chi_squared=2.345, dof=50, reduced_chi_squared=0.047)
        mock_fit_result.get_chi_squared_results.return_value = mock_chi_sq
        mock_results_mgr = MagicMock()
        mock_results_mgr.run_results.fit_results = [mock_fit_result]
        mock_results_mgr_cls.return_value = mock_results_mgr

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sammy_exe = temp_path / "sammy"
            sammy_exe.touch()

            shared_dir = temp_path / "shared"
            shared_dir.mkdir()
            shared_json = shared_dir / "config.json"
            shared_json.write_text("{}", encoding="utf-8")
            (shared_dir / "073-Ta-181.B-VIII.0.par").write_text("ENDF", encoding="utf-8")

            result = _fit_pixel_worker(
                pixel,
                imaging_config,
                sammy_exe,
                shared_json_config=shared_json,
                shared_endf_directory=shared_dir,
            )

        assert result.success is True
        assert result.chi_squared == 2.345
        mock_json_mgr.assert_not_called()
        prepared_files = mock_runner.prepare_environment.call_args.args[0]
        assert prepared_files.json_config_file == shared_json
        assert prepared_files.endf_directory == shared_dir

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


# =============================================================================
# Tests for Issue #178: Progress tracking, graceful shutdown, and integration
# =============================================================================


class TestProgressReporter:
    """Tests for ProgressReporter progress bar wrapper."""

    def test_progress_reporter_init(self):
        """ProgressReporter initializes with a total pixel count and creates a tqdm bar."""

        with patch("pleiades.imaging.orchestrator.tqdm") as mock_tqdm:
            mock_bar = MagicMock()
            mock_tqdm.return_value = mock_bar

            reporter = ProgressReporter(total_pixels=100)

            mock_tqdm.assert_called_once()
            # Verify total was passed to tqdm
            tqdm_call_kwargs = mock_tqdm.call_args
            assert tqdm_call_kwargs.kwargs.get("total") == 100 or tqdm_call_kwargs.args == (100,), (
                "tqdm must be created with total=100 (positional or keyword)"
            )

    def test_progress_reporter_update(self):
        """Calling update(n) advances the progress bar by n steps."""

        with patch("pleiades.imaging.orchestrator.tqdm") as mock_tqdm:
            mock_bar = MagicMock()
            mock_tqdm.return_value = mock_bar

            reporter = ProgressReporter(total_pixels=50)
            reporter.update(1)
            mock_bar.update.assert_called_with(1)

            reporter.update(5)
            mock_bar.update.assert_called_with(5)

            assert mock_bar.update.call_count == 2

    def test_progress_reporter_context_manager(self):
        """ProgressReporter works as a context manager and auto-closes."""

        with patch("pleiades.imaging.orchestrator.tqdm") as mock_tqdm:
            mock_bar = MagicMock()
            mock_tqdm.return_value = mock_bar

            with ProgressReporter(total_pixels=10) as reporter:
                reporter.update(1)

            # close() must be called on __exit__
            mock_bar.close.assert_called_once()

    def test_progress_reporter_write(self):
        """write() outputs a message through tqdm to prevent garbled output."""

        with patch("pleiades.imaging.orchestrator.tqdm") as mock_tqdm:
            mock_bar = MagicMock()
            mock_tqdm.return_value = mock_bar

            reporter = ProgressReporter(total_pixels=20)
            reporter.write("Pixel (5, 10) SUCCESS")

            mock_bar.write.assert_called_once_with("Pixel (5, 10) SUCCESS")

    def test_progress_reporter_close(self):
        """close() finalizes the progress bar."""

        with patch("pleiades.imaging.orchestrator.tqdm") as mock_tqdm:
            mock_bar = MagicMock()
            mock_tqdm.return_value = mock_bar

            reporter = ProgressReporter(total_pixels=30)
            reporter.close()

            mock_bar.close.assert_called_once()

    def test_progress_reporter_tracks_success_failure_in_postfix(self):
        """ProgressReporter tracks success/failure counts displayed via tqdm postfix."""

        with patch("pleiades.imaging.orchestrator.tqdm") as mock_tqdm:
            mock_bar = MagicMock()
            mock_tqdm.return_value = mock_bar

            reporter = ProgressReporter(total_pixels=10)

            # Track a success
            reporter.record_success()
            # Verify set_postfix was called and includes success info
            postfix_calls = [c for c in mock_bar.method_calls if c[0] == "set_postfix"]
            assert len(postfix_calls) >= 1, "set_postfix should be called after record_success"

            # Track a failure
            reporter.record_failure()
            postfix_calls = [c for c in mock_bar.method_calls if c[0] == "set_postfix"]
            assert len(postfix_calls) >= 2, "set_postfix should be called after record_failure"


class TestGracefulShutdownHandler:
    """Tests for GracefulShutdownHandler signal management."""

    @pytest.fixture(autouse=True)
    def _restore_signal_handlers(self):
        """Safety net: always restore original signal handlers even if a test fails."""
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)
        yield
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)

    def test_shutdown_handler_init(self):
        """shutdown_requested starts as not set (False)."""

        handler = GracefulShutdownHandler()
        assert not handler.shutdown_requested, "shutdown_requested must be False on initialization"

    def test_shutdown_handler_install_uninstall(self):
        """install() registers custom signal handlers; uninstall() restores originals."""

        # Save the original handlers before we start
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigterm = signal.getsignal(signal.SIGTERM)

        handler = GracefulShutdownHandler()
        handler.install()

        # After install, signal handlers should be different from originals
        current_sigint = signal.getsignal(signal.SIGINT)
        current_sigterm = signal.getsignal(signal.SIGTERM)
        assert current_sigint != original_sigint, "SIGINT handler should be changed after install()"
        assert current_sigterm != original_sigterm, "SIGTERM handler should be changed after install()"

        handler.uninstall()

        # After uninstall, original handlers should be restored
        restored_sigint = signal.getsignal(signal.SIGINT)
        restored_sigterm = signal.getsignal(signal.SIGTERM)
        assert restored_sigint == original_sigint, "SIGINT handler not restored after uninstall()"
        assert restored_sigterm == original_sigterm, "SIGTERM handler not restored after uninstall()"

    def test_shutdown_handler_context_manager(self):
        """GracefulShutdownHandler works as a context manager (install on enter, uninstall on exit)."""

        original_sigint = signal.getsignal(signal.SIGINT)

        with GracefulShutdownHandler() as handler:
            # Inside context, handler should be installed
            assert signal.getsignal(signal.SIGINT) != original_sigint
            assert not handler.shutdown_requested

        # After context, original handler should be restored
        assert signal.getsignal(signal.SIGINT) == original_sigint

    def test_shutdown_handler_first_signal_sets_flag(self):
        """First SIGINT sets shutdown_requested flag without killing the process."""

        with GracefulShutdownHandler() as handler:
            assert not handler.shutdown_requested

            # Send SIGINT to ourselves (first signal = graceful)
            os.kill(os.getpid(), signal.SIGINT)

            assert handler.shutdown_requested, "shutdown_requested must be True after first SIGINT"

    def test_shutdown_handler_second_signal_forces_exit(self):
        """Second signal raises SystemExit or forces termination."""

        with GracefulShutdownHandler() as handler:
            # First signal: sets flag
            os.kill(os.getpid(), signal.SIGINT)
            assert handler.shutdown_requested

            # Second signal: should force exit (SystemExit or KeyboardInterrupt)
            with pytest.raises((SystemExit, KeyboardInterrupt)):
                os.kill(os.getpid(), signal.SIGINT)

    def test_shutdown_handler_sigterm(self):
        """SIGTERM is handled the same as SIGINT (sets shutdown flag)."""

        with GracefulShutdownHandler() as handler:
            assert not handler.shutdown_requested

            os.kill(os.getpid(), signal.SIGTERM)

            assert handler.shutdown_requested, "shutdown_requested must be True after SIGTERM"


class TestWorkerInitializer:
    """Tests for _worker_initializer subprocess setup."""

    def test_worker_initializer_ignores_sigint(self):
        """After _worker_initializer(), SIGINT handler is SIG_IGN so children ignore Ctrl+C."""

        # Save original handler
        original_handler = signal.getsignal(signal.SIGINT)

        try:
            _worker_initializer()

            current_handler = signal.getsignal(signal.SIGINT)
            assert current_handler == signal.SIG_IGN, (
                f"SIGINT handler should be SIG_IGN after _worker_initializer(), got {current_handler}"
            )
        finally:
            # Restore original handler so test framework isn't broken
            signal.signal(signal.SIGINT, original_handler)


class TestFitPixelsProgressIntegration:
    """Tests for fit_pixels() integration with ProgressReporter and GracefulShutdownHandler."""

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_fit_pixels_uses_progress_reporter(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable
    ):
        """fit_pixels() creates and uses ProgressReporter for progress tracking."""
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

        # Mock shared JSON staging
        mock_json_instance = MagicMock()

        def create_json_side_effect(isotopes, abundances, working_dir):
            working_dir.mkdir(parents=True, exist_ok=True)
            shared_json = working_dir / "config.json"
            shared_json.write_text("{}", encoding="utf-8")
            return shared_json

        mock_json_instance.create_json_config.side_effect = create_json_side_effect
        mock_json_mgr.return_value = mock_json_instance

        # Mock executor
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        def submit_side_effect(
            fn, pixel, imaging_cfg, sammy_exe, resolution_file, shared_json, shared_endf, *args, **kwargs
        ):
            future = Future()
            future.set_result(
                PixelFitResult(
                    row=pixel.row,
                    col=pixel.col,
                    fit_results=None,
                    success=False,
                    error_message="test",
                    chi_squared=None,
                )
            )
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=2
        )

        with patch("pleiades.imaging.orchestrator.ProgressReporter") as mock_progress_cls:
            mock_progress = MagicMock()
            mock_progress.__enter__ = MagicMock(return_value=mock_progress)
            mock_progress.__exit__ = MagicMock(return_value=False)
            mock_progress_cls.return_value = mock_progress

            results = orchestrator.fit_pixels(pixels)

            # ProgressReporter must be created with the correct total
            mock_progress_cls.assert_called_once_with(total_pixels=3)
            # update() must be called once per pixel
            assert mock_progress.update.call_count == 3

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_fit_pixels_graceful_shutdown_saves_checkpoint(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable, tmp_path
    ):
        """When a shutdown signal is received, completed futures are drained and checkpoint is saved.

        Scenario: 5 pixels submitted. 2 processed in main loop before shutdown triggers.
        1 additional future already completed (drained). 2 futures still pending (not resolved).
        Checkpoint should contain exactly 3 pixels (2 from loop + 1 drained).
        The 2 pending pixels should be reported as interrupted placeholders.
        """
        pixels = [
            PixelSpectrum(
                row=i,
                col=0,
                energy=np.linspace(1, 100, 50),
                transmission=np.random.uniform(0.5, 1.0, 50),
                uncertainty=np.full(50, 0.01),
            )
            for i in range(5)
        ]

        # Mock shared JSON staging
        mock_json_instance = MagicMock()

        def create_json_side_effect(isotopes, abundances, working_dir):
            working_dir.mkdir(parents=True, exist_ok=True)
            shared_json = working_dir / "config.json"
            shared_json.write_text("{}", encoding="utf-8")
            return shared_json

        mock_json_instance.create_json_config.side_effect = create_json_side_effect
        mock_json_mgr.return_value = mock_json_instance

        # Mock executor: first 3 futures are pre-resolved, last 2 are pending (never resolved).
        # This simulates real behavior where some workers finish before shutdown while others
        # are still running.
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        futures_created = []

        def submit_side_effect(
            fn, pixel, imaging_cfg, sammy_exe, resolution_file, shared_json, shared_endf, *args, **kwargs
        ):
            future = Future()
            if pixel.row < 3:
                # First 3 pixels complete immediately
                future.set_result(
                    PixelFitResult(
                        row=pixel.row,
                        col=pixel.col,
                        fit_results=None,
                        success=False,
                        error_message="test",
                        chi_squared=None,
                    )
                )
            # Pixels 3 and 4 remain pending (never resolved) — simulates in-flight workers
            futures_created.append(future)
            return future

        mock_executor.submit.side_effect = submit_side_effect

        checkpoint_file = tmp_path / "shutdown_checkpoint.pkl"

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=2
        )

        # Mock GracefulShutdownHandler to simulate shutdown after 2 pixels
        with patch("pleiades.imaging.orchestrator.GracefulShutdownHandler") as mock_shutdown_cls:
            mock_shutdown = MagicMock()
            mock_shutdown.__enter__ = MagicMock(return_value=mock_shutdown)
            mock_shutdown.__exit__ = MagicMock(return_value=False)

            # Simulate: shutdown_requested is False for first 2, then True
            shutdown_side_effect_values = [False, False, True, True, True, True, True, True]
            type(mock_shutdown).shutdown_requested = PropertyMock(side_effect=shutdown_side_effect_values)
            mock_shutdown_cls.return_value = mock_shutdown

            results = orchestrator.fit_pixels(pixels, checkpoint_file=checkpoint_file, checkpoint_interval=1)

        # A checkpoint should have been saved
        assert checkpoint_file.exists(), "Checkpoint file must be saved when shutdown is signaled"

        # Verify checkpoint contains exactly 3 pixels: 2 from main loop + 1 drained
        with open(checkpoint_file, "rb") as f:
            saved = pickle.load(f)
        assert isinstance(saved, CheckpointData)
        assert len(saved.completed_pixels) == 3, (
            f"Expected 3 completed pixels (2 from loop + 1 drained), got {len(saved.completed_pixels)}"
        )

        # Verify the 2 pending pixels are reported as interrupted placeholders in results
        interrupted = [r for r in results if r.error_message == "Batch fitting interrupted by shutdown signal"]
        assert len(interrupted) == 2, f"Expected 2 interrupted placeholders, got {len(interrupted)}"

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_fit_pixels_uses_worker_initializer(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable
    ):
        """ProcessPoolExecutor is created with initializer=_worker_initializer."""

        pixels = [
            PixelSpectrum(
                row=0,
                col=0,
                energy=np.linspace(1, 100, 50),
                transmission=np.random.uniform(0.5, 1.0, 50),
                uncertainty=np.full(50, 0.01),
            )
        ]

        # Mock shared JSON staging
        mock_json_instance = MagicMock()

        def create_json_side_effect(isotopes, abundances, working_dir):
            working_dir.mkdir(parents=True, exist_ok=True)
            shared_json = working_dir / "config.json"
            shared_json.write_text("{}", encoding="utf-8")
            return shared_json

        mock_json_instance.create_json_config.side_effect = create_json_side_effect
        mock_json_mgr.return_value = mock_json_instance

        # Mock executor
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        def submit_side_effect(
            fn, pixel, imaging_cfg, sammy_exe, resolution_file, shared_json, shared_endf, *args, **kwargs
        ):
            future = Future()
            future.set_result(
                PixelFitResult(
                    row=pixel.row,
                    col=pixel.col,
                    fit_results=None,
                    success=False,
                    error_message="test",
                    chi_squared=None,
                )
            )
            return future

        mock_executor.submit.side_effect = submit_side_effect

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=2
        )

        results = orchestrator.fit_pixels(pixels)

        # ProcessPoolExecutor must be created with initializer=_worker_initializer
        mock_executor_cls.assert_called_once()
        executor_call_kwargs = mock_executor_cls.call_args.kwargs
        assert "initializer" in executor_call_kwargs, "ProcessPoolExecutor must be called with initializer kwarg"
        assert executor_call_kwargs["initializer"] == _worker_initializer, (
            "ProcessPoolExecutor initializer must be _worker_initializer"
        )

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_fit_pixels_checkpoint_is_valid_after_completion(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable, tmp_path
    ):
        """fit_pixels() writes a valid, loadable checkpoint file after completion."""
        pixels = [
            PixelSpectrum(
                row=0,
                col=0,
                energy=np.linspace(1, 100, 50),
                transmission=np.random.uniform(0.5, 1.0, 50),
                uncertainty=np.full(50, 0.01),
            )
        ]

        # Mock shared JSON staging
        mock_json_instance = MagicMock()

        def create_json_side_effect(isotopes, abundances, working_dir):
            working_dir.mkdir(parents=True, exist_ok=True)
            shared_json = working_dir / "config.json"
            shared_json.write_text("{}", encoding="utf-8")
            return shared_json

        mock_json_instance.create_json_config.side_effect = create_json_side_effect
        mock_json_mgr.return_value = mock_json_instance

        # Mock executor
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        def submit_side_effect(
            fn, pixel, imaging_cfg, sammy_exe, resolution_file, shared_json, shared_endf, *args, **kwargs
        ):
            future = Future()
            future.set_result(
                PixelFitResult(
                    row=pixel.row,
                    col=pixel.col,
                    fit_results=None,
                    success=False,
                    error_message="test",
                    chi_squared=None,
                )
            )
            return future

        mock_executor.submit.side_effect = submit_side_effect

        checkpoint_file = tmp_path / "checkpoint_valid.pkl"

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        orchestrator.fit_pixels(pixels, checkpoint_file=checkpoint_file, checkpoint_interval=1)

        # The checkpoint file must exist and be loadable with correct content
        assert checkpoint_file.exists()
        with open(checkpoint_file, "rb") as f:
            loaded = pickle.load(f)
        assert isinstance(loaded, CheckpointData)
        assert loaded.total_pixels == 1
        assert (0, 0) in loaded.completed_pixels

    def test_save_checkpoint_atomic_write_uses_tmp_and_rename(self, imaging_config, mock_sammy_executable, tmp_path):
        """_save_checkpoint writes to a .tmp file then renames to final path (atomic)."""
        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=1
        )

        checkpoint_file = tmp_path / "checkpoint.pkl"
        completed = {
            (0, 0): PixelFitResult(
                row=0, col=0, fit_results=None, success=False, error_message="test", chi_squared=None
            )
        }

        orchestrator._save_checkpoint(checkpoint_file, completed, total_pixels=1)

        # After successful save: final file exists, .tmp file does NOT exist
        assert checkpoint_file.exists(), "Final checkpoint file must exist"
        assert not checkpoint_file.with_suffix(".tmp").exists(), ".tmp file must be cleaned up after atomic rename"

        # Verify the file is a valid checkpoint
        with open(checkpoint_file, "rb") as f:
            loaded = pickle.load(f)
        assert isinstance(loaded, CheckpointData)
        assert loaded.total_pixels == 1

    @patch("pleiades.imaging.orchestrator.JsonManager")
    @patch("pleiades.imaging.orchestrator.ProcessPoolExecutor")
    def test_fit_pixels_cancels_futures_on_shutdown(
        self, mock_executor_cls, mock_json_mgr, imaging_config, mock_sammy_executable, tmp_path
    ):
        """When shutdown is requested, remaining futures are cancelled."""
        pixels = [
            PixelSpectrum(
                row=i,
                col=0,
                energy=np.linspace(1, 100, 50),
                transmission=np.random.uniform(0.5, 1.0, 50),
                uncertainty=np.full(50, 0.01),
            )
            for i in range(4)
        ]

        # Mock shared JSON staging
        mock_json_instance = MagicMock()

        def create_json_side_effect(isotopes, abundances, working_dir):
            working_dir.mkdir(parents=True, exist_ok=True)
            shared_json = working_dir / "config.json"
            shared_json.write_text("{}", encoding="utf-8")
            return shared_json

        mock_json_instance.create_json_config.side_effect = create_json_side_effect
        mock_json_mgr.return_value = mock_json_instance

        # Create futures - 2 completed, 2 pending (not set)
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        futures = []

        def submit_side_effect(
            fn, pixel, imaging_cfg, sammy_exe, resolution_file, shared_json, shared_endf, *args, **kwargs
        ):
            future = Future()
            if pixel.row < 2:
                # These two complete
                future.set_result(
                    PixelFitResult(
                        row=pixel.row,
                        col=pixel.col,
                        fit_results=None,
                        success=False,
                        error_message="test",
                        chi_squared=None,
                    )
                )
            # rows 2,3 stay pending (not set_result)
            futures.append(future)
            return future

        mock_executor.submit.side_effect = submit_side_effect

        checkpoint_file = tmp_path / "cancel_test.pkl"

        orchestrator = BatchFittingOrchestrator(
            imaging_config=imaging_config, sammy_executable=mock_sammy_executable, n_workers=2
        )

        # Mock GracefulShutdownHandler - shutdown after first pixel
        with patch("pleiades.imaging.orchestrator.GracefulShutdownHandler") as mock_shutdown_cls:
            mock_shutdown = MagicMock()
            mock_shutdown.__enter__ = MagicMock(return_value=mock_shutdown)
            mock_shutdown.__exit__ = MagicMock(return_value=False)
            # Shutdown requested immediately
            type(mock_shutdown).shutdown_requested = PropertyMock(return_value=True)
            mock_shutdown_cls.return_value = mock_shutdown

            results = orchestrator.fit_pixels(pixels, checkpoint_file=checkpoint_file, checkpoint_interval=1)

        # Pending futures (rows 2,3 which never had set_result) should be cancelled
        # Futures for rows 0,1 had set_result called → done, cancel() skipped
        cancelled_futures = [f for f in futures if f.cancelled()]
        assert len(cancelled_futures) == 2, f"Expected 2 cancelled futures (rows 2,3), got {len(cancelled_futures)}"

        # Checkpoint must be saved with partial results
        assert checkpoint_file.exists(), "Checkpoint must be saved when shutdown triggers partial completion"
