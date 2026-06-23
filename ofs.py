#!/usr/bin/env python3
#
# ERIS
# Z-machine V5/V8 interpreter
# for Commodore Amiga (Kickstart 1.3 or higher)
# Copyright (c) 2026, Stefan Vogt
#
"""ofs.py - minimal Amiga OFS (Old File System) DD disk writer, stdlib only.

Builds a genuine bootable AmigaDOS 880K disk from a handful of root files plus
an s/startup-sequence - enough to ship the Infocom z3 interpreter (an AmigaDOS
binary that reads Story.Data via dos.library). This replaces the amitools/xdftool
dependency and the prebuilt disk templates: the whole filesystem (bootblock,
root, bitmap, file headers + extension blocks, the s/ directory, hash chains,
every checksum) is generated here in portable stdlib Python.

Block formats follow the Amiga Disk File layout. All multi-byte fields are
big-endian; a 512-byte block "checksum" is the value that makes the 128
longwords sum to zero.
"""

SECTOR  = 512
SECTORS = 1760                      # 2 sides * 80 tracks * 11 sectors
BSIZE   = 512
ROOT_BLOCK = SECTORS // 2           # 880 on a DD disk

T_HEADER = 2
T_DATA   = 8
T_LIST   = 16
ST_ROOT    = 1
ST_USERDIR = 2
ST_FILE    = -3                     # stored as 0xFFFFFFFD

HT_SIZE   = BSIZE // 4 - 56         # 72 hash-table / data-pointer slots
DATA_CAP  = BSIZE - 24             # 488 OFS data bytes per data block
FIRST_PTR = HT_SIZE - 1            # array index that holds the first data ptr

# Standard AmigaDOS OFS bootblock code: Kickstart verifies the checksum, then
# calls offset 12; this finds dos.library in ROM, inits it, and returns its base
# in d0 so the OS continues booting (mount, run s/startup-sequence).
#   lea dosName(pc),a1 / jsr -96(a6) [FindResident] / tst.l d0 / beq.s done
#   move.l d0,a0 / move.l 22(a0),a0 [rt_Init] / jsr (a0) / done: rts / "dos.library",0
BOOT_CODE = bytes.fromhex(
    "43fa0014" "4eaeffa0" "4a80" "6708" "2040" "20680016" "4e90" "4e75"
) + b"dos.library\x00"


def _u32(v):
    return (v & 0xFFFFFFFF).to_bytes(4, "big")


def name_hash(name):
    """AmigaDOS (non-international) filename hash -> 0..HT_SIZE-1."""
    h = len(name)
    for ch in name:
        h = (h * 13 + ord(ch.upper())) & 0x7FF
    return h % HT_SIZE


def _checksum(block, off):
    """Value at `off` that makes all 128 longwords sum to 0 (mod 2^32)."""
    b = bytearray(block)
    b[off:off + 4] = b"\x00\x00\x00\x00"
    s = 0
    for i in range(0, BSIZE, 4):
        s = (s + int.from_bytes(b[i:i + 4], "big")) & 0xFFFFFFFF
    return _u32(-s)


def _carry_sum(block):
    """Bootblock checksum: 32-bit add-with-carry; a valid block sums to all-ones."""
    s = 0
    for i in range(0, len(block), 4):
        s += int.from_bytes(block[i:i + 4], "big")
        if s > 0xFFFFFFFF:
            s = (s + 1) & 0xFFFFFFFF
    return s


class _Dir:
    """A directory (root or subdir) collecting entries for hash-chain wiring."""
    def __init__(self, block, name, parent, sec_type):
        self.block = block
        self.name = name
        self.parent = parent
        self.sec_type = sec_type
        self.entries = []            # list of (name, header_block)


