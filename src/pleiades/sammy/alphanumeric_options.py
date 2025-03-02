from pydantic import BaseModel, Field, model_validator, field_validator, root_validator
from typing import List, Union, Optional



class AlphanumericOptions(BaseModel):
    """ SAMMY relies on the use of alphanumeric commands to govern the operations it will perform. 
        These commands, which are in English, are located in card set 3 of the INPut file. 
        Commands are divided into 23 different categories (not all represented here)


        
    """

    general_options: Optional[List[Union[str, List[str]]]] = Field(default_factory=lambda: [
        "",
        ["UNRESOLVED RESONANCE region","FRITZ FROEHNERS FITAcs", "FITACS"]
    ])

    # Experimental data input control
    experimental_data_input_options: Optional[List[Union[str, List[str]]]] = Field(default_factory=lambda: [
        "DATA ARE IN ORIGINAL multi-style format",
        ["DATA FORMAT IS ONE Point per line", "USE CSISRS FORMAT FOr data", "CSISRS"],
        ["USE TWENTY SIGNIFICAnt digits", "TWENTY"],
        "DATA ARE IN STANDARD odf format",
        "DATA ARE IN ODF FILE",
        ["DATA ARE ENDF/B FILE", "USE ENDF/B ENERGIES and data, with MAT=9999"],
        "DIFFERENTIAL DATA ARe in ascii file",
        "DO NOT DIVIDE DATA Into regions",
        "DIVIDE DATA INTO REGions with a fixed number of data points per region"
    ])

    # Experimental data input control for covariance matrix
    covariance_matrix_data_input_options: Optional[List[Union[str, List[str]]]] = Field(default_factory=lambda: [
        ["IMPLICIT DATA COVARIance is wanted", "IDC"],
        ["USER SUPPLIED IMPLICit data covariance matrix", "USER IDC"],
        "PUP COVARIANCE IS IN an ascii file",
        "CREATE PUP FILE FROM varied parameters used in this run",
        ["ADD CONSTANT TERM TO data covariance", "ADD CONSTANT TO DATA covariance matrix"],
        "DO NOT ADD CONSTANT term to data covariance",
        "USE DEFAULT FOR CONStant term to add to data covariance",
        ["USE TEN PERCENT DATA uncertainty", "ADD TEN PERCENT DATA uncertainty"],
        "DATA COVARIANCE IS Diagonal",
        "DATA HAS OFF-DIAGONAl contribution to covariance matrix of the form (a+bEi) (a+bEj)",
        "DATA COVARIANCE FILE is named YYYYYY.YYY",
        "FREE FORMAT DATA COVariance YYYYYY.YYY"
    ])

    # Broadening options
    broadening_options: Optional[List[str]] = Field(default_factory=lambda: [
        "BROADENING IS WANTED",
        "BROADENING IS NOT WAnted"
    ])

    # Doppler Broadening options
    doppler_broadening_options: Optional[List[Union[str, List[str]]]] = Field(default_factory=lambda: [
        ["USE FREE GAS MODEL Of doppler broadening", "FGM"],
        "USE LEAL-HWANG DOPPLer broadening",
        ["HIGH ENERGY GAUSSIAN approximation for Doppler broadening", "USE MULTI-STYLE DOPPler broadening", "HEGA"],
        ["USE CRYSTAL LATTICE model of doppler broadening", "CLM"],
        "NO LOW-ENERGY BROADEning is to be used"
    ])

    # Multiple scattering corrections
    multiple_scattering_corrections_options: Optional[List[Union[str, List[str]]]] = Field(default_factory=lambda: [
        ["DO NOT INCLUDE SELF-shielding multiple-scattering corrections", "NO SELF-SHIELDING ANd multiple-scattering corrections"],
        ["USE SELF SHIELDING Only no scattering", "SELF SHIELD", "INCLUDE ONLY SELF SHielding and not Multiple scattering"],
        ["USE SINGLE SCATTERINg plus self shielding", "SINGLE"],
        ["INCLUDE DOUBLE SCATTering corrections", "USE MULTIPLE SCATTERing plus single scattering", "DOUBLE", "MULTIPLE"],
        ["INFINITE SLAB", "NO FINITE-SIZE CORREctions to single scattering"],
        ["FINITE SLAB", "FINITE SIZE CORRECTIons to single scattering"],
        "MAKE NEW FILE WITH Edge effects",
        "FILE WITH EDGE EFFECts already exists",
        "MAKE PLOT FILE OF MUltiple scattering pieces",
        ["NORMALIZE AS CROSS Section rather than yield", "CROSS SECTION"],
        ["NORMALIZE AS YIELD Rather than cross section", "YIELD"],
        "NORMALIZE AS (1-E)SIgma",
        "PRINT MULTIPLE SCATTering corrections",
        ["PREPARE INPUT FOR MOnte carlo simulation", "MONTE CARLO"],
        "Y2 VALUES ARE TABULAted",
        "USE QUADRATIC INTERPolation for y1",
        "USE LINEAR INTERPOLAtion for y1",
        ["VERSION 7.0.0 FOR Multiple scattering", "V7"],
        "DO NOT CALCULATE Y0"
    ])

    # Bayes solution options
    bayes_solution_options: Optional[List[Union[str, List[str]]]] = Field(default_factory=lambda: [
        "SOLVE BAYES EQUATIONs", 
        "DO NOT SOLVE BAYES Equations", 
        "LET SAMMY CHOOSE WHIch inversion scheme to use",
        ["USE (N+V) INVERSION scheme", "NPV"],
        ["USE (I+Q) INVERSION scheme", "IPQ"],
        ["USE (M+W) INVERSION scheme", "MPW"],
        "USE LEAST SQUARES TO define prior parameter covariance matrix",
        "TAKE BABY STEPS WITH least-squares method",
        "REMEMBER ORIGINAL PArameter values",
        "USE REMEMBERED ORIGInal parameter values"
    ])

    # Options for printing into SAMMY.LPT
    lpt_file_options: Optional[List[Union[str, List[str]]]] = Field(default_factory=lambda: [
        "DO NOT PRINT ANY INPut parameters",
        "PRINT ALL INPUT PARAmeters",
        "PRINT VARIED INPUT Parameters",
        "DO NOT PRINT INPUT Data",
        ["PRINT INPUT DATA", "PRINT EXPERIMENTAL Values"],
        "DO NOT PRINT THEORETical values",
        ["PRINT THEORETICAL VAlues", "PRINT THEORETICAL CRoss sections"],
        "DO NOT PRINT PARTIAL derivatives",
        "SUPPRESS INTERMEDIATe printout",
        "DO NOT SUPPRESS ANY intermediate printout",
        "DO NOT USE SHORT FORmat for output",
        "USE SHORT FORMAT FOR output",
        "DO NOT PRINT REDUCED widths",
        "PRINT REDUCED WIDTHS",
        "DO NOT PRINT SMALL Correlation coefficients",
        "DO NOT PRINT DEBUG Info",
        ["PRINT DEBUG INFORMATion", "DEBUG"],
        "PRINT CAPTURE AREA In lpt file",
        ["CHI SQUARED IS NOT Wanted", "DO NOT PRINT LS CHI squared"],
        ["CHI SQUARED IS WANTEd", "PRINT LS CHI SQUARED"],
        "PRINT BAYES CHI SQUAred",
        "DO NOT PRINT BAYES Chi squared",
        ["DO NOT PRINT WEIGHTEd Residuals", "DO NOT PRINT LS WEIGhted residuals"],
        ["PRINT WEIGHTED RESIDuals", "PRINT LS WEIGHTED REsiduals"],
        "PRINT BAYES WEIGHTED residuals",
        "DO NOT PRINT BAYES Weighted residuals",
        "DO NOT PRINT PHASE Shifts",
        "PRINT PHASE SHIFTS For input parameters"
    ])

    @root_validator(pre=True)
    def check_mutually_exclusive_options(cls, values):
        # Check mutually exclusive options for r_matrix_options
        r_matrix_options = values.get('r_matrix_options', [])
        r_matrix_mutually_exclusive_groups = [
            ["REICH-MOORE FORMALISm is wanted", "MORE ACCURATE REICHmoore", "XCT"],
            ["ORIGINAL REICH-MOORE formalism", "CRO"],
            ["MULTILEVEL BREITWIGner is wanted", "MLBW FORMALISM IS WAnted", "MLBW"],
            ["SINGLE LEVEL BREITWigner is wanted", "SLBW FORMALISM IS WAnted", "SLBW"],
            ["REDUCED WIDTH AMPLITudes are used for input"]
        ]
        cls._check_mutually_exclusive(r_matrix_options, r_matrix_mutually_exclusive_groups)

        # Check mutually exclusive options for input_quantum_numbers_options
        input_quantum_numbers_options = values.get('input_quantum_numbers_options', [])
        input_quantum_numbers_mutually_exclusive_groups = [
            ["USE NEW SPIN GROUP Format", "PARTICLE PAIR DEFINItions are used", "KEY-WORD PARTICLE-PAir definitions are given"]
        ]
        cls._check_mutually_exclusive(input_quantum_numbers_options, input_quantum_numbers_mutually_exclusive_groups)

        return values

    @staticmethod
    def _check_mutually_exclusive(options, mutually_exclusive_groups):
        selected_options = set()
        for group in mutually_exclusive_groups:
            group_set = set(group)
            selected_in_group = group_set.intersection(options)
            if len(selected_in_group) > 1:
                raise ValueError(f"Mutually exclusive options selected: {selected_in_group}")
            selected_options.update(selected_in_group)

    # validator for alphanumeric options
    @model_validator(mode="after")
    def validate_alphanumeric_options(self) -> "AlphanumericOptions":
        """Validate that the alphanumeric options are unique."""
        # Check if all options are unique
        all_options = [
            self.r_matrix_options, self.input_quantum_numbers_options, self.input_covariance_matrix_options,
            self.output_covariance_matrix_options, self.experimental_data_input_options, 
            self.covariance_matrix_data_input_options, self.broadening_options, self.doppler_broadening_options,
            self.multiple_scattering_corrections_options, self.bayes_solution_options, self.lpt_file_options
        ]
        all_options_flat = [item for sublist in all_options if sublist is not None for item in sublist]
        if len(all_options_flat) != len(set(all_options_flat)):
            raise ValueError("All alphanumeric options must be unique")
        return self

    # validate that all fields are strings
    @field_validator(mode="after")
    def validate_fields_are_strings(self) -> "AlphanumericOptions":
        """Validate that all fields are strings."""
        all_options = [
            self.r_matrix_options, self.input_quantum_numbers_options, self.input_covariance_matrix_options,
            self.output_covariance_matrix_options, self.experimental_data_input_options, 
            self.covariance_matrix_data_input_options, self.broadening_options, self.doppler_broadening_options,
            self.multiple_scattering_corrections_options, self.bayes_solution_options, self.lpt_file_options
        ]
        for option in all_options:
            if option is not None:
                for item in option:
                    if isinstance(item, list):
                        for subitem in item:
                            if not isinstance(subitem, str):
                                raise ValueError("All fields must be strings")
                    elif not isinstance(item, str):
                        raise ValueError("All fields must be strings")
        return self


























