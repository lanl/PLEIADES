from pleiades import sammyParFile, sammyUtils
from numpy import testing
import pytest
import pathlib

def test_sammyUtils_run_endf():
    # run SAMMY and create PAR file from ENDF
    sammyUtils.sammy_par_from_endf("Eu-153",14.96)

    # read produced par file
    eu153 = sammyParFile('.archive/Eu-153/results/SAMNDF.PAR').read()

    # check that 2 spin groups are defined
    spin_groups = eu153.data["spin_group"]
    assert len(spin_groups)==2