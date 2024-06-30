from pleiades import sammyUtils
from pleiades import sammyRunner

eu_nat = sammyUtils.SammyFitConfig('../sammyFitEnNat.ini')

sammyUtils.sammy_par_from_endf(isotope='Eu-151')
sammyUtils.sammy_par_from_endf(isotope='Eu-153')

#psu.sammy_par_from_endf(isotope='U-238',archive=True,verbose_level=1)
#psu.sammy_par_from_endf(isotope='U-235',archive=True,verbose_level=1)


