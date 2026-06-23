#!/usr/bin/env python3
#
# ERIS
# Z-machine V5/V8 interpreter
# for Atari ST (GEMDOS/TOS)
# Copyright (c) 2026, Stefan Vogt
#
"""gemdos.py - Eris Atari ST disk builder (module 12).

Builds a 720K double-sided GEMDOS/FAT12 disk (2 sides x 80 tracks x 9 sectors x
512 bytes = 1440 sectors). The disk is a NORMAL FAT12 filesystem (it mounts and
copies like any ST/PC disk) that ALSO self-boots: the boot sector carries a
standard BPB plus the assembled boot code (platform/st/boot.s), and one word is
adjusted so the 256-word big-endian sector checksum equals 0x1234, the value TOS
requires to execute a boot sector.

Self-boot model (decided in M7): the disk carries the resident interpreter as a
normal GEMDOS program in an AUTO folder (AUTO\\ERIS.PRG). TOS auto-executes every
AUTO-folder program before the desktop comes up, fullscreen with no GEM, which is
the standard, robust way ST games self-boot. Eris then reads the story from a
file (STORY.DAT in the root) via GEMDOS Fopen/Fread. The disk stays a normal
copyable FAT12 disk throughout.

This is the GEMDOS analogue of ofs.py (the Amiga OFS writer): a from-scratch
FAT12 filesystem (boot sector, two FATs, fixed root directory, the AUTO
subdirectory with its . / .. entries, cluster chains, data area) in portable
stdlib Python, so it runs identically under the Debian-hosted Puny BuildTools.
BPB fields and FAT/directory structures follow the Intel/little-endian
convention ST disks share with MS-DOS; the boot-sector executable checksum is
big-endian (a TOS quirk). test_gemdos.py round-trips a built disk.

Usage:
    gemdos.py --boot BOOT.bin --prg ERIS.PRG --story GAME.z5 --out DISK.st
    gemdos.py --boot BOOT.bin --out DISK.st          (empty bootable disk; M1)
"""
import argparse
import struct
import sys

SECTOR = 512
SECTORS = 1440             # 2 sides * 80 tracks * 9 sectors = 720K
DISK_BYTES = SECTOR * SECTORS
BOOT_CODE_OFFSET = 0x1E    # BPB occupies 0x00..0x1D; boot code follows
EXEC_MAGIC = 0x1234        # TOS executes a boot sector whose word-sum is this

# 720K FAT12 geometry (the standard DD parameters).
BYTES_PER_SECTOR = 512
SECTORS_PER_CLUSTER = 2
RESERVED_SECTORS = 1
NUM_FATS = 2
ROOT_ENTRIES = 112
TOTAL_SECTORS = 1440
MEDIA = 0xF9
SECTORS_PER_FAT = 3
SECTORS_PER_TRACK = 9
NUM_HEADS = 2

CLUSTER_BYTES = SECTOR * SECTORS_PER_CLUSTER                 # 1024
ROOT_DIR_SECTORS = (ROOT_ENTRIES * 32 + SECTOR - 1) // SECTOR  # 7
DATA_START_SECTOR = (RESERVED_SECTORS + NUM_FATS * SECTORS_PER_FAT
                     + ROOT_DIR_SECTORS)                    # 14
TOTAL_CLUSTERS = (TOTAL_SECTORS - DATA_START_SECTOR) // SECTORS_PER_CLUSTER
DIR_ENTRY = 32
FAT12_EOC = 0xFFF          # end-of-cluster-chain marker
FAT12_FREE = 0x000

# A fixed timestamp keeps the build deterministic (FAT date: 1986-06-10, the
# Atari ST's launch year; FAT time: 00:00:00). Format is the MS-DOS packing.
FIXED_DATE = ((1986 - 1980) << 9) | (6 << 5) | 10
FIXED_TIME = 0


