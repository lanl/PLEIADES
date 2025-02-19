#!/usr/bin/env python
"""Top level parameter file handler for SAMMY."""

import pathlib
from enum import Enum, auto
from typing import List, Optional, Union

from pydantic import BaseModel, Field

from pleiades.sammy.parameters import (
    BroadeningParameterCard,
    DataReductionCard,
    ExternalREntry,
    ExternalRFunction,
    IsotopeCard,
    NormalizationBackgroundCard,
    ORRESCard,
    ParamagneticParameters,
    RadiusCard,
    ResonanceCard,
    UnusedCorrelatedCard,
    UserResolutionParameters,
)


class CardOrder(Enum):
    """Defines the standard order of cards in SAMMY parameter files.

    Order follows Table VI B.2 in the SAMMY documentation.
    The order is relevant for writing files, though cards can be read in any order.
    """

    RESONANCE = auto()  # Card Set 1: Resonance parameters
    FUDGE = auto()  # Card Set 2: Fudge factor
    EXTERNAL_R = auto()  # Card Set 3: External R-function parameters
    BROADENING = auto()  # Card Set 4: Broadening parameters
    UNUSED_CORRELATED = auto()  # Card Set 5: Unused but correlated variables
    NORMALIZATION = auto()  # Card Set 6: Normalization and background
    RADIUS = auto()  # Card Set 7/7a: Radius parameters
    DATA_REDUCTION = auto()  # Card Set 8: Data reduction parameters
    ORRES = auto()  # Card Set 9: Oak Ridge resolution function
    ISOTOPE = auto()  # Card Set 10: Isotopic/nuclide abundances
    PARAMAGNETIC = auto()  # Card Set 12: Paramagnetic cross section
    # RESOLUTION = auto()         # Card Set 14: Facility resolution functions, not implemented yet
    USER_RESOLUTION = auto()  # Card Set 16: User-defined resolution

    @classmethod
    def get_field_name(cls, card_type: "CardOrder") -> str:
        """Get the corresponding field name in SammyParameterFile for a card type.

        Args:
            card_type: The card type enum value

        Returns:
            str: Field name used in the parameter file class
        """
        # Map enum values to field names
        field_map = {
            cls.RESONANCE: "resonance",
            cls.FUDGE: "fudge",
            cls.EXTERNAL_R: "external_r",
            cls.BROADENING: "broadening",
            cls.UNUSED_CORRELATED: "unused_correlated",
            cls.NORMALIZATION: "normalization",
            cls.RADIUS: "radius",
            cls.DATA_REDUCTION: "data_reduction",
            cls.ORRES: "orres",
            cls.ISOTOPE: "isotope",
            cls.PARAMAGNETIC: "paramagnetic",
            # cls.RESOLUTION: "resolution",  # Not implemented yet
            cls.USER_RESOLUTION: "user_resolution",
        }
        return field_map[card_type]


