#!/bin/bash
# dragon64.sh - Dragon 64 disk builder for the Puny BuildTools. The
# Z-machine version comes from the project config:
#   z3 -> wrap the Infocom Color Computer terp disk in a DragonDOS VDK
#   z5 -> a SINGLE SELF-BOOTING DragonDOS disk with Ceres (CERES-D.BIN)
# Puny BuildTools, (c) 2024-2026 Stefan Vogt

# read the project config (provides ZVERSION, STORY)
source config.sh

echo -e "\ndragon64.sh 2.0 - Dragon 64 disk builder"
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

OUT=${STORY}_dragon64.vdk

# cleanup a previous build
if [ -f ${OUT} ] ; then
    rm ${OUT}
fi

if [[ $ZVERSION == 5 ]] ; then
    # Ceres: a single self-booting DragonDOS disk. The player types BOOT.
    # dragon_boot.bin is the stage-1 loader, hosted alongside the engine.
    mkdsk.py -o ${OUT} --dragon --boot ${INTERP}/dragon_boot.bin \
        --bin ${INTERP}/CERES-D.BIN --story ${STORY}.z5
else
    # z3: build the Color Computer terp disk, then wrap it in a VDK
    # (DragonDOS header + the CoCo image + byte fill). Proven path.
    TMP=.${STORY}_dragon_tmp.dsk
    cp ${INTERP}/trs_coco.dsk ${TMP}
    # skip the first two tracks, they have the terp
    dd if=${STORY}.z3 of=${TMP} conv=notrunc bs=1 seek=9216 count=64512 >/dev/null
    # the directory track for loadm + exec
    dd if=${STORY}.z3 of=${TMP} conv=notrunc bs=1 skip=64512 seek=82944 count=69120 >/dev/null
    touch ${OUT}
    dd if=${INTERP}/dragondos_header of=${OUT} bs=1G oflag=append conv=notrunc
    dd if=${TMP} of=${OUT} bs=1G oflag=append conv=notrunc
    dd if=${INTERP}/dragon_bytefill of=${OUT} bs=1G oflag=append conv=notrunc
    rm ${TMP}
fi

echo -e "Created ${OUT}\n"
