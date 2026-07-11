# Pure-Python Path Tracer

A physically-based Monte Carlo path tracer with **zero dependencies** — no
numpy, no PIL, nothing but the Python standard library. Output is plain-text
PPM (P3), which any image viewer opens and which needs no imaging library to
write.

```bash
python3 render.py                        # fast preview (multi-core)
python3 render.py -w 960 -s 200 -d 12    # high quality
python3 render.py -j 8                   # explicit worker count
python3 ppm_to_ascii.py out.ppm          # view any PPM right in the terminal
```

## The physics

The renderer estimates the **rendering equation**

> L(p, ω) = Lₑ(p, ω) + ∫ f(p, ωᵢ, ω) L(p′, ωᵢ) (n·ωᵢ) dωᵢ

by Monte Carlo integration: each pixel fires many jittered camera rays, and
every surface hit either emits, absorbs, or probabilistically scatters the ray
according to its material's BSDF. Averaging hundreds of such random walks per
pixel converges (unbiasedly) to the true radiance — that's why path-traced
images are grainy at low sample counts and smooth out as `-s` grows.

Implemented effects:

- **Lambertian diffuse** — cosine-weighted hemisphere scattering, which is why
  color bleeds softly between nearby surfaces.
- **Metal** — mirror reflection with a `fuzz` parameter that perturbs the
  reflected ray inside a sphere, giving brushed-metal roughness.
- **Dielectric glass** — Snell-law refraction with total internal reflection
  and **Schlick's approximation** of the Fresnel equations, so glass gets more
  mirror-like at grazing angles, exactly like real glass.
- **Emissive materials** — area lights; all illumination comes from geometry,
  there are no point lights.
- **Thin-lens depth of field** — rays originate from a disk-shaped aperture
  and converge on the focal plane; everything off that plane blurs.
- **Russian roulette** path termination for unbiased early exits, gamma-2
  correction, and a gradient sky dome.
- **Multiprocessing** — scanline rows are farmed out across CPU cores.

## Files

- `render.py` — vectors, materials, geometry, camera, integrator, CLI.
- `ppm_to_ascii.py` — renders any PPM as ANSI truecolor half-blocks in the
  terminal (two pixels per character cell), so you can inspect renders over
  SSH without an image viewer.
