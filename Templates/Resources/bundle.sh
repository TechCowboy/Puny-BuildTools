#!/bin/bash
# Puny BuildTools
# bundle.sh - the game release archiver
# (c) 2026 Stefan Vogt

# bundles your game files and places them in an archive at a given path

#read config file
source config.sh

echo "bundle.sh 2.4 - the game release archiver"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

while getopts ':t:h' opt; do
  case "$opt" in
    t)
      arg="$OPTARG"
      if [ -d ${OPTARG} ]; then
        echo "Generating '${RELEASE}' archive [...] path: ${OPTARG}"

        # Every artifact below is added only if it was actually built. This way
        # a locally customized all.sh that targets a subset of systems still
        # bundles cleanly, without 'name not matched' warnings.

        # --- recommended targets ------------------------------------------
        if [ -f ${STORY}_c64.d64 ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_c64.d64
        fi
        if [ -f ${STORY}_amiga.adf ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_amiga.adf
        fi
        if [ -f ${STORY}_atari8bit.atr ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_atari8bit.atr
        fi
        if [ -f ${STORY}_atarist.st ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_atarist.st
        fi
        if [ -f ${STORY}_cpc_pcw.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_cpc_pcw.dsk
        fi
        if [ -f ${STORY}_mega65.d81 ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_mega65.d81
        fi
        if [ -f ${STORY}_plus4.d64 ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_plus4.d64
        fi
        if [ -f ${STORY}_c128.d71 ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_c128.d71
        fi
        if [ -f ${STORY}_bbc_elk.ssd ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_bbc_elk.ssd
        fi
        if [ -f ${STORY}_MSX.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_MSX.dsk
        fi
        if [ -f ${STORY}_mac.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_mac.dsk
        fi
        if [ -f ${STORY}_trs80_m3.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_trs80_m3.dsk
        fi
        if [ -f ${STORY}_trs80_m4.dsk ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_trs80_m4.dsk
        fi
        # modern PC / bare Z-machine version 5 story file
        if [ -f ${STORY}.z5 ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}.z5
        fi

        # Spectrum +3 ships alongside its CP/M boot disk
        if [ -f ${STORY}_speccy.dsk ] ; then
            cp ~/FictionTools/Templates/Interpreters/CPM_Plus_speccy.dsk .
            zip ${STORY}_${RELEASE}.zip ${STORY}_speccy.dsk CPM_Plus_speccy.dsk
            rm CPM_Plus_speccy.dsk
        fi

        # SAM Coupe ships alongside its ProDOS boot disk
        if [ -f ${STORY}_sam_coupe.cpm ] ; then
            cp ~/FictionTools/Templates/Interpreters/ProDOS_SAM.dsk .
            zip ${STORY}_${RELEASE}.zip ${STORY}_sam_coupe.cpm ProDOS_SAM.dsk
            rm ProDOS_SAM.dsk
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
                cp ~/FictionTools/Templates/Interpreters/dragon64_loader.vdk .
                zip ${STORY}_${RELEASE}.zip dragon64_loader.vdk
                rm dragon64_loader.vdk
            fi
            zip ${STORY}_${RELEASE}.zip ${STORY}_dragon64.vdk
        fi

        # Commander X16 (ZIP-mode Ozmoo target)
        if [ -f ${STORY}_x16.zip ] ; then
            zip ${STORY}_${RELEASE}.zip ${STORY}_x16.zip
        fi

        # folder-output targets (built into the Releases directory)
        if [ -d Releases/DOS ] ; then
            cp -R Releases/DOS .
            zip -r ${STORY}_${RELEASE}.zip DOS
            rm -rf DOS
        fi
        if [ -d Releases/Agon ] ; then
            cp -R Releases/Agon .
            zip -r ${STORY}_${RELEASE}.zip Agon
            rm -rf Agon
        fi
        if [ -d Releases/Next ] ; then
            cp -R Releases/Next .
            zip -r ${STORY}_${RELEASE}.zip Next
            rm -rf Next
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

        # --- release documents, added only if present in the Releases dir ---
        if [ -f Releases/readme.txt ] ; then
            cp Releases/readme.txt .
            zip ${STORY}_${RELEASE}.zip readme.txt
            rm readme.txt
        fi
        if [ -f Releases/licenses.txt ] ; then
            cp Releases/licenses.txt .
            zip ${STORY}_${RELEASE}.zip licenses.txt
            rm licenses.txt
        fi
        if [ -f Releases/PlayIF.pdf ] ; then
            cp Releases/PlayIF.pdf .
            zip ${STORY}_${RELEASE}.zip PlayIF.pdf
            rm PlayIF.pdf
        fi
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

        # deliver the archive to the requested path and clean up
        if [ -f ${STORY}_${RELEASE}.zip ] ; then
            cp ${STORY}_${RELEASE}.zip ${OPTARG}
            rm ${STORY}_${RELEASE}.zip
            echo -e "\nDistribution archive for '${STORY}' successfully generated."
        else
            echo -e "\nNothing was built, so no archive was generated. Operation aborted.\n"
            exit 1
        fi
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
