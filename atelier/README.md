# Atelier

A generative art gallery in a **single self-contained HTML file** — six
"rooms," each a different algorithm, each animating live with curated default
parameters. Open `index.html`, wander the rooms, tweak the sliders, reseed,
and save any frame as a PNG.

## The rooms

**I · Zephyr — flow fields.** Thousands of particles advected through layered
value-noise vector fields (the noise is implemented from scratch — no
libraries), drawing long translucent strokes that accumulate into silk-like
currents.

**II · Conservatory — L-system garden.** Stochastic Lindenmayer systems:
grammar rules rewrite an axiom string, a turtle interprets it into branches,
and per-branch phase offsets add wind sway. Randomized rule choices make
every plant an individual.

**III · Petri — reaction–diffusion.** The Gray-Scott model integrated live on
a pixel grid via `ImageData`: two virtual chemicals diffuse and react, and
tiny changes to the feed/kill rates flip the universe between coral growth,
mitosing cells, and traveling waves.

**IV · Strange Orbits — chaotic attractors.** Clifford/de Jong attractor maps
iterated millions of times, with hit-density accumulated per pixel and
tone-mapped, so the chaos renders as glowing smoke.

**V · Cathedral — Voronoi stained glass.** A Voronoi tessellation refined by
Lloyd relaxation (each seed migrates to its cell's centroid), drawn as glass
panes with luminous leading between them.

**VI · Mycelium — differential growth.** A closed loop of nodes that repels
itself while its edges subdivide — the curve buckles and folds like fungal
hyphae or coral margins filling the plane.

## Gallery features

Room switcher with smooth transitions, per-room parameter panels (changes
that alter structure re-initialize the room), seeded randomness with a
reseed button, and PNG export via `canvas.toDataURL`. Verified headlessly:
all six rooms initialize and run 90 frames under a stubbed canvas without
errors.
