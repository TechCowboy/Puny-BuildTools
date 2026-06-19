#!/usr/bin/env python3
"""mkatr.py - Varuna disk builder (design doc module 12 / section 5).

Builds bootable Atari ATR disk images carrying the Varuna boot loader and a
Z-machine v5 story, with the single-disk-awareness split marker.

Standard library only and deterministic output: the same inputs always
produce byte-identical images. This portability is required because the
builder also runs under the Debian-hosted Puny BuildTools at packaging time
(CLAUDE.md), even though all development is on macOS.

Densities (design doc section 5) - TWO formats only:
  sd  90K  - 720 x 128-byte sectors. The physical-release floor: every Atari
             drive (810/1050/XF551) reads SD. Single disk if terp+story fit,
             else SPANNED across disks with the split marker set.
  dd  180K - 720 sectors, 1-3 are 128 byte, 4-720 are 256 byte. For drive
             emulation (FujiNet/SIO2SD). ALWAYS one disk; the build is REJECTED
             if terp+story exceed 180K (never spanned).
  Enhanced density (ED 130K) is intentionally NOT supported: the 1050 reads SD,
  so SD already covers it (design doc section 5).

Key conventions:
  - Sectors 1-3 are ALWAYS 128 bytes (the Atari boot region), even on DD, so
    the OS ROM bootstrap (which reads 128-byte sectors) can load the loader.
    The Varuna boot loader is therefore <= 384 bytes.
  - The pager thinks in 256-byte logical pages regardless of density. A page
    is one DD data sector, or a pair of SD/ED sectors. Story page 0 starts at
    physical sector 4 (right after the boot region).
  - Split marker: Flags 1 (header byte $01) bit 2 (value 4). The builder sets
    it ONLY when the story actually spans more than one disk. A story that
    fits one disk leaves it clear, so the terp never prompts for a swap that
    will not come. The marker lives in the header ($00-$3F), which is outside
    the Z-machine checksum range ($40..end), so setting it never breaks
    @verify.

No em dashes anywhere; plain ASCII only.
"""

import argparse
import os
import sys

PAGE = 256                  # logical page size the pager always sees
BOOT_SECTORS = 3            # sectors 1-3, always 128 bytes
BOOT_SECTOR_SIZE = 128
ATR_MAGIC = 0x0296
SPLIT_MARKER = 0x04         # Flags 1 bit 2

# Story header field offsets (Z-Machine Standards 1.1).
H_VERSION = 0x00
H_FLAGS1 = 0x01
H_HIGHMEM = 0x04            # base of high memory (word)
H_STATIC = 0x0E            # base of static memory (word)
H_SERIAL = 0x12            # serial / release date (6 bytes)
H_LENGTH = 0x1A            # file length (word, units of 4 bytes in v4/5)
H_CHECKSUM = 0x1C          # file checksum (word)


# ---------------------------------------------------------------------------
# Density geometry
# ---------------------------------------------------------------------------
DENSITIES = {
    # name: (total_sectors, data_sector_size). ED (1040 x 128) is deliberately
    # excluded (design doc section 5): the 1050 reads SD, so SD covers it.
    "sd": (720, 128),
    "dd": (720, 256),
}

# Disk-ID label (16 bytes) written into the boot region (sector 3) of every
# disk, so the terp can confirm the right disk is inserted after a swap and
# reject a save/spanned disk from a different story.
DISK_LABEL_OFF = 368        # boot-region byte offset (sector 3, rel offset 112)
DISK_LABEL_MAGIC = b"VDSK"


def geometry(density):
    if density not in DENSITIES:
        raise ValueError("unknown density %r (use sd or dd; ED is not supported)"
                         % density)
    total, data_size = DENSITIES[density]
    return {"density": density, "total_sectors": total, "data_size": data_size}


def disk_label(disk_no, total_disks, info):
    """The 16-byte disk-ID block: magic, disk number, total, story serial +
    checksum (so a disk from another story is detectable)."""
    lab = bytearray(16)
    lab[0:4] = DISK_LABEL_MAGIC
    lab[4] = disk_no
    lab[5] = total_disks
    lab[6:12] = info["serial"]
    lab[12] = (info["checksum"] >> 8) & 0xFF
    lab[13] = info["checksum"] & 0xFF
    return bytes(lab)


def sectors_per_page(geom):
    """Physical sectors that make up one 256-byte logical page."""
    return PAGE // geom["data_size"]   # 1 for DD, 2 for SD/ED


def first_data_sector():
    """Story page 0 starts right after the 3 boot sectors."""
    return BOOT_SECTORS + 1            # sector 4


