#!/bin/bash
# trs80_m3.sh - TRS80 Model 3 disk builder
# Puny BuildTools, (c) 2024 Stefan Vogt

#read config file 
source config.sh

echo -e "\ntrs80_m3.sh 3.0 - TRS80 Model 3 disk builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1
fi

#cleanup 
if [ -f ${STORY}_trs80_m3.dsk ] ; then
    rm ${STORY}_trs80_m3.dsk
fi

#prepare story 
cp ${STORY}.z${ZVERSION} STORY.DAT

#copy disk template with interpreter
cp ~/FictionTools/Templates/Interpreters/TRS80_M3.dsk .

#write story file on TRS-80 Model 3 (LDOS) disk image
mv TRS80_M3.dsk ${STORY}_trs80_m3.dsk
#wine ~/FictionTools/trswrite.exe -o ${STORY}_trs80_m3.dsk STORY.DAT
trspunytool -x -s -i -ss -td4 -w ${STORY}_trs80_m3.dsk STORY.DAT
printf "\n" # only cosmetical
trspunytool -x -s -i -ss -td4 -w ${STORY}_trs80_m3.dsk ~/FictionTools/Templates/Interpreters/M3ZVM.CMD
printf "\n" # only cosmetic
trs80-tool dir ${STORY}_trs80_m3.dsk

#post cleanup
rm STORY.DAT

echo -e "\nTRS80 Model 3 disk successfully built if directory has STORY.DAT and M3ZVM.CMD.\n"
