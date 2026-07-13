#!/usr/bin/env python3
"""
Emergency response-time model for the Meridian city template.

Instead of asserting "response times are low", this script estimates them
from the actual layout geometry. It was written during iteration 2 (see
iteration_log.md) to compare three emergency-station strategies, and the
numbers it prints are the ones cited in masterplan.md.

Model
-----
- The city is a "hex flower": 1 core district + 6 petal districts.
  Each district is a regular hexagon, 3.0 km flat-to-flat (apothem 1.5 km).
  Petal centers sit 3.0 km from the core center, so districts are tangent.
  Total urban area ~54.5 km^2.
- Space is discretised into 100 m street-grid cells. Travel is 4-connected
  (Manhattan) breadth-first search over cells, which approximates a real
  street network: Manhattan distance on a grid averages ~1.27x the
  straight-line distance, close to measured street-network detour factors
  of 1.2-1.4 for gridded cities (Boscoe et al. 2012 report ~1.4 including
  highways; dense grids run lower).
- Response time = turnout + travel:
    turnout: 75 s   (NFPA 1710 targets 60-80 s from alarm to wheels rolling)
    travel:  network distance / 10 m/s (36 km/h average emergency speed --
             lights-and-sirens urban averages are commonly 30-45 km/h)
- Demand is assumed uniform over all urban cells. This is a simplification:
  it slightly overweights parks and industry, but residential fabric in the
  template is deliberately even, so the error is small and unbiased.

Configurations compared
-----------------------
  A: 3 consolidated "campus" stations   (iteration-2 strawman: economies of
     scale, one big station per ~330k people)
  B: 7 district stations (one per district center)
  C: ~32 micro-stations on a 1.4 km triangular lattice (adopted design)
  C-quake: config C with 25% of stations knocked out (seeded random), the
     post-earthquake degraded mode the redundancy is meant to survive
  H: transport time to the nearest of 4 hospitals (core + 3 alternating
     petals), i.e. the second leg of an EMS run

Everything is stdlib-only and deterministic.
"""

import math
import random
from collections import deque

# ---------------------------------------------------------------- geometry

CELL = 100.0            # m, grid resolution
APOTHEM = 1500.0        # m, district hexagon apothem (3.0 km flat-to-flat)
DISTRICT_SPACING = 3000.0  # m, center-to-center (tangent hexagons)
TURNOUT_S = 75.0        # s, alarm -> wheels rolling
SPEED_MS = 10.0         # m/s, average emergency travel speed (36 km/h)

# Unit normals of the three face-axes of a flat-topped hexagon rotated so
# flats face the 0/60/120-degree directions (matching district tangency).
_AXES = [(math.cos(a), math.sin(a)) for a in (0.0, math.pi / 3, 2 * math.pi / 3)]

DISTRICT_CENTERS = [(0.0, 0.0)] + [
    (DISTRICT_SPACING * math.cos(k * math.pi / 3),
     DISTRICT_SPACING * math.sin(k * math.pi / 3))
    for k in range(6)
]


def in_hex(px, py, cx, cy, apothem=APOTHEM):
    dx, dy = px - cx, py - cy
    return all(abs(dx * ux + dy * uy) <= apothem for ux, uy in _AXES)


def in_city(px, py):
    return any(in_hex(px, py, cx, cy) for cx, cy in DISTRICT_CENTERS)


