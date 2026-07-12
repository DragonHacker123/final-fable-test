"""Functional + concurrency tests. Target a version: RL_VERSION=v2 python3 run_tests.py

Feature-detects per version so older iterations still run (their gaps show
up as SKIP lines, which is the point of keeping them).
"""

import importlib
import inspect
import os
import sys
import threading
import time

V = os.environ.get("RL_VERSION", "v1")
rl = importlib.import_module(f"iterations.{V}")
print(f"=== testing {V} ===")

failures = []


def check(name, cond, detail=""):
    status = "ok  " if cond else "FAIL"
    print(f"{status} {name}" + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def has_param(cls, name):
    for klass in cls.__mro__:
        if name in getattr(klass.__init__, "__code__", type("", (), {
                "co_varnames": ()})).co_varnames:
            return True
    return False


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


# ---------------------------------------------------------------- basics
def basic_semantics(cls):
    if has_param(cls, "clock"):
        clk = FakeClock()
        lim = cls(5, 0.5, clock=clk)
        got = sum(lim.allow("u") for _ in range(6))
        check(f"{cls.__name__}: 5/6 burst admitted", got == 5, f"got {got}")
        clk.t += 0.6
        check(f"{cls.__name__}: admits after window", lim.allow("u"))
    else:
        lim = cls(5, 0.5)
        got = sum(lim.allow("u") for _ in range(6))
        check(f"{cls.__name__}: 5/6 burst admitted", got == 5, f"got {got}")
        time.sleep(0.6)
        check(f"{cls.__name__}: admits after window", lim.allow("u"))


def key_isolation(cls):
    lim = cls(2, 1.0)
    a = [lim.allow("A") for _ in range(3)]
    b = [lim.allow("B") for _ in range(3)]
    check(f"{cls.__name__}: keys independent", a == b == [True, True, False])


def thread_safety(cls):
    lim = cls(100, 5.0)
    admitted = []
    barrier = threading.Barrier(32)

    def worker():
        barrier.wait()
        admitted.append(sum(lim.allow("k") for _ in range(50)))

    threads = [threading.Thread(target=worker) for _ in range(32)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total = sum(admitted)
    check(f"{cls.__name__}: concurrent admits == limit", total == 100,
          f"got {total}")


def zero_and_bad_config(cls):
    try:
        cls(0, 1)
        check(f"{cls.__name__}: rejects limit=0", False)
    except ValueError:
        check(f"{cls.__name__}: rejects limit=0", True)


# ------------------------------------------------------------ v2 features
def per_key_limits(cls):
    if not hasattr(cls, "set_limit"):
        print(f"SKIP {cls.__name__}: per-key limits (not implemented)")
        return
    clk = FakeClock()
    lim = cls(1, 1.0, clock=clk)
    lim.set_limit("vip", 5, 1.0)
    vip = sum(lim.allow("vip") for _ in range(6))
    pleb = sum(lim.allow("pleb") for _ in range(6))
    check(f"{cls.__name__}: per-key override", (vip, pleb) == (5, 1),
          f"vip={vip} pleb={pleb}")


def eviction(cls):
    if not has_param(cls, "idle_ttl"):
        print(f"SKIP {cls.__name__}: eviction (not implemented)")
        return
    clk = FakeClock()
    lim = cls(5, 1.0, clock=clk, stripes=1, idle_ttl=2.0)
    for i in range(500):
        lim.allow(f"key{i}")
    before = lim.key_count()
    clk.t += 10.0
    for _ in range(600):   # enough ops to cross the sweep threshold
        lim.allow("survivor")
    after = lim.key_count()
    check(f"{cls.__name__}: idle keys evicted", before >= 500 and after <= 2,
          f"before={before} after={after}")


def backwards_clock(cls):
    """Contract: a clock regression must never crash or permanently poison
    a key; once the clock resumes, the key must fully recover within
    2 x window. (Iteration-3 lesson: demanding recovery within ONE window
    was over-strict -- a sliding window legitimately remembers admitted
    requests for a full window after they happen.)"""
    if not has_param(cls, "clock"):
        print(f"SKIP {cls.__name__}: backwards clock (no injectable clock)")
        return
    clk = FakeClock()
    lim = cls(3, 1.0, clock=clk)
    lim.allow("u")
    clk.t -= 50.0           # hostile clock
    ok = True
    try:
        for _ in range(5):
            lim.allow("u")
        clk.t += 50.0 + 2 * 1.0    # resume + two full windows
        ok = lim.allow("u")
    except Exception:
        ok = False
    check(f"{cls.__name__}: survives backwards clock", bool(ok))


def override_change_resets(cls):
    if not hasattr(rl, "EVICT_PER_OP"):
        print(f"SKIP {cls.__name__}: override-change reset (v3+ semantics)")
        return
    clk = FakeClock()
    lim = cls(10, 1.0, clock=clk)
    for _ in range(10):
        lim.allow("u")                    # exhaust the default budget
    lim.set_limit("u", 3, 1.0)            # shrink limit -> state resets
    got = sum(lim.allow("u") for _ in range(5))
    check(f"{cls.__name__}: override change resets state", got == 3,
          f"got {got}")


def explicit_sweep(cls):
    if not hasattr(cls, "sweep"):
        print(f"SKIP {cls.__name__}: explicit sweep (not implemented)")
        return
    clk = FakeClock()
    lim = cls(5, 1.0, clock=clk, idle_ttl=2.0)
    for i in range(1000):
        lim.allow(f"key{i}")
    clk.t += 50.0
    lim.sweep()
    check(f"{cls.__name__}: sweep() empties idle state", lim.key_count() == 0,
          f"left {lim.key_count()}")


def retry_after(cls):
    if not hasattr(cls, "check"):
        print(f"SKIP {cls.__name__}: retry_after (not implemented)")
        return
    clk = FakeClock()
    lim = cls(3, 1.0, clock=clk)
    for _ in range(3):
        lim.allow("u")
    d = lim.check("u")
    ok = (not d.allowed) and 0.0 < d.retry_after <= 1.0
    if not ok:
        check(f"{cls.__name__}: retry_after sane", False,
              f"allowed={d.allowed} retry={d.retry_after}")
        return
    # the estimate must actually work: wait that long, then succeed
    clk.t += d.retry_after + 1e-9
    check(f"{cls.__name__}: retry_after honored", lim.check("u").allowed)


def burst_knob(cls):
    if cls.__name__ != "TokenBucket" or \
            "burst" not in inspect.signature(cls.__init__).parameters:
        return
    clk = FakeClock()
    lim = cls(10, 1.0, burst=3, clock=clk)
    got = sum(lim.allow("u") for _ in range(10))
    check("TokenBucket: burst caps initial spike", got == 3, f"got {got}")
    clk.t += 0.5    # refills 5 tokens but capacity clamps at 3
    got = sum(lim.allow("u") for _ in range(10))
    check("TokenBucket: capacity clamped to burst", got == 3, f"got {got}")


ALGOS = [rl.TokenBucket, rl.SlidingWindowLog, rl.SlidingWindowCounter]
for cls in ALGOS:
    retry_after(cls)
    burst_knob(cls)
    basic_semantics(cls)
    key_isolation(cls)
    thread_safety(cls)
    zero_and_bad_config(cls)
    per_key_limits(cls)
    eviction(cls)
    backwards_clock(cls)
    override_change_resets(cls)
    explicit_sweep(cls)

print(f"\n{'ALL TESTS PASSED' if not failures else f'{len(failures)} FAILURES: {failures}'}")
sys.exit(1 if failures else 0)
