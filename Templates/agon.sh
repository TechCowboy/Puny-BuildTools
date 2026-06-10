#!/bin/bash
# agon.sh - Agon Light/Console8 release builder
# Puny BuildTools, (c) 2026 Shawn Sijnstra & Stefan Vogt

#read config file 
source config.sh

echo -e "\nagon.sh 1.1 - Agon Light release builder"
echo -e "Puny BuildTools, (c) 2026 Shawn Sijnstra & Stefan Vogt\n"

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1;
fi 
cp ${STORY}.z${ZVERSION} STORY.DAT

#pre-cleanup
if [ -d Releases/Agon ] ; then
    rm -rf Releases/Agon
fi

#copy resources
#place story in temporary directory
mv STORY.DAT ~/FictionTools/Templates/Interpreters/AgonTEMP

#copy content to Release directory
cp -r ~/FictionTools/Templates/Interpreters/AgonTEMP Releases/Agon

#check for loading screen and arrange resources
if ! [ -f Resources/SCREEN.SCR ] ; then
    echo "No SCREEN.SCR found in /Resources dir."
    echo -e "Agon release without loading screen successfully built.\n"
else
    cp Resources/SCREEN.PAL Releases/Agon
    cp Resources/SCREEN.SCR Releases/Agon
    echo "SCREEN.SCR found in /Resources dir."
    echo -e "Agon release with loading screen successfully built.\n"
fi
