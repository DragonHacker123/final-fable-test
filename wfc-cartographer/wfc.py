#!/usr/bin/env python3
"""WFC Cartographer — procedural map generation via Wave Function Collapse.

Pure Python, zero dependencies. Generates coherent fantasy maps (coastlines,
forests, mountains, rivers, roads, towns) by collapsing a grid of tile
superpositions against adjacency constraints, with entropy-driven cell
selection and constraint propagation.

Usage:
    python3 wfc.py                  # 60x28 map, random seed
    python3 wfc.py --seed 7         # reproducible map
    python3 wfc.py -w 80 -H 40     # custom size
    python3 wfc.py --animate        # watch the collapse happen live
"""

import argparse
import random
import sys
import time
from collections import deque

# ---------------------------------------------------------------------------
# Tile set: each tile has a glyph, ANSI color, base weight, and a terrain
# class. Adjacency is defined between classes, which keeps the ruleset small
# while still producing believable geography.
# ---------------------------------------------------------------------------

TILES = {
    "deep":     {"glyph": "≈", "color": "\033[38;5;18m",  "weight": 10, "cls": "deep"},
    "sea":      {"glyph": "~", "color": "\033[38;5;27m",  "weight": 12, "cls": "sea"},
    "shore":    {"glyph": "░", "color": "\033[38;5;222m", "weight": 8,  "cls": "shore"},
    "plain":    {"glyph": ".", "color": "\033[38;5;107m", "weight": 40, "cls": "plain"},
    "meadow":   {"glyph": ",", "color": "\033[38;5;112m", "weight": 25, "cls": "plain"},
    "forest":   {"glyph": "♣", "color": "\033[38;5;28m",  "weight": 22, "cls": "forest"},
    "deepwood": {"glyph": "♠", "color": "\033[38;5;22m",  "weight": 10, "cls": "forest"},
    "hill":     {"glyph": "n", "color": "\033[38;5;101m", "weight": 14, "cls": "hill"},
    "mountain": {"glyph": "▲", "color": "\033[38;5;245m", "weight": 8,  "cls": "mountain"},
    "peak":     {"glyph": "△", "color": "\033[38;5;255m", "weight": 3,  "cls": "mountain"},
    "river":    {"glyph": "≀", "color": "\033[38;5;39m",  "weight": 6,  "cls": "river"},
    "town":     {"glyph": "⌂", "color": "\033[38;5;208m", "weight": 2,  "cls": "town"},
    "road":     {"glyph": "+", "color": "\033[38;5;180m", "weight": 5,  "cls": "road"},
}

RESET = "\033[0m"

# Which terrain classes may sit next to each other (symmetric).
ADJ_CLASS = {
    ("deep", "deep"), ("deep", "sea"),
    ("sea", "sea"), ("sea", "shore"),
    ("shore", "shore"), ("shore", "plain"), ("shore", "river"), ("shore", "road"),
    ("plain", "plain"), ("plain", "forest"), ("plain", "hill"), ("plain", "river"),
    ("plain", "town"), ("plain", "road"), ("plain", "shore"),
    ("forest", "forest"), ("forest", "hill"), ("forest", "river"), ("forest", "road"),
    ("hill", "hill"), ("hill", "mountain"), ("hill", "river"), ("hill", "road"),
    ("mountain", "mountain"),
    ("river", "river"), ("river", "town"),
    ("town", "road"), ("town", "town"),
    ("road", "road"),
}
ADJ_CLASS |= {(b, a) for a, b in ADJ_CLASS}

NAMES = list(TILES)
IDX = {n: i for i, n in enumerate(NAMES)}
N = len(NAMES)
FULL = (1 << N) - 1

# Precompute, for each tile, the bitmask of tiles allowed beside it.
ALLOWED = []
for a in NAMES:
    mask = 0
    for b in NAMES:
        if (TILES[a]["cls"], TILES[b]["cls"]) in ADJ_CLASS:
            mask |= 1 << IDX[b]
    ALLOWED.append(mask)

WEIGHTS = [TILES[n]["weight"] for n in NAMES]


def bits(mask):
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


class Contradiction(Exception):
    pass


