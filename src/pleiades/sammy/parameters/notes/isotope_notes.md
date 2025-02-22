# isotope.py

## File Header
- Shebang: `#!/usr/bin/env python`
- Docstring: Description of the module and format specifications for Card Set 10

## Imports
- List
- Optional
- BaseModel
- Field
- model_validator
- VaryFlag
- format_float
- format_vary
- safe_parse
- Logger
- _log_and_raise_error
- os

## Constants
- FORMAT_STANDARD
- SPIN_GROUP_STANDARD
- FORMAT_EXTENDED
- SPIN_GROUP_EXTENDED
- CARD_10_HEADERS

## Classes
- IsotopeParameters
    - Attributes
        - mass
        - abundance
        - uncertainty
        - flag
        - spin_groups
    - Methods
        - validate_groups
        - from_lines
        - to_lines

- IsotopeCard
    - Attributes
        - isotopes
        - extended
    - Methods
        - is_header_line
        - from_lines
        - to_lines

## Main Function
- Example usage