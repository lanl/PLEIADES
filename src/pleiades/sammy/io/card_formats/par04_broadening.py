#!/usr/bin/env python
from typing import List

from pydantic import BaseModel

from pleiades.experimental.models import BroadeningParameters
from pleiades.sammy.fitting.config import FitConfig
from pleiades.utils.helper import VaryFlag
from pleiades.utils.logger import loguru_logger

logger = loguru_logger.bind(name=__name__)

LINE_TWO_FORMAT = {
    "crfn": slice(0, 10),  # Matching radius (F)
    "temp": slice(10, 20),  # Effective temperature (K)
    "thick": slice(20, 30),  # Sample thickness (atoms/barn)
    "deltal": slice(30, 40),  # Spread in flight-path length (m)
    "deltag": slice(40, 50),  # Gaussian resolution width (μs)
    "deltae": slice(50, 60),  # e-folding width of exponential resolution (μs)
    "flag_crfn": slice(60, 62),  # Flag for CRFN
    "flag_temp": slice(62, 64),  # Flag for TEMP
    "flag_thick": slice(64, 66),  # Flag for THICK
    "flag_deltal": slice(66, 68),  # Flag for DELTAL
    "flag_deltag": slice(68, 70),  # Flag for DELTAG
    "flag_deltae": slice(70, 72),  # Flag for DELTAE
}

LINE_THREE_FORMAT = {
    "d_crfn": slice(0, 10),  # Uncertainty on CRFN
    "d_temp": slice(10, 20),  # Uncertainty on TEMP
    "d_thick": slice(20, 30),  # Uncertainty on THICK
    "d_deltal": slice(30, 40),  # Uncertainty on DELTAL
    "d_deltag": slice(40, 50),  # Uncertainty on DELTAG
    "d_deltae": slice(50, 60),  # Uncertainty on DELTAE
}

LINE_FOUR_FORMAT = {
    "deltc1": slice(0, 10),  # Width of Gaussian, constant in energy (eV)
    "deltc2": slice(10, 20),  # Width of Gaussian, linear in energy (unitless)
    "flag_deltc1": slice(60, 62),  # Flag for DELTC1
    "flag_deltc2": slice(62, 64),  # Flag for DELTC2
}

LINE_FIVE_FORMAT = {
    "d_deltc1": slice(0, 10),  # Uncertainty on DELTC1
    "d_deltc2": slice(10, 20),  # Uncertainty on DELTC2
}