def disk_capacity_pages(geom):
    """How many 256-byte logical pages of story fit on one disk."""
    data_sectors = geom["total_sectors"] - BOOT_SECTORS
    return data_sectors // sectors_per_page(geom)


def image_size_bytes(geom):
    """Total data byte count of the image (excludes the 16-byte ATR header)."""
    data_sectors = geom["total_sectors"] - BOOT_SECTORS
    return BOOT_SECTORS * BOOT_SECTOR_SIZE + data_sectors * geom["data_size"]


def sector_offset(geom, sector_no):
    """Byte offset within the image data (after the ATR header) of a 1-based
    physical sector. Honors the 128-byte boot-sector convention on DD."""
    if sector_no <= BOOT_SECTORS:
        return (sector_no - 1) * BOOT_SECTOR_SIZE
    base = BOOT_SECTORS * BOOT_SECTOR_SIZE
    return base + (sector_no - BOOT_SECTORS - 1) * geom["data_size"]


# ---------------------------------------------------------------------------
# Story header parsing and the split decision
# ---------------------------------------------------------------------------
def be16(data, off):
    return (data[off] << 8) | data[off + 1]


def parse_story(data):
    version = data[H_VERSION]
    if version != 5:
        raise ValueError("expected a v5 story, got version %d" % version)
    length_words = be16(data, H_LENGTH)
    declared_len = length_words * 4 if length_words else len(data)
    return {
        "version": version,
        "flags1": data[H_FLAGS1],
        "high_base": be16(data, H_HIGHMEM),
        "static_base": be16(data, H_STATIC),
        "declared_len": declared_len,
        "actual_len": len(data),
        "checksum": be16(data, H_CHECKSUM),
        "serial": bytes(data[H_SERIAL:H_SERIAL + 6]),
        "pages": (len(data) + PAGE - 1) // PAGE,
    }


def split_plan(geom, story_pages):
    """Return the per-disk page counts. One entry -> single disk (marker
    clear); more than one -> spanned (marker set). Generic ruleset: disk 1 is
    filled to capacity by lowest address, the rest follow by address."""
    cap = disk_capacity_pages(geom)
    if cap <= 0:
        raise ValueError("density has no room for story data")
    if story_pages <= cap:
        return [story_pages]
    plan = []
    remaining = story_pages
    while remaining > 0:
        take = min(cap, remaining)
        plan.append(take)
        remaining -= take
    return plan


# ---------------------------------------------------------------------------
# Image assembly
# ---------------------------------------------------------------------------
def atr_header(geom):
    size = image_size_bytes(geom)
    assert size % 16 == 0, "image size must be a whole number of paragraphs"
    pars = size // 16
    h = bytearray(16)
    h[0] = ATR_MAGIC & 0xFF
    h[1] = (ATR_MAGIC >> 8) & 0xFF
    h[2] = pars & 0xFF
    h[3] = (pars >> 8) & 0xFF
    h[4] = geom["data_size"] & 0xFF
    h[5] = (geom["data_size"] >> 8) & 0xFF
    h[6] = (pars >> 16) & 0xFF
    # bytes 7-10 CRC (0), 11-15 unused (0).
    return bytes(h)


def build_disk(geom, boot, story_chunk, set_marker, marker_in_chunk):
    """Assemble one ATR image (header + sector data).

    boot          : boot-loader bytes (<= 384) for sectors 1-3.
    story_chunk   : the slice of story bytes that lives on this disk.
    set_marker    : whether to set the split marker on this disk's header copy.
    marker_in_chunk : True if this chunk begins at story page 0 (so the header
                      is present in this chunk and the marker can be applied).
    """
    if len(boot) > BOOT_SECTORS * BOOT_SECTOR_SIZE:
        raise ValueError("boot loader is %d bytes; max is %d (3 boot sectors)"
                         % (len(boot), BOOT_SECTORS * BOOT_SECTOR_SIZE))

    data = bytearray(image_size_bytes(geom))

    # Boot loader into sectors 1-3.
    data[0:len(boot)] = boot

    # Story chunk into the data area starting at the first data sector.
    chunk = bytearray(story_chunk)
    if marker_in_chunk:
        # Apply or clear the split marker on the on-disk header copy.
        if set_marker:
            chunk[H_FLAGS1] |= SPLIT_MARKER
        else:
            chunk[H_FLAGS1] &= ~SPLIT_MARKER & 0xFF
    start = sector_offset(geom, first_data_sector())
    data[start:start + len(chunk)] = chunk

    return atr_header(geom) + bytes(data)


