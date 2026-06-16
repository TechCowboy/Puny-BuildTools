#!/bin/bash
# trs_coco.sh - TRS-80 Color Computer 1/2 disk builder for the Puny
# BuildTools. The Z-machine version comes from the project config:
#   z3 -> overlay the story onto the Infocom Color Computer terp disk
#   z5 -> a self-contained Ceres (CERES.BIN) RS-DOS disk
# Puny BuildTools, (c) 2026 Stefan Vogt

# read the project config (provides ZVERSION, STORY)
source config.sh

echo -e "\ntrs_coco.sh 2.0 - TRS-80 Color Computer 1/2 disk builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

# prebuilt interpreters and templates live here in the BuildTools
INTERP=~/FictionTools/Templates/Interpreters

# Z-machine version check (z3 and z5 are supported)
if [[ $ZVERSION != 3 && $ZVERSION != 5 ]] ; then
    echo -e "This target supports Z-machine versions 3 and 5 only. Operation aborted.\n"
    exit 1
fi

# story file present?
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1
fi

OUT=${STORY}_trs_coco.dsk

# cleanup a previous build
if [ -f ${OUT} ] ; then
    rm ${OUT}
fi

if [[ $ZVERSION == 5 ]] ; then
    # Ceres: a self-contained RS-DOS disk (BASIC loader + interpreter +
    # story). Boots with RUN"CERES".
    mkdsk.py -o ${OUT} --bin ${INTERP}/CERES.BIN --story ${STORY}.z5
else
    # z3: overlay the story onto a copy of the Infocom Color Computer
    # terp disk (proven path, unchanged).
    cp ${INTERP}/trs_coco.dsk .
    mv trs_coco.dsk ${OUT}
    # skip the first two tracks, they have the terp
    dd if=${STORY}.z3 of=${OUT} conv=notrunc bs=1 seek=9216 count=64512 >/dev/null
    # the directory track for loadm + exec
    dd if=${STORY}.z3 of=${OUT} conv=notrunc bs=1 skip=64512 seek=82944 count=69120 >/dev/null
fi

echo -e "Created ${OUT}\n"
