"""Unit tests for pleiades.imaging.api.analyze_imaging.

These tests verify the orchestration/wiring logic of the high-level
``analyze_imaging()`` function. All heavy components (SAMMY execution,
file I/O, data loading) are mocked so tests run without SAMMY installed.

Tests are written BEFORE implementation (TDD). They exercise:
  - Correct pipeline ordering: load → iter_pixels → orchestrator → aggregator → save
  - Correct parameter forwarding to each component
  - TempFileManager lifecycle management
  - Input validation with clear error messages
  - Checkpoint/resume parameter handling
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pleiades.imaging.config import ImagingConfig
from pleiades.imaging.models import (
    HyperspectralData,
    Imaging2DResults,
    PixelFitResult,
    PixelSpectrum,
)
from pleiades.imaging.temp_manager import TempFileManager

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_imaging_config():
    """Create a minimal ImagingConfig for testing."""
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
def mock_sammy_executable(tmp_path):
    """Create a mock SAMMY executable file on disk."""
    exe = tmp_path / "sammy"
    exe.touch()
    exe.chmod(0o755)
    return exe


@pytest.fixture
def mock_source_path(tmp_path):
    """Create a mock source TIFF file on disk."""
    src = tmp_path / "data.tif"
    src.touch()
    return src


@pytest.fixture
def sample_energy():
    """Return a small energy array for testing."""
    return np.linspace(1.0, 100.0, 10)


@pytest.fixture
def sample_pixels():
    """Return a small list of PixelSpectrum objects (2x3 image)."""
    pixels = []
    energy = np.linspace(1.0, 100.0, 10)
    for row in range(2):
        for col in range(3):
            pixels.append(
                PixelSpectrum(
                    row=row,
                    col=col,
                    energy=energy,
                    transmission=np.random.uniform(0.3, 0.9, 10),
                    uncertainty=np.full(10, 0.01),
                )
            )
    return pixels


@pytest.fixture
def sample_pixel_results():
    """Return PixelFitResult objects for a 2x3 image (all failures for simplicity)."""
    results = []
    for row in range(2):
        for col in range(3):
            results.append(
                PixelFitResult(
                    row=row,
                    col=col,
                    fit_results=None,
                    success=False,
                    error_message="mock failure",
                    chi_squared=None,
                )
            )
    return results


@pytest.fixture
def mock_hyperspectral_data(tmp_path):
    """Create a mock HyperspectralData object for a 2x3 image with 10 energy bins."""
    data = np.random.uniform(0.3, 0.9, (10, 2, 3)).astype(np.float32)
    energy = np.linspace(1.0, 100.0, 10)
    uncertainty = np.full_like(data, 0.01)
    return HyperspectralData(
        data=data,
        energy=energy,
        uncertainty=uncertainty,
        source_file=tmp_path / "data.tif",
    )


@pytest.fixture
def mock_imaging_2d_results(mock_hyperspectral_data):
    """Create a mock Imaging2DResults object for a 2x3 image."""
    return Imaging2DResults(
        abundance_maps=np.zeros((1, 2, 3)),
        isotope_names=["Ta-181"],
        chi_squared_map=np.zeros((2, 3)),
        success_mask=np.zeros((2, 3), dtype=bool),
        source_hyperspectral=mock_hyperspectral_data,
        pixel_results=[],
        metadata={},
    )


def _build_patches():
    """Return a dict of patch targets for the three core components.

    All patches target the import location in ``pleiades.imaging.api``.
    """
    return {
        "loader": "pleiades.imaging.api.HyperspectralLoader",
        "orchestrator": "pleiades.imaging.api.BatchFittingOrchestrator",
        "aggregator": "pleiades.imaging.api.ResultsAggregator",
    }


# ---------------------------------------------------------------------------
# TestAnalyzeImagingBasic
# ---------------------------------------------------------------------------


class TestAnalyzeImagingBasic:
    """Happy-path tests: verify the pipeline is wired together correctly."""

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_basic_pipeline_wiring(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify that analyze_imaging calls components in the correct order."""
        from pleiades.imaging.api import analyze_imaging

        # Configure mock loader
        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        # Configure mock orchestrator
        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        # Configure mock aggregator
        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        # Call the function
        result = analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        # Verify loader was constructed and called
        MockLoader.assert_called_once()
        loader_instance.load.assert_called_once()

        # Verify orchestrator was constructed and called
        MockOrchestrator.assert_called_once()
        orch_instance.fit_pixels.assert_called_once()

        # fit_pixels receives a callable (pixel factory); invoking it calls iter_pixels
        pixel_factory = orch_instance.fit_pixels.call_args[0][0]
        assert callable(pixel_factory)
        list(pixel_factory())  # invoke to trigger iter_pixels
        loader_instance.iter_pixels.assert_called()

        # Verify aggregator was constructed and called
        MockAggregator.assert_called_once()
        agg_instance.aggregate.assert_called_once()

        # Verify the returned result
        assert result is mock_imaging_2d_results

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_returns_imaging_2d_results(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify return type is the Imaging2DResults from aggregator."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        result = analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        assert isinstance(result, Imaging2DResults)
        assert result is mock_imaging_2d_results

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_loader_receives_source_and_energy(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        sample_energy,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify loader is constructed with source and energy."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            energy=sample_energy,
        )

        # Verify loader constructor received source and energy
        call_kwargs = MockLoader.call_args
        # The source should be a Path (converted from str if needed)
        assert call_kwargs[0][0] == mock_source_path or call_kwargs[1].get("source") == mock_source_path
        # Energy should be passed
        if len(call_kwargs[0]) > 1:
            np.testing.assert_array_equal(call_kwargs[0][1], sample_energy)
        else:
            np.testing.assert_array_equal(call_kwargs[1]["energy"], sample_energy)

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_source_as_string_accepted(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify that source can be a string path (not just Path object)."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        # Pass source as str instead of Path
        result = analyze_imaging(
            source=str(mock_source_path),
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        # Should succeed without error
        assert result is mock_imaging_2d_results


# ---------------------------------------------------------------------------
# TestAnalyzeImagingParameterPassing
# ---------------------------------------------------------------------------


class TestAnalyzeImagingParameterPassing:
    """Verify all parameters are forwarded correctly to sub-components."""

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_n_workers_passed_to_orchestrator(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify n_workers is forwarded to BatchFittingOrchestrator."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            n_workers=8,
        )

        # Check the orchestrator was constructed with n_workers=8
        orch_call_kwargs = MockOrchestrator.call_args
        assert orch_call_kwargs[1].get("n_workers") == 8 or (
            len(orch_call_kwargs[0]) > 2 and orch_call_kwargs[0][2] == 8
        )

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_checkpoint_params_passed_to_fit_pixels(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
        tmp_path,
    ):
        """Verify checkpoint_file and checkpoint_interval are forwarded to fit_pixels."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        ckpt = tmp_path / "checkpoint.pkl"

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            checkpoint_file=ckpt,
            checkpoint_interval=25,
        )

        fit_call_kwargs = orch_instance.fit_pixels.call_args
        assert fit_call_kwargs[1].get("checkpoint_file") == ckpt or fit_call_kwargs[0][1] == ckpt
        # Check checkpoint_interval
        if "checkpoint_interval" in fit_call_kwargs[1]:
            assert fit_call_kwargs[1]["checkpoint_interval"] == 25
        else:
            assert fit_call_kwargs[0][2] == 25

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_timeout_and_retries_passed_to_fit_pixels(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify timeout_per_job and max_retries are forwarded to fit_pixels."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            timeout_per_job=30.0,
            max_retries=3,
        )

        fit_call_kwargs = orch_instance.fit_pixels.call_args[1]
        assert fit_call_kwargs["timeout_per_job"] == 30.0
        assert fit_call_kwargs["max_retries"] == 3

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_imaging_config_passed_to_orchestrator(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify imaging_config is forwarded to orchestrator constructor."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        orch_call = MockOrchestrator.call_args
        # imaging_config should be the first positional or a keyword arg
        if orch_call[0]:
            assert orch_call[0][0] is mock_imaging_config
        else:
            assert orch_call[1]["imaging_config"] is mock_imaging_config

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_sammy_executable_passed_to_orchestrator(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify sammy_executable is forwarded to orchestrator constructor."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        orch_call = MockOrchestrator.call_args
        # sammy_executable should be the second positional or a keyword arg
        if len(orch_call[0]) > 1:
            assert orch_call[0][1] == mock_sammy_executable
        else:
            assert orch_call[1]["sammy_executable"] == mock_sammy_executable

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_aggregator_receives_isotopes_height_width(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify aggregator is constructed with isotope_names, height, width from loaded data."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        # The hyperspectral data is 10x2x3, so height=2, width=3
        agg_call = MockAggregator.call_args
        # Check isotope_names from config
        if agg_call[0]:
            assert agg_call[0][0] == mock_imaging_config.isotopes
            assert agg_call[0][1] == 2  # height
            assert agg_call[0][2] == 3  # width
        else:
            assert agg_call[1]["isotope_names"] == mock_imaging_config.isotopes
            assert agg_call[1]["height"] == 2
            assert agg_call[1]["width"] == 3

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_aggregator_receives_pixel_results_and_hyperspectral(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify aggregator.aggregate receives pixel_results and hyperspectral data."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        agg_call = agg_instance.aggregate.call_args
        # First arg should be pixel_results from orchestrator
        assert agg_call[0][0] is sample_pixel_results
        # Second arg should be the hyperspectral data from loader
        assert agg_call[0][1] is mock_hyperspectral_data

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_default_n_workers_is_four(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify default n_workers=4 is used when not specified."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        orch_call = MockOrchestrator.call_args
        if "n_workers" in orch_call[1]:
            assert orch_call[1]["n_workers"] == 4
        elif len(orch_call[0]) > 2:
            assert orch_call[0][2] == 4

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_resolution_file_passed_to_orchestrator(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
        tmp_path,
    ):
        """Verify resolution_file is forwarded to BatchFittingOrchestrator."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        res_file = tmp_path / "resolution.dat"
        res_file.touch()

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            resolution_file=res_file,
        )

        orch_call_kwargs = MockOrchestrator.call_args[1]
        assert orch_call_kwargs["resolution_file"] == res_file


# ---------------------------------------------------------------------------
# TestAnalyzeImagingROI
# ---------------------------------------------------------------------------


class TestAnalyzeImagingROI:
    """Verify ROI parameter is forwarded to iter_pixels."""

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_roi_passed_to_iter_pixels(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify roi is forwarded to loader.iter_pixels()."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        roi = (0, 0, 2, 1)
        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            roi=roi,
        )

        # Invoke the factory to trigger iter_pixels
        pixel_factory = orch_instance.fit_pixels.call_args[0][0]
        list(pixel_factory())

        iter_call = loader_instance.iter_pixels.call_args
        assert iter_call[1].get("roi") == roi or (iter_call[0] and iter_call[0][0] == roi)

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_roi_none_passed_by_default(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify roi=None is the default when not specified."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        # Invoke the factory to trigger iter_pixels
        pixel_factory = orch_instance.fit_pixels.call_args[0][0]
        list(pixel_factory())

        iter_call = loader_instance.iter_pixels.call_args
        # roi should be None (default)
        if iter_call[1]:
            assert iter_call[1].get("roi") is None
        elif iter_call[0]:
            assert iter_call[0][0] is None
        # If no args at all, that also means default None was used

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_pixels_from_iter_pixels_passed_to_fit_pixels(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify pixels extracted via iter_pixels are passed to fit_pixels."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        # fit_pixels receives a callable (pixel factory)
        fit_call = orch_instance.fit_pixels.call_args
        pixel_factory = fit_call[0][0] if fit_call[0] else fit_call[1]["pixels"]
        assert callable(pixel_factory)
        # Invoke factory to get pixels and verify content
        pixels_list = list(pixel_factory())
        assert len(pixels_list) == len(sample_pixels)
        for actual, expected in zip(pixels_list, sample_pixels):
            assert actual.row == expected.row
            assert actual.col == expected.col


# ---------------------------------------------------------------------------
# TestAnalyzeImagingSavePath
# ---------------------------------------------------------------------------


class TestAnalyzeImagingSavePath:
    """Verify save_hdf5 behavior based on save_path parameter."""

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_save_hdf5_called_when_save_path_provided(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        tmp_path,
    ):
        """Verify save_hdf5 is called when save_path is given."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        # Use a MagicMock for the results so we can verify save_hdf5
        mock_results = MagicMock(spec=Imaging2DResults)
        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_results

        save_path = tmp_path / "output.h5"
        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            save_path=save_path,
        )

        mock_results.save_hdf5.assert_called_once_with(save_path)

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_save_hdf5_not_called_when_save_path_none(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
    ):
        """Verify save_hdf5 is NOT called when save_path is None."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        mock_results = MagicMock(spec=Imaging2DResults)
        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            # save_path not provided (default None)
        )

        mock_results.save_hdf5.assert_not_called()

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_results_returned_even_when_save_path_provided(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        tmp_path,
    ):
        """Verify results are returned regardless of save_path."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        mock_results = MagicMock(spec=Imaging2DResults)
        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_results

        save_path = tmp_path / "output.h5"
        result = analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            save_path=save_path,
        )

        assert result is mock_results


# ---------------------------------------------------------------------------
# TestAnalyzeImagingTempManager
# ---------------------------------------------------------------------------


class TestAnalyzeImagingTempManager:
    """Verify TempFileManager lifecycle and parameter passing."""

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_temp_manager_passed_to_orchestrator(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
        tmp_path,
    ):
        """Verify user-provided temp_manager is forwarded to orchestrator."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        temp_mgr = MagicMock(spec=TempFileManager)
        temp_mgr.__enter__ = MagicMock(return_value=temp_mgr)
        temp_mgr.__exit__ = MagicMock(return_value=False)

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            temp_manager=temp_mgr,
        )

        orch_call = MockOrchestrator.call_args
        assert orch_call[1].get("temp_manager") is temp_mgr

    @patch("pleiades.imaging.api.TempFileManager")
    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_default_temp_manager_created_when_none(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        MockTempMgr,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify a default TempFileManager is created when temp_manager=None."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        # Configure TempFileManager mock as context manager
        default_mgr = MagicMock(spec=TempFileManager)
        default_mgr.__enter__ = MagicMock(return_value=default_mgr)
        default_mgr.__exit__ = MagicMock(return_value=False)
        MockTempMgr.return_value = default_mgr

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            temp_manager=None,
        )

        # A TempFileManager should have been created
        MockTempMgr.assert_called_once()
        # And it should have been passed to the orchestrator
        orch_call = MockOrchestrator.call_args
        assert orch_call[1].get("temp_manager") is default_mgr

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_user_temp_manager_not_entered_by_analyze_imaging(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """When user provides a temp_manager, analyze_imaging should NOT enter its context.

        The orchestrator's fit_pixels handles the context management internally.
        analyze_imaging should pass it through without entering/exiting.
        """
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        temp_mgr = MagicMock(spec=TempFileManager)
        temp_mgr.__enter__ = MagicMock(return_value=temp_mgr)
        temp_mgr.__exit__ = MagicMock(return_value=False)

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            temp_manager=temp_mgr,
        )

        # The user-provided temp_manager should NOT have __enter__/__exit__ called
        # by analyze_imaging (the orchestrator handles that internally in fit_pixels).
        temp_mgr.__enter__.assert_not_called()
        temp_mgr.__exit__.assert_not_called()


# ---------------------------------------------------------------------------
# TestAnalyzeImagingInputValidation
# ---------------------------------------------------------------------------


class TestAnalyzeImagingInputValidation:
    """Verify input validation raises ValueError for invalid inputs."""

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_n_workers_zero_raises_value_error(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
    ):
        """n_workers=0 should raise ValueError."""
        from pleiades.imaging.api import analyze_imaging

        with pytest.raises(ValueError, match="n_workers"):
            analyze_imaging(
                source=mock_source_path,
                imaging_config=mock_imaging_config,
                sammy_executable=mock_sammy_executable,
                n_workers=0,
            )

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_n_workers_negative_raises_value_error(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
    ):
        """n_workers=-1 should raise ValueError."""
        from pleiades.imaging.api import analyze_imaging

        with pytest.raises(ValueError, match="n_workers"):
            analyze_imaging(
                source=mock_source_path,
                imaging_config=mock_imaging_config,
                sammy_executable=mock_sammy_executable,
                n_workers=-1,
            )

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_checkpoint_interval_zero_raises_value_error(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
    ):
        """checkpoint_interval=0 should raise ValueError."""
        from pleiades.imaging.api import analyze_imaging

        with pytest.raises(ValueError, match="checkpoint_interval"):
            analyze_imaging(
                source=mock_source_path,
                imaging_config=mock_imaging_config,
                sammy_executable=mock_sammy_executable,
                checkpoint_interval=0,
            )

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_checkpoint_interval_negative_raises_value_error(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
    ):
        """checkpoint_interval=-5 should raise ValueError."""
        from pleiades.imaging.api import analyze_imaging

        with pytest.raises(ValueError, match="checkpoint_interval"):
            analyze_imaging(
                source=mock_source_path,
                imaging_config=mock_imaging_config,
                sammy_executable=mock_sammy_executable,
                checkpoint_interval=-5,
            )

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_max_retries_negative_raises_value_error(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
    ):
        """max_retries=-1 should raise ValueError."""
        from pleiades.imaging.api import analyze_imaging

        with pytest.raises(ValueError, match="max_retries"):
            analyze_imaging(
                source=mock_source_path,
                imaging_config=mock_imaging_config,
                sammy_executable=mock_sammy_executable,
                max_retries=-1,
            )

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_roi_wrong_length_raises_value_error(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
    ):
        """roi with != 4 elements should raise ValueError."""
        from pleiades.imaging.api import analyze_imaging

        with pytest.raises(ValueError, match="roi"):
            analyze_imaging(
                source=mock_source_path,
                imaging_config=mock_imaging_config,
                sammy_executable=mock_sammy_executable,
                roi=(0, 0, 10),  # 3 elements instead of 4
            )

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_roi_five_elements_raises_value_error(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
    ):
        """roi with 5 elements should raise ValueError."""
        from pleiades.imaging.api import analyze_imaging

        with pytest.raises(ValueError, match="roi"):
            analyze_imaging(
                source=mock_source_path,
                imaging_config=mock_imaging_config,
                sammy_executable=mock_sammy_executable,
                roi=(0, 0, 10, 10, 5),
            )

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_resume_without_checkpoint_file_raises_value_error(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
    ):
        """resume=True without checkpoint_file should raise ValueError."""
        from pleiades.imaging.api import analyze_imaging

        with pytest.raises(ValueError, match="checkpoint_file|resume"):
            analyze_imaging(
                source=mock_source_path,
                imaging_config=mock_imaging_config,
                sammy_executable=mock_sammy_executable,
                resume=True,
                checkpoint_file=None,
            )

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_max_retries_zero_is_valid(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """max_retries=0 should be valid (no retries)."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        # Should NOT raise
        result = analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            max_retries=0,
        )
        assert result is mock_imaging_2d_results

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_n_workers_one_is_valid(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """n_workers=1 should be valid (single worker)."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        # Should NOT raise
        result = analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            n_workers=1,
        )
        assert result is mock_imaging_2d_results

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_checkpoint_interval_one_is_valid(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """checkpoint_interval=1 should be valid (checkpoint every pixel)."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        # Should NOT raise
        result = analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            checkpoint_interval=1,
        )
        assert result is mock_imaging_2d_results


# ---------------------------------------------------------------------------
# TestAnalyzeImagingCheckpointResume
# ---------------------------------------------------------------------------


class TestAnalyzeImagingCheckpointResume:
    """Verify checkpoint and resume parameter handling."""

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_resume_true_with_checkpoint_file_passed_to_fit_pixels(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
        tmp_path,
    ):
        """Verify resume=True and checkpoint_file are forwarded to fit_pixels."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        ckpt = tmp_path / "checkpoint.pkl"

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            checkpoint_file=ckpt,
            resume=True,
        )

        fit_call_kwargs = orch_instance.fit_pixels.call_args[1]
        assert fit_call_kwargs["checkpoint_file"] == ckpt
        assert fit_call_kwargs["resume"] is True

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_resume_false_is_default(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify resume=False is default when not specified."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        fit_call_kwargs = orch_instance.fit_pixels.call_args[1]
        assert fit_call_kwargs.get("resume") is False or fit_call_kwargs.get("resume") is None

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_checkpoint_file_none_by_default(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify checkpoint_file=None is default when not specified."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        fit_call_kwargs = orch_instance.fit_pixels.call_args[1]
        assert fit_call_kwargs.get("checkpoint_file") is None

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_checkpoint_file_without_resume_passed_correctly(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
        tmp_path,
    ):
        """Verify checkpoint_file is forwarded even without resume=True.

        This enables saving new checkpoints without resuming from an existing one.
        """
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        ckpt = tmp_path / "checkpoint.pkl"

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            checkpoint_file=ckpt,
            resume=False,
        )

        fit_call_kwargs = orch_instance.fit_pixels.call_args[1]
        assert fit_call_kwargs["checkpoint_file"] == ckpt
        assert fit_call_kwargs["resume"] is False


# ---------------------------------------------------------------------------
# TestAnalyzeImagingPipelineOrder
# ---------------------------------------------------------------------------


class TestAnalyzeImagingPipelineOrder:
    """Verify that pipeline steps execute in the correct order."""

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_load_before_iter_pixels(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify load() is called before iter_pixels()."""
        from pleiades.imaging.api import analyze_imaging

        call_order = []

        loader_instance = MockLoader.return_value
        loader_instance.load.side_effect = lambda: (call_order.append("load"), mock_hyperspectral_data)[1]
        loader_instance.iter_pixels.side_effect = lambda **kwargs: (
            call_order.append("iter_pixels"),
            iter(sample_pixels),
        )[1]

        orch_instance = MockOrchestrator.return_value

        def fit_pixels_side_effect(pixel_factory, **kwargs):
            list(pixel_factory())  # invoke factory to trigger iter_pixels
            return sample_pixel_results

        orch_instance.fit_pixels.side_effect = fit_pixels_side_effect

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        assert call_order.index("load") < call_order.index("iter_pixels")

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_fit_pixels_before_aggregate(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify fit_pixels() is called before aggregate()."""
        from pleiades.imaging.api import analyze_imaging

        call_order = []

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.side_effect = lambda *a, **kw: (call_order.append("fit_pixels"), sample_pixel_results)[
            1
        ]

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.side_effect = lambda *a, **kw: (call_order.append("aggregate"), mock_imaging_2d_results)[
            1
        ]

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        assert call_order.index("fit_pixels") < call_order.index("aggregate")

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_full_pipeline_order(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        tmp_path,
    ):
        """Verify complete pipeline order: load → iter_pixels → fit_pixels → aggregate → save."""
        from pleiades.imaging.api import analyze_imaging

        call_order = []

        loader_instance = MockLoader.return_value
        loader_instance.load.side_effect = lambda: (call_order.append("load"), mock_hyperspectral_data)[1]
        loader_instance.iter_pixels.side_effect = lambda **kwargs: (
            call_order.append("iter_pixels"),
            iter(sample_pixels),
        )[1]

        orch_instance = MockOrchestrator.return_value

        def fit_pixels_side_effect(pixel_factory, **kwargs):
            list(pixel_factory())  # invoke factory → appends "iter_pixels"
            call_order.append("fit_pixels")
            return sample_pixel_results

        orch_instance.fit_pixels.side_effect = fit_pixels_side_effect

        mock_results = MagicMock(spec=Imaging2DResults)
        mock_results.save_hdf5.side_effect = lambda p: call_order.append("save_hdf5")

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.side_effect = lambda *a, **kw: (call_order.append("aggregate"), mock_results)[1]

        save_path = tmp_path / "output.h5"
        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            save_path=save_path,
        )

        assert call_order == ["load", "iter_pixels", "fit_pixels", "aggregate", "save_hdf5"]


# ---------------------------------------------------------------------------
# TestAnalyzeImagingEdgeCases
# ---------------------------------------------------------------------------


class TestAnalyzeImagingEdgeCases:
    """Edge cases and additional scenarios."""

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_energy_none_default(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify energy=None is passed to loader by default."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        loader_call = MockLoader.call_args
        # energy should be None by default
        if "energy" in loader_call[1]:
            assert loader_call[1]["energy"] is None
        elif len(loader_call[0]) > 1:
            assert loader_call[0][1] is None

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_roi_four_elements_valid(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify roi with exactly 4 elements passes validation."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        # Should NOT raise
        result = analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            roi=(0, 0, 3, 2),
        )
        assert result is mock_imaging_2d_results

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_timeout_per_job_none_by_default(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
    ):
        """Verify timeout_per_job=None is the default."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value
        orch_instance.fit_pixels.return_value = sample_pixel_results

        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_imaging_2d_results

        analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
        )

        fit_call_kwargs = orch_instance.fit_pixels.call_args[1]
        assert fit_call_kwargs.get("timeout_per_job") is None

    @patch("pleiades.imaging.api.ResultsAggregator")
    @patch("pleiades.imaging.api.BatchFittingOrchestrator")
    @patch("pleiades.imaging.api.HyperspectralLoader")
    def test_all_parameters_forwarded_together(
        self,
        MockLoader,
        MockOrchestrator,
        MockAggregator,
        mock_imaging_config,
        mock_sammy_executable,
        mock_source_path,
        sample_pixels,
        sample_pixel_results,
        sample_energy,
        mock_hyperspectral_data,
        mock_imaging_2d_results,
        tmp_path,
    ):
        """Integration test: verify all parameters are forwarded when all are specified."""
        from pleiades.imaging.api import analyze_imaging

        loader_instance = MockLoader.return_value
        loader_instance.load.return_value = mock_hyperspectral_data
        loader_instance.iter_pixels.return_value = iter(sample_pixels)

        orch_instance = MockOrchestrator.return_value

        def fit_pixels_side_effect(pixel_factory, **kwargs):
            list(pixel_factory())  # invoke factory to trigger iter_pixels
            return sample_pixel_results

        orch_instance.fit_pixels.side_effect = fit_pixels_side_effect

        mock_results = MagicMock(spec=Imaging2DResults)
        agg_instance = MockAggregator.return_value
        agg_instance.aggregate.return_value = mock_results

        temp_mgr = MagicMock(spec=TempFileManager)
        temp_mgr.__enter__ = MagicMock(return_value=temp_mgr)
        temp_mgr.__exit__ = MagicMock(return_value=False)

        ckpt = tmp_path / "checkpoint.pkl"
        save_path = tmp_path / "output.h5"
        roi = (1, 0, 3, 2)

        result = analyze_imaging(
            source=mock_source_path,
            imaging_config=mock_imaging_config,
            sammy_executable=mock_sammy_executable,
            energy=sample_energy,
            n_workers=16,
            roi=roi,
            checkpoint_file=ckpt,
            checkpoint_interval=50,
            resume=True,
            timeout_per_job=60.0,
            max_retries=2,
            temp_manager=temp_mgr,
            save_path=save_path,
        )

        # Verify loader
        loader_call = MockLoader.call_args
        if "energy" in loader_call[1]:
            np.testing.assert_array_equal(loader_call[1]["energy"], sample_energy)

        # Verify orchestrator constructor
        orch_call = MockOrchestrator.call_args[1]
        assert orch_call["n_workers"] == 16
        assert orch_call["temp_manager"] is temp_mgr

        # Verify fit_pixels call
        fit_call = orch_instance.fit_pixels.call_args[1]
        assert fit_call["checkpoint_file"] == ckpt
        assert fit_call["checkpoint_interval"] == 50
        assert fit_call["resume"] is True
        assert fit_call["timeout_per_job"] == 60.0
        assert fit_call["max_retries"] == 2

        # Verify ROI was passed to iter_pixels
        iter_call = loader_instance.iter_pixels.call_args
        assert iter_call[1].get("roi") == roi or (iter_call[0] and iter_call[0][0] == roi)

        # Verify save was called
        mock_results.save_hdf5.assert_called_once_with(save_path)

        # Verify return
        assert result is mock_results
