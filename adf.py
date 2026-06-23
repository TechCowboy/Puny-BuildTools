#!/usr/bin/env python3
#
# ERIS
# Z-machine V5/V8 interpreter
# for Commodore Amiga (Kickstart 1.3 or higher)
# Copyright (c) 2026, Stefan Vogt
#
"""adf.py - Eris Amiga disk builder (module 12).

Builds an 880K ADF (standard Amiga 3.5" DD: 2 sides x 80 tracks x 11 sectors
x 512 bytes = 1760 sectors) that self-boots from a custom bootblock via
trackdisk.device, with NO Workbench. Stdlib-only and deterministic, so it runs
identically under the Debian-hosted Puny BuildTools at packaging time.

The bootblock (platform/amiga/boot.s, assembled to a raw .bin) already carries
the 12-byte header ('DOS\\0', a zeroed checksum field, the rootblock word);
this builder places it at sectors 0-1, pads to 1024 bytes, and computes the
Amiga bootblock checksum so Kickstart will accept and execute it.

Later milestones add the resident Eris payload on subsequent tracks and an
optional loading screen ahead of it; M1 produces the bootable banner disk.

Two disk kinds:
  * Eris    (default): a custom-bootblock, no-AmigaDOS disk carrying the resident
            Eris interpreter + story (--boot + --interp + --story).
  * Infocom (--infocom BIN): a genuine bootable AmigaDOS OFS disk carrying
            Infocom's own z3 interpreter, the story as Story.Data, and an
            s/startup-sequence that runs it. Built from scratch via ofs.py, so it
            needs no amitools/xdftool and no disk templates.

Usage:
    adf.py --boot BOOT.bin --interp ERIS.bin --story GAME.z5 --out DISK.adf
    adf.py --infocom amigaz3 --story GAME.z3 --out DISK.adf [--volume NAME]
"""
import argparse
import os
import sys

import iff
import ofs

SECTOR = 512
SECTORS = 1760              # 2 sides * 80 tracks * 11 sectors
DISK_BYTES = SECTOR * SECTORS   # 901120 = 880K
BOOTBLOCK_BYTES = SECTOR * 2    # 1024


def carry_sum(block):
    """32-bit add-with-carry over all 256 longwords of the bootblock (the
    routine Kickstart runs). A valid block sums to 0xFFFFFFFF."""
    assert len(block) == BOOTBLOCK_BYTES
    s = 0
    for i in range(0, BOOTBLOCK_BYTES, 4):
        v = int.from_bytes(block[i:i + 4], "big")
        s += v
        if s > 0xFFFFFFFF:        # carry wraps back into bit 0
            s = (s + 1) & 0xFFFFFFFF
    return s


def bootblock_checksum(block):
    """Checksum value to store at offset 4 (one's complement of the sum taken
    with the field zeroed), so the completed block sums to 0xFFFFFFFF."""
    return (~carry_sum(block)) & 0xFFFFFFFF


# Length fields the loader carries as magic longwords; the builder patches
# them: the interpreter length (sector-rounded, used by the loader's own read)
# and the story length (actual; Eris rounds it for its trackdisk read).
INTERP_LEN_MAGIC = b"\x1A\x2B\x3C\x4D"
STORY_LEN_MAGIC  = b"\x3C\x4D\x5E\x6F"
# Patched IN THE INTERPRETER image (eris.c eris_scrn_off/eris_scrn_len): a SCRN
# loading-screen blob's disk offset and length, or 0/0 on a no-screen disk - so
# the no-screen boot path is byte-for-byte the old one.
SCRN_OFF_MAGIC = b"\x5C\x6D\x7E\x8F"
SCRN_LEN_MAGIC = b"\x6D\x7E\x8F\x9A"


def _roundup(n):
    return (n + SECTOR - 1) // SECTOR * SECTOR


