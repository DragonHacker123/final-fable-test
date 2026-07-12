# Ratelimit Lab

A rate-limiter library built deliberately **in the open**: five full
write → test → critique → rewrite iterations, each preserved as a runnable
snapshot in `iterations/v1.py` … `v5.py`. The canonical library is
`ratelimiter.py` (a copy of v5).

```python
from ratelimiter import TokenBucket, SlidingWindowLog, SlidingWindowCounter

lim = SlidingWindowLog(100, 60.0)          # 100 requests / 60s per key
lim.set_limit("vip-user", 1000, 60.0)      # per-key override
if lim.allow(user_id):
    ...
d = lim.check(user_id)                     # Decision(allowed, retry_after)
```

Run everything:

```bash
RL_VERSION=v5 python3 run_tests.py     # any of v1..v5
RL_VERSION=v5 python3 benchmark.py
```

## Final benchmark (v5, clean two-pass measurement)

118,295 requests, 200 keys, limit 50/1s, three 400-rps bursts:

```
algorithm                 fp%    fn%  agree%  worstW   peak KB   ns/req   keys  8thr Mop/s
TokenBucket              0.00   0.00  100.00    1.72      43.3     7824    200       0.166
SlidingWindowLog         0.00   0.00  100.00    1.00     278.3     5387    200       0.196
SlidingWindowCounter     2.49   1.92   95.59    1.16      42.4     5996    200       0.174
```

- fp/fn are measured against **each algorithm's own contract** (a
  mathematical token-bucket oracle for TokenBucket, an exact sliding-window
  oracle for the other two).
- **worstW** is the contract-neutral number: the most requests actually
  admitted in any real trailing window, as a multiple of the limit. The
  bucket's 1.72× is its burst allowance, not a bug; the log is exact by
  construction; the counter overshoots ≤ 1.16× while using 6.5× less
  memory than the log.

The trade-off triangle, in one line each: **log** = exact but O(limit)
memory per key; **counter** = 2 counters per key but ±2–5% decision error
at window boundaries; **bucket** = 2 floats per key, zero error against its
own contract, but its contract permits bursts.

## The iteration log

### v1 — naive but complete
Three algorithms, one lock per limiter, `time.time()`. All 15 functional
tests passed; benchmark ran.
**Critique found:** no per-key limits (a stated requirement!); wall-clock
time (NTP step = corrupted buckets); unbounded per-key memory; one global
lock serializing all keys — invisible in the single-threaded benchmark,
which was itself a gap.

### v2 — injectable clock, per-key overrides, striped locks, eviction
Contended throughput jumped **4×** (0.037 → 0.15 Mop/s, 8 threads). The new
backwards-clock test failed for SlidingWindowCounter.
**Critique found:** counter mis-credits requests made while the clock is
rewound; override reads unsynchronized and override changes reinterpret old
state under new params (numeric nonsense for the counter); eviction sweep
is O(stripe) inline under the lock **and** never runs on stripes that go
quiet; hot path 45% slower than v1.

### v3 — clamped clock, override-change-resets semantics, LRU eviction
Measured the eviction pathology directly: after 50k keys expire, v2's next
unlucky request stalls **18.4 ms**; v3's amortized (≤2 evictions/request)
approach bounds it at **0.03 ms**.
**Critique found:** the backwards-clock test itself was wrong — it demanded
recovery within one window, but a sliding window legitimately remembers a
full window of history; the correct contract (recover ≤ 2×window) passes
for v3 *and* v2, meaning iteration 2 partially fixed a misdiagnosis. Also:
per-request allocations climbing every version (5.4 → 7.9 → 9.8 µs); the
benchmark labeled the token bucket's burst semantics as "false positives."

### v4 — honest metrics, mutable hot-path entries, lazy log allocation
Added the per-contract oracles and the worstW column; all tests green.
**Critique found:** the benchmark timed the oracle + overshoot tracker
*inside* the measured region — every version's absolute perf/memory numbers
were harness-polluted (v4's own row looked like a regression because of
it); token-bucket burst capacity not configurable; the overrides-dict leak
flagged in v2 still unfixed two iterations later; bool-only API forces
callers to reinvent Retry-After math.

### v5 — two-pass benchmark, burst knob, check()/Decision, leak fix
Clean measurement finally shows the true memory story (43 KB vs 278 KB
peak — the log is 6.5× hungrier, previously masked by oracle allocations).
`TokenBucket(limit, window, burst=)` caps spikes independently of rate;
`check()` returns a tested retry-after (the test *waits exactly that long*
and asserts success); `clear_limit()` now frees both override and state.
All 5 versions pass the final suite (older ones SKIP features they lack).

## Verdict

The biggest quality jump was **v1 → v2**: injectable clocks made every
subsequent test deterministic and fast, striping fixed a 4× contention
cliff, and per-key limits closed a requirements hole — all structural.
The second most valuable step wasn't code at all: v4/v5's benchmark
overhaul changed *what I believed* about the library (the "memory gap"
between algorithms tripled once the harness stopped polluting the
measurement, and the token bucket went from "14.7% inaccurate" to "exactly
correct, different contract"). Returns diminished sharply in v3–v4 on the
algorithm side — the three cores were essentially correct after v2, and
iteration effort shifted to semantics, measurement honesty, and API
ergonomics. An iteration 6 would fix the remaining known warts: per-key
burst overrides (the `burst` knob currently applies only to default-param
keys), a sharded or lock-free fast path (the GIL caps threaded throughput
near 0.17 Mop/s regardless of striping — a C extension or free-threaded
Python target would change the design), and probabilistic eviction sampling
so cold stripes shed memory without an explicit `sweep()` call.
