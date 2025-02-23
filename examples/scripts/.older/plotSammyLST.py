import sys
import pleiades.sammyPlotter as psp

print("--> Plotting LPT file")
psp.process_and_plot_lst_file("./U_235.LST", residual=True, quantity='transmission')