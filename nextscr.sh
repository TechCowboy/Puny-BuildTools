#!/bin/bash
# nextscr.sh - Spectrum Next (.NXI) screen maker
# Puny BuildTools, (c) 2026 Stefan Vogt

echo "nextscr.sh 1.0 - Spectrum Next (.NXI) screen maker"
echo -e "Puny BuildTools, (c) 2026 Stefan Vogt\n"

while getopts ':c:h' opts
do
	case $opts in
		c)
            if ! [ -f ${OPTARG} ] ; then
                echo -e "File ${OPTARG} not found. Aborting operation.\n"
                exit 1
            fi
            nextraw -columns ${OPTARG}
            cp *.nxi screen.nxi
            echo
            exit 0
		    ;;

        h) 
            echo "Converts .BMP images to Spectrum Next .NXI format."
            echo -e "Input file requirements: 16-256 colors, 320x256 pixels, 8-bit image.\n"
            echo -e "Usage: [nextscr.sh -c image.bmp] -> 16-256 color .NXI 320x256"
            echo -e "output will be 'screen.nxi'\n"
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
