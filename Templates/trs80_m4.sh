#!/bin/bash
# trs80_m4.sh - TRS80 Model 4 disk builder
# Puny BuildTools, (c) 2024 Stefan Vogt

#read config file 
source config.sh

echo -e "\ntrs80_m4.sh 3.0 - TRS80 Model 4 disk builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1
fi 

#cleanup 
if [ -f ${STORY}_trs80_m4.dsk ] ; then
    rm ${STORY}_trs80_m4.dsk
fi

#prepare story 
cp ${STORY}.z${ZVERSION} STORY.DAT

#copy disk template with interpreter
cp ~/FictionTools/Templates/Interpreters/TRS80_M4.dsk .

#write story file on TRS-80 Model 3 (LDOS) disk image
mv TRS80_M4.dsk ${STORY}_trs80_m4.dsk
#wine ~/FictionTools/trswrite.exe -o ${STORY}_trs80_m4.dsk STORY.DAT
trspunytool -x -s -i -ss -td4 -w ${STORY}_trs80_m4.dsk STORY.DAT
printf "\n" # only cosmetic
trspunytool -x -s -i -ss -td4 -w ${STORY}_trs80_m4.dsk ~/FictionTools/Templates/Interpreters/M4ZVM64.CMD 
printf "\n" # only cosmetic
trs80-tool dir ${STORY}_trs80_m4.dsk

#post cleanup
rm STORY.DAT

echo -e "\nTRS80 Model 4 disk successfully built if directory has STORY.DAT and M4ZVM64.CMD.\n"
