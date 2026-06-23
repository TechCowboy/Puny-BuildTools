#!/usr/bin/env python3
#
# ERIS
# Z-machine V5/V8 interpreter
# for Commodore Amiga (Kickstart 1.3 or higher)
# Copyright (c) 2026, Stefan Vogt
#
"""iff.py - decode an IFF ILBM loading screen to a tiny raw planar blob.

The Amiga loaders never parse images (design rule); this does it in stdlib
Python at build time. An ILBM (320x200, 16 or 32 colours, optionally ByteRun1
packed) is turned into "ErisSCRN": a small header, an Amiga 4-bit palette, then
de-interleaved planar bitplane data the loader can DMA straight onto a screen.

Raw layout (big-endian), what the display loader reads:
    0  4  'S','C','R','N'
    4  2  width      (pixels)
    6  2  height     (rows)
    8  2  depth      (number of bitplanes)
   10  2  row_bytes  ((width+15)//16*2)
   12  2  ncolours
   14  ncolours*2  palette, one 0x0RGB word per colour (4 bits/gun)
   ..  depth*(row_bytes*height) bytes  planar bitplanes (plane 0 first)
"""
import struct


def _chunks(data):
    """Yield (id, payload) for each chunk inside a FORM ILBM."""
    if data[0:4] != b"FORM" or data[8:12] != b"ILBM":
        raise SystemExit("iff: not an IFF ILBM")
    i = 12
    end = 8 + struct.unpack(">I", data[4:8])[0]
    while i + 8 <= end:
        cid = data[i:i + 4]
        size = struct.unpack(">I", data[i + 4:i + 8])[0]
        yield cid, data[i + 8:i + 8 + size]
        i += 8 + size + (size & 1)            # chunks are word-aligned


def _unpack_byterun1(data, want):
    """Decompress an ILBM ByteRun1 (PackBits) BODY to `want` bytes."""
    out = bytearray()
    i = 0
    n = len(data)
    while len(out) < want and i < n:
        c = data[i]; i += 1
        if c < 128:
            out += data[i:i + c + 1]; i += c + 1
        elif c > 128:
            out += bytes([data[i]]) * (257 - c); i += 1
        # c == 128: no-op
    return bytes(out)


def ilbm_to_raw(iff_bytes):
    bmhd = cmap = body = None
    for cid, payload in _chunks(iff_bytes):
        if cid == b"BMHD":
            bmhd = payload
        elif cid == b"CMAP":
            cmap = payload
        elif cid == b"BODY":
            body = payload
    if not (bmhd and cmap and body is not None):
        raise SystemExit("iff: missing BMHD, CMAP or BODY")

    width, height = struct.unpack(">HH", bmhd[0:4])
    depth = bmhd[8]
    masking = bmhd[9]
    compression = bmhd[10]
    row_bytes = ((width + 15) // 16) * 2
    rows_per_line = depth + (1 if masking == 1 else 0)   # +1 mask plane if present

    if compression == 1:
        body = _unpack_byterun1(body, row_bytes * rows_per_line * height)
    elif compression != 0:
        raise SystemExit("iff: unsupported compression %d" % compression)

    # de-interleave: ILBM stores, per scanline, plane0 row, plane1 row, ...
    # (then a mask row if masking==1). Pull each bitplane out contiguously.
    planes = bytearray()
    for p in range(depth):
        for r in range(height):
            off = (r * rows_per_line + p) * row_bytes
            planes += body[off:off + row_bytes]

    ncolours = len(cmap) // 3
    pal = bytearray()
    for c in range(ncolours):
        r8, g8, b8 = cmap[c * 3], cmap[c * 3 + 1], cmap[c * 3 + 2]
        word = ((r8 >> 4) << 8) | ((g8 >> 4) << 4) | (b8 >> 4)   # Amiga 0x0RGB
        pal += struct.pack(">H", word)

    head = b"SCRN" + struct.pack(">HHHHH", width, height, depth, row_bytes, ncolours)
    return bytes(head + pal + planes)


if __name__ == "__main__":
    import sys
    raw = ilbm_to_raw(open(sys.argv[1], "rb").read())
    w, h, depth, rb, nc = struct.unpack(">HHHHH", raw[4:14])
    print("ILBM -> raw: %dx%d depth %d (%d colours), %d bytes "
          "(%d header+palette + %d planar)"
          % (w, h, depth, nc, len(raw), 14 + nc * 2, depth * rb * h))
