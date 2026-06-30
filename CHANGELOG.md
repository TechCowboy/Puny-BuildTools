# Changelog

## 3.0.1 (Starlit Path minor update)

* fixed Commodore disk builds (C64, Plus/4, MEGA65, C128) that stopped producing output after the Ozmoo 15.7 update, which renamed the colour option -dc:bg:fg to -bgcol/-fgcol
* fixed the Ozmoo exomizer lookup, also broken by the 15.7 update: exomizer is resolved via PATH again instead of a hardcoded path

## 3.0 (Starlit Path)
* Debian Trixie compatibility, various improvements and structural updates
* updated Inform 6 compiler to latest trunk
* added Ceres, a clean-room Z-machine version 5 interpreter (6809 assembly) for the TRS-80 Color Computer 1/2 and the Dragon 64
* TRS CoCo and Dragon 64 promoted from deprecated to full targets, now supporting Z-machine version 5 (via Ceres) in addition to version 3
* split the combined trs_coco_dragon64 builder into separate trs_coco and dragon64 targets
* added mkdsk.py, a dependency-free Python disk image builder for the Ceres targets
* added Varuna, a clean-room Z-machine version 5 (XZIP) interpreter (6502 assembly) for the Atari 8-bit XL/XE, replacing the Jindroush 128K hack: it runs on a stock 64K machine, uses demand-paged virtual memory for stories larger than RAM, and supports international/accented characters and save/restore (extra RAM on a 130XE or Rambo board is used as page cache when present)
* added mkatr.py, a dependency-free Python Atari 8-bit disk builder for the Varuna target, producing a single DD 180K image (XF551 drive, plus FujiNet/SIO2SD) and SD 90K images for every Atari drive (810/1050/XF551), automatically spanning SD across multiple disks for large stories
* added Eris, a clean-room Z-machine version 5 interpreter (one shared core) for the Commodore Amiga (stock A500, Kickstart 1.3) and the Atari ST (stock 520STF), replacing the old template-based Amiga/ST path; the disks are self-booting and need no Workbench or hard disk, and Eris supports international/accented characters and the full range of Z-machine text styles, with save/restore to a separate disk; the Z-machine version 3 path still wraps Infocom's own Amiga and Atari ST interpreters
* added from-scratch Python disk builders for the Amiga (adf.py, an 880K AmigaDOS ADF) and the Atari ST (gemdos.py, a 720K GEMDOS/FAT12 disk), stdlib-only and building bootable disks with no external tools
* Atari ST loading screens: supply one colour DEGAS .pi1 and the builder automatically derives a monochrome .pi3 version (pixel-doubled, Bayer-dithered), so the artwork displays on both colour and monochrome ST monitors
* the Amiga and MEGA65 targets can now share the same screen16.iff loading-screen resource
* ifftool.sh: Amiga/MEGA65 IFF screens are now 320x200 (compatible with both PAL and NTSC; the old 320x256 was PAL-only), and the obsolete Amiga loader-executable feature has been removed (ifftool.sh 1.3)
* dropped the amitools/vamos dependency: the Amiga and Atari ST disks are now built natively in Python, no GitHub pip install required
* removed zip2st (the old Atari ST disk builder) and dropped python3-pip from the dependencies, nothing in the BuildTools needs pip anymore
* Agon Light is now a build target, includes the whole family e.g. Console8
* Commander X16 is now a build target
* ZX Spectrum Next is now a build target (prior only supported through bare z-file)
* nextscr tool for producing ZX Spectrum Next loading screens in .nxi format
* replaced TRS-80 disk builder with Linux-native binary
* TRS-80 Model 3 and 4 targets now supported under MacOS (OrbStack) hosts
* Wine dependency dropped completely, everything runs Linux-native on Debian, WSL2, OrbStack
* added hacked Infocom z5 interpreter for Apple II that needs no CP/M (see hacks for usage)
* the Apple II z5 Infocom hack now auto-builds a two-disk set (with a .nib second disk) for stories too large for one disk
* updated Ozmoo to latest version
* some of the VEZZA binaries have been updated to the latest version 
* updated miscancellous existing build templates 
* updated installation instructions, documentation and pixel guide
* added support to include walkthrough.txt and invisiclues.txt files
* bundle.sh now adds every artifact conditionally, so a customized all.sh that builds only a subset of targets bundles cleanly without 'file not found' warnings (bundle.sh 2.4)

