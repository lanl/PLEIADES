"""TRINIDI-style physics-based isotopic density recovery for 2D imaging.

Uses SAMMY in forward-model mode to generate per-isotope reference absorption
spectra, then solves a non-negative least squares (NNLS) problem at each pixel
to recover areal densities.  This avoids per-pixel nonlinear fitting and is
guaranteed to converge (convex optimisation).

The core insight: the transmission equation ``T(E) = exp(-sum_i n_i sigma_i(E))``
becomes linear in the log domain::

    -ln(T(E)) = sum_i n_i sigma_i(E)

which is solved via ``scipy.optimize.nnls``.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls

from pleiades.imaging.config import ImagingConfig
from pleiades.imaging.models import HyperspectralData, Imaging2DResults
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)


@dataclass
class ReferenceSpectrum:
    """Single isotope's reference absorption spectrum from SAMMY forward model.

    Attributes:
        isotope_name: Isotope identifier (e.g. ``"Ta-181"``).
        energy: Energy grid in eV, shape ``(n_energy,)``.
        transmission: Theoretical transmission ``T_i(E)``, shape ``(n_energy,)``.
        absorption: Absorption profile ``A_i(E) = -ln(T_i(E))``, shape ``(n_energy,)``.
    """

    isotope_name: str
    energy: np.ndarray
    transmission: np.ndarray
    absorption: np.ndarray


class PhysicsRecovery:
    """TRINIDI-style physics-based isotopic density recovery.

    Uses SAMMY forward-model to generate per-isotope reference absorption
    spectra, then solves NNLS at each pixel to recover areal densities.

    Args:
        imaging_config: Configuration with isotopes and material properties.
        sammy_executable: Path to the SAMMY binary.
        resolution_file: Optional path to instrument resolution function file.
    """

    TRANSMISSION_FLOOR = 1e-6
    TRANSMISSION_CEIL = 1.0 - 1e-6
    OPEN_BEAM_THRESHOLD = 1e-4

    def __init__(
        self,
        imaging_config: ImagingConfig,
        sammy_executable: Path,
        resolution_file: Path | None = None,
    ) -> None:
        self.imaging_config = imaging_config
        self.sammy_executable = sammy_executable
        self.resolution_file = resolution_file

    # ------------------------------------------------------------------
    # Reference spectrum generation
    # ------------------------------------------------------------------

    def generate_reference_spectra(
        self,
        energy: np.ndarray,
        working_dir: Path | None = None,
    ) -> list[ReferenceSpectrum]:
        """Generate reference absorption spectra via SAMMY forward model.

        Runs SAMMY once per isotope in forward-model mode
        (``DO NOT SOLVE BAYES EQUATIONS``) and extracts the theoretical
        transmission from the ``.LST`` output.

        Args:
            energy: Energy grid in eV.
            working_dir: Directory for SAMMY working files. If ``None``, a
                temporary directory is created.

        Returns:
            List of :class:`ReferenceSpectrum`, one per isotope in the config.

        Raises:
            RuntimeError: If SAMMY forward-model fails for any isotope.
        """
        spectra: list[ReferenceSpectrum] = []
        for isotope_name in self.imaging_config.isotopes:
            logger.info(f"Generating reference spectrum for {isotope_name}")
            ref = self._run_sammy_forward_model(isotope_name, energy, working_dir=working_dir)
            spectra.append(ref)
        return spectra

    def _run_sammy_forward_model(
        self,
        isotope_name: str,
        energy: np.ndarray,
        working_dir: Path | None = None,
    ) -> ReferenceSpectrum:
        """Run SAMMY in forward-model mode for a single isotope.

        Creates a synthetic flat-transmission pixel, configures SAMMY with
        ``DO NOT SOLVE BAYES EQUATIONS``, and extracts the theoretical
        transmission from the output.

        Args:
            isotope_name: Isotope name (e.g. ``"Ta-181"``).
            energy: Energy grid in eV.
            working_dir: Optional working directory.

        Returns:
            ReferenceSpectrum with energy, transmission, and absorption arrays.

        Raises:
            RuntimeError: If SAMMY execution fails.
        """
        from pleiades.sammy.alphanumerics import BayesSolutionOptions
        from pleiades.sammy.backends.local import LocalSammyConfig, LocalSammyRunner
        from pleiades.sammy.fitting.options import FitOptions
        from pleiades.sammy.interface import SammyFilesMultiMode
        from pleiades.sammy.io.data_manager import convert_csv_to_sammy_twenty
        from pleiades.sammy.io.inp_manager import InpManager
        from pleiades.sammy.io.json_manager import JsonManager
        from pleiades.sammy.results.manager import ResultsManager

        # Sanitize isotope name for use in filesystem paths
        safe_name = isotope_name.replace("/", "_").replace("\\", "_").replace(" ", "_")

        cleanup_dir = False
        if working_dir is None:
            tmp = tempfile.mkdtemp(prefix=f"recovery_{safe_name}_")
            working_dir = Path(tmp)
            cleanup_dir = True

        try:
            pixel_dir = working_dir / f"ref_{safe_name}"
            pixel_dir.mkdir(parents=True, exist_ok=True)

            # 1. Create synthetic flat-transmission pixel (open beam)
            transmission = np.ones_like(energy)
            uncertainty = 0.01 * np.ones_like(energy)
            csv_file = pixel_dir / "pixel.txt"
            df = pd.DataFrame({"energy": energy, "transmission": transmission, "uncertainty": uncertainty})
            df.to_csv(csv_file, sep="\t", index=False)

            twenty_file = pixel_dir / "pixel.twenty"
            convert_csv_to_sammy_twenty(csv_file, twenty_file)

            # 2. Create single-isotope config for this isotope
            single_config = ImagingConfig(
                isotopes=[isotope_name],
                element=self.imaging_config.element,
                mass_number=self.imaging_config.mass_number,
                density_g_cm3=self.imaging_config.density_g_cm3,
                thickness_mm=self.imaging_config.thickness_mm,
                atomic_mass_amu=self.imaging_config.atomic_mass_amu,
                min_energy_eV=float(energy.min()),
                max_energy_eV=float(energy.max()),
                temperature_K=self.imaging_config.temperature_K,
                natural_abundances=False,
                custom_abundances=[1.0],
                fit_abundances=False,
            )

            # 3. Create JSON config (downloads ENDF files)
            json_manager = JsonManager()
            json_path = json_manager.create_json_config(
                isotopes=[isotope_name],
                abundances=[1.0],
                working_dir=pixel_dir,
            )

            # 4. Create INP file with forward-model options
            inp_file = pixel_dir / "sammy.inp"
            fit_config = single_config.to_fit_config()
            dataset_metadata = single_config.to_dataset_metadata()

            # Override FitOptions to use forward-model mode
            fit_options = FitOptions.from_multi_isotope_config()
            fit_options.bayes_solution = BayesSolutionOptions(
                do_not_solve_bayes_equations=True,
            )

            InpManager.create_multi_isotope_inp(
                inp_file,
                fit_config=fit_config,
                title=f"Forward model: {isotope_name}",
                dataset_metadata=dataset_metadata,
                resolution_file_path=self.resolution_file,
                fit_options=fit_options,
            )

            # 5. Execute SAMMY
            files = SammyFilesMultiMode(
                input_file=inp_file,
                json_config_file=json_path,
                data_file=twenty_file,
                endf_directory=pixel_dir,
                fit_abundances=False,
            )

            config = LocalSammyConfig(
                sammy_executable=self.sammy_executable,
                working_dir=pixel_dir / "sammy_working",
                output_dir=pixel_dir / "sammy_output",
            )
            runner = LocalSammyRunner(config)
            runner.validate_config()
            runner.prepare_environment(files)
            result = runner.execute_sammy(files)

            if not result.success:
                raise RuntimeError(f"SAMMY forward-model failed for {isotope_name}: {result.error_message}")

            runner.collect_outputs(result)
            runner.cleanup()

            # 6. Parse results and extract theoretical transmission
            lpt_file = pixel_dir / "sammy_output" / "SAMMY.LPT"
            lst_file = pixel_dir / "sammy_output" / "SAMMY.LST"
            results_manager = ResultsManager(lpt_file_path=lpt_file, lst_file_path=lst_file)

            sammy_data = results_manager.run_results.data
            if sammy_data is None or sammy_data.data is None:
                raise RuntimeError(f"No SAMMY output data found for {isotope_name}")

            # In forward-model mode (DO NOT SOLVE BAYES EQUATIONS), the
            # "Final theoretical transmission" column is all zeros because
            # SAMMY did not solve.  The model prediction lives in the
            # "Zeroth-order theoretical transmission" column instead.
            zeroth_col = "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)"
            final_col = "Final theoretical transmission as evaluated by SAMMY (dimensionless)"

            if zeroth_col in sammy_data.data.columns:
                theo_series = sammy_data.data[zeroth_col]
            elif final_col in sammy_data.data.columns:
                theo_series = sammy_data.data[final_col]
            else:
                raise RuntimeError(
                    f"No theoretical transmission column found in SAMMY output for {isotope_name}. "
                    f"Available columns: {list(sammy_data.data.columns)}"
                )

            theo_trans = np.array(theo_series, dtype=np.float64)
            theo_energy = np.array(sammy_data.energy, dtype=np.float64)

            # Interpolate to requested energy grid if SAMMY energy differs.
            # Use constant edge extrapolation (not linear extrapolation) to
            # avoid producing values outside physical bounds.
            if len(theo_energy) != len(energy) or not np.allclose(theo_energy, energy, rtol=1e-6):
                from scipy.interpolate import interp1d

                interp_fn = interp1d(
                    theo_energy,
                    theo_trans,
                    kind="linear",
                    bounds_error=False,
                    fill_value=(theo_trans[0], theo_trans[-1]),
                )
                theo_trans = interp_fn(energy)

            # Clamp and compute absorption
            theo_trans = np.clip(theo_trans, self.TRANSMISSION_FLOOR, self.TRANSMISSION_CEIL)
            absorption = -np.log(theo_trans)

            return ReferenceSpectrum(
                isotope_name=isotope_name,
                energy=energy.copy(),
                transmission=theo_trans,
                absorption=absorption,
            )

        finally:
            if cleanup_dir:
                shutil.rmtree(working_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Per-pixel NNLS recovery
    # ------------------------------------------------------------------

    def recover_pixel(
        self,
        transmission: np.ndarray,
        uncertainty: np.ndarray,
        dictionary: np.ndarray,
    ) -> tuple[np.ndarray, float, bool]:
        """Recover isotopic scaling coefficients for a single pixel via NNLS.

        Solves ``min_c ||W @ y - W @ D @ c||^2  s.t.  c >= 0`` where:

        - ``y = -ln(T_obs)`` (observed absorption)
        - ``D`` is the dictionary matrix of reference absorption profiles
        - ``W = diag(1 / sigma_abs)`` are the weights
        - ``c`` are non-negative scaling coefficients

        Each column of ``D`` is a reference absorption profile
        ``A_ref(E) = -ln(T_ref(E))`` generated by SAMMY for a specific
        isotope at a specific areal density.  The recovered coefficients
        ``c_i`` are therefore **scale factors relative to the reference
        areal density**, not absolute areal densities.  For multi-isotope
        cases, ``recover_image`` normalises these to fractional abundances.

        Args:
            transmission: Observed transmission spectrum, shape ``(n_energy,)``.
            uncertainty: Transmission uncertainty, shape ``(n_energy,)``.
            dictionary: Reference absorption matrix, shape ``(n_energy, n_isotopes)``.
                Must be 2-D.

        Returns:
            Tuple of ``(coefficients, chi_squared, success)`` where:

            - ``coefficients``: Recovered scaling coefficients, shape ``(n_isotopes,)``.
            - ``chi_squared``: Chi-squared value of the fit.
            - ``success``: ``True`` if NNLS converged, ``False`` on solver failure.

        Raises:
            ValueError: If ``dictionary`` is not 2-D or its first axis does not
                match the length of ``transmission``.
        """
        if dictionary.ndim != 2:
            raise ValueError(f"dictionary must be 2-D (n_energy, n_isotopes), got {dictionary.ndim}-D")
        if dictionary.shape[0] != transmission.shape[0]:
            raise ValueError(
                f"dictionary rows ({dictionary.shape[0]}) must match transmission length ({transmission.shape[0]})"
            )
        n_isotopes = dictionary.shape[1]

        # Clamp transmission to avoid log(0) or log(negative)
        t_clamped = np.clip(transmission, self.TRANSMISSION_FLOOR, self.TRANSMISSION_CEIL)

        # Convert to absorption domain
        y = -np.log(t_clamped)

        # Compute absorption-domain uncertainty via error propagation: sigma_abs = sigma_T / T
        sigma_t = np.maximum(uncertainty, 1e-10)  # Clamp zero uncertainty
        sigma_abs = sigma_t / t_clamped
        sigma_abs = np.maximum(sigma_abs, 1e-10)  # Safety clamp

        # Build weight vector
        weights = 1.0 / sigma_abs

        # Weighted NNLS via element-wise multiplication (O(n) memory, O(n*k) time)
        # Equivalent to W @ y and W @ D where W = diag(weights), but without
        # allocating a dense (n_energy, n_energy) diagonal matrix.
        Wy = weights * y
        WD = weights[:, np.newaxis] * dictionary

        try:
            coefficients, rnorm = nnls(WD, Wy)
        except ValueError as exc:
            logger.debug(
                f"NNLS ValueError: {exc} (transmission shape={transmission.shape}, dictionary shape={dictionary.shape})"
            )
            return np.zeros(n_isotopes), float("nan"), False
        except Exception as exc:
            logger.warning(
                f"Unexpected NNLS failure: {exc} "
                f"(transmission shape={transmission.shape}, dictionary shape={dictionary.shape})"
            )
            return np.zeros(n_isotopes), float("nan"), False

        # Compute chi-squared from residuals using clamped data (consistent
        # with what NNLS actually fitted)
        predicted_absorption = dictionary @ coefficients
        predicted_transmission = np.exp(-predicted_absorption)
        chi_squared = self._compute_chi_squared(t_clamped, predicted_transmission, sigma_t)

        return coefficients, float(chi_squared), True

    # ------------------------------------------------------------------
    # Full image recovery
    # ------------------------------------------------------------------

    def recover_image(
        self,
        hyperspectral: HyperspectralData,
        reference_spectra: list[ReferenceSpectrum] | None = None,
        roi: tuple[int, int, int, int] | None = None,
        stride: int = 1,
        denoise_nmf: int = 0,
    ) -> Imaging2DResults:
        """Recover isotopic abundances for an entire image via NNLS.

        For each pixel, solves the NNLS problem using the provided (or
        generated) reference spectra.  Pixels with near-unity transmission
        (open beam) are skipped and left as NaN.

        Args:
            hyperspectral: Input hyperspectral data.
            reference_spectra: Pre-computed reference spectra.  If ``None``,
                :meth:`generate_reference_spectra` is called (requires SAMMY).
            roi: Region of interest as ``(x1, y1, x2, y2)``.  Only pixels
                within this box are processed; the rest remain NaN.  If
                ``None``, all pixels are processed.
            stride: Spatial stride for pixel iteration.  ``stride=4`` processes
                every 4th pixel in both directions.  Unprocessed positions
                remain NaN.  Default is 1 (every pixel).
            denoise_nmf: Number of NMF components for denoising preprocessing.
                When > 0, applies NMF low-rank denoising to the hyperspectral
                data before the per-pixel NNLS solve.  This exploits spatial
                redundancy across all pixels to filter spectral noise while
                preserving resonance structure.  Set to the number of expected
                isotopes (e.g. 2).  Default is 0 (no denoising).

        Returns:
            :class:`Imaging2DResults` with recovered abundance maps.

        Raises:
            ValueError: If no reference spectra are provided and no
                imaging_config is available, if energy grids mismatch,
                or if ``denoise_nmf`` is negative.
            RuntimeError: If reference spectrum generation fails.
        """
        if denoise_nmf < 0:
            raise ValueError(f"denoise_nmf must be >= 0, got {denoise_nmf}")
        if stride < 1:
            raise ValueError(f"stride must be >= 1, got {stride}")

        # Optional NMF denoising preprocessing
        if denoise_nmf > 0:
            from pleiades.imaging.nmf_recovery import NMFRecovery

            logger.info(f"Applying NMF denoising with {denoise_nmf} components before NNLS recovery")
            nmf = NMFRecovery(n_components=denoise_nmf)
            hyperspectral = nmf.denoise(hyperspectral)

        if reference_spectra is None:
            if not hasattr(self, "imaging_config"):
                raise ValueError(
                    "No reference_spectra provided and no imaging_config available for generating them via SAMMY."
                )
            reference_spectra = self.generate_reference_spectra(hyperspectral.energy)

        n_isotopes = len(reference_spectra)
        n_energy, height, width = hyperspectral.shape

        # Validate reference spectra energy grids match hyperspectral data
        for ref in reference_spectra:
            if len(ref.absorption) != n_energy:
                raise ValueError(
                    f"Reference spectrum '{ref.isotope_name}' has {len(ref.absorption)} energy bins "
                    f"but hyperspectral data has {n_energy}. Energy grids must match."
                )
            if not np.allclose(ref.energy, hyperspectral.energy, rtol=1e-6):
                raise ValueError(
                    f"Reference spectrum '{ref.isotope_name}' energy grid does not match "
                    f"hyperspectral energy grid. Values differ beyond rtol=1e-6."
                )

        # Determine pixel iteration bounds from ROI
        if roi is not None:
            x1, y1, x2, y2 = roi
            # Allow x1 == x2 or y1 == y2 (empty ROI from edge-crop remapping
            # when bin_size > 1) but reject reversed or out-of-bounds coordinates.
            if not (0 <= x1 <= x2 <= width and 0 <= y1 <= y2 <= height):
                raise ValueError(
                    f"Invalid ROI {roi} for image shape (height={height}, width={width}). "
                    f"Must satisfy 0 <= x1 <= x2 <= width and 0 <= y1 <= y2 <= height."
                )
        else:
            x1, y1, x2, y2 = 0, 0, width, height

        # Build dictionary matrix (n_energy, n_isotopes)
        dictionary = np.column_stack([ref.absorption for ref in reference_spectra])

        # Allocate output arrays
        density_maps = np.full((n_isotopes, height, width), np.nan, dtype=np.float64)
        chi_squared_map = np.full((height, width), np.nan, dtype=np.float64)
        success_mask = np.zeros((height, width), dtype=bool)

        isotope_names = [ref.isotope_name for ref in reference_spectra]

        n_pixels = height * width
        logger.info(
            f"Starting physics recovery: {height}x{width} pixels ({n_pixels} total), "
            f"{n_isotopes} isotopes, {n_energy} energy bins"
            + (f", stride={stride}" if stride > 1 else "")
            + (f", roi=({x1},{y1},{x2},{y2})" if roi is not None else "")
        )

        completed = 0
        for row in range(y1, y2, stride):
            for col in range(x1, x2, stride):
                transmission = hyperspectral.data[:, row, col]

                if hyperspectral.uncertainty is not None:
                    uncertainty = hyperspectral.uncertainty[:, row, col]
                else:
                    uncertainty = 0.01 * np.abs(transmission)
                    uncertainty = np.maximum(uncertainty, 1e-10)

                # Skip pixels with non-finite transmission or uncertainty
                if not np.all(np.isfinite(transmission)) or not np.all(np.isfinite(uncertainty)):
                    completed += 1
                    continue

                # Skip open-beam pixels (T~1 everywhere → no absorption signal)
                max_absorption = np.max(-np.log(np.clip(transmission, self.TRANSMISSION_FLOOR, 1.0)))
                if max_absorption < self.OPEN_BEAM_THRESHOLD:
                    # Leave as NaN + success_mask=False
                    completed += 1
                    continue

                coeffs, chi2, success = self.recover_pixel(transmission, uncertainty, dictionary)

                if success:
                    density_maps[:, row, col] = coeffs
                    chi_squared_map[row, col] = chi2
                    success_mask[row, col] = True

                completed += 1

            # Log progress per row
            if (row - y1 + 1) % max(1, (y2 - y1) // 10) == 0:
                logger.debug(f"Physics recovery progress: row {row + 1}/{y2} ({completed} pixels processed)")

        logger.info(
            f"Physics recovery complete: {np.sum(success_mask)} succeeded, {np.sum(~success_mask)} failed/skipped"
        )

        # Normalize coefficients to abundance fractions
        abundance_maps = self._coefficients_to_abundances(density_maps, success_mask)

        return Imaging2DResults(
            abundance_maps=abundance_maps,
            isotope_names=isotope_names,
            chi_squared_map=chi_squared_map,
            success_mask=success_mask,
            source_hyperspectral=hyperspectral,
            metadata={
                "method": "hybrid_nmf_nnls" if denoise_nmf > 0 else "physics_recovery",
                "n_isotopes": n_isotopes,
                **({"denoise_nmf": denoise_nmf} if denoise_nmf > 0 else {}),
            },
        )

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coefficients_to_abundances(
        density_maps: np.ndarray,
        success_mask: np.ndarray,
    ) -> np.ndarray:
        """Normalise NNLS density coefficients to fractional abundances.

        For single-isotope cases, the NNLS coefficient is a relative areal
        density (not an abundance fraction).  It is passed through unchanged
        because there is nothing to normalise against — the coefficient
        carries absolute information about sample thickness.

        For multi-isotope cases, per-pixel coefficients are normalised to
        sum to 1.0 (preserving ratios), giving fractional abundances.
        Pixels where all coefficients are zero receive NaN.

        Args:
            density_maps: Array of shape ``(n_isotopes, height, width)``.
            success_mask: Boolean mask of shape ``(height, width)``.

        Returns:
            Abundance maps with the same shape as ``density_maps``.
        """
        n_isotopes = density_maps.shape[0]
        if n_isotopes == 1:
            return density_maps.copy()

        abundance_maps = density_maps.copy()
        coeff_sum = np.nansum(abundance_maps, axis=0)  # (height, width)

        # Normalise where sum > 0
        nonzero = (coeff_sum > 0) & success_mask
        for i in range(n_isotopes):
            abundance_maps[i, nonzero] /= coeff_sum[nonzero]

        # Where sum == 0 (open beam or failed), set to NaN
        zero_sum = (coeff_sum == 0) | ~success_mask
        for i in range(n_isotopes):
            abundance_maps[i, zero_sum] = np.nan

        return abundance_maps

    @staticmethod
    def _compute_chi_squared(
        observed: np.ndarray,
        predicted: np.ndarray,
        uncertainty: np.ndarray,
    ) -> float:
        """Compute chi-squared between observed and predicted values.

        ``chi2 = sum((observed - predicted)^2 / uncertainty^2)``

        Args:
            observed: Observed values.
            predicted: Model-predicted values.
            uncertainty: Measurement uncertainties.

        Returns:
            Chi-squared value (non-negative float).
        """
        sigma = np.maximum(uncertainty, 1e-10)
        residuals = (observed - predicted) / sigma
        return float(np.sum(residuals**2))
