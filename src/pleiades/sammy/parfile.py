#!/usr/bin/env python
"""Top level parameter file handler for SAMMY."""

import pathlib, os
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

from pleiades.utils.logger import Logger, _log_and_raise_error

# Initialize logger with file logging
log_file_path = os.path.join(os.getcwd(), 'pleiades-par.log')
logger = Logger(__name__, log_file=log_file_path)

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

    # CARDS for parameter file object
    fudge: Optional[float] = Field(None, description="Fudge factor for initial uncertainties", ge=0.0, le=1.0)
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
    isotope: Optional[IsotopeCard] = Field(None, description="Isotope parameters")

    def to_string(self) -> str:
        """Convert parameter file to string format.

        Returns:
            str: Parameter file content in SAMMY fixed-width format

        The output follows the standard card order from Table VI B.2.
        Each card is separated by appropriate blank lines.
        """
        where_am_i = "SammyParameterFile.to_string()"

        logger.info(f"{where_am_i}: Attempting to convert parameter file to string format")
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
                logger.debug(f"{where_am_i}: Added lines for {card_type.name} card")

        # Join all lines with newlines
        result = "\n".join(lines)
        logger.info(f"{where_am_i}: Successfully converted parameter file to string format")
        return result

    @classmethod
    def _get_card_class_with_header(cls, line: str):
        """Get card class that matches the header line.

        Args:
            line: Input line to check

        Returns:
            tuple: (CardOrder enum, card class) if found, or (None, None)
        """
        where_am_i = "SammyParameterFile._get_card_class_with_header()"

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
                logger.debug(f"{where_am_i}: card_type:{card_type}\t card_class:{card_class}")
                return card_type, card_class

        logger.info(f"{where_am_i}: No matches found for {line}")
        return None, None

    @classmethod
    def from_string(cls, content: str) -> "SammyParameterFile":
        """Parse content string into a parameter file object.

        Args:
            content: Content of the parameter file.

        Returns:
            SammyParameterFile: Parsed parameter file object.
        """
        where_am_i = "SammyParameterFile.from_string()"
        
        # Split content into lines
        lines = content.splitlines()

        # Early exit for empty content
        if not lines:
            _log_and_raise_error("Empty parameter file content", ValueError)

        # Initialize parameters
        params = {}

        # Second, partition lines into group of lines based on blank lines
        card_groups = []
        current_group = []

        for line in lines:
            if line.strip():
                current_group.append(line)
            else:
                # Only add non-empty groups
                if current_group:  
                    card_groups.append(current_group)
                    current_group = []

        # Don't forget last group
        if current_group: card_groups.append(current_group)

        # Process each group of lines
        for group in card_groups:
            
            # Skip empty groups
            if not group:  
                continue

            # Check first line for header to determine card type
            card_type, card_class = cls._get_card_class_with_header(group[0])

            if card_class:
                # Process card with header
                try:
                    params[CardOrder.get_field_name(card_type)] = card_class.from_lines(group)
                    logger.info(f"{where_am_i}: Successfully parsed {card_type.name} card")
                except Exception as e:
                    logger.error(f"Failed to parse {card_type.name} card: {str(e)}\nLines: {group}")
                    raise ValueError(f"Failed to parse {card_type.name} card: {str(e)}\nLines: {group}")
            else:

                # check if group if fudge factor
                if len(group) == 1:
                    try:
                        params["fudge"] = float(group[0])
                        logger.info(f"{where_am_i}: Successfully parsed fudge factor")
                    except ValueError as e:
                        logger.error(f"Failed to parse fudge factor: {str(e)}\nLines: {group}")
                        raise ValueError(f"Failed to parse fudge factor: {str(e)}\nLines: {group}")
                else:
                    #check if it's a resonance table
                    try:
                        # Try parsing as resonance table
                        params["resonance"] = ResonanceCard.from_lines(group)
                        logger.info(f"{where_am_i}: Successfully parsed resonance table")
                    except Exception as e:
                        logger.error(f"Failed to parse card without header: {str(e)}\nLines: {group}")
                        raise ValueError(f"Failed to parse card without header: {str(e)}\nLines: {group}")

        logger.info(f"{where_am_i}: Successfully parsed all parameter file content from string")
        return cls(**params)

    @classmethod
    def _parse_card(cls, card_type: CardOrder, lines: List[str]):
        """Parse a card's lines into the appropriate object."""
        where_am_i = "SammyParameterFile._parse_card()"

        logger.info(f"{where_am_i}: Attempting to parse card of type: {card_type.name}")
        
        card_class = cls._get_card_class(card_type)
        
        if not card_class:
            _log_and_raise_error(f"No parser implemented for card type: {card_type}", ValueError)

        try:
            parsed_card = card_class.from_lines(lines)
            logger.info(f"Successfully parsed card of type: {card_type.name}")
            return parsed_card
        except Exception as e:
            logger.error(f"Failed to parse {card_type.name} card: {str(e)}\nLines: {lines}")
            # Convert any parsing error into ValueError with context
            raise ValueError(f"Failed to parse {card_type.name} card: {str(e)}\n") from e

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
        where_am_i = "SammyParameterFile.from_file()"

        filepath = pathlib.Path(filepath)
        
        logger.info(f"{where_am_i}: Attempting to read parameter file from: {filepath}")

        if not filepath.exists():
            _log_and_raise_error(f"Parameter file not found: {filepath}", FileNotFoundError)

        try:
            content = filepath.read_text()
            logger.info(f"{where_am_i}: Successfully read content in file: {filepath}")
            return cls.from_string(content)
        
        except UnicodeDecodeError as e:
            _log_and_raise_error(f"Failed to read parameter file - invalid encoding: {e}", ValueError)
        except Exception as e:
            _log_and_raise_error(f"Failed to parse parameter file: {filepath}\n {e}", ValueError)

    def to_file(self, filepath: Union[str, pathlib.Path]) -> None:
        """Write parameter file to disk.

        Args:
            filepath: Path to write parameter file

        Raises:
            OSError: If file cannot be written
            ValueError: If content cannot be formatted
        """
        where_am_i = "SammyParameterFile.to_file()"
        filepath = pathlib.Path(filepath)
        logger.info(f"{where_am_i}: Attempting to write parameter file to: {filepath}")

        # Create parent directories if they don't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)

        try:
            content = self.to_string()
            filepath.write_text(content)
            logger.info(f"{where_am_i}: Successfully wrote parameter file to: {filepath}")

        except OSError as e:
            _log_and_raise_error(f"Failed to write parameter file: {e}", OSError)
        except Exception as e:
            _log_and_raise_error(f"Failed to format parameter file content: {e}", ValueError)

    def print_parameters(self) -> None:
        """Print the details of the parameter file."""
        
        logger.info("SammyParameterFile.print_parameters(): Printing out Sammy Parameter Detials")
        
        print("Sammy Parameter File Details:")

        # check if any cards are present
        if all(value is None for value in self.dict().values()):
            print("No cards present in the parameter file.")
            return
        else:
            for card_type in CardOrder:
                field_name = CardOrder.get_field_name(card_type)
                value = getattr(self, field_name)
                if value is not None:
                    print(f"{field_name}:")
                    if isinstance(value, list):
                        for index, item in enumerate(value):
                            print(f"  {field_name}[{index}]: {item}")
                    else:
                        print(f"  {value}")

if __name__ == "__main__":
    print("TODO: usage example for SAMMY parameter file handling")
