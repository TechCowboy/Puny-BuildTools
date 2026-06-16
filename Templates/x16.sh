#!/bin/bash
# x16.sh - Commander X16 release builder
# Puny BuildTools, (c) 2026 Stefan Vogt

#read config file
source config.sh

echo -e "\nx16.sh 1.0 - Commander X16 release builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1;
fi

#cleanup
if [ -f ${STORY}_x16.zip ] ; then
    rm ${STORY}_x16.zip
fi

#compile
# The Commander X16 is an Ozmoo ZIP-mode target. It produces no disk image and
# does not support a loading screen. Ozmoo writes 'x16_<story>.zip' holding the
# game and the story file. The -df:1 flag removes the intermediate folder.
ruby ~/FictionTools/Templates/Interpreters/Ozmoo/make.rb -t:x16 -ss1:"${LABEL}" -ss2:"Interactive Fiction" -ss3:"${SUBTITLE}" -sw:6 -dm:0 -df:1 ${STORY}.z${ZVERSION}

#rename Ozmoo output to the BuildTools naming scheme (name first, system last)
if ! [ -f x16_${STORY}.zip ] ; then
    echo -e "\nNo output produced. Commander X16 build failed. Operation aborted.\n"
    exit 1
fi
mv x16_${STORY}.zip ${STORY}_x16.zip

echo -e "\nCommander X16 release successfully built.\n"
