#!/bin/bash
# Puny BuildTools
# bundle.sh - the game release archiver
# (c) 2026 Stefan Vogt

# bundles your game files and places them in an archive at a given path

#read config file 
source config.sh

echo "bundle.sh 2.3 - the game release archiver"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

while getopts ':t:h' opt; do
  case "$opt" in
    t)
      arg="$OPTARG"
      if [ -d ${OPTARG} ]; then
        echo "Generating '${RELEASE}' archive [...] path: ${OPTARG}"
      
        cp Releases/PlayIF.pdf .
        cp Releases/readme.txt .
        cp Releases/licenses.txt .
        cp ~/FictionTools/Templates/Interpreters/ProDOS_SAM.dsk .
        cp ~/FictionTools/Templates/Interpreters/CPM_Plus_speccy.dsk .
        cp -R Releases/DOS .
        cp -R Releases/Agon .
        cp -R Releases/Next .
        if [[ $ZVERSION == 3 && -f ${STORY}_dragon64.vdk ]] ; then
            cp ~/FictionTools/Templates/Interpreters/dragon64_loader.vdk .
        fi
      
        # bundle disk images
        zip -r ${STORY}_${RELEASE}.zip ${STORY}_speccy.dsk ${STORY}_amiga.adf ${STORY}_atari8bit.atr ${STORY}_c128.d71 ${STORY}_plus4.d64 ${STORY}_c64.d64 ${STORY}_mega65.d81 ${STORY}_cpc_pcw.dsk ${STORY}_atarist.st ${STORY}.z5 ${STORY}_bbc_elk.ssd ${STORY}_MSX.dsk ${STORY}_trs80_m3.dsk ${STORY}_trs80_m4.dsk CPM_Plus_speccy.dsk ${STORY}_mac.dsk ${STORY}_sam_coupe.cpm ProDOS_SAM.dsk PlayIF.pdf readme.txt licenses.txt DOS Agon Next

        # optional release documents, skipped if the author removed them
        if [ -f Releases/walkthrough.txt ] ; then
            cp Releases/walkthrough.txt .
            zip ${STORY}_${RELEASE}.zip walkthrough.txt
            rm walkthrough.txt
        fi
        if [ -f Releases/invisiclues.txt ] ; then
            cp Releases/invisiclues.txt .
            zip ${STORY}_${RELEASE}.zip invisiclues.txt
            rm invisiclues.txt
        fi

        # Apple II (default CP/M two-disk set, single-disk hack, or two-disk z5 hack with .nib)
        if [ -f ${STORY}_apple2.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_apple2.dsk
        fi
        if [ -f ${STORY}_apple2_s1.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_apple2_s1.dsk
        fi
        if [ -f ${STORY}_apple2_s2.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_apple2_s2.dsk
        fi
        if [ -f ${STORY}_apple2_s2.nib ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_apple2_s2.nib
        fi

        # TRS-80 CoCo and Dragon 64 (z3 and z5)
        if [ -f ${STORY}_trs_coco.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_trs_coco.dsk
        fi
        if [ -f ${STORY}_dragon64.vdk ] ; then
            # the z3 Dragon disk needs the separate loader, the z5 disk self-boots
            if [[ $ZVERSION == 3 ]] ; then
                zip ${STORY}_${RELEASE}.zip dragon64_loader.vdk
            fi
            zip ${STORY}_${RELEASE}.zip ${STORY}_dragon64.vdk
        fi

        # Commander X16 (ZIP-mode Ozmoo target)
        if [ -f ${STORY}_x16.zip ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_x16.zip
        fi

        # in case you also build a target with the hidden -b c128_d64.sh switch
        if [ -f ${STORY}_c128.d64 ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_c128.d64
        fi
        # Z-machine version 3 only targets (deprecated) start here
        if [ -f ${STORY}.z3 ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}.z3
        fi
        if [ -f ${STORY}_ti99.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_ti99.dsk
        fi
        if [ -f ${STORY}_oric_1.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_oric_1.dsk
            zip ${STORY}_${RELEASE}.zip ${STORY}_oric_2.dsk
        fi
        if [ -f ${STORY}_vic20_pet.d64 ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_vic20_pet.d64
        fi
        if [ -f ${STORY}_osborne1.cpm ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_osborne1.cpm
        fi
        if [ -f ${STORY}_kaypro.cpm ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_kaypro.cpm
        fi
        if [ -f ${STORY}_decrainbow.cpm ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_decrainbow.cpm
        fi

        #cleanup
        rm PlayIF.pdf
        rm readme.txt
        rm licenses.txt
        rm CPM_Plus_speccy.dsk
        rm -f dragon64_loader.vdk
        rm ProDOS_SAM.dsk
        cp ${STORY}_${RELEASE}.zip ${OPTARG}
        rm -rf DOS
        rm -rf Agon
        rm -rf Next
        rm ${STORY}_${RELEASE}.zip
        echo -e "\nDistribution archive for '${STORY}' successfully generated."
      else
        echo -e "The path you provided does not exist. Operation aborted.\n"
        exit 1
      fi  
      ;;

    h)
      echo "'bundle.sh' creates an archive for distributing your game. It is"
      echo "meant to be run right after you have compiled the disk images for"
      echo "all target systems using the 'all.sh' script. Note that 'bundle.sh',"
      echo "just like 'config.sh' and 'all.sh', is generated upon project dir"
      echo "initialization and needs to be executed from the project dir itself."
      echo "You may want to edit this script once after project init, so it is"
      echo -e "customized to suite your needs. Use it like this:\n"
      echo -e "./bundle.sh [-t path]\n\nwhere [path] stands for the directory you want the archive to be\nplaced, e.g. ./bundle.sh -t ~/Desktop\n"
      exit 0
      ;;

    :)
      echo -e "Option [-t] requires a valid path as an argument.\n\nSynopsis: ./$(basename $0) [-t path] or [-h] for help.\n"
      exit 1
      ;;

    ?)
      echo -e "Invalid command option.\n\nSynopsis: ./$(basename $0) [-t path] or [-h] for help.\n"
      exit 1
      ;;
  esac
done

if [ $OPTIND -eq 1 ]; then echo -e "Nothing to be done. No options passed. Use [-h] for help."; fi
shift "$(($OPTIND -1))"

echo -e
exit 0;
