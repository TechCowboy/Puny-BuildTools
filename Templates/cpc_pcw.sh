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
    cp ~/FictionTools/Templates/Interpreters/GAME.BAS .
    cp ./Resources/SCREEN.SCR .
    cp ./Resources/SCREEN.PAL .
    cp ./Resources/SCREEN.BAS .
    if ! cpmdsk.py ${STORY}.dsk --amsdos -i DISC.BAS -i GAME.BAS \
            -i SCREEN.SCR -i SCREEN.PAL -i SCREEN.BAS ; then
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