def find_label_offset(lab_path, name, base):
    """Return the file offset of a MADS label (NAME uppercased) given the load
    base address. The .lab format is 'bank<tab>hexaddr<tab>NAME'."""
    name = name.upper()
    for line in open(lab_path):
        parts = line.split()
        if len(parts) >= 3 and parts[2].upper() == name:
            return int(parts[1], 16) - base
    raise ValueError("label %s not found in %s" % (name, lab_path))


def patch_descriptor(terp, terp_lab, spp, ndisks, d1pages, cappages):
    """Patch the spanning descriptor (disk.asm labels) into the terp image,
    which loads at $0700. Lets one terp binary serve any layout."""
    terp = bytearray(terp)

    def at(name):
        return find_label_offset(terp_lab, name, 0x0700)
    terp[at("SPAN_SPP")] = spp & 0xFF
    terp[at("SPAN_NDISKS")] = ndisks & 0xFF
    o = at("SPAN_D1PAGES")
    terp[o] = d1pages & 0xFF
    terp[o + 1] = (d1pages >> 8) & 0xFF
    o = at("SPAN_CAPPAGES")
    terp[o] = cappages & 0xFF
    terp[o + 1] = (cappages >> 8) & 0xFF
    return bytes(terp)


def build_bootable(stage1_path, stage1_lab, terp_path, terp_lab, story_path,
                   out_path, density="dd"):
    """Build the self-booting disk(s): stage-1 in the boot sectors, then the
    interpreter, then the story. DD is always one disk (rejected if it does not
    fit); SD is one disk or, if terp+story exceed it, SPANNED across disks with
    the split marker set. Returns a report dict."""
    geom = geometry(density)
    stage1 = bytearray(open(stage1_path, "rb").read())
    terp = open(terp_path, "rb").read()
    story = open(story_path, "rb").read()
    info = parse_story(story)

    if len(stage1) > BOOT_SECTORS * BOOT_SECTOR_SIZE:
        raise ValueError("stage-1 is %d bytes; max %d" %
                         (len(stage1), BOOT_SECTORS * BOOT_SECTOR_SIZE))

    spp = sectors_per_page(geom)                       # 1 (DD) or 2 (SD)
    dsz = geom["data_size"]
    terp_phys = (len(terp) + dsz - 1) // dsz           # physical sectors for terp
    # disk-1 story capacity is after boot + terp; disk 2+ after boot only.
    d1_cap = (geom["total_sectors"] - BOOT_SECTORS - terp_phys) // spp
    cap = (geom["total_sectors"] - BOOT_SECTORS) // spp
    if d1_cap <= 0:
        raise ValueError("interpreter too large for %s disk 1" % density)
    story_pages = info["pages"]

    if story_pages <= d1_cap:                          # fits one disk
        ndisks, d1pages = 1, story_pages
    elif density == "dd":                              # DD never spans
        raise ValueError(
            "story+terp is %d pages but one DD disk holds %d; DD is single-disk "
            "only - build SD for a spanned release" % (story_pages, d1_cap))
    else:                                              # SD spanning
        d1pages = d1_cap
        remaining = story_pages - d1_cap
        ndisks = 1 + (remaining + cap - 1) // cap
    spanned = ndisks > 1

    # stage-1's load base is in its own boot header (bytes 2-3), not hardwired,
    # so the label offsets stay correct if the loader is relocated.
    s1_base = stage1[2] | (stage1[3] << 8)
    stage1[find_label_offset(stage1_lab, "TERP_NSEC", s1_base)] = terp_phys & 0xFF
    # physical sector size so stage-1 reads 128-byte (SD) or 256-byte (DD) sectors
    sz = find_label_offset(stage1_lab, "TERP_SSZ", s1_base)
    stage1[sz] = dsz & 0xFF
    stage1[sz + 1] = (dsz >> 8) & 0xFF
    terp = patch_descriptor(terp, terp_lab, spp, ndisks, d1pages, cap)

    first_story = BOOT_SECTORS + 1 + terp_phys         # disk-1 story start sector
    base, ext = os.path.splitext(out_path)
    outputs = []

    # --- disk 1: stage-1 + terp + story[0:d1pages] + label ---
    img = bytearray(image_size_bytes(geom))
    img[0:len(stage1)] = stage1
    for i in range(terp_phys):
        o = sector_offset(geom, BOOT_SECTORS + 1 + i)
        img[o:o + dsz] = terp[i * dsz:(i + 1) * dsz].ljust(dsz, b"\0")[:dsz]
    chunk = bytearray(story[0:d1pages * PAGE])
    if spanned:                                        # marker on the header copy
        chunk[H_FLAGS1] |= SPLIT_MARKER
    else:
        chunk[H_FLAGS1] &= ~SPLIT_MARKER & 0xFF
    o = sector_offset(geom, first_story)
    img[o:o + len(chunk)] = chunk
    img[DISK_LABEL_OFF:DISK_LABEL_OFF + 16] = disk_label(1, ndisks, info)
    path1 = out_path if not spanned else "%s.d1%s" % (base, ext)
    with open(path1, "wb") as f:
        f.write(atr_header(geom) + bytes(img))
    outputs.append(path1)

    # --- disk 2+: story chunk + label (no stage-1/terp); story at sector 4 ---
    if spanned:
        offset = d1pages * PAGE
        for d in range(2, ndisks + 1):
            img = bytearray(image_size_bytes(geom))
            chunk = story[offset:offset + cap * PAGE]
            offset += len(chunk)
            o = sector_offset(geom, BOOT_SECTORS + 1)
            img[o:o + len(chunk)] = chunk
            img[DISK_LABEL_OFF:DISK_LABEL_OFF + 16] = disk_label(d, ndisks, info)
            pth = "%s.d%d%s" % (base, d, ext)
            with open(pth, "wb") as f:
                f.write(atr_header(geom) + bytes(img))
            outputs.append(pth)

    return {
        "density": density,
        "terp_bytes": len(terp),
        "terp_sectors": terp_phys,
        "first_story_sector": first_story,
        "story_pages": story_pages,
        "disk1_capacity_pages": d1_cap,
        "capacity_pages": cap,
        "spanned": spanned,
        "ndisks": ndisks,
        "outputs": outputs,
        "output": outputs[0],
    }