def build_boot_sector(boot_code, label):
    if len(boot_code) > SECTOR - BOOT_CODE_OFFSET - 2:
        raise SystemExit("boot code %d bytes does not fit the boot sector"
                         % len(boot_code))
    s = bytearray(SECTOR)

    # 0x00: BRA.S to the boot code at 0x1E (displacement = 0x1E - 2).
    s[0:2] = struct.pack(">H", 0x6000 | (BOOT_CODE_OFFSET - 2))
    # 0x02: OEM / loader name (6 bytes)
    s[2:8] = b"Eris  "[:6]
    # 0x08: disk serial number (3 bytes); fixed for determinism
    s[8:11] = b"\xE2\x15\x00"

    # BPB (little-endian), at the Atari/DOS-standard offsets.
    struct.pack_into("<H", s, 0x0B, BYTES_PER_SECTOR)
    s[0x0D] = SECTORS_PER_CLUSTER
    struct.pack_into("<H", s, 0x0E, RESERVED_SECTORS)
    s[0x10] = NUM_FATS
    struct.pack_into("<H", s, 0x11, ROOT_ENTRIES)
    struct.pack_into("<H", s, 0x13, TOTAL_SECTORS)
    s[0x15] = MEDIA
    struct.pack_into("<H", s, 0x16, SECTORS_PER_FAT)
    struct.pack_into("<H", s, 0x18, SECTORS_PER_TRACK)
    struct.pack_into("<H", s, 0x1A, NUM_HEADS)
    struct.pack_into("<H", s, 0x1C, 0)            # hidden sectors

    # Boot code.
    s[BOOT_CODE_OFFSET:BOOT_CODE_OFFSET + len(boot_code)] = boot_code

    # Make the sector executable: adjust the last word so the big-endian sum of
    # all 256 words equals 0x1234. TOS reads the words big-endian for this.
    s[0x1FE:0x200] = b"\x00\x00"
    total = sum(struct.unpack(">256H", bytes(s))) & 0xFFFF
    adjust = (EXEC_MAGIC - total) & 0xFFFF
    struct.pack_into(">H", s, 0x1FE, adjust)
    if sum(struct.unpack(">256H", bytes(s))) & 0xFFFF != EXEC_MAGIC:
        raise SystemExit("internal: boot sector exec checksum did not verify")
    return s


def _fat12_name(name):
    """Pack 'ERIS.PRG' into the 11-byte 8.3 directory name field (space-padded,
    uppercase). Names are ASCII 8.3 only; no long-name support is needed."""
    if name in (".", ".."):
        base, ext = name, ""
    elif "." in name:
        base, ext = name.split(".", 1)
    else:
        base, ext = name, ""
    base = base.upper()[:8]
    ext = ext.upper()[:3]
    if len(base) > 8 or len(ext) > 3:
        raise SystemExit("gemdos: '%s' is not a valid 8.3 name" % name)
    return (base.ljust(8) + ext.ljust(3)).encode("ascii")


