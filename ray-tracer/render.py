#!/usr/bin/env python3
"""
render.py — a physically-based Monte Carlo path tracer in pure Python.

Zero external dependencies: standard library only, PPM (P3) output.

Features
--------
* Unbiased path tracing of the rendering equation with Russian roulette
* Materials: Lambertian diffuse, metal with fuzz, dielectric glass
  (Snell refraction + Schlick-approximated Fresnel), emissive lights
* Geometry: spheres and an infinite ground plane (checkerboard)
* Thin-lens camera with depth of field, multi-sample anti-aliasing,
  gamma correction, gradient sky
* Parallel rendering across CPU cores via multiprocessing

Usage
-----
    python3 render.py                       # fast preview
    python3 render.py -w 960 -s 200 -d 12   # high quality
    python3 render.py --help
"""

from __future__ import annotations

import argparse
import colorsys
import math
import multiprocessing
import os
import random
import sys
import time

# ---------------------------------------------------------------------------
# Vector algebra
# ---------------------------------------------------------------------------


class Vec3:
    """A minimal immutable-ish 3D vector with the usual algebra."""

    __slots__ = ("x", "y", "z")

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z

    def __add__(self, o):
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o):
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __neg__(self):
        return Vec3(-self.x, -self.y, -self.z)

    def __mul__(self, o):
        if isinstance(o, Vec3):  # Hadamard (component-wise) product
            return Vec3(self.x * o.x, self.y * o.y, self.z * o.z)
        return Vec3(self.x * o, self.y * o, self.z * o)

    __rmul__ = __mul__

    def __truediv__(self, s):
        inv = 1.0 / s
        return Vec3(self.x * inv, self.y * inv, self.z * inv)

    def dot(self, o):
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o):
        return Vec3(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )

    def length_squared(self):
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length(self):
        return math.sqrt(self.length_squared())

    def normalized(self):
        return self / self.length()

    def near_zero(self, eps=1e-8):
        return abs(self.x) < eps and abs(self.y) < eps and abs(self.z) < eps

    def max_component(self):
        return max(self.x, self.y, self.z)

    def __repr__(self):
        return f"Vec3({self.x:.4g}, {self.y:.4g}, {self.z:.4g})"


def reflect(v: Vec3, n: Vec3) -> Vec3:
    """Mirror reflection of v about surface normal n."""
    return v - 2.0 * v.dot(n) * n


def refract(uv: Vec3, n: Vec3, etai_over_etat: float) -> Vec3:
    """Snell's law refraction of unit vector uv through normal n."""
    cos_theta = min(-uv.dot(n), 1.0)
    r_out_perp = etai_over_etat * (uv + cos_theta * n)
    r_out_parallel = -math.sqrt(abs(1.0 - r_out_perp.length_squared())) * n
    return r_out_perp + r_out_parallel


def random_unit_vector(rng: random.Random) -> Vec3:
    """Uniform direction on the unit sphere (Gaussian trick)."""
    while True:
        v = Vec3(rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))
        ls = v.length_squared()
        if ls > 1e-12:
            return v / math.sqrt(ls)


def random_in_unit_disk(rng: random.Random) -> Vec3:
    """Uniform point in the unit disk (for the thin-lens aperture)."""
    while True:
        p = Vec3(rng.uniform(-1, 1), rng.uniform(-1, 1), 0.0)
        if p.length_squared() < 1.0:
            return p


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------


class Material:
    """Base class. scatter() returns (attenuation, out_direction) or None
    if the ray is absorbed. emitted() returns radiance added at the hit."""

    def scatter(self, rd, p, n, front_face, rng):
        return None

    def emitted(self, p):
        return None


class Lambertian(Material):
    """Ideal diffuse surface. Cosine-weighted hemisphere sampling: with the
    PDF cos(theta)/pi matching the BRDF's cosine term, the Monte Carlo
    weight collapses to just the albedo."""

    __slots__ = ("albedo",)

    def __init__(self, albedo: Vec3):
        self.albedo = albedo

    def scatter(self, rd, p, n, front_face, rng):
        direction = n + random_unit_vector(rng)
        if direction.near_zero():
            direction = n
        return self.albedo, direction.normalized()


