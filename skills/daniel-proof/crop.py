#!/usr/bin/env python3
"""Usage: crop.py <in.png> <out.png> <x> <y> <w> <h>  (device pixels, stdlib only)"""
import struct
import sys
import zlib

CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}


def read_png(path):
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos, idat = 8, b""
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", body)
            assert depth == 8 and color in CHANNELS and not interlace, "need 8-bit, non-interlaced, non-palette PNG"
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    bpp = CHANNELS[color]
    stride = width * bpp
    raw = zlib.decompress(idat)
    rows, prev = [], bytearray(stride)
    for r in range(height):
        start = r * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if kind == 1:
                line[i] = (line[i] + a) & 255
            elif kind == 2:
                line[i] = (line[i] + b) & 255
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        prev = line
    return width, height, color, bpp, rows


def write_png(path, width, height, color, rows):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def crop(src, dst, x, y, w, h):
    width, height, color, bpp, rows = read_png(src)
    x, y = max(0, x), max(0, y)
    w, h = min(w, width - x), min(h, height - y)
    write_png(dst, w, h, color, [r[x * bpp:(x + w) * bpp] for r in rows[y:y + h]])


if __name__ == "__main__":
    if len(sys.argv) != 7:
        sys.exit(__doc__)
    crop(sys.argv[1], sys.argv[2], *map(int, sys.argv[3:]))
