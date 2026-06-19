#!/bin/bash
# a8bit.sh - Atari 8-bit disk builder
# Puny BuildTools, (c) 2024 Stefan Vogt

#read config file 
source config.sh

 echo -e "\na8bit.sh 3.0 - Atari 8-bit disk builder"
 echo -e "Puny BuildTools, (c) 2024 Stefan Vogt\n"

#story check / arrangement
if ! [ -f ${STORY}.z${ZVERSION} ] ; then
    echo -e "Story file '${STORY}.z${ZVERSION}' not found. Operation aborted.\n"
    exit 1;
fi 

#cleanup 
if [ -f ${STORY}_a8bit.dsk ] ; then
    rm ${STORY}_a8bit.dsk
fi

suffix=_atari8bit

zmachine3()
{
    a8bin=~/FictionTools/atari8bit/a8.bin # Infocom's early terp, 130kb disk image, 40 columns
    printf "Interpreter: Infocom early single-disk [ZIP]\n"
    printf "Columns: 40\n"
    printf "Memory: min. 48kb\n"
    printf "Disk: Single-Sided, Enhanced-Density, 130kb capacity\n"
    printf "Disk Drive: 1050 and XF551\n\n"
    printf "Disk image built. Booting with BASIC enabled/disabled possible.\n"
    cat $a8bin ${STORY}.z3 > ${STORY}${suffix}.atr 2>/dev/null
    size=`ls -l ${STORY}${suffix}.atr | cut -d' ' -f5`
    head --bytes $((133136-$size)) /dev/zero >> ${STORY}${suffix}.atr
    printf "\n" #just for cosmetical reasons
    exit 0
}

zmachine5()
{
    # Varuna - clean-room XZIP (z5) interpreter, demand-paged, runs on a stock
    # 64K XL/XE (a 130XE's/Rambo's extra RAM becomes extra page cache if present).
    # Replaces the Jindroush 128K hack. One story -> two formats, both built by
    # the Varuna disk builder (mkatr.py):
    #   DD 180K - a single disk for FujiNet / SIO2SD / emulators (no swaps).
    #   SD 90K  - every real Atari drive (810/1050/XF551); spanned across disks
    #             with the Atari split marker set when terp+story exceed 90K.
    # The DD build is rejected by the builder if the story would not fit one disk.
    vdir=~/FictionTools/atari8bit         # where the Varuna artifacts are dropped
    boot=$vdir/boot.bin                   # stage-1 boot loader
    bootlab=$vdir/boot.lab
    terp=$vdir/varuna.bin                 # the interpreter
    terplab=$vdir/varuna.lab
    ddout=${STORY}${suffix}_dd.atr
    sdout=${STORY}${suffix}_sd.atr        # spanned -> ${STORY}${suffix}_sd.d1.atr, ...

    printf "Interpreter: Varuna [XZIP], clean-room, demand-paged\n"
    printf "Columns: 40\n"
    printf "Memory: min. 64kb (130XE/Rambo extended RAM used as cache if present)\n"
    printf "Disk: DD 180kb single + SD 90kb (spans across disks if needed)\n"
    printf "Compatibility: DD - XF551, FujiNet/SIO2SD\n"
    printf "               SD - every Atari drive (810/1050/XF551)\n\n"

    # clean any prior z5 output for this story (DD, single SD, spanned SD)
    rm -f ${ddout} ${sdout} ${STORY}${suffix}_sd.d*.atr

    # DD 180K single image (mkatr.py is assumed on PATH)
    if ! mkatr.py --bootable --stage1 "$boot" --stage1-lab "$bootlab" \
            --terp "$terp" --terp-lab "$terplab" --story ${STORY}.z5 \
            --out ${ddout} --density dd ; then
        printf "\nNote: DD 180kb image not built (story too large for one disk).\n"
    fi

    # SD 90K image(s): single disk, or spanned with the split marker set
    if ! mkatr.py --bootable --stage1 "$boot" --stage1-lab "$bootlab" \
            --terp "$terp" --terp-lab "$terplab" --story ${STORY}.z5 \
            --out ${sdout} --density sd ; then
        printf "\nSD build failed. Operation aborted.\n"
        exit 1
    fi

    printf "\nDisk images built. Boot with BASIC disabled.\n\n"
    exit 0
}

# Z-machine version check
zvalue="$ZVERSION"
if [[ $zvalue == 5 ]] ; then
    zmachine5
elif [[ $zvalue == 3 ]] ; then
    zmachine3
fi