class Checker(Lambertian):
    """Lambertian ground with a procedural checkerboard albedo."""

    __slots__ = ("even", "odd", "scale")

    def __init__(self, even: Vec3, odd: Vec3, scale=1.0):
        self.even, self.odd, self.scale = even, odd, scale

    def scatter(self, rd, p, n, front_face, rng):
        direction = n + random_unit_vector(rng)
        if direction.near_zero():
            direction = n
        parity = (math.floor(p.x * self.scale) + math.floor(p.z * self.scale)) & 1
        return (self.odd if parity else self.even), direction.normalized()


class Metal(Material):
    """Specular conductor. `fuzz` perturbs the mirror direction inside a
    sphere of that radius, modelling surface roughness."""

    __slots__ = ("albedo", "fuzz")

    def __init__(self, albedo: Vec3, fuzz=0.0):
        self.albedo = albedo
        self.fuzz = min(max(fuzz, 0.0), 1.0)

    def scatter(self, rd, p, n, front_face, rng):
        reflected = reflect(rd, n)
        if self.fuzz > 0.0:
            reflected = reflected.normalized() + self.fuzz * random_unit_vector(rng)
        if reflected.dot(n) <= 0.0:  # scattered below the surface: absorbed
            return None
        return self.albedo, reflected.normalized()


class Dielectric(Material):
    """Clear glass. Refracts by Snell's law, falls back to total internal
    reflection when Snell has no solution, and blends reflection vs.
    refraction stochastically using Schlick's Fresnel approximation."""

    __slots__ = ("ior",)

    def __init__(self, index_of_refraction=1.5):
        self.ior = index_of_refraction

    @staticmethod
    def _reflectance(cosine, ref_idx):
        # Schlick's approximation: R(theta) = R0 + (1-R0)(1-cos theta)^5
        r0 = (1.0 - ref_idx) / (1.0 + ref_idx)
        r0 *= r0
        return r0 + (1.0 - r0) * (1.0 - cosine) ** 5

    def scatter(self, rd, p, n, front_face, rng):
        ratio = (1.0 / self.ior) if front_face else self.ior
        cos_theta = min(-rd.dot(n), 1.0)
        sin_theta = math.sqrt(max(0.0, 1.0 - cos_theta * cos_theta))

        cannot_refract = ratio * sin_theta > 1.0
        if cannot_refract or self._reflectance(cos_theta, ratio) > rng.random():
            direction = reflect(rd, n)
        else:
            direction = refract(rd, n, ratio)
        return Vec3(1.0, 1.0, 1.0), direction.normalized()


class Emissive(Material):
    """Light source: emits radiance, absorbs everything that hits it."""

    __slots__ = ("radiance",)

    def __init__(self, color: Vec3, intensity=1.0):
        self.radiance = color * intensity

    def emitted(self, p):
        return self.radiance


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


class Sphere:
    __slots__ = ("center", "radius", "material")

    def __init__(self, center: Vec3, radius: float, material: Material):
        self.center, self.radius, self.material = center, radius, material

    def hit(self, ro, rd, t_min, t_max):
        """Smallest t in (t_min, t_max) where the ray hits, else None.
        Solves |ro + t*rd - c|^2 = r^2, a quadratic in t."""
        ocx = ro.x - self.center.x
        ocy = ro.y - self.center.y
        ocz = ro.z - self.center.z
        a = rd.x * rd.x + rd.y * rd.y + rd.z * rd.z
        half_b = ocx * rd.x + ocy * rd.y + ocz * rd.z
        c = ocx * ocx + ocy * ocy + ocz * ocz - self.radius * self.radius
        disc = half_b * half_b - a * c
        if disc < 0.0:
            return None
        sqrtd = math.sqrt(disc)
        t = (-half_b - sqrtd) / a
        if t <= t_min or t >= t_max:
            t = (-half_b + sqrtd) / a
            if t <= t_min or t >= t_max:
                return None
        return t

    def normal_at(self, p):
        # Dividing by signed radius lets negative radii model hollow shells.
        return (p - self.center) / self.radius


