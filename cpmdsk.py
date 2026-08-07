#!/usr/bin/env python3
"""cpmdsk.py - CP/M file inserter for Amstrad CPC and Sinclair ZX
Spectrum +3 disc images. Copyright (c) 2026 Stefan Vogt.

Adds a file to an existing CP/M .DSK image (standard or EXTENDED CPCEMU
format) as a plain, headerless CP/M file, the way a story file has to be
placed on a Vezza disc. It replaces the iDSK call the CPC and +3 builders
used to make: iDSK reads an imported file through a fixed 128K buffer and
silently drops everything beyond it, so any story larger than 131072
bytes ended up truncated on a disc that still looked perfectly valid.

This builder writes as many directory extents as the file needs and
refuses, loudly, to build a disc that cannot hold it, so a story either
lands intact or the build stops.

Both the CPC and the +3 use 1K blocks with a 64 entry directory. DATA
(sector ids &C1..), SYSTEM/vendor (&41..) and IBM (&01..) formats are
recognised and the reserved system tracks are honoured. Output is
deterministic: identical inputs produce an identical image. Stdlib-only
portable Python, no iDSK or cpmtools dependency.

Usage:
  cpmdsk.py game.dsk -i STORY.DAT
  cpmdsk.py game.dsk -i STORY.DAT -i SCRLOAD.COM
  cpmdsk.py game.dsk -i game.z5 -n STORY.DAT
  cpmdsk.py game.dsk -l
"""

import argparse
import os
import sys

VERSION = "1.0"

SECSIZE = 512           # both machines format 512 byte sectors
BLKSIZE = 1024          # CP/M allocation block
RECSIZE = 128           # CP/M logical record
DIRBLOCKS = 2           # 2 blocks of directory = 64 entries
DIRENTS = DIRBLOCKS * BLKSIZE // 32
BLKPEREXT = 16          # allocation slots in one directory entry
RECPEREXT = BLKPEREXT * BLKSIZE // RECSIZE      # 128 records per extent
EMPTY = 0xE5            # deleted / never used directory entry
# Padding for the unused tail of the last block. CP/M traditionally uses
# &1A, but a freshly formatted disc and iDSK both leave zeroes there, and
# keeping zeroes means every disc under the old 128K ceiling comes out
# byte for byte identical to the ones the BuildTools built before.
PAD = 0x00

# first sector id -> number of reserved (system) tracks
FORMATS = {0xC1: ("data", 0), 0x41: ("system", 2), 0x01: ("ibm", 1)}


class DiskFull(Exception):
    pass


