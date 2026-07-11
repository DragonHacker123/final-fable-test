# Galaxy Forge

An interactive N-body galaxy simulator in a **single self-contained HTML
file**. Open `index.html`, pick a preset, and watch a few thousand stars obey
gravity in real time.

## Presets

- **Spiral** — one self-gravitating disk with a central bulge mass and a
  proper rotation curve; differential rotation shears it into flocculent
  spiral arms over the first rotations.
- **Collision** — the money shot: two prograde disks on a ~92%-of-parabolic
  bound orbit. The first pericenter passage raises bridges and long tidal
  tails (the classic Toomre & Toomre 1972 result — prograde spin is what
  makes the tails dramatic), then the pair falls back and merges.
- **Cluster** — a dense star cluster relaxing under its own gravity.
- **Big Bang** — a hot expansion that recollapses into clumps.

## Controls

drag to fling a new mass into the scene · shift-drag / right-drag to pan ·
wheel to zoom · **space** pause · **.** single-step · **q** show the
quadtree · **r** restart — plus sliders for particle count (500–6000),
time scale, Barnes-Hut accuracy θ, and trail persistence.

## The algorithm

Brute-force gravity is O(n²) — hopeless at 5000 bodies. **Barnes-Hut** builds
a quadtree over the particles each step; distant clusters of stars are
approximated by their center of mass whenever the cell is small compared to
its distance (opening-angle test, s/d < θ), cutting the force sum to
O(n log n). The θ slider trades accuracy against speed live, and pressing
**q** overlays the actual tree so you can watch it adapt to the mass
distribution.

Integration is **leapfrog (kick-drift-kick)** — symplectic, so orbital
energy doesn't secularly drift the way it does with naive Euler — with
**Plummer softening** (ε in the denominator) so close encounters can't
produce infinite forces.

Rendering uses additive-blend glow sprites colored by speed (cool red →
hot blue), translucent-clear motion trails, and a live HUD with fps,
physics ms/step, and an approximate total-energy readout.
