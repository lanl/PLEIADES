from pleiades import sammyUtils
from pleiades import sammyRunner

eu_nat = sammyUtils.SammyFitConfig('../sammyFitEuNat.ini')

sammyUtils.create_parFile_from_endf(eu_nat,verbose_level=1)


#sammyUtils.sammy_par_from_endf(isotope='Eu-151')
#sammyUtils.sammy_par_from_endf(isotope='Eu-153')




