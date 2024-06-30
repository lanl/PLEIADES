from pleiades import sammyUtils
from pleiades import sammyRunner

# Load the configuration file from the ini file in the parent directory
eu_nat = sammyUtils.SammyFitConfig('../sammyFitU.ini')

# Create the needed parFiles from ENDF for the isotopes in the configuration file
sammyUtils.create_parFile_from_endf(eu_nat,verbose_level=1)

# Configure the sammy run, this will create a compound parFile. 
sammyUtils.configure_sammy_run(eu_nat,verbose_level=1)

# Run the sammy fit
sammyRunner.run_sammy(eu_nat,verbose_level=1)

