
@echo off
Echo ex012a.inp >x.x
Echo ex012a.par >>x.x
Echo ex012a.dat >>x.x
Echo.>>x.x
sammy < x.x
Rem # pause
move SAMMY.LPT results\ex012aa.lpt
move SAMMY.ODF results\ex012aa.odf
move SAMMY.PAR results\ex012aa.par
del SAM*.*
del x.x
