#!/bin/bash
# apple2.sh - Apple II disk builder
# Puny BuildTools, (c) 2026 Stefan Vogt

#read config file 
source config.sh

echo -e "\napple2.sh 3.0 - Apple II disk builder"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1;
fi 

z3_hack_infocom()
{
    echo -e "applying Infocom interpreter z3 hack [...]"
    interlz3 ~/FictionTools/Templates/Interpreters/info3k.bin ${STORY}.z3 ${STORY}_apple2.dsk
    echo -e "Apple II disk with Infocom interpreter successfully built.\n"
}

z5_hack_infocom()
{
    echo -e "applying Infocom interpreter z5 hack [...]"
    interlz3 ~/FictionTools/Templates/Interpreters/info5h.bin ${STORY}.z5 ${STORY}_apple2.dsk
    echo -e "Apple II disks with Infocom interpreter successfully built.\n"
}

default_build()
{
    #copy resources
    cp ~/FictionTools/Templates/Interpreters/apple2_boot.dsk .
    cp ~/FictionTools/Templates/Interpreters/apple2_template.dsk .

    #add files to disk
    cpmcp -f apple-do apple2_template.dsk ${STORY}.z${ZVERSION} 0:story.dat

    #apply naming scheme
    mv apple2_boot.dsk ${STORY}_apple2_s1.dsk
    mv apple2_template.dsk ${STORY}_apple2_s2.dsk

    #show disk contents
    cpmls -f apple-do ${STORY}_apple2_s2.dsk

    echo -e "\nApple II disk Side 1 and Side 2 successfully built."
    echo -e "Boot in a system with CPM card installed.\n"
}

#cleanup 
if [ -f ${STORY}_apple2_s1.dsk ] ; then
    rm ${STORY}_apple2_s1.dsk
fi
if [ -f ${STORY}_apple2_s2.dsk ] ; then
    rm ${STORY}_apple2_s2.dsk
fi
if [ -f ${STORY}_apple2.dsk ] ; then
    rm ${STORY}_apple2.dsk
fi

#is the Infocom interpreter hack set in config?
if [[ -v APPLE2_Z3_INFOCOM ]] ; then
    buildWithHack=true
elif [[ -v APPLE2_Z5_INFOCOM ]] ; then
    buildWithHack=true
else
    buildWithHack=false
fi

zvalue="$ZVERSION"
if [[ $zvalue == 3 && $buildWithHack == true ]] ; then
    z3_hack_infocom
elif [[ $zvalue == 5 && $buildWithHack == true ]] ; then
    z5_hack_infocom
else
    default_build
fi

exit 0