class Plane:
    """Infinite horizontal plane y = height with outward normal +Y."""

    __slots__ = ("height", "material", "_normal")

    def __init__(self, height: float, material: Material):
        self.height, self.material = height, material
        self._normal = Vec3(0.0, 1.0, 0.0)

    def hit(self, ro, rd, t_min, t_max):
        if abs(rd.y) < 1e-9:
            return None
        t = (self.height - ro.y) / rd.y
        if t <= t_min or t >= t_max:
            return None
        return t

    def normal_at(self, p):
        return self._normal


# ---------------------------------------------------------------------------
# Camera (thin lens)
# ---------------------------------------------------------------------------


class Camera:
    def __init__(self, lookfrom, lookat, vup, vfov_deg, aspect, aperture, focus_dist):
        theta = math.radians(vfov_deg)
        half_h = math.tan(theta / 2.0)
        viewport_h = 2.0 * half_h
        viewport_w = aspect * viewport_h

        self.w = (lookfrom - lookat).normalized()
        self.u = vup.cross(self.w).normalized()
        self.v = self.w.cross(self.u)

        self.origin = lookfrom
        self.horizontal = focus_dist * viewport_w * self.u
        self.vertical = focus_dist * viewport_h * self.v
        self.lower_left = (
            self.origin
            - self.horizontal / 2.0
            - self.vertical / 2.0
            - focus_dist * self.w
        )
        self.lens_radius = aperture / 2.0

    def get_ray(self, s, t, rng):
        """Ray through viewport coords (s, t) in [0,1]^2, jittered across the
        lens aperture so out-of-focus points blur (depth of field)."""
        if self.lens_radius > 0.0:
            rd = self.lens_radius * random_in_unit_disk(rng)
            offset = self.u * rd.x + self.v * rd.y
        else:
            offset = Vec3(0.0, 0.0, 0.0)
        origin = self.origin + offset
        direction = (
            self.lower_left + s * self.horizontal + t * self.vertical
            - self.origin - offset
        ).normalized()
        return origin, direction


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------


def sky_color(rd: Vec3) -> Vec3:
    """Gradient environment: warm glow at the horizon, deep blue overhead."""
    t = 0.5 * (rd.y + 1.0)
    horizon = Vec3(1.00, 0.62, 0.42)
    zenith = Vec3(0.16, 0.32, 0.75)
    return ((1.0 - t) * horizon + t * zenith) * 0.62


def build_scene():
    """The demo scene: glass, gold and lapis hero spheres on a checkerboard,
    a glowing lamp, and a deterministic ring of small colorful satellites."""
    world = []

    # Ground: infinite checkerboard plane.
    world.append(Plane(0.0, Checker(
        even=Vec3(0.86, 0.83, 0.76), odd=Vec3(0.18, 0.20, 0.24), scale=0.75)))

    # Hero spheres.
    world.append(Sphere(Vec3(0.0, 1.0, 0.0), 1.0, Dielectric(1.5)))          # glass
    world.append(Sphere(Vec3(0.0, 1.0, 0.0), -0.85, Dielectric(1.5)))        # hollow core
    world.append(Sphere(Vec3(2.3, 1.0, -0.6), 1.0, Metal(Vec3(0.93, 0.74, 0.36), 0.03)))  # gold
    world.append(Sphere(Vec3(-2.3, 1.0, -0.6), 1.0, Lambertian(Vec3(0.12, 0.25, 0.62))))  # lapis

    # Glowing lamp, upper left and behind the heroes: the key light.
    world.append(Sphere(Vec3(-3.6, 3.4, -3.0), 1.1, Emissive(Vec3(1.0, 0.80, 0.55), 9.0)))

    # Ring of small satellite spheres with varied materials.
    rng = random.Random(20260711)
    heroes = [Vec3(0.0, 1.0, 0.0), Vec3(2.3, 1.0, -0.6), Vec3(-2.3, 1.0, -0.6)]
    placed = []
    attempts = 0
    while len(placed) < 14 and attempts < 500:
        attempts += 1
        angle = rng.uniform(0.0, 2.0 * math.pi)
        dist = rng.uniform(2.6, 5.6)
        r = rng.uniform(0.26, 0.42)
        pos = Vec3(math.cos(angle) * dist, r, math.sin(angle) * dist - 0.3)
        if any((pos - h).length() < 1.0 + r + 0.15 for h in heroes):
            continue
        if any((pos - q).length() < r + qr + 0.12 for q, qr in placed):
            continue
        placed.append((pos, r))

        pick = rng.random()
        if pick < 0.60:
            rr, gg, bb = colorsys.hsv_to_rgb(rng.random(), rng.uniform(0.6, 0.9), 0.85)
            mat = Lambertian(Vec3(rr * rr, gg * gg, bb * bb))  # rough sRGB -> linear
        elif pick < 0.85:
            tint = Vec3(rng.uniform(0.7, 0.95), rng.uniform(0.7, 0.95), rng.uniform(0.7, 0.95))
            mat = Metal(tint, rng.uniform(0.0, 0.25))
        else:
            mat = Dielectric(1.5)
        world.append(Sphere(pos, r, mat))

    return world


