#!/usr/bin/env python3
"""mkdsk.py - disk image builder for Ceres, the clean-room Z-machine
version 5 interpreter for the Tandy/TRS-80 Color Computer 1/2 and the
Dragon 64. Copyright (c) 2026 Stefan Vogt.

Bundles a prebuilt Ceres binary and a z5 story file into one ready-to-
run game disk:

  CoCo (default): a 35-track single-sided RS-DOS .DSK holding
    CERES.BAS  ASCII BASIC loader: 10 LOADM"CERES":EXEC
    CERES.BIN  the interpreter, a DECB machine-language file
    STORY.DAT  the story, always under this name, written contiguously
               (Ceres reads the FAT granule chain and tolerates
               fragmentation)
  Dragon 64 (--dragon): a single SELF-BOOTING 40-track DragonDOS .VDK
    holding a stage-1 boot loader, the raw CERES-D.BIN engine, and
    STORY.DAT located through a DragonDOS directory extent map; the
    player just types BOOT

The filesystem metadata is kept valid so standard tools can read the
files, and output is deterministic (identical inputs -> identical
image). Stdlib-only portable Python; behaves identically on macOS and
the Debian host the Puny BuildTools run on. No ToolShed/decb dependency.

Usage:
  CoCo:   mkdsk.py -o game.dsk --bin CERES.BIN --story game.z5
  Dragon: mkdsk.py -o game.vdk --dragon --boot dragon_boot.bin \\
                   --bin CERES-D.BIN --story game.z5
  Blank save disk: add --blank (CoCo) or --dragon --blank (Dragon)
"""

import argparse
import sys

SECTOR = 256
SPT = 18                       # sectors per track, numbered 1..18
TRACKS = 35
DIRTRACK = 17
GRAN_SECTORS = 9               # granule = 9 sectors = 2304 bytes
GRAN_BYTES = GRAN_SECTORS * SECTOR
NGRAN = 68                     # granules 0..67, track 17 excluded
DISK_SIZE = TRACKS * SPT * SECTOR

LOADER = b'10 LOADM"CERES":EXEC\r'

# --- Dragon 64 / DragonDOS (M7) ---
DD_TRACKS = 40
DD_SPT = 18                    # sectors per track, numbered 1..18
DD_DIRTRACK = 20               # DragonDOS directory + bitmap
DD_DISK_SIZE = DD_TRACKS * DD_SPT * SECTOR
DD_BOOT_LSN = 2                # boot area = track 0 sectors 3..18
DD_BOOT_SECTORS = 16           # 16 sectors = 4K, loaded to $2600
DD_ENTRY_LEN = 25              # directory entry length
DD_FMT_FILL = 0xE5             # freshly formatted sector fill
# stage-1 loader parameter patch offsets (see src/dragon_boot.asm)
DD_BOOT_PARM = {"nsec": 4, "strk": 5, "ssec": 6}


def vdk_header():
    """A 256-byte VDK header for a 40-track single-sided disk, the
    standard one XRoar reads: 'dk', header length 0x0100,
    version/compat 0x10, source 'X', 40 tracks, 1 side."""
    h = bytearray(256)
    h[0:2] = b"dk"
    h[2:4] = (256).to_bytes(2, "little")   # header length
    h[4] = 0x10                            # VDK version
    h[5] = 0x10                            # VDK compatibility
    h[6] = 0x58                            # source id 'X'
    h[7] = 0x00                            # source version
    h[8] = DD_TRACKS                       # 0x28 = 40
    h[9] = 0x01                            # sides
    return bytes(h)


def dd_lsn_off(lsn):
    """Image offset of a DragonDOS logical sector number."""
    return lsn * SECTOR