class Dsk:
    """A CPCEMU .DSK image with its sectors indexed for in place update."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            self.img = bytearray(f.read())
        if len(self.img) < 0x100:
            raise ValueError("%s is too short to be a .DSK image" % path)

        head = bytes(self.img[:8])
        if head == b"EXTENDED":
            extended = True
        elif head == b"MV - CPC":
            extended = False
        else:
            raise ValueError("%s is not a CPCEMU .DSK image" % path)

        ntracks = self.img[0x30]
        nsides = self.img[0x31]
        if nsides != 1:
            raise ValueError("%s is double sided; only single sided CP/M "
                             "discs are supported" % path)

        # track sizes: one shared value, or a table of 256 byte units
        if extended:
            sizes = [self.img[0x34 + i] * 256 for i in range(ntracks)]
        else:
            sizes = [int.from_bytes(self.img[0x32:0x34], "little")] * ntracks

        self.extended = extended
        self.track_sizes = sizes
        # index every sector as (track, id) -> offset in the image
        self.sectors = {}
        self.spt = 0
        self.ids = []
        off = 0x100
        for trk in range(ntracks):
            if sizes[trk] == 0:         # unformatted track
                continue
            if self.img[off:off + 10] != b"Track-Info":
                raise ValueError("%s: no track header at track %d"
                                 % (path, trk))
            spt = self.img[off + 0x15]
            pos = off + 0x100
            ids = []
            for s in range(spt):
                sit = off + 0x18 + s * 8
                sid, ncode = self.img[sit + 2], self.img[sit + 3]
                length = (int.from_bytes(self.img[sit + 6:sit + 8], "little")
                          if extended else 0) or (128 << ncode)
                if length != SECSIZE:
                    raise ValueError("%s: track %d has %d byte sectors, "
                                     "expected %d" % (path, trk, length,
                                                      SECSIZE))
                self.sectors[(trk, sid)] = pos
                ids.append(sid)
                pos += length
            ids.sort()
            if not self.ids:
                self.spt, self.ids = spt, ids
            elif ids != self.ids:
                raise ValueError("%s: track %d is formatted differently from "
                                 "track 0" % (path, trk))
            off += sizes[trk]

        if not self.ids:
            raise ValueError("%s holds no formatted tracks" % path)

        kind = FORMATS.get(self.ids[0])
        if kind is None:
            raise ValueError("%s: unknown format, first sector id is &%02X"
                             % (path, self.ids[0]))
        self.format, self.reserved = kind
        self.tracks = ntracks
        # total allocation blocks in the data area
        self.blocks = ((ntracks - self.reserved) * self.spt * SECSIZE
                       // BLKSIZE)

    # -- sector and block access -------------------------------------

    def _sector_offset(self, logical):
        """Offset of the n-th logical sector of the data area."""
        trk = self.reserved + logical // self.spt
        sid = self.ids[logical % self.spt]
        try:
            return self.sectors[(trk, sid)]
        except KeyError:
            raise ValueError("%s: sector &%02X of track %d is missing"
                             % (self.path, sid, trk))

    def read_block(self, blk):
        out = bytearray()
        for i in range(BLKSIZE // SECSIZE):
            off = self._sector_offset(blk * (BLKSIZE // SECSIZE) + i)
            out += self.img[off:off + SECSIZE]
        return bytes(out)

    def write_block(self, blk, data):
        assert len(data) == BLKSIZE
        for i in range(BLKSIZE // SECSIZE):
            off = self._sector_offset(blk * (BLKSIZE // SECSIZE) + i)
            self.img[off:off + SECSIZE] = data[i * SECSIZE:(i + 1) * SECSIZE]

    # -- directory ---------------------------------------------------

    def read_dir(self):
        return bytearray(b"".join(self.read_block(b)
                                  for b in range(DIRBLOCKS)))

    def write_dir(self, entries):
        for b in range(DIRBLOCKS):
            self.write_block(b, bytes(entries[b * BLKSIZE:(b + 1) * BLKSIZE]))

    def save(self):
        # An EXTENDED image keeps its track sizes in the table at &34 and
        # the shared size field at &32 is meant to stay zero. iDSK fills it
        # in anyway, so every disc the BuildTools shipped so far carries it.
        # Reproduce that where it is demonstrably true, which keeps output
        # byte for byte identical to the old builds without ever stating a
        # size that some track does not actually have.
        formatted = [s for s in self.track_sizes if s]
        if self.extended and len(set(formatted)) == 1:
            self.img[0x32:0x34] = formatted[0].to_bytes(2, "little")
        with open(self.path, "wb") as f:
            f.write(self.img)


def cpm_name(name):
    """'story.dat' -> (b'STORY   ', b'DAT'), validated."""
    base = os.path.basename(name).upper()
    stem, _, ext = base.partition(".")
    if not stem or len(stem) > 8 or len(ext) > 3:
        raise ValueError("'%s' is not a valid CP/M 8.3 name" % base)
    bad = set(base) & set("<>.,;:=?*[]|/\\\"")
    if bad - {"."}:
        raise ValueError("'%s' holds characters CP/M does not allow" % base)
    return stem.ljust(8).encode("ascii"), ext.ljust(3).encode("ascii")


def used_blocks(entries):
    """Every allocation block claimed by a live directory entry."""
    used = set(range(DIRBLOCKS))
    for i in range(0, len(entries), 32):
        e = entries[i:i + 32]
        if e[0] == EMPTY:
            continue
        used.update(b for b in e[16:32] if b)
    return used


def remove_file(entries, stem, ext, user):
    """Mark any existing copy deleted. Returns True if one was there."""
    found = False
    for i in range(0, len(entries), 32):
        e = entries[i:i + 32]
        if e[0] != user:
            continue
        # attribute bits live in the high bit of each name character
        if (bytes(b & 0x7F for b in e[1:9]) == stem
                and bytes(b & 0x7F for b in e[9:12]) == ext):
            entries[i] = EMPTY
            found = True
    return found


def add_file(dsk, path, name=None, user=0, quiet=False):
    stem, ext = cpm_name(name or path)
    with open(path, "rb") as f:
        data = f.read()

    entries = dsk.read_dir()
    if remove_file(entries, stem, ext, user) and not quiet:
        print("replacing existing %s.%s" % (stem.decode().rstrip(),
                                            ext.decode().rstrip()))

    nblocks = max(1, -(-len(data) // BLKSIZE))
    nextents = max(1, -(-nblocks // BLKPEREXT))

    used = used_blocks(entries)
    free = [b for b in range(dsk.blocks) if b not in used]
    if len(free) < nblocks:
        raise DiskFull("%s needs %d blocks (%d bytes) but only %d of %d "
                       "blocks are free" % (os.path.basename(path), nblocks,
                                            len(data), len(free), dsk.blocks))
    slots = [i for i in range(0, len(entries), 32) if entries[i] == EMPTY]
    if len(slots) < nextents:
        raise DiskFull("%s needs %d directory entries but only %d of %d are "
                       "free" % (os.path.basename(path), nextents, len(slots),
                                 DIRENTS))

    # lowest free block first, which is what CP/M itself would do
    chosen = free[:nblocks]
    for n, blk in enumerate(chosen):
        chunk = data[n * BLKSIZE:(n + 1) * BLKSIZE]
        dsk.write_block(blk, chunk.ljust(BLKSIZE, bytes([PAD])))

    records = max(1, -(-len(data) // RECSIZE))
    for e in range(nextents):
        slot = slots[e]
        rc = min(RECPEREXT, records - e * RECPEREXT)
        al = chosen[e * BLKPEREXT:(e + 1) * BLKPEREXT]
        entry = bytearray(32)
        entry[0] = user
        entry[1:9] = stem
        entry[9:12] = ext
        entry[12] = e & 0x1F            # EX, extent number low
        entry[13] = 0                   # S1
        entry[14] = e >> 5              # S2, extent number high
        entry[15] = rc                  # records held by this extent
        entry[16:16 + len(al)] = bytes(al)
        entries[slot:slot + 32] = entry

    dsk.write_dir(entries)
    if not quiet:
        print("added %s: %d bytes, %d blocks, %d extents"
              % (os.path.basename(path), len(data), nblocks, nextents))


def list_catalog(dsk):
    entries = dsk.read_dir()
    print("%s: %s format, %d tracks, %d blocks"
          % (os.path.basename(dsk.path), dsk.format, dsk.tracks, dsk.blocks))
    files = {}
    for i in range(0, len(entries), 32):
        e = entries[i:i + 32]
        if e[0] == EMPTY:
            continue
        stem = bytes(b & 0x7F for b in e[1:9]).decode("latin1").rstrip()
        ext = bytes(b & 0x7F for b in e[9:12]).decode("latin1").rstrip()
        extent = (e[14] << 5) | (e[12] & 0x1F)
        key = (e[0], "%s.%s" % (stem, ext))
        size, extents = files.get(key, (0, 0))
        files[key] = (max(size, extent * RECPEREXT * RECSIZE + e[15] * RECSIZE),
                      extents + 1)
    for (user, name), (size, extents) in sorted(files.items()):
        print("  user %d  %-12s %7d bytes  %2d extent(s)"
              % (user, name, size, extents))
    print("  %d of %d blocks free"
          % (dsk.blocks - len(used_blocks(entries)), dsk.blocks))


def main():
    # printed before the parser runs, so it shows on -h and on the usage
    # errors argparse handles and exits on by itself
    print("cpmdsk.py v%s - CP/M file inserter for CPC / Spectrum +3"
          % VERSION)
    print("Copyright (c) 2026 Stefan Vogt\n")

    ap = argparse.ArgumentParser(
        description="Add files to an Amstrad CPC or ZX Spectrum +3 CP/M "
                    ".DSK image.")
    ap.add_argument("image", nargs="?", help="the .DSK image to write into")
    ap.add_argument("-i", "--insert", metavar="FILE", action="append",
                    default=[], help="file to add (may be repeated)")
    ap.add_argument("-n", "--name", metavar="NAME",
                    help="name to store the file under, if it should differ")
    ap.add_argument("-u", "--user", type=int, default=0, metavar="N",
                    help="CP/M user number (default 0)")
    ap.add_argument("-l", "--list", action="store_true",
                    help="list the catalog instead of adding anything")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="do not report each file, only problems")
    ap.add_argument("-V", "--version", action="store_true",
                    help="show the version and exit")
    args = ap.parse_args()

    if args.version:
        return
    if not args.image:          # launched bare, so show the help menu
        ap.print_help()
        return

    if args.name and len(args.insert) != 1:
        sys.exit("error: -n names a single file, so use it with one -i")
    if not args.insert and not args.list:
        sys.exit("error: nothing to do, pass -i FILE or -l")
    if not 0 <= args.user <= 15:
        sys.exit("error: CP/M user numbers run from 0 to 15")

    try:
        dsk = Dsk(args.image)
    except (OSError, ValueError) as e:
        sys.exit("error: %s" % e)

    if args.list:
        list_catalog(dsk)
        return

    for path in args.insert:
        try:
            add_file(dsk, path, args.name, args.user, args.quiet)
        except DiskFull as e:
            sys.exit("error: disc full: %s" % e)
        except (OSError, ValueError) as e:
            sys.exit("error: %s" % e)

    try:
        dsk.save()
    except OSError as e:
        sys.exit("error: %s" % e)


if __name__ == "__main__":
    main()
