"""Benchmark: memory + accuracy under burst traffic, vs an exact oracle.

Traffic model per key: quiet trickle, then a hard burst, then trickle —
the pattern that separates the algorithms.

Oracle: "no more than LIMIT requests admitted in ANY window of length W"
(exact sliding-window semantics, computed on the oracle's own admitted
history). For each request we ask the oracle: would admitting this violate
the invariant? Comparing each limiter's verdict to the oracle's gives:

  false positive  = limiter admitted, oracle says it should have throttled
  false negative  = limiter throttled, oracle says it could have admitted

Run: RL_VERSION=v1 python3 benchmark.py
"""

import importlib
import os
import random
import sys
import time
import tracemalloc
from collections import deque

V = os.environ.get("RL_VERSION", "v1")
rl = importlib.import_module(f"iterations.{V}")

LIMIT, WINDOW = 50, 1.0
KEYS = 200
DURATION = 12.0          # virtual seconds
SEED = 1234


def gen_traffic():
    """[(virtual_time, key)] — trickle at ~10 rps with 3 bursts at ~400 rps."""
    rng = random.Random(SEED)
    events = []
    for k in range(KEYS):
        key = f"key{k}"
        t = rng.uniform(0, 0.5)
        while t < DURATION:
            in_burst = any(bs <= t < bs + 0.5 for bs in (3.0, 6.0, 9.0))
            rate = 400.0 if in_burst else 10.0
            events.append((t, key))
            t += rng.expovariate(rate)
    events.sort()
    return events


class Oracle:
    """Exact sliding-window admission (greedy) per key."""

    def __init__(self):
        self.hist = {}

    def allow(self, t, key):
        h = self.hist.setdefault(key, deque())
        while h and h[0] <= t - WINDOW:
            h.popleft()
        if len(h) < LIMIT:
            h.append(t)
            return True
        return False


def patched_clock(module):
    """The limiters read wall time; drive them on virtual time instead."""
    state = {"now": 0.0}
    module.time = type(sys)("faketime")
    module.time.time = lambda: state["now"]
    module.time.monotonic = lambda: state["now"]
    return state


class TokenBucketOracle:
    """Exact mathematical token bucket (burst=LIMIT, rate=LIMIT/WINDOW).
    Measures the token-bucket IMPLEMENTATION against its own contract, so
    fp/fn mean bugs -- not the (expected) semantic gap vs sliding windows."""

    def __init__(self):
        self.state = {}

    def allow(self, t, key):
        tokens, last = self.state.get(key, (float(LIMIT), t))
        tokens = min(float(LIMIT), tokens + max(0.0, t - last) * (LIMIT / WINDOW))
        if tokens >= 1.0:
            self.state[key] = (tokens - 1.0, t)
            return True
        self.state[key] = (tokens, t)
        return False


ORACLES = {"TokenBucket": TokenBucketOracle}


class Overshoot:
    """Contract-neutral: worst count of ADMITTED requests in any real
    sliding window of length WINDOW, per key, as a multiple of LIMIT."""

    def __init__(self):
        self.hist = {}
        self.worst = 0

    def admit(self, t, key):
        h = self.hist.setdefault(key, deque())
        h.append(t)
        while h and h[0] <= t - WINDOW:
            h.popleft()
        if len(h) > self.worst:
            self.worst = len(h)


def run(cls, events):
    """Two passes so accuracy bookkeeping never contaminates perf numbers.

    Pass A (untimed): limiter vs oracle vs overshoot tracker -> accuracy.
    Pass B (clean):   fresh limiter alone inside the timed/traced region.
    """
    clock = patched_clock(rl)

    # -- pass A: accuracy ---------------------------------------------------
    limiter = cls(LIMIT, WINDOW)
    oracle = ORACLES.get(cls.__name__, Oracle)()
    shoot = Overshoot()
    fp = fn = agree = 0
    for t, key in events:
        clock["now"] = t
        got = limiter.allow(key)
        want = oracle.allow(t, key)
        if got:
            shoot.admit(t, key)
        if got and not want:
            fp += 1
        elif want and not got:
            fn += 1
        else:
            agree += 1

    # -- pass B: performance, limiter only ----------------------------------
    limiter = cls(LIMIT, WINDOW)
    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]
    wall0 = time.perf_counter()
    for t, key in events:
        clock["now"] = t
        limiter.allow(key)
    wall = time.perf_counter() - wall0
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    n = len(events)
    return {
        "algo": cls.__name__,
        "n": n,
        "fp%": 100 * fp / n,
        "fn%": 100 * fn / n,
        "agree%": 100 * agree / n,
        "peak_kb": (peak - base) / 1024,
        "ns/req": 1e9 * wall / n,
        "keys": limiter.key_count(),
        "worstw": shoot.worst / LIMIT,
    }


def contended_throughput(cls, threads=8, per_thread=30_000, keys=64):
    """Real-clock hammer from N threads over a shared limiter."""
    import threading
    limiter = cls(10_000, 1.0)
    names = [f"k{i}" for i in range(keys)]
    barrier = threading.Barrier(threads + 1)

    def worker(seed):
        rng = random.Random(seed)
        barrier.wait()
        for _ in range(per_thread):
            limiter.allow(names[rng.randrange(keys)])

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(threads)]
    for t in ts:
        t.start()
    barrier.wait()
    t0 = time.perf_counter()
    for t in ts:
        t.join()
    dt = time.perf_counter() - t0
    return threads * per_thread / dt / 1e6   # Mops/s


def main():
    events = gen_traffic()
    print(f"=== benchmark {V} ===")
    print(f"{len(events)} requests, {KEYS} keys, limit {LIMIT}/{WINDOW}s, "
          f"bursts at t=3,6,9\n")
    hdr = (f"{'algorithm':<22}{'fp%':>7}{'fn%':>7}{'agree%':>8}{'worstW':>8}"
           f"{'peak KB':>10}{'ns/req':>9}{'keys':>7}{'8thr Mop/s':>12}")
    print(hdr)
    print("-" * len(hdr))
    print("(fp/fn vs each algorithm's own contract; worstW = max admitted "
          "in any real window / limit)")
    for cls in (rl.TokenBucket, rl.SlidingWindowLog, rl.SlidingWindowCounter):
        r = run(cls, events)
        mops = contended_throughput(cls)
        print(f"{r['algo']:<22}{r['fp%']:>7.2f}{r['fn%']:>7.2f}{r['agree%']:>8.2f}"
              f"{r['worstw']:>8.2f}{r['peak_kb']:>10.1f}{r['ns/req']:>9.0f}"
              f"{r['keys']:>7}{mops:>12.3f}")


if __name__ == "__main__":
    main()