def build_camera(aspect, aperture):
    lookfrom = Vec3(0.0, 2.1, 7.5)
    lookat = Vec3(0.0, 1.0, 0.0)
    focus_dist = (lookfrom - lookat).length()
    return Camera(lookfrom, lookat, Vec3(0.0, 1.0, 0.0),
                  vfov_deg=32.0, aspect=aspect,
                  aperture=aperture, focus_dist=focus_dist)


# ---------------------------------------------------------------------------
# Path tracing core
# ---------------------------------------------------------------------------

T_MIN = 1e-4
T_MAX = 1e9
RR_START = 3  # bounce index at which Russian roulette kicks in


def hit_world(world, ro, rd):
    """Closest intersection along the ray, as (object, t), or (None, _)."""
    closest = T_MAX
    hit_obj = None
    for obj in world:
        t = obj.hit(ro, rd, T_MIN, closest)
        if t is not None:
            closest = t
            hit_obj = obj
    return hit_obj, closest


def ray_color(ro, rd, world, max_depth, rng):
    """Iteratively integrate one light path: L = sum of emitted radiance
    weighted by the accumulated throughput of every bounce so far."""
    color = Vec3(0.0, 0.0, 0.0)
    throughput = Vec3(1.0, 1.0, 1.0)

    for bounce in range(max_depth):
        obj, t = hit_world(world, ro, rd)

        if obj is None:  # escaped: pick up the sky's radiance and stop
            color = color + throughput * sky_color(rd)
            break

        p = Vec3(ro.x + rd.x * t, ro.y + rd.y * t, ro.z + rd.z * t)
        n = obj.normal_at(p)
        front_face = rd.dot(n) < 0.0
        if not front_face:
            n = -n

        mat = obj.material
        emitted = mat.emitted(p)
        if emitted is not None:
            color = color + throughput * emitted

        scattered = mat.scatter(rd, p, n, front_face, rng)
        if scattered is None:  # absorbed
            break
        attenuation, new_dir = scattered
        throughput = throughput * attenuation
        ro, rd = p, new_dir

        # Russian roulette: probabilistically kill dim paths, and boost the
        # survivors by 1/p so the estimator stays unbiased.
        if bounce >= RR_START:
            p_continue = min(0.95, max(0.05, throughput.max_component()))
            if rng.random() > p_continue:
                break
            throughput = throughput / p_continue

    return color


# ---------------------------------------------------------------------------
# Renderer (parallel over scanlines)
# ---------------------------------------------------------------------------

_G = {}  # per-worker globals, filled by _init_worker


def _init_worker(width, height, samples, depth, aperture, clamp, seed):
    _G["width"] = width
    _G["height"] = height
    _G["samples"] = samples
    _G["depth"] = depth
    _G["clamp"] = clamp if clamp > 0 else float("inf")
    _G["seed"] = seed
    _G["world"] = build_scene()
    _G["camera"] = build_camera(width / height, aperture)


