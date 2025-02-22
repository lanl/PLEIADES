# radius.py

## Imports
- re
- os
- Enum
- List
- Optional
- Tuple
- Union
- BaseModel
- Field
- field_validator
- model_validator
- VaryFlag
- format_float
- format_vary
- parse_keyword_pairs_to_dict
- safe_parse
- Logger
- _log_and_raise_error

## Logger Initialization
- log_file_path
- logger

## Constants
- CARD_7_HEADER
- CARD_7A_HEADER
- CARD_7_ALT_HEADER
- FORMAT_DEFAULT
- FORMAT_ALTERNATE

## Enums
- RadiusFormat
- OrbitalMomentum

## Classes
- RadiusParameters
  - Attributes
    - effective_radius
    - true_radius
    - channel_mode
    - vary_effective
    - vary_true
    - spin_groups
    - channels
  - Methods
    - validate_spin_groups
    - validate_vary_true
    - validate_channels
    - validate_true_radius_consistency
    - __repr__

- RadiusCardDefault
  - Attributes
    - parameters
  - Methods
    - is_header_line
    - _parse_numbers_from_line
    - _parse_spin_groups_and_channels
    - from_lines
    - to_lines

- RadiusCardAlternate
  - Attributes
    - parameters
  - Methods
    - is_header_line
    - _parse_numbers_from_line
    - _parse_spin_groups_and_channels
    - from_lines
    - to_lines

- RadiusCardKeyword
  - Attributes
    - parameters
    - particle_pair
    - orbital_momentum
    - relative_uncertainty
    - absolute_uncertainty
  - Methods
    - is_header_line
    - _parse_values
    - from_lines
    - to_lines

- RadiusCard
  - Attributes
    - parameters
    - particle_pair
    - orbital_momentum
    - relative_uncertainty
    - absolute_uncertainty
  - Methods
    - is_header_line
    - detect_format
    - from_lines
    - to_lines
    - from_values

## Main Function
- Example usage