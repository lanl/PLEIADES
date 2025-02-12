#!/usr/bin/env python
"""Top level parameter file handler for SAMMY."""

from enum import Enum, auto
from typing import List, Optional

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
    ResonanceEntry,
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
    resonance: Optional[ResonanceEntry] = Field(None, description="Resonance parameters")
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
                lines.append(f"{value:10.4f}")
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
        """Parse parameter file content into SammyParameterFile object.

        Args:
            content: String containing parameter file content

        Returns:
            SammyParameterFile: Parsed parameter file object

        Raises:
            ValueError: If content format is invalid
        """
        lines = content.splitlines()
        if not lines:
            raise ValueError("Empty parameter file content")

        params = {}
        current_card = None
        card_lines = []

        # Process lines
        line_idx = 0
        while line_idx < len(lines):
            line = lines[line_idx]

            # First non-empty line should be fudge factor
            if not current_card and line.strip():
                try:
                    params["fudge"] = float(line.strip())
                    line_idx += 1
                    continue
                except ValueError:
                    # Not a fudge factor, try other cards
                    pass

            # Check for card headers
            card_type, card_class = cls._get_card_class_with_header(line)
            if card_class:
                # Process previous card if exists
                if current_card and card_lines:
                    params[CardOrder.get_field_name(current_card)] = cls._parse_card(current_card, card_lines)

                # Start new card
                current_card = card_type
                card_lines = [line]
            else:
                # Not a header, add to current card if exists
                if current_card:
                    card_lines.append(line)

            line_idx += 1

        # Process final card
        if current_card and card_lines:
            params[CardOrder.get_field_name(current_card)] = cls._parse_card(current_card, card_lines)

        return cls(**params)

    @classmethod
    def _parse_card(cls, card_type: CardOrder, lines: List[str]):
        """Parse a card's lines into the appropriate object."""
        card_class = cls._get_card_class(card_type)
        if not card_class:
            raise ValueError(f"No parser implemented for card type: {card_type}")
        return card_class.from_lines(lines)

    @classmethod
    def _get_card_class(cls, card_type: CardOrder):
        """Get the card class for a given card type."""
        card_map = {
            CardOrder.RESONANCE: ResonanceEntry,
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


if __name__ == "__main__":
    print("TODO: usage example for SAMMY parameter file handling")
