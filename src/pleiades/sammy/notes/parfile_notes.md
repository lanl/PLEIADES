# parfile.py

## Imports
- pathlib
- os
- Enum
- auto
- List
- Optional
- Union
- BaseModel
- Field
- BroadeningParameterCard
- DataReductionCard
- ExternalREntry
- ExternalRFunction
- IsotopeCard
- NormalizationBackgroundCard
- ORRESCard
- ParamagneticParameters
- RadiusCard
- ResonanceCard
- UnusedCorrelatedCard
- UserResolutionParameters
- Logger
- _log_and_raise_error

## Logger Initialization
- log_file_path
- logger

## Enums
- CardOrder
  - Methods
    - get_field_name

## Classes
- SammyParameterFile
  - Attributes
    - fudge
    - resonance
    - external_r
    - broadening
    - unused_correlated
    - normalization
    - radius
    - data_reduction
    - orres
    - paramagnetic
    - user_resolution
    - isotope
  - Methods
    - to_string
    - _get_card_class_with_header
    - from_string
    - _parse_card
    - _get_card_class
    - from_file
    - to_file
    - print_parameters

## Main Function
- Example usage