## 2.4 (Unknown Transmission)

* updated Inform 6 compiler to latest trunk
* updated ZAbbrevMaker to newest version 0.11, tool now called zabbrev

## 2.3 (Andromeda Calling)

* various bugfixes in deprecated modules / templates
* all.sh now can be run with switch -d to build deprecated targets
* bundle.sh no longer skips deprecated targets, if found, they are added to the bundle
* bundle.sh cleanup process improved
* ProDOS template updated (SAM Coupe)
* command to install dependencies in installation instructions improved for Debian compatibility
* installation instructions now with Wine32 disclaimer
* installation instructions now allow WSL2/Linux users to opt out Wine32 targets (TRS80 Model 3 and 4)
* revised documentation
* added deprecated target documentation

## 2.2 (Craters of Ganymede)

* fixes an issue that causes BBC/Acorn to not build with >= Python 3.12
* reverting DOS .z5 interpreter to Frotz since Infocom's is too buggy
* fixes issue with DOS launch scripts not properly launching (UTF8 -> CP437)
* bundling the latest Inform work in progress interpreter

## 2.1 (Pillars of Creation)

* removed 'trsread' from binary distribution
* added 'trs80-tool' to binary distribution
* added Infocom's MS-DOS .z5 interpreter version 6J
* TRS-80 modules now use 'trs80-tool' to list the disk directory
* MS-DOS module now builds projects with Infocom interpreters by default (lower memory footprint)
* added OrbStack resource file '.punyorb' for MacOS hosts
* modules using Wine now disabled on MacOS (TRS80 Model 3 & 4), as Wine doesn't work in OrbStack
* updated 'installation' chapter in the documentation
* added 'limitations' chapter to the documentation

## 2.0.1 (Helix Nebula minor update)

* updated Inform compiler binary: fixing zchar_weight 1 instead of 4, plural flags, new /~n flag
* CLI feature: current git version appended to CLI version number
* introducing 'hacks' logic
* hack feature: Apple 2 module can use Infocom interpreter for .z3 target
* hacks chapter added to the documentation

## 2.0 (Helix Nebula)

