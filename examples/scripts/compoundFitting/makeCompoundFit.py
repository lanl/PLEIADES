from pleiades import sammyUtils

# Load the configuration file from the ini file in the parent directory
uranium = sammyUtils.SammyFitConfig('../configFiles/uranium.ini')

# Create the needed parFiles from ENDF for the isotopes in the configuration file
sammyUtils.create_parFile_from_endf(uranium,verbose_level=2)
