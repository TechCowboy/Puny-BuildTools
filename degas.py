#!/usr/bin/env python3
#
# ERIS
# Z-machine V5/V8 interpreter
# for Atari ST (GEMDOS/TOS)
# Copyright (c) 2026, Stefan Vogt
#
"""degas.py - Atari ST DEGAS loading-screen decoder (the iff.py analogue).

DEGAS is the ST screen format the Puny BuildTools already emit; the builder
consumes it with NO conversion. Unlike the Amiga's IFF ILBM (compressed +
planar, decoded by iff.py), an uncompressed DEGAS file IS the raw ST screen:
  PI1 (32034 bytes): res word 0 (low res, 320x200, 16 colours) + 16 palette
                     words + 32000 bytes of interleaved-plane screen memory.
  PI3 (32034 bytes): res word 2 (mono, 640x400) + 16 palette words (only the
                     first matters) + 32000 bytes of 1-plane screen memory.
So "decoding" is just: validate, then split off the 16-word palette and the
32000-byte screen. The on-disk blob the ST display path consumes is simply
[32-byte palette][32000-byte screen] - pure data, no format for the ST side to
parse (consistent with the design's "the terp never parses image formats").
"""

DEGAS_SIZE = 32034          # uncompressed: 2 res + 32 palette + 32000 screen
PAL_BYTES  = 32             # 16 ST 0x0RGB palette words
SCR_BYTES  = 32000          # one ST screenful (interleaved planes / 1 plane)

RES_LOW  = 0                # 320x200, 16 colours (PI1) - a colour monitor
RES_MED  = 1                # 640x200,  4 colours (PI2)
RES_MONO = 2                # 640x400, monochrome (PI3) - a mono monitor


def load(path):
    """Return (res, blob) where blob = 32-byte palette + 32000-byte screen.
    Raises on anything but a valid uncompressed DEGAS file."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) != DEGAS_SIZE:
        raise SystemExit("degas: %s is %d bytes, not a %d-byte uncompressed "
                         "DEGAS (PI1/PI2/PI3)" % (path, len(data), DEGAS_SIZE))
    res = (data[0] << 8) | data[1]
    if res not in (RES_LOW, RES_MED, RES_MONO):
        raise SystemExit("degas: %s has a bad resolution word 0x%04X" % (path, res))
    palette = data[2:2 + PAL_BYTES]
    screen  = data[2 + PAL_BYTES:2 + PAL_BYTES + SCR_BYTES]
    return res, palette + screen


def _bayer8():
    """The 8x8 ordered (Bayer) dither matrix, values 0..63."""
    def rec(n):
        if n == 1:
            return [[0]]
        m = rec(n // 2)
        s = len(m)
        out = [[0] * n for _ in range(n)]
        for y in range(n):
            for x in range(n):
                out[y][x] = 4 * m[y % s][x % s] + [[0, 2], [3, 1]][y // s][x // s]
        return out
    return rec(8)


def to_mono_blob(res, blob):
    """Derive a 640x400 1-bit MONO screen from a low-res colour PI1 blob, for a
    mono monitor (DEGAS cannot be made in PI3 by Multipaint, so the builder
    derives it). Pipeline: decode the 16-colour image -> luminance -> 2x scale to
    640x400 -> Bayer 8x8 ordered dither -> pack one bitplane. Returns the same
    [32-byte palette][32000-byte screen] blob shape STDISP.PRG consumes (palette =
    pen 0 black, pen 1 white). Only a PI1 (res 0) yields a mono derivation; a PI3
    source (res 2) is already mono and returns None (caller uses it as-is)."""
    if res != RES_LOW:
        return None
    palb, screen = blob[:PAL_BYTES], blob[PAL_BYTES:]
    gray = []
    for i in range(16):
        v = (palb[i * 2] << 8) | palb[i * 2 + 1]
        r = ((v >> 8) & 7) * 36          # ST 3-bit guns -> 0..252
        g = ((v >> 4) & 7) * 36
        b = (v & 7) * 36
        gray.append(0.30 * r + 0.59 * g + 0.11 * b)   # Rec.601 luma
    # decode the 320x200 16-colour image to a luminance grid
    src = [[0.0] * 320 for _ in range(200)]
    for y in range(200):
        base = y * 160
        for grp in range(20):
            g0 = base + grp * 8
            words = [(screen[g0 + p * 2] << 8) | screen[g0 + p * 2 + 1] for p in range(4)]
            for bit in range(16):
                idx = sum(((words[p] >> (15 - bit)) & 1) << p for p in range(4))
                src[y][grp * 16 + bit] = gray[idx]
    # 2x to 640x400, Bayer-dither to 1 bit, pack one plane (80 bytes/scanline).
    # Bit set (1) = white pixel (pen 1); palette gives pen 1 = white, pen 0 = black.
    B = _bayer8()
    out = bytearray(SCR_BYTES)            # 32000 = 80 * 400
    for y in range(400):
        sy = src[y >> 1]
        row = y * 80
        for bx in range(80):
            byte = 0
            for bit in range(8):
                x = bx * 8 + bit
                if sy[x >> 1] >= (B[y & 7][x & 7] + 0.5) / 64.0 * 255.0:
                    byte |= 0x80 >> bit
            out[row + bx] = byte
    pal = bytearray(PAL_BYTES)
    pal[0:2] = b"\x00\x00"                # pen 0 = 0x000 black
    pal[2:4] = b"\x07\x77"                # pen 1 = 0x777 white
    return bytes(pal) + bytes(out)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("usage: degas.py FILE.pi1   (validates + reports)")
    r, blob = load(sys.argv[1])
    kind = {RES_LOW: "PI1 low-res 16-colour", RES_MED: "PI2 med-res 4-colour",
            RES_MONO: "PI3 mono"}[r]
    print("%s: %s, blob %d bytes (%d palette + %d screen)"
          % (sys.argv[1], kind, len(blob), PAL_BYTES, SCR_BYTES))
