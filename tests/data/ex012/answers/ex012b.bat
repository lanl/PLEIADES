
@echo off
Echo ex012b.inp >x.x
Echo ex012a.par >>x.x
Echo ex012a.dat >>x.x
Echo.>>x.x
sammy < x.x
Rem # pause
move SAMMY.LPT results\ex012bb.lpt
move SAMMY.ODF results\ex012bb.odf
del SAM*.*

del x.x
