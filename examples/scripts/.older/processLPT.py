import argparse, sys
import pandas
import pleiades.sammyOutput as pso



print("--> Reading in LPT file")
#u235_lptFile = pso.LptFile("./U_235.LPT")
siNat_lptResults = pso.lptResults("./Si_NAT.LPT")

print(siNat_lptResults._results)
