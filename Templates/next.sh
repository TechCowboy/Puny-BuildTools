#!/bin/bash
# next.sh - ZX Spectrum Next release builder
# Puny BuildTools, (c) 2026 Stefan Vogt

#read config file 
source config.sh

echo -e "\next.sh 1.0 - ZX Spectrum Next release builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1;
fi 
cp ${STORY}.z${ZVERSION} story.z${ZVERSION}

#pre-cleanup
if [ -d Releases/Next ] ; then
    rm -rf Releases/Next
fi

#copy resources
#place story in temporary directory
mv story.z${ZVERSION} ~/FictionTools/Templates/Interpreters/NextTEMP

#copy content to Release directory
cp -r ~/FictionTools/Templates/Interpreters/NextTEMP Releases/Next

#check for loading screen and arrange resources
if ! [ -f Resources/screen.nxi ] ; then
    echo "No screen.nxi found in /Resources dir."
    echo -e "Spectrum Next release without loading screen successfully built.\n"
else
    cp Resources/screen.nxi Releases/Next
    echo "screen.nxi found in /Resources dir."
    echo -e "Spectrum Next release with loading screen successfully built.\n"
fi
