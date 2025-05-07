from enum import Enum
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field

from pleiades.utils.units import CrossSectionUnitOptions, EnergyUnitOptions


class DataTypeOptions(str, Enum):
    TRANSMISSION = "TRANSMISSION"
    TOTAL_CROSS_SECTION = "TOTAL CROSS SECTION"
    SCATTERING = "SCATTERING"
    ELASTIC = "ELASTIC"
    DIFFERENTIAL_ELASTIC = "DIFFERENTIAL ELASTIC"
    DIFFERENTIAL_REACTION = "DIFFERENTIAL REACTION"
    REACTION = "REACTION"
    INELASTIC_SCATTERING = "INELASTIC SCATTERING"
    FISSION = "FISSION"
    CAPTURE = "CAPTURE"
    SELF_INDICATION = "SELF INDICATION"
    INTEGRAL = "INTEGRAL"
    COMBINATION = "COMBINATION"


class dataParameters(BaseModel):
    """Container for data parameters.

    Attributes:
        data_file: File containing the data
        data_format: Format of the data
        data_type: Type of the data
        energy_units: Units of energy
        cross_section_units: Units of cross-section
        data_title: Title of the data
        data_comment: Comment for the data
    """

    data_file: str = Field(description="File containing the data", default=None)
    data_type: DataTypeOptions = Field(description="Type of the data", default=DataTypeOptions.TRANSMISSION)
    energy_units: EnergyUnitOptions = Field(description="Units of energy", default=EnergyUnitOptions.eV)
    cross_section_units: CrossSectionUnitOptions = Field(
        description="Units of cross-section", default=CrossSectionUnitOptions.barn
    )
    data_title: str = Field(description="Title of the data", default=None)
    data_comment: str = Field(description="Comment for the data", default=None)


class LstData(BaseModel):
    """
    Container for LST data, loaded from a SAMMY .LST file using pandas.

    Attributes:
        data_file: Path to the LST file.
        data: Pandas DataFrame holding the LST data.
    """

    model_config = {"arbitrary_types_allowed": True}

    data_file: str = Field(description="File containing the data", default=None)
    data_type: DataTypeOptions = Field(description="Type of the data", default=DataTypeOptions.TRANSMISSION)
    data_format: str = Field(description="Format of the data", default="LST")
    energy_units: EnergyUnitOptions = Field(description="Units of energy", default=EnergyUnitOptions.eV)
    cross_section_units: CrossSectionUnitOptions = Field(
        description="Units of cross-section", default=CrossSectionUnitOptions.barn
    )
    data: Optional[pd.DataFrame] = Field(default=None, exclude=True)

    # All possible columns in a SAMMY.LPT file (always in this order)
    _all_column_names = [
        "Energy",
        "Experimental cross section (barns)",
        "Absolute uncertainty in experimental cross section (barns)",
        "Zeroth-order theoretical cross section as evaluated by SAMMY (barns)",
        "Final theoretical cross section as evaluated by SAMMY (barns)",
        "Experimental transmission (dimensionless)",
        "Absolute uncertainty in experimental transmission",
        "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)",
        "Final theoretical transmission as evaluated by SAMMY (dimensionless)",
        "Theoretical uncertainty on Zeroth-order theoretical cross section or transmission",
        "Theoretical uncertainty on Final theoretical cross section or transmission",
        "Adjusted energy initially",
        "Adjusted energy finally",
    ]

    def model_post_init(self, __context):
        if self.data_file is not None:
            self.load()

    def load(self):
        """Load the LST file into a pandas DataFrame and validate columns."""
        self.data = pd.read_csv(self.data_file, sep=r"\s+", header=None, comment="#")
        n_cols = self.data.shape[1]
        self.data.columns = self._all_column_names[:n_cols]
        self.validate_columns()

    def validate_columns(self):
        """Validate columns based on data_type."""
        transmission_cols = [
            "Experimental transmission (dimensionless)",
            "Absolute uncertainty in experimental transmission",
            "Zeroth-order theoretical transmission as evaluated by SAMMY (dimensionless)",
            "Final theoretical transmission as evaluated by SAMMY (dimensionless)",
        ]
        cross_section_cols = [
            "Experimental cross section (barns)",
            "Absolute uncertainty in experimental cross section",
            "Zeroth-order theoretical cross section as evaluated by SAMMY (barns)",
            "Final theoretical cross section as evaluated by SAMMY (barns)",
        ]

        if self.data_type == DataTypeOptions.TRANSMISSION:
            # Transmission data must have all transmission columns
            for col in transmission_cols:
                if col not in self.data.columns:
                    raise ValueError(f"Missing required transmission column: {col}")

        elif self.data_type == DataTypeOptions.TOTAL_CROSS_SECTION or self.data_type == DataTypeOptions.SCATTERING:
            # Cross-section data must have all cross-section columns
            for col in cross_section_cols:
                if col not in self.data.columns:
                    raise ValueError(f"Missing required cross-section column: {col}")
            # Should not have transmission columns
            for col in transmission_cols:
                if col in self.data.columns:
                    raise ValueError(f"Unexpected transmission column for cross-section data: {col}")

    @property
    def energy(self):
        return self.data["Energy"] if self.data is not None else None

    @property
    def experimental_cross_section(self):
        return self.data["Experimental cross section"] if self.data is not None else None

    @property
    def theoretical_cross_section(self):
        return self.data["Final theoretical cross section"] if self.data is not None else None

    @property
    def experimental_transmission(self):
        return self.data["Experimental transmission"] if self.data is not None else None

    @property
    def theoretical_transmission(self):
        return self.data["Final theoretical transmission"] if self.data is not None else None
