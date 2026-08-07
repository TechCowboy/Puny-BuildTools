#!/bin/bash
# cpc_pcw.sh - Amstrad CPC/PCW disc builder
# Puny BuildTools, (c) 2026 Stefan Vogt

#read config file
source config.sh

echo -e "\ncpc_pcw.sh 2.6 - Amstrad CPC/PCW disc builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1;
fi 

#cleanup 
if [ -f ${STORY}_cpc_pcw.dsk ] ; then
    rm ${STORY}_cpc_pcw.dsk
fi

#copy resources
cp ~/FictionTools/Templates/Interpreters/cpc_vezza.dsk .
mv cpc_vezza.dsk ${STORY}.dsk

#prepare story 
cp ${STORY}.z${ZVERSION} STORY.DAT

#place story on disk image
if ! cpmdsk.py ${STORY}.dsk -i STORY.DAT ; then
    echo -e "\nThe story does not fit on a CPC/PCW disc. The CP/M system"
    echo -e "files and the interpreter take up a large part of it."
    echo -e "Operation aborted.\n"
    rm -f STORY.DAT ${STORY}.dsk
    exit 1
fi

# build disc with or without loading screen
if ! [ -f Resources/SCREEN.SCR ] ; then
    mv ${STORY}.dsk ${STORY}_cpc_pcw.dsk
    echo -e "\nNo SCREEN.SCR, SCREEN.PAL and SCREEN.BAS found in /Resources dir."
    echo -e "CPC/PCW disc without loading screen successfully built.\n"
    rm STORY.DAT
else
    cp ~/FictionTools/Templates/Interpreters/DISC.BAS .
    idsk ${STORY}.dsk -i DISC.BAS
    cp ~/FictionTools/Templates/Interpreters/GAME.BAS .
    idsk ${STORY}.dsk -i GAME.BAS
    cp ./Resources/SCREEN.SCR .
    idsk ${STORY}.dsk -i SCREEN.SCR #-t 1 -c c000
    cp ./Resources/SCREEN.PAL .
    idsk ${STORY}.dsk -i SCREEN.PAL #-t 1 -c a000
    cp ./Resources/SCREEN.BAS .
    idsk ${STORY}.dsk -i SCREEN.BAS #-t 1 -c a000
    # iDSK formats extra tracks when it runs out of room instead of saying
    # so. A 3" disc holds 40 tracks, so a grown image means the loading
    # screen did not really fit and the disc would be unreliable.
    if [ $(stat -c%s ${STORY}.dsk) -ne $(stat -c%s \
            ~/FictionTools/Templates/Interpreters/cpc_vezza.dsk) ] ; then
        echo -e "\nThe story and the loading screen do not both fit on a"
        echo -e "CPC/PCW disc. Remove SCREEN.SCR from /Resources to build"
        echo -e "without a loading screen. Operation aborted.\n"
        rm -f STORY.DAT DISC.BAS GAME.BAS SCREEN.BAS SCREEN.SCR SCREEN.PAL
        rm -f ${STORY}.dsk
        exit 1
    fi
    echo -e "\nSCREEN.SCR, SCREEN.PAL and SCREEN.BAS found in /Resources dir."
    echo -e "CPC/PCW disc with loading screen successfully built.\n"
    mv ${STORY}.dsk ${STORY}_cpc_pcw.dsk
    rm STORY.DAT
    rm DISC.BAS
    rm GAME.BAS
    rm SCREEN.BAS
    rm SCREEN.SCR
    rm SCREEN.PAL
fi
