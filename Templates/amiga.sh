#!/bin/bash
# amiga.sh - Commodore Amiga disk builder
# Puny BuildTools, (c) 2026 Stefan Vogt
#
# Builds a self-booting Amiga disk (.adf) for the configured story:
#   z5 / z8 -> Eris, our own resident interpreter (self-booting, no Workbench)
#   z3      -> Infocom's own Amiga interpreter on a bootable AmigaDOS disk
# Disk images are built from scratch by adf.py (stdlib Python, on PATH) - no
# templates, no amitools/vamos. An optional loading screen is taken from
# Resources/screen16.iff (IFF ILBM). On a z5/z8 disk Eris shows the screen
# itself; on a z3 disk the 'display' viewer shows it.

#read config file
source config.sh

echo -e "\namiga.sh 4.0 - Commodore Amiga disk builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

# Eris binaries (interpreter, bootblock, viewer, Infocom terp) live here. Override
# INTERP only for local testing; the default is the established BuildTools path.
INTERP=${INTERP:-~/FictionTools/Templates/Interpreters}
SCREEN=Resources/screen16.iff

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1
fi

#cleanup
if [ -f ${STORY}_amiga.adf ] ; then
    rm ${STORY}_amiga.adf
fi

# z-machine version -> interpreter: z3 = Infocom, z5/z8 = Eris
case ${ZVERSION} in
    3)   mode=infocom ;;
    5|8) mode=eris ;;
    *)   echo -e "Unsupported Z-version '${ZVERSION}'. Eris builds z5/z8; z3 via Infocom.\n"
         exit 1 ;;
esac

# loading screen present?
if [ -f ${SCREEN} ] ; then
    buildWithLoader=true
else
    buildWithLoader=false
fi

#build the disk image
if [ ${mode} = infocom ] ; then
    if ${buildWithLoader} ; then
        echo "Configuring Z3 Infocom disk with loading screen."
        adf.py --infocom "${INTERP}/amigaz3" --story ${STORY}.z${ZVERSION} \
            --screen ${SCREEN} --loader "${INTERP}/display" \
            --out ${STORY}_amiga.adf
    else
        echo "Configuring Z3 Infocom disk."
        adf.py --infocom "${INTERP}/amigaz3" --story ${STORY}.z${ZVERSION} \
            --out ${STORY}_amiga.adf
    fi
else
    if ${buildWithLoader} ; then
        echo "Configuring Z${ZVERSION} Eris disk with loading screen."
        adf.py --boot "${INTERP}/amiga_boot.bin" --interp "${INTERP}/eris_interp.bin" \
            --story ${STORY}.z${ZVERSION} --screen ${SCREEN} \
            --out ${STORY}_amiga.adf
    else
        echo "Configuring Z${ZVERSION} Eris disk."
        adf.py --boot "${INTERP}/amiga_boot.bin" --interp "${INTERP}/eris_interp.bin" \
            --story ${STORY}.z${ZVERSION} --out ${STORY}_amiga.adf
    fi
fi

#post-notification
if ${buildWithLoader} ; then
    echo -e "\n'${SCREEN}' found in Resources."
    echo -e "Commodore Amiga disk with loading screen successfully built: ${STORY}_amiga.adf\n"
else
    echo -e "\nNo 'screen16.iff' in Resources."
    echo -e "Commodore Amiga disk without loading screen successfully built: ${STORY}_amiga.adf\n"
fi