def build(boot_path, interp_path, story_path, screen_path=None):
    with open(boot_path, "rb") as f:
        boot = bytearray(f.read())
    if len(boot) > BOOTBLOCK_BYTES:
        raise SystemExit("boot code %d bytes exceeds the 1024-byte bootblock"
                         % len(boot))
    if boot[0:3] != b"DOS":
        raise SystemExit("boot code does not start with the 'DOS' id")

    with open(interp_path, "rb") as f:
        interp = bytearray(f.read())                 # mutable: we patch the SCRN fields
    with open(story_path, "rb") as f:
        story = f.read()
    scrn = iff.ilbm_to_raw(open(screen_path, "rb").read()) if screen_path else b""

    disk = bytearray(DISK_BYTES)
    interp_rounded = _roundup(len(interp))
    story_off = BOOTBLOCK_BYTES + interp_rounded     # disk byte offset of the story
    scrn_off  = story_off + _roundup(len(story))     # the loading screen follows it
    if scrn_off + _roundup(len(scrn)) > DISK_BYTES:
        raise SystemExit("interpreter + story + screen overflow the 880K disk")

    # Tell the interpreter where the loading screen is (0/0 = none, no-op path).
    so = interp.find(SCRN_OFF_MAGIC)
    sl = interp.find(SCRN_LEN_MAGIC)
    if so < 0 or sl < 0:
        raise SystemExit("interpreter is missing the SCRN_OFF/SCRN_LEN magics")
    interp[so:so + 4] = (scrn_off if scrn else 0).to_bytes(4, "big")
    interp[sl:sl + 4] = len(scrn).to_bytes(4, "big")

    # Patch the loader's length fields (interpreter rounded; story actual).
    i = boot.find(INTERP_LEN_MAGIC)
    j = boot.find(STORY_LEN_MAGIC)
    if i < 0 or j < 0:
        raise SystemExit("loader is missing the INTERP_LEN/STORY_LEN magics")
    boot[i:i + 4] = interp_rounded.to_bytes(4, "big")
    boot[j:j + 4] = len(story).to_bytes(4, "big")

    # Lay it all down: interpreter after the boot sectors, story after it, the
    # optional loading screen last.
    disk[BOOTBLOCK_BYTES:BOOTBLOCK_BYTES + len(interp)] = interp
    disk[story_off:story_off + len(story)] = story
    if scrn:
        disk[scrn_off:scrn_off + len(scrn)] = scrn

    # Bootblock last (it holds the now-patched lengths), with its checksum.
    block = bytearray(BOOTBLOCK_BYTES)
    block[0:len(boot)] = boot
    block[4:8] = b"\x00\x00\x00\x00"
    block[4:8] = bootblock_checksum(block).to_bytes(4, "big")
    if carry_sum(block) != 0xFFFFFFFF:        # what Kickstart will verify
        raise SystemExit("internal: bootblock checksum did not verify")
    disk[0:BOOTBLOCK_BYTES] = block
    return disk


def build_infocom(infocom_path, story_path, volume, screen_path=None, loader_path=None):
    """A bootable AmigaDOS OFS disk: Infocom's z3 interpreter, the story as
    Story.Data, and an s/startup-sequence that runs the interpreter by name. With
    a loading screen (--screen + --loader), the display program runs first and
    waits for a keypress, then the interpreter."""
    with open(infocom_path, "rb") as f:
        interp = f.read()
    with open(story_path, "rb") as f:
        story = f.read()
    name = os.path.basename(infocom_path)
    files = [(name, interp), ("Story.Data", story)]
    startup = name + "\n"                          # just the binary name, no flags
    if screen_path:
        if not loader_path:
            raise SystemExit("--screen needs --loader (the display program)")
        with open(loader_path, "rb") as f:
            loader = f.read()
        raw = iff.ilbm_to_raw(open(screen_path, "rb").read())
        files = [("display", loader), ("screen.raw", raw)] + files
        startup = "display\n" + startup            # show the screen, then the game
    return ofs.build_dos_disk(volume, files, startup.encode("latin-1"))


def main(argv):
    ap = argparse.ArgumentParser(description="Eris Amiga ADF builder")
    ap.add_argument("--out", required=True, help="output .adf path")
    ap.add_argument("--story", required=True, help="the story file")
    ap.add_argument("--boot", help="assembled Eris bootblock .bin (Eris disk)")
    ap.add_argument("--interp", help="Eris interpreter image (Eris disk)")
    ap.add_argument("--infocom", help="Infocom z3 interpreter binary (builds a "
                                      "bootable AmigaDOS z3 disk instead of Eris)")
    ap.add_argument("--volume", help="z3 disk volume name (default: story name)")
    ap.add_argument("--screen", help="IFF ILBM loading screen, shown (dismiss with "
                                     "a click or key) before the game loads")
    ap.add_argument("--loader", help="the display program binary (needed with --screen)")
    args = ap.parse_args(argv)

    if args.infocom:
        volume = args.volume or os.path.splitext(os.path.basename(args.story))[0]
        disk = build_infocom(args.infocom, args.story, volume, args.screen, args.loader)
        kind = "bootable AmigaDOS z3 disk" + (" + loading screen" if args.screen else "")
    else:
        if not args.boot or not args.interp:
            raise SystemExit("an Eris disk needs --boot and --interp "
                             "(or pass --infocom for a z3 disk)")
        disk = build(args.boot, args.interp, args.story, args.screen)
        kind = "Eris bootable ADF" + (" + loading screen" if args.screen else "")

    with open(args.out, "wb") as f:
        f.write(disk)
    print("wrote %s (%d bytes, %d sectors, 880K %s)"
          % (args.out, len(disk), SECTORS, kind))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