* project rebranded to 'The Puny BuildTools'
* documentation has been completely rewritten
* simplified and accessible installation process
* host system now Linux 64-bit only, optimized for Debian/Ubuntu
* preconfigured to be compatible with WSL2 (Windows) and OrbStack (MacOS)
* project structure and logic completely redesigned
* version system implemented for all components and modules
* centralized interpreters and disk image templates
* former build scripts heavily improved and refactored to CLI modules
* added 'bundle.sh' release archiver
* configuration file format update
* integrated Vezza interpreter by Shawn Sijnstra as standard for a broad range of targets
* integrated Jindroush's Atari 8-bit interpreter for z5 targets
* fixed problem with Atari 8-bit games not working properly if story file too small
* Atari 8-bit XZIP target now built on improved disk image: Single-Sided, Double-Density, 180kb capacity (1050 and XF551 disk drives)
* countless interpreter and disk template updates (really, I lost track)
* default target architecture now Z-machine version 5 since all available targets do support now both .z5 and .z3: C64, Amiga, ZX Spectrum, Amstrad CPC/PCW, Atari ST, Atari 8-bit, MS-DOS, MSX, BBC Micro/Acorn Electron, C128, Plus/4, Apple II, SAM Coupe, TRS80 Model 3, TRS 80 Model 4, Mega65, classic Macintosh
* the following targets have been deprecated and considered unsupported but are still available for Z-machine v3 only: VIC20/PET, DEC Rainbow, TRS CoCo/Dragon64, Osborne1, Ti99/4a, Oric, Kaypro
* environment variables and paths sourced out in '.punyrc', '.punywsl' and '.pi6rc'
* added dedicated command-line interface 'Puny CLI'
* CLI feature: project initialization
* CLI feature: configuration file editor
* CLI feature: project compilation
* CLI feature: create optimized abbrevations for project (uses ZAbbrevMaker by Henrik Åsman)
* CLI feature: test project (compile and run)
* CLI feature: list target systems and valid build arguments
* CLI feature: version information for all bundled components and modules
* CLI feature: disk image factory
* auto-build disk images with loading screen when pixel artwork is found in the project's 'Resources' folder
* pixel artwork guide for all targets supporting loading screens
* 'An Author's Guide to the Galaxy' as a real-life example of how you would work with the Puny BuildTools
* added 'pi6', a super accessible Inform 6 compiler wrapper, preconfigured to use PunyInform as library (doesn't need a project structure)
* added updater and permissions editor 'Puny-Wan Kenobi'
* Kenobi feature: update local Puny BuildTools installation
* Kenobi feature: check if Puny BuildTools have sufficient permissions
* Kenobi feature: fix permissions of existing Puny BuildTools installations
* added 'ifftool.sh', a Commodore Amiga/MEGA65 IFF screen maker, which converts .PNG images to .IFF images in Amiga and Mega65 resolutions, can also compile .PNG images to executable Amiga binaries
* added 'cpcscr.sh', an Amstrad CPC screen maker, which converts .PNG images to CPC loading screens, palette files and BASIC loaders, using 'martine' as backend
* added 'degaspi1.sh', an Atari ST (Degas .PI1) screen maker, which converts .PNG images to Degas .PI1 format
* added 'makescr.sh' a ZX Spectrum CP/M+ loading screen maker
* 'punycustom' folder feature, which will use files placed in there in favor of Puny library files and extensions
* latest Inform compiler changes from Zarf's branch integrated
* a billion other things I am confident I forgot to mention here

## 1.5

* support for new target systems via additional build scripts: TRS-80 Model 3, TRS-80 Model 4, DEC Rainbow, Osborne 1, Kaypro
* added sanitized disk images for the new target systems
* updated readme template providing loading instructions in Releases dir
* bundled Hibernated 1 Director's Cut source is now R12
* added new targets to bundle script
* updated gitignore sample, fixed Atari 8-bit 2-disk interpreter image ignores, added DOS directory to ignored paths
* appended all.sh script with the new targets
* bumped puny command line utility in FictionTools
* documentation update

## 1.4

* added Atari 8-bit disk creator utility, which allows to bundle games using either the early Infocom interpreter (single disk) or the late Infocom interpreter (two disks) working around the constraints of Atari disks when having a large story file
* added multiple binary template files used by the Atari 8-bit disk creator utility
* added version B, E and G of the late Infocom Atari 8-bit interpreter, the creator utility uses version G by default
* the puny wrapper tool no longer auto-generates Atari 8-bit images as the target has its own build script in the Build directory now (a8bit.sh)
* updated documentation, added Atari 8-bit disk creator usage (see interpreters section)
* updated the Hibernated 1 Director's Cut sources to R10


## 1.3

* the line to include the generic abbreviations in shell.inf is no longer commented, which absolutely made no sense anyway
* moved the abbreviations wrapper script to the build directory
* added ZAbbrevMaker by Henrik Åsman @heasm66 as standard tool for generating optimized story abbreviations
* fixed an error in the H1DC source that originated from a default message suffix change in PunyInform, thanks to @spacehobo for the pull request
* upgrade to Inform 6 compiler v6.36 (dev) as the new version comes with a much better abbreviations logic

## 1.2

* appended Apple II target to z5_all.sh
* added Infocom's Apple IIe z5 interpreter
* optional interpreter Amiga Frotz (z3 and z5 capable) included
* new binary cc1541 in FictionTools

## 1.1

* added script that allows you to build a Z-machine version 5 game for all targets capable of running z5
* own DrawStatusLine routine for z5 games as Puny's routine might cause misbehavior with some of the Infocom interpreters (see shell.inf)
* added templates with Infocom's only Amiga based Z-Machine version 5 interpreter
* upgrade to Inform 6 compiler v6.36 (dev)
* documentation update

## 1.0

* initial release