class Fat12Disk:
    """A from-scratch FAT12 image: boot sector, two FAT copies, a fixed-size
    root directory, and a data area of 1024-byte clusters. Files and the AUTO
    subdirectory are allocated cluster chains; the round-trip self-test in
    test_gemdos.py re-parses everything this writes."""

    def __init__(self):
        self.img = bytearray(DISK_BYTES)
        self.fat = [FAT12_FREE] * (TOTAL_CLUSTERS + 2)   # entries 0..N+1
        self.fat[0] = 0xF00 | MEDIA                      # media in cluster 0
        self.fat[1] = FAT12_EOC
        self.next_free = 2

    # --- cluster allocation / chaining -----------------------------------
    def _alloc_chain(self, nbytes):
        """Allocate a cluster chain large enough for nbytes; return the start
        cluster (or 0 for an empty file)."""
        nclusters = (nbytes + CLUSTER_BYTES - 1) // CLUSTER_BYTES
        if nclusters == 0:
            return 0, []
        chain = []
        for _ in range(nclusters):
            if self.next_free > TOTAL_CLUSTERS + 1:
                raise SystemExit("gemdos: disk full")
            chain.append(self.next_free)
            self.next_free += 1
        for i, c in enumerate(chain):
            self.fat[c] = chain[i + 1] if i + 1 < len(chain) else FAT12_EOC
        return chain[0], chain

    def _cluster_offset(self, cluster):
        sec = DATA_START_SECTOR + (cluster - 2) * SECTORS_PER_CLUSTER
        return sec * SECTOR

    def _write_chain(self, chain, data):
        for i, c in enumerate(chain):
            chunk = data[i * CLUSTER_BYTES:(i + 1) * CLUSTER_BYTES]
            off = self._cluster_offset(c)
            self.img[off:off + len(chunk)] = chunk

    # --- directory entries -----------------------------------------------
    def _entry(self, name, attr, start_cluster, size):
        e = bytearray(DIR_ENTRY)
        e[0:11] = _fat12_name(name)
        e[11] = attr
        struct.pack_into("<H", e, 22, FIXED_TIME)
        struct.pack_into("<H", e, 24, FIXED_DATE)
        struct.pack_into("<H", e, 26, start_cluster)
        struct.pack_into("<I", e, 28, size)
        return e

    def add_file_data(self, data):
        """Allocate + write a file's bytes; return its start cluster."""
        start, chain = self._alloc_chain(len(data))
        self._write_chain(chain, data)
        return start

    def add_subdir(self, files):
        """Create a subdirectory (e.g. AUTO) holding `files` = [(name, bytes)].
        Returns the subdir's start cluster. The subdir's data is its directory
        entries, opening with the mandatory '.' (self) and '..' (parent = root,
        cluster 0) entries."""
        # First lay down each file so we know its start cluster, then build the
        # subdir's own directory block, then place that in its cluster.
        child_entries = []
        for name, data in files:
            start = self.add_file_data(data)
            child_entries.append(self._entry(name, 0x20, start, len(data)))

        dir_bytes = bytearray()
        # '.' and '..' get filled in after we know the subdir's own cluster.
        dir_bytes += bytes(DIR_ENTRY)        # placeholder for '.'
        dir_bytes += bytes(DIR_ENTRY)        # placeholder for '..'
        for e in child_entries:
            dir_bytes += e

        sub_start, chain = self._alloc_chain(len(dir_bytes))
        dot = self._entry(".", 0x10, sub_start, 0)
        dotdot = self._entry("..", 0x10, 0, 0)    # parent is the root dir
        dir_bytes[0:DIR_ENTRY] = dot
        dir_bytes[DIR_ENTRY:2 * DIR_ENTRY] = dotdot
        self._write_chain(chain, dir_bytes)
        return sub_start

    # --- emit ------------------------------------------------------------
    def _emit_fat(self):
        raw = bytearray(SECTOR * SECTORS_PER_FAT)
        for n in range(len(self.fat)):
            v = self.fat[n] & 0xFFF
            off = n + (n // 2)        # n * 3 // 2
            if n % 2 == 0:
                raw[off] = v & 0xFF
                raw[off + 1] = (raw[off + 1] & 0xF0) | ((v >> 8) & 0x0F)
            else:
                raw[off] = (raw[off] & 0x0F) | ((v << 4) & 0xF0)
                raw[off + 1] = (v >> 4) & 0xFF
        for copy in range(NUM_FATS):
            base = (RESERVED_SECTORS + copy * SECTORS_PER_FAT) * SECTOR
            self.img[base:base + len(raw)] = raw

    def build(self, boot_code, label, root_entries):
        """root_entries: list of pre-built 32-byte directory entries for the
        root directory (files and the AUTO subdir)."""
        self.img[0:SECTOR] = build_boot_sector(boot_code, label)
        self._emit_fat()
        root_off = (RESERVED_SECTORS + NUM_FATS * SECTORS_PER_FAT) * SECTOR
        blob = b"".join(bytes(e) for e in root_entries)
        if len(blob) > ROOT_DIR_SECTORS * SECTOR:
            raise SystemExit("gemdos: too many root directory entries")
        self.img[root_off:root_off + len(blob)] = blob
        return self.img


# On-disk filenames for the optional DEGAS loading screen. STDISP.PRG picks the
# colour (low-res) or mono blob by Getrez() at boot.
SCRNLO_FILE = "SCRNLO.DAT"     # colour low-res blob (the PI1, palette + screen)
SCRNHI_FILE = "SCRNHI.DAT"     # mono blob (640x400 1-bit, Bayer-dithered from the PI1)
STDISP_FILE = "STDISP.PRG"     # the display program (platform/st/stdisp.c)


def autorun_inf(prog="A:\\START.PRG"):
    """A minimal TOS/EmuTOS desktop .INF whose #Z line auto-runs `prog` when the
    desktop loads. The Infocom z3 interpreter needs GEM (it crashes if run from
    an AUTO folder, which executes before the desktop), so a z3 disk launches it
    from the desktop this way. Lines other than #Z are conventional desktop
    state; #Z is the auto-start application."""
    return (
        "#a000000\r\n#b000000\r\n"
        "#c7770007000600070055200505552220770557075055507703111103\r\n"
        "#d\r\n#E 18 11\r\n"
        "#W 00 00 02 06 26 0C 00 @\r\n"
        "#W 00 00 02 08 26 0C 00 @\r\n"
        "#M 00 00 00 FF A FLOPPY DISK@ @\r\n"
        "#T 00 03 02 FF   TRASH@ @\r\n"
        "#Z 01 " + prog + "@\r\n"
        "#F FF 04   @ *.*@\r\n"
        "#G 03 FF   *.PRG@ @\r\n"
    ).encode("latin-1")


def emit_disk(boot_code, label, root_files, auto_files):
    """root_files / auto_files: lists of (name, bytes). The auto_files are placed
    in an AUTO folder in the given order (TOS runs AUTO programs in directory
    order). Returns the 720K image."""
    d = Fat12Disk()
    root = []
    for name, data in root_files:
        root.append(d._entry(name, 0x20, d.add_file_data(data), len(data)))
    if auto_files:
        auto_start = d.add_subdir(list(auto_files))
        root.append(d._entry("AUTO", 0x10, auto_start, 0))
    return d.build(boot_code, label, root)


def _screen_files(root, auto, screen, stdisp):
    """Add the optional DEGAS loading screen. screen = (colour_blob, mono_blob or
    None) or None. Places AUTO\\STDISP.PRG (runs first, picks by Getrez, shows the
    screen, waits for a key) + the colour blob (SCRNLO.DAT) and, when derived, the
    mono blob (SCRNHI.DAT). Shared by both disk kinds."""
    if screen is None:
        return
    if stdisp is None:
        raise SystemExit("--screen needs --stdisp (the STDISP.PRG display program)")
    colour_blob, mono_blob = screen
    auto.insert(0, (STDISP_FILE, stdisp))     # before the game/terp
    root.append((SCRNLO_FILE, colour_blob))
    if mono_blob is not None:
        root.append((SCRNHI_FILE, mono_blob))


def build_eris_disk(boot_code, label, prg, story, screen=None, stdisp=None):
    """The Eris disk: AUTO\\ERIS.PRG (auto-run) + STORY.DAT, plus an optional
    DEGAS loading screen shown by AUTO\\STDISP.PRG first."""
    root = [("STORY.DAT", story)]
    auto = [("ERIS.PRG", prg)]
    _screen_files(root, auto, screen, stdisp)
    return emit_disk(boot_code, label, root, auto)


def build_infocom_disk(boot_code, label, terp, story, screen=None, stdisp=None):
    """The z3 (Infocom) disk: the interpreter as START.PRG in the root,
    auto-launched from the desktop by DESKTOP.INF/EMUDESK.INF (#Z), reading
    STORY.DAT. (The Infocom terp needs GEM, so it cannot run from AUTO.) An
    optional DEGAS screen is shown by AUTO\\STDISP.PRG before the desktop."""
    inf = autorun_inf("A:\\START.PRG")
    root = [("START.PRG", terp), ("STORY.DAT", story),
            ("DESKTOP.INF", inf), ("EMUDESK.INF", inf)]
    auto = []
    _screen_files(root, auto, screen, stdisp)
    return emit_disk(boot_code, label, root, auto)


def main(argv):
    ap = argparse.ArgumentParser(description="Eris Atari ST GEMDOS builder")
    ap.add_argument("--boot", required=True, help="assembled boot code .bin")
    ap.add_argument("--out", required=True, help="output disk image (.st)")
    ap.add_argument("--prg", help="ERIS.PRG (Eris disk; placed in AUTO\\)")
    ap.add_argument("--infocom", help="Infocom z3 interpreter .prg (builds a z3 "
                                      "disk: placed as START.PRG, desktop auto-run)")
    ap.add_argument("--story", help="the story file, placed as STORY.DAT")
    ap.add_argument("--screen", help="DEGAS PI1 loading screen (shown before the game)")
    ap.add_argument("--stdisp", help="STDISP.PRG display program (needed with --screen)")
    ap.add_argument("--label", default="ERIS", help="volume label")
    args = ap.parse_args(argv)

    boot_code = open(args.boot, "rb").read()
    story  = open(args.story, "rb").read()  if args.story  else None
    stdisp = open(args.stdisp, "rb").read() if args.stdisp else None
    screen = None
    if args.screen:
        import degas
        res, colour_blob = degas.load(args.screen)
        mono_blob = degas.to_mono_blob(res, colour_blob)   # derive the mono version
        screen = (colour_blob, mono_blob)

    if args.infocom:
        if story is None:
            raise SystemExit("a z3 disk needs --story (the z3 game file)")
        terp = open(args.infocom, "rb").read()
        disk = build_infocom_disk(boot_code, args.label, terp, story, screen, stdisp)
        kind = "z3 Infocom disk (START.PRG + STORY.DAT, desktop auto-run)"
    elif args.prg:
        if story is None:
            raise SystemExit("an Eris disk needs --story")
        prg = open(args.prg, "rb").read()
        disk = build_eris_disk(boot_code, args.label, prg, story, screen, stdisp)
        kind = "Eris disk (AUTO\\ERIS.PRG + STORY.DAT)"
    else:
        disk = emit_disk(boot_code, args.label, [], [])   # empty formatted (save disk)
        kind = "empty formatted GEMDOS disk"
    if screen is not None:
        kind += " + DEGAS screen (colour + mono)"

    with open(args.out, "wb") as f:
        f.write(disk)
    print("wrote %s (%d bytes, %d sectors, 720K %s)"
          % (args.out, len(disk), SECTORS, kind))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
