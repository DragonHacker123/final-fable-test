"""
gradcheck.py -- verify the autodiff engine against finite differences.

For a scalar function f built out of Value ops, the analytic gradient
df/dx_i produced by backprop must match the central finite difference

    (f(x_i + h) - f(x_i - h)) / (2h)

to high precision. We test a handful of hand-built expressions covering
every op, plus a batch of randomly generated expression trees.
"""

import math
import random

from engine import Value


def numerical_grad(f, xs, i, h=1e-6):
    """Central finite difference of f w.r.t. xs[i] (xs is a list of floats)."""
    xs_hi = list(xs); xs_hi[i] += h
    xs_lo = list(xs); xs_lo[i] -= h
    return (f(xs_hi) - f(xs_lo)) / (2 * h)


def analytic_grads(f, xs):
    vals = [Value(x) for x in xs]
    out = f(vals)
    out.backward()
    return [v.grad for v in vals], out.data


def check(name, f, xs, tol=1e-4):
    """Compare analytic vs numerical gradients; raise on mismatch."""
    grads, _ = analytic_grads(f, xs)
    worst = 0.0
    for i in range(len(xs)):
        num = numerical_grad(lambda ys: _eval(f, ys), xs, i)
        denom = max(1.0, abs(grads[i]), abs(num))
        rel = abs(grads[i] - num) / denom
        worst = max(worst, rel)
        assert rel < tol, (
            f"FAIL [{name}] d/dx{i}: analytic={grads[i]:.10f} numerical={num:.10f} rel_err={rel:.3e}"
        )
    print(f"  ok  {name:<38s} max_rel_err={worst:.3e}")


def _eval(f, xs):
    """Evaluate f on plain floats by wrapping them in Values."""
    return f([Value(x) for x in xs]).data


# ------------------------------------------------------------ fixed tests

def fixed_tests():
    print("hand-built expressions:")
    check("add/mul/sub", lambda v: (v[0] + v[1]) * v[2] - v[0] * 3.0, [1.3, -2.1, 0.7])
    check("division", lambda v: v[0] / v[1] + 2.0 / v[0], [1.7, -0.9])
    check("power", lambda v: v[0] ** 3 + v[1] ** -2, [1.4, 2.2])
    check("tanh", lambda v: (v[0] * v[1] + v[2]).tanh(), [0.5, -1.2, 0.3])
    check("relu chain", lambda v: (v[0] * 2.0 + 1.0).relu() * v[1], [0.8, -1.5])
    check("exp", lambda v: (v[0] * v[1]).exp() + v[0].exp(), [0.4, -0.7])
    check("log", lambda v: (v[0] * v[0] + 1.5).log() * v[1], [0.9, 2.0])
    check("deep composite",
          lambda v: ((v[0] * v[1]).tanh() + (v[2] ** 2 + 1.1).log()).exp()
                    / (1.0 + (v[0] + v[2]).relu()),
          [0.6, -0.4, 1.1])
    # a value used twice: gradient must ACCUMULATE, not overwrite
    check("reused node", lambda v: v[0] * v[0] + v[0].tanh() * v[0], [0.8])
    # the fused dot kernel must match the unfused chain of + and *
    check("fused dot",
          lambda v: Value.dot(v[0:2], v[2:4], v[4]).tanh() * v[0],
          [0.7, -0.3, 1.1, 0.4, -0.6])


# ----------------------------------------------------------- random tests

def random_expr(vs, rng, depth=0):
    """Build a random smooth expression tree over the variables vs.

    Ops are chosen so the function stays finite and differentiable at the
    sample point (log gets a positive-shifted argument; relu inputs are
    shifted away from the kink at 0).
    """
    if depth > 3 or rng.random() < 0.25:
        return rng.choice(vs)
    op = rng.randrange(8)
    a = random_expr(vs, rng, depth + 1)
    if op == 0:
        return a + random_expr(vs, rng, depth + 1)
    if op == 1:
        return a * random_expr(vs, rng, depth + 1)
    if op == 2:
        return a - random_expr(vs, rng, depth + 1)
    if op == 3:
        return a.tanh()
    if op == 4:
        return (a * 0.3).exp()
    if op == 5:
        return (a * a + 1.5).log()
    if op == 6:
        return (a + 4.0).relu()          # inputs are in [-1,1]: far from kink
    return a / (random_expr(vs, rng, depth + 1) * random_expr(vs, rng, depth + 1) + 3.0)


def random_tests(n=30, seed=1337):
    print(f"\n{n} random expression trees (seed={seed}):")
    rng = random.Random(seed)
    passed = 0
    for t in range(n):
        nvars = rng.randint(1, 4)
        xs = [rng.uniform(-1.0, 1.0) for _ in range(nvars)]
        struct_seed = rng.randrange(10 ** 9)

        def f(vs, s=struct_seed):
            r = random.Random(s)          # same tree shape every call
            e = random_expr(vs, r)
            for _ in range(2):            # force some node reuse / fan-out
                e = e + random_expr(vs, r) * e
            return e.tanh() + e * 0.1     # keep output well-scaled
        check(f"random tree #{t:02d} ({nvars} vars)", f, xs)
        passed += 1
    return passed


if __name__ == "__main__":
    fixed_tests()
    n = random_tests()
    print(f"\nGRADCHECK PASSED: 10 fixed + {n} random expressions, "
          f"analytic gradients match central finite differences.")