class SammyParameterFile(BaseModel):
    """Top level parameter file for SAMMY.

    All components are optional as parameter files may contain different
    combinations of cards based on the analysis needs.
    """

    # REQUIRED CARDS
    fudge: float = Field(default=0.1, description="Fudge factor for initial uncertainties", ge=0.0, le=1.0)
    # OPTIONAL CARDS
    resonance: Optional[ResonanceCard] = Field(None, description="Resonance parameters")
    external_r: Optional[ExternalREntry] = Field(None, description="External R matrix parameters")
    broadening: Optional[BroadeningParameterCard] = Field(None, description="Broadening parameters")
    unused_correlated: Optional[UnusedCorrelatedCard] = Field(None, description="Unused but correlated variables")
    normalization: Optional[NormalizationBackgroundCard] = Field(None, description="Normalization and background parameters")
    radius: Optional[RadiusCard] = Field(None, description="Radius parameters")
    data_reduction: Optional[DataReductionCard] = Field(None, description="Data reduction parameters")
    orres: Optional[ORRESCard] = Field(None, description="ORRES card parameters")
    paramagnetic: Optional[ParamagneticParameters] = Field(None, description="Paramagnetic parameters")
    user_resolution: Optional[UserResolutionParameters] = Field(None, description="User-defined resolution function parameters")
    # TODO: Need to verify by Sammy experts on whether the following are mandatory or optional
    isotope: Optional[IsotopeCard] = Field(None, description="Isotope parameters")

    def to_string(self) -> str:
        """Convert parameter file to string format.

        Returns:
            str: Parameter file content in SAMMY fixed-width format

        The output follows the standard card order from Table VI B.2.
        Each card is separated by appropriate blank lines.
        """
        lines = []

        # Process each card type in standard order
        for card_type in CardOrder:
            field_name = CardOrder.get_field_name(card_type)
            value = getattr(self, field_name)

            # Skip None values (optional cards not present)
            if value is None:
                continue

            # Special handling for fudge factor
            if card_type == CardOrder.FUDGE:
                lines.append(f"{value:<10.4f}")
                continue

            # For all other cards, use their to_lines() method
            card_lines = value.to_lines()
            if card_lines:  # Only add non-empty line lists
                lines.extend(card_lines)

        # Join all lines with newlines
        return "\n".join(lines)

    @classmethod
    def _get_card_class_with_header(cls, line: str):
        """Get card class that matches the header line.

        Args:
            line: Input line to check

        Returns:
            tuple: (CardOrder enum, card class) if found, or (None, None)
        """
        card_checks = [
            (CardOrder.BROADENING, BroadeningParameterCard),
            (CardOrder.DATA_REDUCTION, DataReductionCard),
            (CardOrder.EXTERNAL_R, ExternalRFunction),
            (CardOrder.ISOTOPE, IsotopeCard),
            (CardOrder.NORMALIZATION, NormalizationBackgroundCard),
            (CardOrder.ORRES, ORRESCard),
            (CardOrder.RADIUS, RadiusCard),
            (CardOrder.USER_RESOLUTION, UserResolutionParameters),
            (CardOrder.UNUSED_CORRELATED, UnusedCorrelatedCard),
            (CardOrder.PARAMAGNETIC, ParamagneticParameters),
        ]

        for card_type, card_class in card_checks:
            if hasattr(card_class, "is_header_line") and card_class.is_header_line(line):
                return card_type, card_class

        return None, None

    @classmethod
    def from_string(cls, content: str) -> "SammyParameterFile":
        """Parse content string into a parameter file object.

        Args:
            content: Content of the parameter file.

        Returns:
            SammyParameterFile: Parsed parameter file object.
        """
        # Split content into lines
        lines = content.splitlines()

        # Early exit for empty content
        if not lines:
            raise ValueError("Empty parameter file content")

        # Initialize parameters
        params = {}

        # First parse out fudge factor if it exists
        fudge_idx = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped:  # Skip empty lines
                try:
                    params["fudge"] = float(stripped)
                    fudge_idx = i
                    break
                except ValueError:
                    continue
        # now remove the fudge factor line from the list to simplify grouping
        # lines into cards
        if fudge_idx is not None:
            del lines[fudge_idx]

        # Second, partition lines into group of lines based on blank lines
        card_groups = []
        current_group = []

        for line in lines:
            if line.strip():
                current_group.append(line)
            else:
                if current_group:  # Only add non-empty groups
                    card_groups.append(current_group)
                    current_group = []

        if current_group:  # Don't forget last group
            card_groups.append(current_group)

        # Process each group of lines
        for group in card_groups:
            if not group:  # Skip empty groups
                continue

            # Check first line for header to determine card type
            card_type, card_class = cls._get_card_class_with_header(group[0])

            if card_class:
                # Process card with header
                try:
                    params[CardOrder.get_field_name(card_type)] = card_class.from_lines(group)
                except Exception as e:
                    raise ValueError(f"Failed to parse {card_type.name} card: {str(e)}")
            else:
                # No header - check if it's a resonance table
                try:
                    # Try parsing as resonance table
                    params["resonance"] = ResonanceCard.from_lines(group)
                except Exception as e:
                    print(f"Failed to parse card without header: {str(e)}")
                    raise ValueError(f"Failed to parse card without header: {str(e)}\nLines: {group}")

        return cls(**params)

    @classmethod
    def _parse_card(cls, card_type: CardOrder, lines: List[str]):
        """Parse a card's lines into the appropriate object."""
        card_class = cls._get_card_class(card_type)
        if not card_class:
            raise ValueError(f"No parser implemented for card type: {card_type}")

        try:
            return card_class.from_lines(lines)
        except Exception as e:
            print(card_type)
            print(lines)
            # Convert any parsing error into ValueError with context
            raise ValueError(f"Failed to parse {card_type.name} card: {str(e)}") from e

    @classmethod
    def _get_card_class(cls, card_type: CardOrder):
        """Get the card class for a given card type."""
        card_map = {
            CardOrder.RESONANCE: ResonanceCard,
            CardOrder.EXTERNAL_R: ExternalRFunction,
            CardOrder.BROADENING: BroadeningParameterCard,
            CardOrder.UNUSED_CORRELATED: UnusedCorrelatedCard,
            CardOrder.NORMALIZATION: NormalizationBackgroundCard,
            CardOrder.RADIUS: RadiusCard,
            CardOrder.DATA_REDUCTION: DataReductionCard,
            CardOrder.ORRES: ORRESCard,
            CardOrder.ISOTOPE: IsotopeCard,
            CardOrder.PARAMAGNETIC: ParamagneticParameters,
            CardOrder.USER_RESOLUTION: UserResolutionParameters,
        }
        return card_map.get(card_type)

    @classmethod
    def from_file(cls, filepath: Union[str, pathlib.Path]) -> "SammyParameterFile":
        """Read parameter file from disk.

        Args:
            filepath: Path to parameter file

        Returns:
            SammyParameterFile: Parsed parameter file object

        Raises:
            FileNotFoundError: If file does not exist
            ValueError: If file content is invalid
        """
        filepath = pathlib.Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Parameter file not found: {filepath}")

        try:
            content = filepath.read_text()
            return cls.from_string(content)
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to read parameter file - invalid encoding: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse parameter file: {e}")

    def to_file(self, filepath: Union[str, pathlib.Path]) -> None:
        """Write parameter file to disk.

        Args:
            filepath: Path to write parameter file

        Raises:
            OSError: If file cannot be written
            ValueError: If content cannot be formatted
        """
        filepath = pathlib.Path(filepath)

        # Create parent directories if they don't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)

        try:
            content = self.to_string()
            filepath.write_text(content)
        except OSError as e:
            raise OSError(f"Failed to write parameter file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to format parameter file content: {e}")


if __name__ == "__main__":
    print("TODO: usage example for SAMMY parameter file handling")