class OFSDisk:
    def __init__(self, volume="Eris"):
        self.img = bytearray(SECTOR * SECTORS)
        self.volume = volume[:30]
        self.free = [True] * SECTORS
        self.free[0] = self.free[1] = False          # bootblock
        self.free[ROOT_BLOCK] = False
        self.bitmap_block = self._alloc()             # right after the root
        self.blocks = {}                              # staged block_num -> bytearray
        self.dirs = []                                # _Dir list (root first)
        self.root = _Dir(ROOT_BLOCK, self.volume, 0, ST_ROOT)
        self.dirs.append(self.root)

    def _alloc(self):
        for b in range(2, SECTORS):
            if self.free[b]:
                self.free[b] = False
                return b
        raise SystemExit("ofs: disk full")

    def _stage(self, num, block):
        self.blocks[num] = block

    def _ptr_table(self, block, ptrs):
        for i, p in enumerate(ptrs):
            off = 24 + (FIRST_PTR - i) * 4
            block[off:off + 4] = _u32(p)

    def _data_blocks(self, header_key, data):
        if not data:
            return []
        n = (len(data) + DATA_CAP - 1) // DATA_CAP
        nums = [self._alloc() for _ in range(n)]
        for i in range(n):
            chunk = data[i * DATA_CAP:(i + 1) * DATA_CAP]
            blk = bytearray(SECTOR)
            blk[0:4]   = _u32(T_DATA)
            blk[4:8]   = _u32(header_key)
            blk[8:12]  = _u32(i + 1)
            blk[12:16] = _u32(len(chunk))
            blk[16:20] = _u32(nums[i + 1] if i + 1 < n else 0)
            blk[24:24 + len(chunk)] = chunk
            blk[20:24] = _checksum(blk, 20)
            self._stage(nums[i], blk)
        return nums

    def add_file(self, name, data, parent):
        """Stage a file under directory block `parent`; return its header block."""
        name = name[:30]
        header = self._alloc()
        dnums = self._data_blocks(header, data)
        groups = [dnums[i:i + HT_SIZE] for i in range(0, len(dnums), HT_SIZE)] or [[]]
        exts = [self._alloc() for _ in groups[1:]]

        hdr = bytearray(SECTOR)
        hdr[0:4]   = _u32(T_HEADER)
        hdr[4:8]   = _u32(header)
        hdr[8:12]  = _u32(len(groups[0]))
        hdr[16:20] = _u32(dnums[0] if dnums else 0)
        self._ptr_table(hdr, groups[0])
        hdr[324:328] = _u32(len(data))
        hdr[432]     = len(name)
        hdr[433:433 + len(name)] = name.encode("latin-1")
        hdr[500:504] = _u32(parent)
        hdr[504:508] = _u32(exts[0] if exts else 0)
        hdr[508:512] = _u32(ST_FILE)
        self._stage(header, hdr)

        for k, grp in enumerate(groups[1:]):
            eb = bytearray(SECTOR)
            eb[0:4]   = _u32(T_LIST)
            eb[4:8]   = _u32(exts[k])
            eb[8:12]  = _u32(len(grp))
            self._ptr_table(eb, grp)
            eb[500:504] = _u32(header)                 # parent = the file header
            eb[504:508] = _u32(exts[k + 1] if k + 1 < len(exts) else 0)
            eb[508:512] = _u32(ST_FILE)
            self._stage(exts[k], eb)
        return header

    def reserve_dir(self, name, parent):
        """Reserve a subdirectory block so its children can point at it; the
        block is built in finalize once its entries are known."""
        d = _Dir(self._alloc(), name[:30], parent, ST_USERDIR)
        self.dirs.append(d)
        return d

    def _dir_skeleton(self, d):
        """Stage a directory block's metadata (no hash table yet)."""
        blk = bytearray(SECTOR)
        blk[0:4] = _u32(T_HEADER)
        if d.sec_type == ST_ROOT:
            blk[12:16]   = _u32(HT_SIZE)
            blk[312:316] = _u32(0xFFFFFFFF)            # bm_flag valid
            blk[316:320] = _u32(self.bitmap_block)
        else:
            blk[4:8] = _u32(d.block)
        blk[432] = len(d.name)
        blk[433:433 + len(d.name)] = d.name.encode("latin-1")
        blk[500:504] = _u32(d.parent)
        blk[508:512] = _u32(d.sec_type)
        self._stage(d.block, blk)

    def _wire_dir(self, d):
        """Fill directory `d`'s hash table and each child's hash chain. Every
        child (file header or subdir block) is already staged, so the chain
        pointer can be written into it."""
        blk = self.blocks[d.block]
        buckets = {}
        for name, header in d.entries:
            h = name_hash(name)
            self.blocks[header][496:500] = _u32(buckets.get(h, 0))
            buckets[h] = header
        for h, head in buckets.items():
            blk[24 + h * 4:24 + h * 4 + 4] = _u32(head)

    def _emit_bitmap(self):
        blk = bytearray(SECTOR)
        for word in range((SECTORS - 2 + 31) // 32):
            val = 0
            for bit in range(32):
                b = 2 + word * 32 + bit
                if b < SECTORS and self.free[b]:
                    val |= 1 << bit
            blk[4 + word * 4:4 + word * 4 + 4] = _u32(val)
        blk[0:4] = _checksum(blk, 0)
        self.img[self.bitmap_block * SECTOR:(self.bitmap_block + 1) * SECTOR] = blk

    def _emit_bootblock(self):
        blk = bytearray(BSIZE * 2)
        blk[0:4]  = b"DOS\x00"
        blk[8:12] = _u32(ROOT_BLOCK)
        blk[12:12 + len(BOOT_CODE)] = BOOT_CODE
        blk[4:8]  = _u32(~_carry_sum(blk))
        if _carry_sum(blk) != 0xFFFFFFFF:
            raise SystemExit("ofs: bootblock checksum did not verify")
        self.img[0:BSIZE * 2] = blk

    def finalize(self):
        # stage all directory skeletons, then wire hash tables + chains (needs
        # every file header AND subdir block already staged), then emit with
        # checksums.
        for d in self.dirs:
            self._dir_skeleton(d)
        for d in self.dirs:
            self._wire_dir(d)
        for num, blk in self.blocks.items():
            blk[20:24] = _checksum(blk, 20)
            self.img[num * SECTOR:(num + 1) * SECTOR] = blk
        self._emit_bitmap()
        self._emit_bootblock()
        return self.img


def build_dos_disk(volume, root_files, startup_sequence):
    """root_files: list of (name, bytes). Plus an s/startup-sequence. Returns the
    880K image of a bootable OFS disk."""
    d = OFSDisk(volume)
    for name, data in root_files:
        d.root.entries.append((name, d.add_file(name, data, ROOT_BLOCK)))
    s = d.reserve_dir("s", ROOT_BLOCK)
    ss = d.add_file("startup-sequence", startup_sequence, s.block)
    s.entries.append(("startup-sequence", ss))
    d.root.entries.append(("s", s.block))
    return d.finalize()