def build(story_path, boot_path, out_path, density):
    """Build the image(s) for a story at one density. Returns a report dict."""
    geom = geometry(density)
    story = open(story_path, "rb").read()
    boot = open(boot_path, "rb").read()
    info = parse_story(story)

    plan = split_plan(geom, info["pages"])
    spanned = len(plan) > 1

    # Slice the story by page, disk by disk.
    cap_bytes = disk_capacity_pages(geom) * PAGE
    outputs = []
    base, ext = os.path.splitext(out_path)
    offset = 0
    for i, _pages in enumerate(plan):
        chunk = story[offset:offset + cap_bytes]
        offset += len(chunk)
        img = build_disk(geom, boot, chunk,
                         set_marker=spanned,
                         marker_in_chunk=(i == 0))
        path = out_path if not spanned else "%s.d%d%s" % (base, i + 1, ext)
        with open(path, "wb") as f:
            f.write(img)
        outputs.append(path)

    return {
        "density": density,
        "story_bytes": info["actual_len"],
        "story_pages": info["pages"],
        "capacity_pages": disk_capacity_pages(geom),
        "spanned": spanned,
        "disks": len(plan),
        "marker_set": spanned,
        "outputs": outputs,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        ok = ok and cond
        print(("  ok   " if cond else "  FAIL ") + name)

    # Geometry / capacity sanity (SD + DD only; ED is not supported).
    dd = geometry("dd")
    sd = geometry("sd")
    try:
        geometry("ed")
        check("ED is rejected", False)
    except ValueError:
        check("ED density is rejected (not supported)", True)
    check("DD image size = 3*128 + 717*256",
          image_size_bytes(dd) == 3 * 128 + 717 * 256)
    check("DD image size divisible by 16", image_size_bytes(dd) % 16 == 0)
    check("SD image size = 720*128", image_size_bytes(sd) == 720 * 128)
    check("DD capacity = 717 pages", disk_capacity_pages(dd) == 717)
    check("SD capacity = 358 pages", disk_capacity_pages(sd) == 358)
    check("DD page is 1 sector", sectors_per_page(dd) == 1)
    check("SD page is 2 sectors", sectors_per_page(sd) == 2)

    # Sector offsets: DD sector 4 sits right after the 384-byte boot region.
    check("DD sector 1 at offset 0", sector_offset(dd, 1) == 0)
    check("DD sector 4 at offset 384", sector_offset(dd, 4) == 384)
    check("DD sector 5 at offset 640", sector_offset(dd, 5) == 384 + 256)
    check("SD sector 4 at offset 384", sector_offset(sd, 4) == 384)
    check("SD sector 5 at offset 512", sector_offset(sd, 5) == 384 + 128)

    # Split decision: H2 (538 pages) fits DD (717) but not SD (358).
    check("H2 fits one DD disk", split_plan(dd, 538) == [538])
    check("H2 spans SD disks", len(split_plan(sd, 538)) > 1)
    check("SD plan fills disk 1 to capacity",
          split_plan(sd, 538)[0] == 358)

    # Marker behavior on a synthetic minimal v5 header.
    story = bytearray(PAGE * 4)
    story[H_VERSION] = 5
    story[H_FLAGS1] = 0x00
    boot = bytes([0, 1, 0x00, 0x07, 0x06, 0x07])  # plausible 6-byte boot header

    fits = build_disk(dd, boot, bytes(story), set_marker=False,
                      marker_in_chunk=True)
    flags_off = 16 + sector_offset(dd, first_data_sector()) + H_FLAGS1
    check("single-disk: marker stays clear",
          (fits[flags_off] & SPLIT_MARKER) == 0)

    spanned = build_disk(sd, boot, bytes(story), set_marker=True,
                         marker_in_chunk=True)
    flags_off_sd = 16 + sector_offset(sd, first_data_sector()) + H_FLAGS1
    check("spanned: marker set on disk 1 header",
          (spanned[flags_off_sd] & SPLIT_MARKER) == SPLIT_MARKER)

    # ATR header magic + sector-size field.
    check("ATR magic word", fits[0] == 0x96 and fits[1] == 0x02)
    check("DD sector-size field = 256", fits[4] == 0x00 and fits[5] == 0x01)
    check("SD sector-size field = 128", spanned[4] == 0x80 and spanned[5] == 0x00)

    # Disk-ID label format.
    info = {"serial": b"230101", "checksum": 0xBEEF}
    lab = disk_label(2, 3, info)
    check("disk label magic 'VDSK'", lab[0:4] == b"VDSK")
    check("disk label carries disk_no/total", lab[4] == 2 and lab[5] == 3)
    check("disk label carries serial + checksum",
          lab[6:12] == b"230101" and lab[12] == 0xBE and lab[13] == 0xEF)

    print()
    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    return ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv):
    p = argparse.ArgumentParser(description="Varuna ATR disk builder")
    p.add_argument("--selftest", action="store_true", help="run internal tests")
    p.add_argument("--story", help="path to the .z5 story file")
    p.add_argument("--boot", help="path to the assembled boot loader binary")
    p.add_argument("-o", "--out", help="output .atr path")
    p.add_argument("--density", default="dd", choices=["sd", "dd"])
    p.add_argument("--bootable", action="store_true",
                   help="build a self-booting disk (stage-1 + interpreter + story)")
    p.add_argument("--stage1", help="stage-1 boot binary (with --bootable)")
    p.add_argument("--stage1-lab", help="stage-1 MADS label file (with --bootable)")
    p.add_argument("--terp", help="interpreter binary (with --bootable)")
    p.add_argument("--terp-lab", help="interpreter MADS label file (with --bootable)")
    args = p.parse_args(argv)

    if args.selftest:
        return 0 if selftest() else 1

    if args.bootable:
        if not (args.stage1 and args.stage1_lab and args.terp and args.terp_lab
                and args.story and args.out):
            p.error("--bootable needs --stage1 --stage1-lab --terp --terp-lab "
                    "--story --out")
        rep = build_bootable(args.stage1, args.stage1_lab, args.terp,
                             args.terp_lab, args.story, args.out, args.density)
        print("Varuna bootable disk builder")
        print("  density          : %s" % rep["density"])
        print("  interpreter      : %d bytes, %d sectors" %
              (rep["terp_bytes"], rep["terp_sectors"]))
        print("  story starts at  : sector %d" % rep["first_story_sector"])
        print("  story            : %d pages (disk1 cap %d, disk cap %d)" %
              (rep["story_pages"], rep["disk1_capacity_pages"], rep["capacity_pages"]))
        print("  spanned          : %s (%d disk%s)" %
              (rep["spanned"], rep["ndisks"], "" if rep["ndisks"] == 1 else "s"))
        for o in rep["outputs"]:
            print("  wrote            : %s" % o)
        return 0

    if not (args.story and args.boot and args.out):
        p.error("--story, --boot and --out are required (or use --selftest)")

    rep = build(args.story, args.boot, args.out, args.density)
    print("Varuna disk builder")
    print("  density        : %s" % rep["density"])
    print("  story          : %d bytes, %d logical pages"
          % (rep["story_bytes"], rep["story_pages"]))
    print("  disk capacity  : %d pages" % rep["capacity_pages"])
    print("  spanned        : %s (%d disk%s)"
          % (rep["spanned"], rep["disks"], "" if rep["disks"] == 1 else "s"))
    print("  split marker   : %s" % ("SET" if rep["marker_set"] else "clear"))
    for o in rep["outputs"]:
        print("  wrote          : %s" % o)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