class Wave:
    """The superposition grid plus AC-3 style constraint propagation."""

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.cells = [FULL] * (w * h)

    def entropy(self, mask):
        # Shannon entropy over remaining tile weights (plus tie-break noise).
        total = sum(WEIGHTS[i] for i in bits(mask))
        import math
        e = 0.0
        for i in bits(mask):
            p = WEIGHTS[i] / total
            e -= p * math.log(p)
        return e

    def lowest_entropy_cell(self):
        best, best_e = -1, 1e9
        for idx, mask in enumerate(self.cells):
            c = mask.bit_count()
            if c <= 1:
                continue
            e = self.entropy(mask) + self.rng.random() * 1e-4
            if e < best_e:
                best, best_e = idx, e
        return best

    def neighbors(self, idx):
        x, y = idx % self.w, idx // self.w
        if x > 0:
            yield idx - 1
        if x < self.w - 1:
            yield idx + 1
        if y > 0:
            yield idx - self.w
        if y < self.h - 1:
            yield idx + self.w

    def propagate(self, start):
        queue = deque([start])
        while queue:
            idx = queue.popleft()
            here = self.cells[idx]
            allowed_next = 0
            for t in bits(here):
                allowed_next |= ALLOWED[t]
            for n in self.neighbors(idx):
                new = self.cells[n] & allowed_next
                if new == 0:
                    raise Contradiction(f"cell {n} has no options")
                if new != self.cells[n]:
                    self.cells[n] = new
                    queue.append(n)

    def biased_weight(self, tile_idx, x):
        """Continent gradient: ocean dominates the west, land the middle,
        mountains the east. This is what turns raw WFC noise into geography."""
        t = x / max(1, self.w - 1)
        cls = TILES[NAMES[tile_idx]]["cls"]
        w = WEIGHTS[tile_idx]
        if cls in ("deep", "sea"):
            return w * (10.0 * (1.0 - t) ** 5 + 0.02)
        if cls == "shore":
            return w * (4.0 * (1.0 - t) ** 4 + 0.2)
        if cls == "mountain":
            return w * (8.0 * t ** 5 + 0.02)
        if cls == "hill":
            return w * (3.0 * t ** 3 + 0.15)
        # plain / forest / river / town / road peak mid-continent
        return w * (3.5 * max(0.0, 1.0 - abs(t - 0.55) * 1.8) + 0.25)

    def collapse_cell(self, idx):
        mask = self.cells[idx]
        x = idx % self.w
        opts = list(bits(mask))
        wts = [max(1e-6, self.biased_weight(i, x)) for i in opts]
        pick = self.rng.choices(opts, weights=wts, k=1)[0]
        self.cells[idx] = 1 << pick
        self.propagate(idx)

    def seed_geography(self):
        """Bias the map: ocean on the west edge, mountains near the east."""
        for y in range(self.h):
            self.cells[y * self.w] &= (1 << IDX["deep"]) | (1 << IDX["sea"])
            self.propagate(y * self.w)
        land = ((1 << IDX["plain"]) | (1 << IDX["meadow"]) |
                (1 << IDX["forest"]) | (1 << IDX["hill"]))
        mid_x = self.w // 2
        for y in range(2, self.h - 2, 4):
            idx = y * self.w + mid_x
            if self.cells[idx] & land:
                self.cells[idx] &= land
                self.propagate(idx)
        ridge_x = self.w - 3
        for y in range(self.h // 4, 3 * self.h // 4, 3):
            idx = y * self.w + ridge_x
            keep = self.cells[idx] & (
                (1 << IDX["mountain"]) | (1 << IDX["peak"]) | (1 << IDX["hill"]))
            if keep:
                self.cells[idx] = keep
                self.propagate(idx)

    def run(self, animate=False):
        self.seed_geography()
        while True:
            idx = self.lowest_entropy_cell()
            if idx < 0:
                return
            self.collapse_cell(idx)
            if animate:
                sys.stdout.write("\033[H")
                print(self.render(show_super=True))
                time.sleep(0.002)

    def render(self, show_super=False):
        rows = []
        for y in range(self.h):
            row = []
            for x in range(self.w):
                mask = self.cells[y * self.w + x]
                c = mask.bit_count()
                if c == 1:
                    t = TILES[NAMES[next(bits(mask))]]
                    row.append(t["color"] + t["glyph"] + RESET)
                elif show_super:
                    shade = " ░▒▓"[min(3, c // 4)]
                    row.append("\033[38;5;238m" + shade + RESET)
                else:
                    row.append("?")
            rows.append("".join(row))
        return "\n".join(rows)


def generate(w, h, seed, animate=False, max_retries=40):
    for attempt in range(max_retries):
        rng = random.Random(seed + attempt if seed is not None else None)
        wave = Wave(w, h, rng)
        try:
            if animate:
                sys.stdout.write("\033[2J\033[H")
            wave.run(animate=animate)
            return wave, attempt
        except Contradiction:
            continue
    raise SystemExit("could not generate a consistent map; try another seed")


def main():
    ap = argparse.ArgumentParser(description="Wave Function Collapse map generator")
    ap.add_argument("-w", "--width", type=int, default=60)
    ap.add_argument("-H", "--height", type=int, default=28)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--animate", action="store_true", help="watch the collapse live")
    args = ap.parse_args()

    t0 = time.time()
    wave, retries = generate(args.width, args.height, args.seed, args.animate)
    dt = time.time() - t0

    print(wave.render())
    legend = "  ".join(
        f"{TILES[n]['color']}{TILES[n]['glyph']}{RESET} {n}" for n in NAMES)
    print("\n" + legend)
    print(f"\n{args.width}x{args.height} map in {dt:.2f}s "
          f"({retries} contradiction restarts)")


if __name__ == "__main__":
    main()