class DragonDosDisk:
    """A DragonDOS 40-track single-sided image. Files are allocated as
    contiguous runs of logical sectors, skipping the boot area (track
    0) and the directory track (track 20); a run that straddles track
    20 or exceeds 255 sectors becomes multiple extents, exactly the
    extent map Ceres reads back. Output is wrapped in a VDK for XRoar."""

    def __init__(self):
        self.image = bytearray(bytes([DD_FMT_FILL]) * DD_DISK_SIZE)
        self.used = set()
        # reserve the whole boot track and the directory track
        for s in range(DD_SPT):
            self.used.add(0 * DD_SPT + s)
            self.used.add(DD_DIRTRACK * DD_SPT + s)
        self.entries = []
        self.next_lsn = DD_SPT          # first data sector = track 1 sector 1

    def write_boot(self, data):
        if len(data) > DD_BOOT_SECTORS * SECTOR:
            raise DiskFull("boot stub is %d bytes, max %d"
                           % (len(data), DD_BOOT_SECTORS * SECTOR))
        off = dd_lsn_off(DD_BOOT_LSN)
        self.image[off:off + len(data)] = data

    def alloc(self, data):
        """Place data as contiguous sectors, returning [(lsn, count)]
        extents (at most 4 fit a directory header)."""
        nsec = max(1, -(-len(data) // SECTOR))
        extents = []
        placed = 0
        lsn = self.next_lsn
        while placed < nsec:
            while lsn in self.used:
                lsn += 1
            if lsn >= DD_TRACKS * DD_SPT:
                raise DiskFull("out of sectors")
            start = lsn
            count = 0
            while (placed < nsec and lsn not in self.used
                   and lsn < DD_TRACKS * DD_SPT and count < 255):
                chunk = data[placed * SECTOR:(placed + 1) * SECTOR]
                self.image[lsn * SECTOR:lsn * SECTOR + len(chunk)] = chunk
                self.used.add(lsn)
                placed += 1
                count += 1
                lsn += 1
            extents.append((start, count))
        self.next_lsn = lsn
        return extents

    def add_entry(self, name, ext, extents, total_bytes):
        if len(extents) > 4:
            raise DiskFull(
                "%s.%s needs %d extents; the directory header holds 4 "
                "(continuation entries are not implemented)"
                % (name, ext, len(extents)))
        e = bytearray(DD_ENTRY_LEN)
        e[0] = 0x00                        # attribute: in-use file header
        e[1:9] = name.upper().encode("ascii").ljust(8)
        e[9:12] = ext.upper().encode("ascii").ljust(3)
        for i, (lsn, count) in enumerate(extents):
            e[12 + i * 3] = (lsn >> 8) & 0xFF
            e[12 + i * 3 + 1] = lsn & 0xFF
            e[12 + i * 3 + 2] = count
        # bytes used in the final sector (256 stored as 0, DragonDOS)
        nsec = sum(c for _, c in extents)
        last = total_bytes - (nsec - 1) * SECTOR if total_bytes else 0
        e[24] = last & 0xFF
        self.entries.append(e)

    def _build_bam(self):
        """Track 20 sectors 1-2: free-space bitmap (set bit = free) plus
        geometry. Ceres never reads this; it is here so the image is a
        valid DragonDOS disk for standard tools."""
        bam = bytearray(b"\xff" * SECTOR)
        for lsn in self.used:
            bam[lsn // 8] &= ~(1 << (lsn % 8)) & 0xFF
        bam[0xFC] = DD_TRACKS
        bam[0xFD] = DD_SPT                 # single sided
        bam[0xFE] = (~DD_TRACKS) & 0xFF
        bam[0xFF] = (~DD_SPT) & 0xFF
        off = (DD_DIRTRACK * DD_SPT + 0) * SECTOR   # track 20 sector 1
        self.image[off:off + SECTOR] = bam
        # sector 2 is the bitmap's second half (unused on a 40-track SS
        # disk); leave it as the formatted fill.

    def finalize(self):
        self._build_bam()
        # directory entries: track 20 sectors 3..18, 10 entries/sector
        base_lsn = DD_DIRTRACK * DD_SPT + 2            # sector 3
        # clear the directory region first
        for s in range(2, DD_SPT):
            off = (DD_DIRTRACK * DD_SPT + s) * SECTOR
            self.image[off:off + SECTOR] = b"\x00" * SECTOR
        for i, entry in enumerate(self.entries):
            sec = i // 10
            slot = i % 10
            off = (base_lsn + sec) * SECTOR + slot * DD_ENTRY_LEN
            self.image[off:off + DD_ENTRY_LEN] = entry
        return vdk_header() + bytes(self.image)


def build_dragon(args):
    """Build the single self-booting DragonDOS disk (M7)."""
    if args.blank:
        disk = DragonDosDisk()
        image = disk.finalize()
        with open(args.output, "wb") as f:
            f.write(image)
        print("%s: %d bytes, blank Ceres Dragon save disk"
              % (args.output, len(image)))
        return

    if not args.boot:
        sys.exit("error: --dragon needs --boot (the stage-1 loader)")
    if not args.bin:
        sys.exit("error: --dragon needs --bin (the CERES-D engine image)")

    with open(args.boot, "rb") as f:
        boot = bytearray(f.read())
    if boot[0:2] != b"OS":
        sys.exit("error: %s is not a Dragon boot stub (no 'OS' signature)"
                 % args.boot)
    with open(args.bin, "rb") as f:
        engine = f.read()
    if engine[0:1] == b"\x00":
        sys.exit("error: %s looks like a DECB binary; the Dragon engine "
                 "must be a raw image (assemble with lwasm -r)" % args.bin)

    story = None
    if args.story:
        with open(args.story, "rb") as f:
            story = f.read()
        if not story or story[0] != 5:
            sys.exit("error: %s is not a version 5 story file" % args.story)

    disk = DragonDosDisk()
    try:
        # engine: contiguous, well clear of track 20 so the stage-1
        # loader can read it sequentially without extent logic
        eng_ext = disk.alloc(engine)
        if len(eng_ext) != 1:
            sys.exit("error: engine spans %d extents; it must be one "
                     "contiguous run for the stage-1 loader" % len(eng_ext))
        eng_lsn, eng_count = eng_ext[0]
        eng_trk = eng_lsn // DD_SPT
        eng_sec = eng_lsn % DD_SPT + 1
        disk.add_entry("CERES", "BIN", eng_ext, len(engine))

        # patch the stage-1 loader with the engine's location and length
        boot[DD_BOOT_PARM["nsec"]] = eng_count
        boot[DD_BOOT_PARM["strk"]] = eng_trk
        boot[DD_BOOT_PARM["ssec"]] = eng_sec
        disk.write_boot(boot)

        if story is not None:
            st_ext = disk.alloc(story)
            disk.add_entry("STORY", "DAT", st_ext, len(story))

        image = disk.finalize()
    except DiskFull as e:
        sys.exit("error: disk full: %s" % e)

    with open(args.output, "wb") as f:
        f.write(image)
    print("%s: %d-byte VDK (40 trk SS DragonDOS)" % (args.output, len(image)))
    print("  boot     track 0 sectors 3-18 ('OS' stub -> $2600)")
    print("  CERES.BIN %6d bytes  track %d sector %d, %d sectors -> $2800"
          % (len(engine), eng_trk, eng_sec, eng_count))
    if story is not None:
        ext_str = " ".join("LSN%d+%d" % (l, c) for l, c in st_ext)
        print("  STORY.DAT %6d bytes  extents: %s" % (len(story), ext_str))

# directory entry file types
FT_BASIC = 0
FT_DATA = 1
FT_ML = 2

FLAG_BINARY = 0x00
FLAG_ASCII = 0xFF


def gran_track(g):
    """Granule index to track number (track 17 is the directory)."""
    t = g // 2
    if t >= DIRTRACK:
        t += 1
    return t


def gran_offset(g):
    """Image offset of the first byte of granule g."""
    return (gran_track(g) * SPT + (g % 2) * GRAN_SECTORS) * SECTOR


def sector_offset(track, sector):
    """Image offset of (track, sector), sectors numbered 1..18."""
    return (track * SPT + sector - 1) * SECTOR


class DiskFull(Exception):
    pass


class RsdosDisk:
    """An RS-DOS disk image under construction. Files are allocated
    contiguously from granule 0 upward, so each file occupies one
    unbroken run of granules; the FAT chains are valid regardless."""

    def __init__(self):
        # $FF everywhere matches a freshly formatted (DSKINI) disk:
        # free FAT entries and never-used directory slots are $FF
        self.image = bytearray(b"\xff" * DISK_SIZE)
        self.fat = bytearray(b"\xff" * SECTOR)
        self.entries = []
        self.next_gran = 0

    def add_file(self, name, ext, ftype, flag, data):
        size = len(data)
        ngrans = max(1, -(-size // GRAN_BYTES))
        if self.next_gran + ngrans > NGRAN:
            raise DiskFull(
                "%s.%s needs %d granules, only %d free"
                % (name, ext, ngrans, NGRAN - self.next_gran))
        first = self.next_gran
        self.next_gran += ngrans

        for i in range(ngrans):
            off = gran_offset(first + i)
            chunk = data[i * GRAN_BYTES:(i + 1) * GRAN_BYTES]
            self.image[off:off + len(chunk)] = chunk
            if i < ngrans - 1:
                self.fat[first + i] = first + i + 1

        # last FAT entry: $C0 + sectors used in the final granule
        last_bytes = size - (ngrans - 1) * GRAN_BYTES
        last_sectors = -(-last_bytes // SECTOR)
        self.fat[first + ngrans - 1] = 0xC0 + last_sectors
        # bytes in the last sector; a full final sector is stored as
        # 256 ($0100), the DECB convention, so size round-trips as
        # (sectors - 1) * 256 + last_sector_bytes
        in_last = last_bytes - (last_sectors - 1) * SECTOR if size else 0

        entry = bytearray(32)
        entry[0:8] = name.upper().encode("ascii").ljust(8)
        entry[8:11] = ext.upper().encode("ascii").ljust(3)
        entry[11] = ftype
        entry[12] = flag
        entry[13] = first
        entry[14] = in_last >> 8
        entry[15] = in_last & 0xFF
        self.entries.append(entry)
        return first, ngrans

    def finalize(self):
        if len(self.entries) > 72:
            raise DiskFull("more than 72 directory entries")
        # FAT/GAT: track 17 sector 2
        off = sector_offset(DIRTRACK, 2)
        self.image[off:off + SECTOR] = self.fat
        # directory: track 17 sectors 3..11, 8 entries per sector
        for i, entry in enumerate(self.entries):
            off = sector_offset(DIRTRACK, 3 + i // 8) + (i % 8) * 32
            self.image[off:off + 32] = entry
        return bytes(self.image)


def main():
    ap = argparse.ArgumentParser(
        description="Build an RS-DOS .DSK image for Ceres.")
    ap.add_argument("-o", "--output", required=True,
                    help="output .DSK image")
    ap.add_argument("--bin", metavar="FILE",
                    help="interpreter binary (DECB ML file, CERES.BIN)")
    ap.add_argument("--story", metavar="FILE",
                    help="z5 story file; written as STORY.DAT")
    ap.add_argument("--blank", action="store_true",
                    help="produce an empty formatted disk (a Ceres save disk)")
    ap.add_argument("--dragon", action="store_true",
                    help="build a DragonDOS VDK instead of an RS-DOS .DSK")
    ap.add_argument("--boot", metavar="FILE",
                    help="Dragon stage-1 boot stub (dragon_boot.bin)")
    args = ap.parse_args()

    if args.dragon:
        build_dragon(args)
        return

    if args.blank:
        # An empty, formatted RS-DOS disk: valid GAT/FAT/directory,
        # all data tracks free. Ceres writes its raw save image over
        # the low data tracks; the directory on track 17 is untouched.
        image = RsdosDisk().finalize()
        with open(args.output, "wb") as f:
            f.write(image)
        print("%s: %d bytes, blank Ceres save disk" % (args.output, len(image)))
        return

    if not args.bin:
        sys.exit("error: --bin is required (or use --blank)")

    with open(args.bin, "rb") as f:
        bin_data = f.read()
    if not bin_data or bin_data[0] != 0x00:
        sys.exit("error: %s does not look like a DECB binary "
                 "(missing $00 preamble)" % args.bin)

    story_data = None
    if args.story:
        with open(args.story, "rb") as f:
            story_data = f.read()
        if not story_data or story_data[0] != 5:
            sys.exit("error: %s is not a version 5 story file "
                     "(Ceres is V5-only)" % args.story)

    disk = RsdosDisk()
    files = [("CERES", "BAS", FT_BASIC, FLAG_ASCII, LOADER),
             ("CERES", "BIN", FT_ML, FLAG_BINARY, bin_data)]
    if story_data is not None:
        files.append(("STORY", "DAT", FT_DATA, FLAG_BINARY, story_data))

    try:
        for name, ext, ftype, flag, data in files:
            first, ngrans = disk.add_file(name, ext, ftype, flag, data)
            print("  %-8s.%-3s %7d bytes  granules %d-%d"
                  % (name, ext, len(data), first, first + ngrans - 1))
        image = disk.finalize()
    except DiskFull as e:
        sys.exit("error: disk full: %s" % e)

    with open(args.output, "wb") as f:
        f.write(image)
    print("%s: %d bytes, %d of %d granules free"
          % (args.output, len(image), NGRAN - disk.next_gran, NGRAN))


if __name__ == "__main__":
    main()
