#!/usr/bin/env python3
"""
ppm_to_ascii.py — preview a PPM image in the terminal, no image viewer needed.

Two modes:
  * ansi  (default): 24-bit ANSI color using the U+2580 upper-half-block
    glyph, packing two image rows into every terminal line (fg = top pixel,
    bg = bottom pixel).
  * ascii: plain luminance-ramp characters, safe to paste anywhere.

Usage:
    python3 ppm_to_ascii.py render.ppm
    python3 ppm_to_ascii.py render.ppm --width 100 --mode ascii
"""

from __future__ import annotations

import argparse
import shutil
import sys

ASCII_RAMP = " .:-=+*#%@"


def read_ppm(path):
    """Read a P3 (ASCII) or P6 (binary) PPM. Returns (width, height, pixels)
    where pixels is a flat list of (r, g, b) ints in [0, 255]."""
    with open(path, "rb") as f:
        data = f.read()

    # Tokenize the header, skipping '#' comments.
    tokens = []
    i = 0
    while len(tokens) < 4 and i < len(data):
        # skip whitespace
        while i < len(data) and data[i : i + 1].isspace():
            i += 1
        if i < len(data) and data[i : i + 1] == b"#":
            while i < len(data) and data[i : i + 1] != b"\n":
                i += 1
            continue
        start = i
        while i < len(data) and not data[i : i + 1].isspace():
            i += 1
        if start < i:
            tokens.append(data[start:i])

    magic = tokens[0]
    width, height, maxval = int(tokens[1]), int(tokens[2]), int(tokens[3])
    if maxval <= 0:
        raise ValueError("bad maxval in PPM header")

    if magic == b"P6":
        i += 1  # single whitespace byte after maxval
        raw = data[i : i + width * height * 3]
        values = list(raw)
    elif magic == b"P3":
        values = [int(t) for t in data[i:].split()]
    else:
        raise ValueError(f"unsupported PPM magic {magic!r}")

    if len(values) < width * height * 3:
        raise ValueError("PPM pixel data truncated")

    scale = 255.0 / maxval
    pixels = [
        (
            int(values[k] * scale),
            int(values[k + 1] * scale),
            int(values[k + 2] * scale),
        )
        for k in range(0, width * height * 3, 3)
    ]
    return width, height, pixels


def downsample(width, height, pixels, out_w, out_h):
    """Box-filter the image down to out_w x out_h."""
    result = []
    for oy in range(out_h):
        y0 = oy * height // out_h
        y1 = max(y0 + 1, (oy + 1) * height // out_h)
        for ox in range(out_w):
            x0 = ox * width // out_w
            x1 = max(x0 + 1, (ox + 1) * width // out_w)
            r = g = b = n = 0
            for y in range(y0, y1):
                base = y * width
                for x in range(x0, x1):
                    pr, pg, pb = pixels[base + x]
                    r += pr
                    g += pg
                    b += pb
                    n += 1
            result.append((r // n, g // n, b // n))
    return result


def print_ansi(cells, out_w, out_h):
    """Two image rows per terminal line via the upper-half-block glyph."""
    lines = []
    for y in range(0, out_h - 1, 2):
        parts = []
        for x in range(out_w):
            tr, tg, tb = cells[y * out_w + x]
            br, bg, bb = cells[(y + 1) * out_w + x]
            parts.append(
                f"\x1b[38;2;{tr};{tg};{tb}m\x1b[48;2;{br};{bg};{bb}m▀"
            )
        lines.append("".join(parts) + "\x1b[0m")
    print("\n".join(lines))


def print_ascii(cells, out_w, out_h):
    """Plain-text luminance ramp (Rec. 709 luma)."""
    lines = []
    for y in range(out_h):
        chars = []
        for x in range(out_w):
            r, g, b = cells[y * out_w + x]
            luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
            idx = min(int(luma / 255.0 * len(ASCII_RAMP)), len(ASCII_RAMP) - 1)
            chars.append(ASCII_RAMP[idx])
        lines.append("".join(chars))
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Terminal preview of a PPM image.")
    parser.add_argument("file", help="path to a P3 or P6 PPM file")
    parser.add_argument("--width", type=int, default=0,
                        help="preview width in characters (default: fit terminal)")
    parser.add_argument("--mode", choices=("ansi", "ascii"), default="ansi",
                        help="ansi = 24-bit color half-blocks, ascii = plain text")
    args = parser.parse_args()

    width, height, pixels = read_ppm(args.file)

    out_w = args.width or min(shutil.get_terminal_size((100, 40)).columns, 110)
    out_w = min(out_w, width)
    if args.mode == "ansi":
        # Half-blocks give 2 vertical pixels per char; chars are ~2x tall.
        out_h = max(2, round(out_w * height / width))
        out_h -= out_h % 2
    else:
        # Plain chars are ~2x taller than wide: halve the row count.
        out_h = max(1, round(out_w * height / width / 2))

    cells = downsample(width, height, pixels, out_w, out_h)
    if args.mode == "ansi":
        print_ansi(cells, out_w, out_h)
    else:
        print_ascii(cells, out_w, out_h)

    print(f"[{args.file}: {width}x{height} -> {out_w}x{out_h} preview]",
          file=sys.stderr)


if __name__ == "__main__":
    main()
