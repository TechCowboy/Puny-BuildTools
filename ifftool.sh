#!/bin/bash
# ifftool.sh - Commodore Amiga/MEGA65 IFF screen maker
# Puny BuildTools, (c) 2024 Stefan Vogt
# NOTE: Requires ImageMagick at path

echo "ifftool.sh 1.3 - Commodore Amiga/MEGA65 IFF screen maker"
echo -e "Puny BuildTools, (c) 2024 Stefan Vogt\n"

while getopts ':l:m:h' opts
do
    case $opts in
        l)  # 16 color .IFF image (MEGA65 and Amiga)
            if ! [ -f ${OPTARG} ] ; then
                echo -e "File ${OPTARG} not found. Aborting operation.\n"
                exit 1
            fi
            convert ${OPTARG} -resize 320x200\! -colors 16 -depth 4 megascr.ppm
            ppmtoilbm -maxplanes 8 megascr.ppm >screen16.iff
            rm megascr.ppm
            echo
            exit 0
            ;;

        m)  # 256 color .IFF image (MEGA65)
            if ! [ -f ${OPTARG} ] ; then
                echo -e "File ${OPTARG} not found. Aborting operation.\n"
                exit 1;
            fi
            convert ${OPTARG} -resize 320x200\! -colors 256 -depth 8 megascr.ppm
            ppmtoilbm -maxplanes 8 megascr.ppm >screen256.iff
            rm megascr.ppm
            echo
            exit 0
            ;;

        h)
            echo "Converts .PNG to .IFF images in MEGA65 and Amiga resolutions."
            echo -e "The 16 color screen16.iff can be shared by the MEGA65 and Amiga targets.\n"
            echo -e "Switches:"
            echo -e "   [-l image.png] -> 16 color MEGA65/Amiga .IFF 320x200"
            echo -e "   good for importing gfx with reduced palette, e.g. Atari ST .PI1"
            echo -e "   output will be: 'screen16.iff'\n"
            echo -e "   [-m image.png] -> 256 color MEGA65 .IFF 320x200"
            echo -e "   output will be 'screen256.iff'\n"
            ;;

        :)
            echo -e "Option [-${OPTARG}] requires an argument.\nType: $(basename $0) [-h] for help.\n"
            exit
            ;;

        *)
            echo -e "Wrong argument passed.\nType: $(basename $0) [-h] for help.\n"
            exit 0
            ;;
    esac
done

if [ $OPTIND -eq 1 ]; then echo -e "Nothing to be done. No options passed. Use [-h] for help.\n"; fi
shift "$(($OPTIND -1))"