class Card04(BaseModel):
    """
    Class representing the Card 4 format for broadening parameters in the SAMMY parameter file.
    This class is used to extract broadening information based on a default format.
    """

    @classmethod
    def is_header_line(cls, line: str) -> bool:
        """Check if line is a valid header line.

        Args:
            line: Input line to check

        Returns:
            bool: True if the first 5 characters of the line are 'ISOTO'
        """

        return line.strip().upper().startswith("BROAD")

    @classmethod
    def from_lines(cls, lines: List[str], fit_config: FitConfig) -> bool:
        """Read lines of the SAMMY parameter file and update the FitConfig object.
        This method extracts the broadening parameters from the lines based on the defined formats.

        Args:
            lines (list): The lines of the SAMMY parameter file.
            fit_config (FitConfig): The FitConfig object to update.

        Returns:
            bool: True if the lines were successfully read and processed.
        """

        if not lines:
            message = "No lines provided"
            logger.error(message)
            raise ValueError(message)

        # Validate header
        if not cls.is_header_line(lines[0]):
            message = f"Invalid header line: {lines[0]}"
            logger.error(message)
            raise ValueError(message)

        # if fit_config is not an instance of FitConfig, raise an error
        if fit_config is not None and not isinstance(fit_config, FitConfig):
            message = "fit_config must be an instance of FitConfig"
            logger.error(message)
            raise ValueError(message)
        elif fit_config is None:
            fit_config = FitConfig()

        # Remove header
        if cls.is_header_line(lines[0]):
            lines = lines[1:]

        main_line = None
        unc_line = None
        gaussian_line = None
        gaussian_unc_line = None

        # Find up to 4 non-blank lines
        non_blank_lines = [line for line in lines if line.strip()]
        if non_blank_lines:
            main_line = non_blank_lines[0] if len(non_blank_lines) > 0 else None
            unc_line = non_blank_lines[1] if len(non_blank_lines) > 1 else None
            gaussian_line = non_blank_lines[2] if len(non_blank_lines) > 2 else None
            gaussian_unc_line = non_blank_lines[3] if len(non_blank_lines) > 3 else None

        main_kwargs = {}
        # Parse main line
        if main_line:
            for key, sl in LINE_TWO_FORMAT.items():
                val = main_line[sl].strip()
                if key.startswith("flag_"):
                    try:
                        main_kwargs[key] = VaryFlag(int(val)) if val else VaryFlag.NO
                    except Exception:
                        main_kwargs[key] = VaryFlag.NO
                else:
                    main_kwargs[key] = float(val) if val else None

        # Parse uncertainties
        if unc_line:
            for key, sl in LINE_THREE_FORMAT.items():
                val = unc_line[sl].strip()
                main_kwargs[key] = float(val) if val else None

        # Parse Gaussian parameters
        if gaussian_line:
            for key, sl in LINE_FOUR_FORMAT.items():
                val = gaussian_line[sl].strip()
                if key.startswith("flag_"):
                    try:
                        main_kwargs[key] = VaryFlag(int(val)) if val else VaryFlag.NO
                    except Exception:
                        main_kwargs[key] = VaryFlag.NO
                else:
                    main_kwargs[key] = float(val) if val else None

        # Parse Gaussian uncertainties
        if gaussian_unc_line:
            for key, sl in LINE_FIVE_FORMAT.items():
                val = gaussian_unc_line[sl].strip()
                main_kwargs[key] = float(val) if val else None

        broad_params = BroadeningParameters(**main_kwargs)
        fit_config.physics_params.broadening_parameters = broad_params
        logger.info("Assigned broadening parameters to fit_config.physics_params.broadening_parameters")

        return True

    @classmethod
    def to_lines(cls, fit_config: FitConfig):
        broadening_params = fit_config.physics_params.broadening_parameters

        # Helper to format floats - explicit values over implicit blanks
        def fmt(val, width=10, prec=6):
            if val is None:
                return " " * width
            # Explicitly write 0.0 instead of blanks (explicit > implicit principle)
            return f"{val:>{width}.{prec}f}"

        # Helper to format flags - explicit zeros over implicit blanks
        def flag_val(flag, width=2):
            if flag is None:
                return " " * width
            # Explicitly write 0 instead of blanks (explicit > implicit principle)
            return f"{flag.value:{width}d}"

        line2 = (
            fmt(broadening_params.crfn)
            + fmt(broadening_params.temp)
            + fmt(broadening_params.thick)
            + fmt(broadening_params.deltal)
            + fmt(broadening_params.deltag)
            + fmt(broadening_params.deltae)
            + flag_val(broadening_params.flag_crfn)
            + flag_val(broadening_params.flag_temp)
            + flag_val(broadening_params.flag_thick)
            + flag_val(broadening_params.flag_deltal)
            + flag_val(broadening_params.flag_deltag)
        )
        line3 = (
            fmt(broadening_params.d_crfn)
            + fmt(broadening_params.d_temp)
            + fmt(broadening_params.d_thick)
            + fmt(broadening_params.d_deltal)
            + fmt(broadening_params.d_deltag)
            + fmt(broadening_params.d_deltae)
        )
        lines = ["BROADENING PARAMETERS FOLLOW", line2]
        # Only append line3 if it is not all spaces
        if line3.strip():
            lines.append(line3)

        lines.append("")
        return lines