def _render_row(j):
    width, height = _G["width"], _G["height"]
    samples, depth = _G["samples"], _G["depth"]
    world, camera = _G["world"], _G["camera"]
    clamp = _G["clamp"]
    rng = random.Random((_G["seed"] << 24) ^ (j * 0x9E3779B1))

    inv_s = 1.0 / samples
    gamma = 1.0 / 2.2
    out = []
    for i in range(width):
        r = g = b = 0.0
        for _ in range(samples):
            u = (i + rng.random()) / (width - 1)
            v = (height - 1 - j + rng.random()) / (height - 1)
            ro, rd = camera.get_ray(u, v, rng)
            c = ray_color(ro, rd, world, depth, rng)
            # Firefly suppression: clamp rare ultra-bright samples. Slightly
            # biased (darkens caustics a touch) but massively reduces noise.
            r += min(c.x, clamp)
            g += min(c.y, clamp)
            b += min(c.z, clamp)
        # Average, clamp, gamma-encode, quantize to 8 bits.
        for channel in (r, g, b):
            value = min(max(channel * inv_s, 0.0), 1.0) ** gamma
            out.append(str(int(255.999 * value)))
    return j, " ".join(out)


def render(width, height, samples, depth, aperture, clamp, seed, jobs,
           out_path):
    start = time.time()
    rows = [None] * height
    init_args = (width, height, samples, depth, aperture, clamp, seed)

    if jobs <= 1:
        _init_worker(*init_args)
        for j in range(height):
            rows[j] = _render_row(j)[1]
            _progress(j + 1, height, start)
    else:
        with multiprocessing.Pool(jobs, initializer=_init_worker,
                                  initargs=init_args) as pool:
            done = 0
            for j, data in pool.imap_unordered(_render_row, range(height),
                                               chunksize=2):
                rows[j] = data
                done += 1
                _progress(done, height, start)

    sys.stderr.write("\n")
    with open(out_path, "w") as f:
        f.write(f"P3\n{width} {height}\n255\n")
        f.write("\n".join(rows))
        f.write("\n")

    elapsed = time.time() - start
    n_rays = width * height * samples
    print(f"wrote {out_path}  ({width}x{height}, {samples} spp, "
          f"{n_rays:,} primary rays, {elapsed:.1f}s)", file=sys.stderr)


def _progress(done, total, start):
    if done % 4 == 0 or done == total:
        pct = 100.0 * done / total
        elapsed = time.time() - start
        sys.stderr.write(f"\r  rendering… {done}/{total} rows "
                         f"({pct:5.1f}%)  {elapsed:6.1f}s")
        sys.stderr.flush()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Pure-Python physically-based path tracer (PPM output).")
    parser.add_argument("-w", "--width", type=int, default=320,
                        help="image width in pixels (default: 320)")
    parser.add_argument("-s", "--samples", type=int, default=24,
                        help="samples per pixel (default: 24)")
    parser.add_argument("-d", "--depth", type=int, default=8,
                        help="maximum path length in bounces (default: 8)")
    parser.add_argument("-a", "--aspect", type=float, default=16.0 / 9.0,
                        help="aspect ratio width/height (default: 16/9)")
    parser.add_argument("--aperture", type=float, default=0.12,
                        help="lens aperture for depth of field (default: 0.12)")
    parser.add_argument("--clamp", type=float, default=6.0,
                        help="per-sample radiance clamp for firefly "
                             "suppression; 0 disables (default: 6.0)")
    parser.add_argument("--seed", type=int, default=1,
                        help="random seed (default: 1)")
    parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 1,
                        help="parallel worker processes (default: CPU count)")
    parser.add_argument("-o", "--output", default="render.ppm",
                        help="output PPM file (default: render.ppm)")
    args = parser.parse_args()

    height = max(2, int(args.width / args.aspect))
    render(args.width, height, args.samples, args.depth,
           args.aperture, args.clamp, args.seed, args.jobs, args.output)


if __name__ == "__main__":
    main()
