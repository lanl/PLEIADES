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
            - Returns: str
        - _get_card_class_with_header
            @classmethod
            - Parameters:
                - header: str
            - Returns: Type[BaseModel]
        - from_string 
            @classmethod
            - Parameters:
                - data: str
            - Returns: SammyParameterFile
        - _parse_card
            @classmethod
            - Parameters:
                - card_data: str
            - Returns: BaseModel
        - _get_card_class
            @classmethod
            - Parameters:
                - card_name: str
            - Returns: Type[BaseModel]
        - from_file 
            @classmethod
            - Parameters:
                - file_path: Union[str, pathlib.Path]
            - Returns: SammyParameterFile
        - to_file
            - Parameters:
                - file_path: Union[str, pathlib.Path]
        - print_parameters
            - Parameters:
                - None

## Main Function
- Example usage