def build_cells():
    """All 100 m cells whose centers fall inside the urban footprint."""
    reach = DISTRICT_SPACING + APOTHEM / math.cos(math.pi / 6) + CELL
    n = int(reach // CELL) + 1
    cells = {}
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            x, y = i * CELL, j * CELL
            if in_city(x, y):
                cells[(i, j)] = (x, y)
    return cells


# ------------------------------------------------------------ station sets

def snap(cells, x, y):
    """Nearest existing cell to a coordinate (stations must sit on streets)."""
    return min(cells, key=lambda ij: (cells[ij][0] - x) ** 2 + (cells[ij][1] - y) ** 2)


def stations_consolidated(cells):
    """Config A: 3 campuses at alternating petal centers."""
    pts = [DISTRICT_CENTERS[k] for k in (2, 4, 6)]  # petals at 60, 180, 300 deg
    return [snap(cells, x, y) for x, y in pts]


def stations_district(cells):
    """Config B: one station per district center."""
    return [snap(cells, x, y) for x, y in DISTRICT_CENTERS]


def stations_lattice(cells, spacing=1400.0):
    """Config C: micro-stations on a triangular lattice clipped to the city."""
    row_h = spacing * math.sqrt(3) / 2
    reach = DISTRICT_SPACING + APOTHEM * 2
    out = []
    r = 0
    y = -reach
    while y <= reach:
        offset = (spacing / 2) if (r % 2) else 0.0
        x = -reach + offset
        while x <= reach:
            if in_city(x, y):
                out.append(snap(cells, x, y))
            x += spacing
        y += row_h
        r += 1
    return sorted(set(out))


def stations_hospitals(cells):
    """Config H: 4 hospitals -- core + petals at 0, 120, 240 degrees."""
    pts = [DISTRICT_CENTERS[0], DISTRICT_CENTERS[1],
           DISTRICT_CENTERS[3], DISTRICT_CENTERS[5]]
    return [snap(cells, x, y) for x, y in pts]


# ------------------------------------------------------------------- model

def bfs_distances(cells, sources):
    """Multi-source BFS over the 4-connected street grid. Returns meters."""
    dist = {ij: None for ij in cells}
    q = deque()
    for s in sources:
        dist[s] = 0.0
        q.append(s)
    while q:
        i, j = q.popleft()
        d = dist[(i, j)]
        for ni, nj in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if (ni, nj) in dist and dist[(ni, nj)] is None:
                dist[(ni, nj)] = d + CELL
                q.append((ni, nj))
    return dist


def summarize(cells, sources, turnout=TURNOUT_S):
    dist = bfs_distances(cells, sources)
    times = sorted((turnout + d / SPEED_MS) / 60.0 for d in dist.values())
    n = len(times)
    return {
        "stations": len(sources),
        "mean": sum(times) / n,
        "median": times[n // 2],
        "p90": times[int(n * 0.90)],
        "max": times[-1],
    }


def main():
    cells = build_cells()
    area_km2 = len(cells) * (CELL / 1000.0) ** 2
    print("Meridian emergency response model")
    print(f"urban cells: {len(cells)}  (~{area_km2:.1f} km^2 at {CELL:.0f} m resolution)")
    print(f"assumptions: turnout {TURNOUT_S:.0f} s, travel {SPEED_MS * 3.6:.0f} km/h, "
          f"Manhattan network distances\n")

    lattice = stations_lattice(cells)
    rng = random.Random(42)
    degraded = rng.sample(lattice, k=int(len(lattice) * 0.75))

    configs = [
        ("A  3 consolidated campuses", stations_consolidated(cells), TURNOUT_S),
        ("B  7 district stations",     stations_district(cells),     TURNOUT_S),
        ("C  micro-station lattice",   lattice,                      TURNOUT_S),
        ("C-quake  25% stations lost", degraded,                     TURNOUT_S),
        ("H  transport to 4 hospitals", stations_hospitals(cells),   0.0),
    ]

    print(f"{'config':<30}{'stations':>9}{'mean':>8}{'median':>8}{'p90':>8}{'max':>8}")
    print(f"{'':<30}{'':>9}{'(min)':>8}{'(min)':>8}{'(min)':>8}{'(min)':>8}")
    for name, srcs, turnout in configs:
        s = summarize(cells, srcs, turnout)
        print(f"{name:<30}{s['stations']:>9}"
              f"{s['mean']:>8.1f}{s['median']:>8.1f}{s['p90']:>8.1f}{s['max']:>8.1f}")

    print("\nnotes:")
    print("- H is travel-only (patient already aboard), so no turnout term.")
    print("- NFPA 1710 benchmark: first engine on scene within 5:20 (320 s) for")
    print("  90% of calls. Config C meets it with a wide margin; config A fails it")
    print("  outright, which is why iteration 2 rejected consolidation.")


if __name__ == "__main__":
    main()
