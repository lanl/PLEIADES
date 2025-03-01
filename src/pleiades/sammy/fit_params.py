from enum import Enum
from pydantic import BaseModel, Field, constr
from pleiades.core.nuclear_params import nuclearParameters
from pleiades.core.physics_params import PhysicsParameters

#Fitting comman



class DataType(str, Enum):
    TRANSMISSION = "TRANSmission"
    TOTAL_CROSS_SECTION = "TOTAL cross section"
    SCATTERING = "SCATTering"
    ELASTIC = "ELASTic"
    DIFFERENTIAL_ELASTIC = "DIFFErential elastic"
    DIFFERENTIAL_REACTION = "DIFFErentiAL REaction"
    REACTION = "REACTion"
    INELASTIC_SCATTERING = "INELAstic scattering"
    FISSION = "FISSion"
    CAPTURE = "CAPTure"
    SELF_INDICATION = "SELF-indication"
    INTEGRAL = "INTEGral"
    COMBINATION = "COMBInation"

class FitRoutineParameters(BaseModel):
    """Container for fit routine parameters.

    Attributes:
        max_iterations: Maximum number of iterations
        tolerance: Tolerance for chi-squared convergence
        max_cpu_time: Maximum CPU time allowed
        max_wall_time: Maximum wall time allowed
        max_memory: Maximum memory allowed
        max_disk: Maximum disk space allowed
    """

    max_iterations: int = Field(description="Maximum number of iterations")
    i_correlation: int = Field(description="Correlation matrix interval", Default=50)
    endf_mat_num: int = Field(description="ENDF material number", Default=0)

