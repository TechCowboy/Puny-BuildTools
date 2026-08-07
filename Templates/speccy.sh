#!/bin/bash
# speccy.sh - Sinclair ZX Spectrum +3 disk builder
# Puny BuildTools, (c) 2026 Stefan Vogt

#read config file
source config.sh

echo -e "\nspeccy.sh 2.6 - Sinclair ZX Spectrum +3 disk builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1;
fi

#cleanup
if [ -f ${STORY}_speccy.dsk ] ; then
    rm ${STORY}_speccy.dsk
fi

#prepare story
cp ${STORY}.z${ZVERSION} STORY.DAT

# build disc with or without loading screen
if ! [ -f Resources/SCRLOAD.COM ] ; then
    cp ~/FictionTools/Templates/Interpreters/Spec_Vezza.dsk .
    mv Spec_Vezza.dsk ${STORY}_speccy.dsk
    if ! cpmdsk.py ${STORY}_speccy.dsk -i STORY.DAT ; then
        echo -e "\nThe story does not fit on a +3 disc. Operation aborted.\n"
        rm -f STORY.DAT ${STORY}_speccy.dsk
        exit 1
    fi
    echo -e "\nNo SCRLOAD.COM found in /Resources dir."
    echo -e "ZX Spectrum +3 disk without loading screen successfully built.\n"
    rm STORY.DAT
    exit 0
else
    cp ~/FictionTools/Templates/Interpreters/Spec_Vezza_SCR.dsk .
    cp Resources/SCRLOAD.COM .
    mv Spec_Vezza_SCR.dsk ${STORY}_speccy.dsk
    if ! cpmdsk.py ${STORY}_speccy.dsk -i STORY.DAT -i SCRLOAD.COM ; then
        echo -e "\nThe story and the loading screen do not both fit on a +3"
        echo -e "disc. Remove SCRLOAD.COM from /Resources to build without a"
        echo -e "loading screen. Operation aborted.\n"
        rm -f STORY.DAT SCRLOAD.COM ${STORY}_speccy.dsk
        exit 1
    fi
    echo -e "\nSCRLOAD.COM found in /Resources dir."
    echo -e "ZX Spectrum +3 disk with loading screen successfully built.\n"
    rm STORY.DAT
    rm SCRLOAD.COM
    exit 0
fi
