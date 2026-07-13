# 🏙 Worldwide City — the Meridian template

A blueprint for a **self-sufficient, disaster-resilient city template** designed to be
replicated across the globe — 1,000,000 residents, seven hexagonal districts, 54.5 km²
urban core, ~1,250 km² productive hinterland. Designed through five documented
iterations, each of which fixed a real flaw in the previous version and paid a named
trade-off for it.

## Deliverables

| File | What it is |
|---|---|
| [`index.html`](index.html) | **Interactive 3D visualisation** (Three.js, vendored — works offline). Orbit/zoom/pan, eight toggleable layers (buildings, tram, emergency stations + computed coverage, green, hinterland, coastal hazard module, labels), click any structure for its design rationale. |
| [`masterplan.md`](masterplan.md) | The design document: urban form, hazard engineering modules with real-world precedents, food/water/energy/materials loop closure, the contentment floors, the 33-station emergency layout, economy, the 25-law charter, crime & flawed-human systems, and an honest list of what is *not* solved. |
| [`iteration_log.md`](iteration_log.md) | The five iterations: flaw → fix → trade-off, from towers-in-a-park (v1) to the parameterised hazard-module family (v6). |
| [`response_model.py`](response_model.py) | Emergency response times **computed, not asserted**: BFS over a 100 m street grid of the actual layout. Stdlib-only, deterministic. |

## Run it

```bash
# 3D visualisation — just open it (Three.js is vendored in lib/)
open index.html

# emergency response model
python3 response_model.py
```

Useful views: `index.html?layers=coverage` (response coverage),
`?layers=coastal` (tsunami defence module), `?cam=0,14000,300` (top-down).

## Headline numbers (all derived in the docs)

- Gross density **18,300 /km²** with charter-enforced quality floors
  (≥35 m²/person, 2 h sun, ≤45 dB quiet façade, park within 300 m, p90 commute ≤35 min)
- Emergency response **p90 = 2.8 min** with 33 micro-stations — and still
  **3.6 min with 25% of stations destroyed** (the post-earthquake case the lattice
  is designed for); 3 consolidated stations would fail NFPA 1710 at 8.1 min
- Food: ~1,000 km² hinterland belt, plant-forward diet; vertical farms demoted to
  the ~2% of calories they're actually good for
- Crime target stated honestly: **homicide < 0.5/100k, not zero**
- Economy: market Georgism — land held in trust, rent funds universal basics,
  38% non-market housing, job guarantee

The final section of the masterplan lists the open problems — led by the
founding-endowment financing gap — because presenting this as solved would be a lie.