class AlphanumericParameters(BaseModel):
    """Container for alphanumeric commands that could be used in fitting.

    Attributes:
        r_matrix_option: Command for R-matrix approximation
        input_quantum_numbers_option: Command for quantum numbers input control
        input_covariance_matrix_option: Command for prior covariance matrix input control
        output_covariance_matrix_option: Command for parameter covariance matrix output control
        experimental_data_input_option: Command for experimental data input control
        covariance_matrix_data_input_option: Command for covariance matrix data input control
        broadening_option: Command for broadening
        doppler_broadening_option: Command for Doppler broadening
    """

    r_matrix_option: constr(regex=r"^(UNRESOLVED RESONANCE region|FRITZ FROEHNERS FITAcs|FITACS|REICH-MOORE FORMALISm is wanted|MORE ACCURATE REICHmoore|XCT|ORIGINAL REICH-MOORE formalism|CRO|MULTILEVEL BREITWIGner is wanted|MLBW FORMALISM IS WAnted|MLBW|SINGLE LEVEL BREITWigner is wanted|SLBW FORMALISM IS WAnted|SLBW|REDUCED WIDTH AMPLITudes are used for input)$") # type: ignore
    input_quantum_numbers_option: constr(regex=r"^(USE NEW SPIN GROUP Format|PARTICLE PAIR DEFINItions are used|KEY-WORD PARTICLE-PAir definitions are given|QUANTUM NUMBERS ARE in parameter file|PUT QUANTUM NUMBERS into parameter file|SPIN OF INCIDENT PARticle is \+|SPIN OF INCIDENT PARticle is -|USE I4 FORMAT TO REAd spin group number|INPUT IS ENDF/B FILE|USE ENERGY RANGE FROm endf/b file 2|FLAG ALL RESONANCE Parameters)$")
    input_covariance_matrix_option: constr(regex=r"^(IGNORE INPUT BINARY covariance file|IGNORE|ENERGY UNCERTAINTIES are at end of line in par file|RETROACTIVE OLD PARAmeter file new covariance|RETROACTIVE|U COVARIANCE MATRIX is correct, p is not|P COVARIANCE MATRIX is correct, u is not|MODIFY P COVARIANCE matrix before using|INITIAL DIAGONAL U Covariance|INITIAL DIAGONAL P Covariance|PERMIT NON POSITIVE definite parameter covariance matrices|PERMIT ZERO UNCERTAInties on parameters|READ COMPACT COVARIAnces for parameter priors|READ COMPACT CORRELAtions for parameter priors|COMPACT CORRELATIONS are to be read and used|COMPACT COVARIANCES are to be read and used|PARAMETER COVARIANCE matrix is in endf format|ENDF COVARIANCE MATRix is to be read and Used|USE LEAST SQUARES TO define prior parameter covariance matrix)$")
    output_covariance_matrix_option: constr(regex=r"^(WRITE CORRELATIONS Into compact format|WRITE COVARIANCES INto compact format|PUT CORRELATIONS INTo compact format|PUT COVARIANCES INTO compact format|PUT COVARIANCE MATRIx into endf file 32)$")
    experimental_data_input_option: constr(regex=r"^(DATA ARE IN ORIGINAL multi-style format|DATA FORMAT IS ONE Point per line|USE CSISRS FORMAT FOr data|CSISRS|USE TWENTY SIGNIFICAnt digits|TWENTY|DATA ARE IN STANDARD odf format|DATA ARE IN ODF FILE|DATA ARE ENDF/B FILE|USE ENDF/B ENERGIES and data, with MAT=9999|DIFFERENTIAL DATA ARe in ascii file|DO NOT DIVIDE DATA Into regions|DIVIDE DATA INTO REGions with a fixed number of data points per region)$")
    covariance_matrix_data_input_option: constr(regex=r"^(IMPLICIT DATA COVARIance is wanted|IDC|USER SUPPLIED IMPLICit data covariance matrix|USER IDC|PUP COVARIANCE IS IN an ascii file|CREATE PUP FILE FROM varied parameters used in this run|ADD CONSTANT TERM TO data covariance|ADD CONSTANT TO DATA covariance matrix|DO NOT ADD CONSTANT term to data covariance|USE DEFAULT FOR CONStant term to add to data covariance|USE TEN PERCENT DATA uncertainty|ADD TEN PERCENT DATA uncertainty|DATA COVARIANCE IS Diagonal|DATA HAS OFF-DIAGONAl contribution to covariance matrix of the form \(a\+bEi\) \(a\+bEj\)|DATA COVARIANCE FILE is named YYYYYY.YYY|FREE FORMAT DATA COVariance YYYYYY.YYY)$")
    broadening_option: constr(regex=r"^(BROADENING IS WANTED|BROADENING IS NOT WAnted)$")
    doppler_broadening_option: constr(regex=r"^(USE FREE GAS MODEL Of doppler broadening|FGM|USE LEAL-HWANG DOPPLer broadening|HIGH ENERGY GAUSSIAN approximation for Doppler broadening|USE MULTI-STYLE DOPPler broadening|HEGA|USE CRYSTAL LATTICE model of doppler broadening|CLM|NO LOW-ENERGY BROADEning is to be used)$")

class dataParameters(BaseModel):
    """Container for data parameters.

    Attributes:
        data_file: File containing the data
        data_format: Format of the data
        data_type: Type of the data
        data_units: Units of the data
        data_title: Title of the data
        data_comment: Comment for the data
    """

    data_file: str = Field(description="File containing the data")
    data_format: str = Field(description="Format of the data")
    data_type: DataType = Field(description="Type of the data")
    data_units: str = Field(description="Units of the data")
    data_title: str = Field(description="Title of the data")
    data_comment: str = Field(description="Comment for the data")

class FitParameters(BaseModel):
    """Container for fit parameters including nuclear and physics parameters.

    Attributes:
        nuclear_params (nuclearParameters): Nuclear parameters used in SAMMY calculations.
        physics_params (PhysicsParameters): Physics parameters including energy, normalization, and broadening.
    """

    fit_title: str = Field(description="Title of fitting run")
    tolerance: float = Field(description="Tolerance for chi-squared convergence")
    max_cpu_time: float = Field(description="Maximum CPU time allowed")
    max_wall_time: float = Field(description="Maximum wall time allowed")
    max_memory: float = Field(description="Maximum memory allowed")
    max_disk: float = Field(description="Maximum disk space allowed")

    nuclear_params: nuclearParameters = Field(description="Nuclear parameters used in SAMMY calculations")
    physics_params: PhysicsParameters = Field(description="Physics parameters used in SAMMY calculations")