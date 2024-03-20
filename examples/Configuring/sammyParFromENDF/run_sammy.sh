#%/usr/bin/bash

ARCHIVE=${1:-"Eu-151"}
# create an archive directory
mkdir -p archive/$ARCHIVE
mkdir -p archive/$ARCHIVE/results

ENDFFILE=$(dirname $0)/../../nucDataLibs/resonanceTables/res_endf8.endf
DATFILE="eu153.dat"

# copy files into archive
cp example.inp archive/$ARCHIVE/$ARCHIVE.inp
INPFILE=$ARCHIVE.inp
cp $DATFILE archive/$ARCHIVE/$ARCHIVE.dat
DATFILE=$ARCHIVE.dat

# link the ENDFFILE

cd archive/$ARCHIVE
ln -sf ../../$ENDFFILE $ARCHIVE.endf
ENDFFILE=$ARCHIVE.endf

# run sammy
sammy <<EOF
$INPFILE
$ENDFFILE
$DATFILE

EOF

mv -f SAMMY.LPT results/$ARCHIVE.lpt
# mv -f SAMMY.ODF results/$ARCHIVE.odf
# mv -f SAMMY.PLT results/$ARCHIVE.plt
mv -f SAMNDF.INP results/$ARCHIVE.inp
mv -f SAMNDF.PAR results/$ARCHIVE.par
mv -f SAMQUA.PAR results/$ARCHIVE.qua


# rm -f SAM*.*