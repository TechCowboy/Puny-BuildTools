#!/bin/bash
# atari_st.sh - Atari ST disk builder
# Puny BuildTools, (c) 2026 Stefan Vogt
#
# Builds a self-booting 720K GEMDOS/FAT12 disk (.st) for the configured story:
#   z5 / z8 -> Eris (AUTO\ERIS.PRG, self-booting, fullscreen, no desktop)
#   z3      -> Infocom's own ST interpreter, auto-run from the desktop
# Disk images are built from scratch by gemdos.py (stdlib Python, on PATH) - no
# templates, no zip2st. An optional loading screen is taken from
# Resources/screen.pi1 (DEGAS PI1, a Multipaint export). On the ST BOTH disk
# kinds show it via STDISP.PRG, which also auto-derives a mono version for a
# monochrome monitor.

#read config file
source config.sh

echo -e "\natari_st.sh 4.0 - Atari ST disk builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

# Eris binaries (interpreter, boot sector, viewer, Infocom terp) live here.
# Override INTERP only for local testing; default is the BuildTools path.
INTERP=${INTERP:-~/FictionTools/Templates/Interpreters}
SCREEN=Resources/screen.pi1

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1
fi

#cleanup
if [ -f ${STORY}_atarist.st ] ; then
    rm ${STORY}_atarist.st
fi

# z-machine version -> interpreter: z3 = Infocom, z5/z8 = Eris
case ${ZVERSION} in
    3)   mode=infocom ;;
    5|8) mode=eris ;;
    *)   echo -e "Unsupported Z-version '${ZVERSION}'. Eris builds z5/z8; z3 via Infocom.\n"
         exit 1 ;;
esac

# loading screen present? Both disk kinds show it via AUTO\STDISP.PRG.
if [ -f ${SCREEN} ] ; then
    SCREEN_ARGS="--screen ${SCREEN} --stdisp ${INTERP}/stdisp.prg"
    buildWithLoader=true
else
    SCREEN_ARGS=""
    buildWithLoader=false
fi

#build the disk image
if [ ${mode} = infocom ] ; then
    echo "Configuring Z3 Infocom disk."
    gemdos.py --boot "${INTERP}/st_boot.bin" --infocom "${INTERP}/ATARI_Z3.PRG" \
        --story ${STORY}.z${ZVERSION} ${SCREEN_ARGS} --out ${STORY}_atarist.st
else
    echo "Configuring Z${ZVERSION} Eris disk."
    gemdos.py --boot "${INTERP}/st_boot.bin" --prg "${INTERP}/eris.prg" \
        --story ${STORY}.z${ZVERSION} ${SCREEN_ARGS} --out ${STORY}_atarist.st
fi

#post-notification
if ${buildWithLoader} ; then
    echo -e "\n'${SCREEN}' found in Resources."
    echo -e "Atari ST disk with loading screen successfully built: ${STORY}_atarist.st\n"
else
    echo -e "\nNo 'screen.pi1' in Resources."
    echo -e "Atari ST disk without loading screen successfully built: ${STORY}_atarist.st\n"
fi
