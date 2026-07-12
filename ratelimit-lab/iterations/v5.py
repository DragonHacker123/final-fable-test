"""Rate limiter library, iteration 5 (final).

Three algorithms, one contract:

    limiter.allow(key) -> bool
    limiter.check(key) -> Decision(allowed: bool, retry_after: float)

  * TokenBucket(limit, window, burst=None)   -- steady rate limit/window,
    burst capacity `burst` (default: limit). Allows short overshoot up to
    burst in exchange for O(1) state (2 floats/key).
  * SlidingWindowLog(limit, window)          -- exact: never more than
    `limit` admits in any trailing window. O(limit) state per key.
  * SlidingWindowCounter(limit, window)      -- approximates the log with
    2 counters/key by weighting the previous fixed window.

Shared machinery: injectable monotonic clock, per-key overrides
(set_limit/clear_limit; changing params resets that key's state, and
clearing removes the override entry -- no leak), lock striping, LRU
eviction amortized O(1) per request plus explicit sweep().

Clock contract: use a monotonic clock. If the clock regresses anyway,
elapsed time is treated as zero; keys recover within 2 x window after
the clock resumes.
"""

import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict, deque
from typing import NamedTuple

DEFAULT_STRIPES = 16
EVICT_PER_OP = 2

SEEN, PARAMS, ALGO = 0, 1, 2


class Decision(NamedTuple):
    allowed: bool
    retry_after: float          # 0.0 when allowed; estimate, never negative

    def __bool__(self):
        return self.allowed


class RateLimiter(ABC):
    def __init__(self, limit, window, clock=None, stripes=DEFAULT_STRIPES,
                 idle_ttl=None):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self.limit = limit
        self.window = window
        self.clock = clock or time.monotonic
        self.idle_ttl = idle_ttl
        self._default = (limit, window)
        self._overrides = {}
        self._ov_lock = threading.Lock()
        self._stripes = [
            {"lock": threading.Lock(), "state": OrderedDict()}
            for _ in range(stripes)
        ]

    # ------------------------------------------------------ configuration
    def set_limit(self, key, limit, window):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        with self._ov_lock:
            self._overrides[key] = (limit, window)

    def clear_limit(self, key):
        """Remove a key's override AND its state (frees both immediately)."""
        with self._ov_lock:
            self._overrides.pop(key, None)
        s = self._stripes[hash(key) % len(self._stripes)]
        with s["lock"]:
            s["state"].pop(key, None)

    # ------------------------------------------------------- request path
    def allow(self, key):
        return self._request(key, want_retry=False)[0]

    def check(self, key):
        allowed, retry = self._request(key, want_retry=True)
        return Decision(allowed, retry)

    def _request(self, key, want_retry):
        now = self.clock()
        params = self._overrides.get(key) or self._default
        limit, window = params
        s = self._stripes[hash(key) % len(self._stripes)]
        with s["lock"]:
            state = s["state"]
            entry = state.get(key)
            if entry is None or entry[PARAMS] != params:
                entry = [now, params, None]
                state[key] = entry
            verdict, entry[ALGO] = self._decide(entry[ALGO], now, limit, window)
            retry = 0.0
            if want_retry and not verdict:
                retry = max(0.0, self._retry_after(entry[ALGO], now, limit,
                                                   window))
            entry[SEEN] = now
            state.move_to_end(key)
            budget = EVICT_PER_OP
            while budget and state:
                k, e = next(iter(state.items()))
                ttl = self.idle_ttl if self.idle_ttl is not None \
                    else 2 * e[PARAMS][1]
                if now - e[SEEN] <= ttl:
                    break
                state.popitem(last=False)
                budget -= 1
        return verdict, retry

    # -------------------------------------------------------- maintenance
    def sweep(self):
        now = self.clock()
        for s in self._stripes:
            with s["lock"]:
                state = s["state"]
                while state:
                    k, e = next(iter(state.items()))
                    ttl = self.idle_ttl if self.idle_ttl is not None \
                        else 2 * e[PARAMS][1]
                    if now - e[SEEN] <= ttl:
                        break
                    state.popitem(last=False)

    def key_count(self):
        return sum(len(s["state"]) for s in self._stripes)

    # ----------------------------------------------------- algorithm hooks
    @abstractmethod
    def _decide(self, algo_state, now, limit, window):
        """Return (verdict, new_algo_state); runs under the stripe lock."""

    @abstractmethod
    def _retry_after(self, algo_state, now, limit, window):
        """Seconds until a request could plausibly succeed (post-denial)."""


class TokenBucket(RateLimiter):
    def __init__(self, limit, window, burst=None, **kw):
        super().__init__(limit, window, **kw)
        if burst is not None and burst < 1:
            raise ValueError("burst must be >= 1")
        self.burst = float(burst) if burst is not None else float(limit)

    def _decide(self, st, now, limit, window):
        rate = limit / window
        cap = self.burst if (limit, window) == self._default else float(limit)
        if st is None:
            st = [cap, now]
        tokens = min(cap, st[0] + max(0.0, now - st[1]) * rate)
        if tokens >= 1.0:
            st[0], st[1] = tokens - 1.0, now
            return True, st
        st[0], st[1] = tokens, now
        return False, st

    def _retry_after(self, st, now, limit, window):
        return (1.0 - st[0]) / (limit / window)


class SlidingWindowLog(RateLimiter):
    def _decide(self, st, now, limit, window):
        cutoff = now - window
        if st is None:
            return True, now                 # bare float: 1-request keys stay tiny
        if isinstance(st, float):
            if st <= cutoff:
                return True, now
            if limit > 1:
                return True, deque((st, now))
            return False, st
        log = st
        while log and log[0] <= cutoff:
            log.popleft()
        if len(log) < limit:
            log.append(now)
            return True, log
        return False, log

    def _retry_after(self, st, now, limit, window):
        oldest = st if isinstance(st, float) else st[0]
        return oldest + window - now


class SlidingWindowCounter(RateLimiter):
    def _decide(self, st, now, limit, window):
        win = int(now // window)
        frac = (now % window) / window
        if st is None:
            st = [win, 0, 0]
        cur_win = st[0]
        if win < cur_win:                    # clock regression: freeze
            win, frac = cur_win, 1.0
        elif win == cur_win + 1:
            st[2], st[1], st[0] = st[1], 0, win
        elif win > cur_win + 1:
            st[2], st[1], st[0] = 0, 0, win
        est = st[1] + st[2] * (1.0 - frac)
        if est < limit:
            st[1] += 1
            return True, st
        return False, st

    def _retry_after(self, st, now, limit, window):
        cur_win, cur, prev = st
        if cur >= limit or prev <= 0:
            # current window alone is full: wait for the next one
            return (cur_win + 1) * window - now
        # solve  cur + prev*(1 - f) < limit  for the fraction f
        f = 1.0 - (limit - cur) / prev
        target = (cur_win + f) * window
        return max(target - now, (cur_win + 1) * window - now
                   if cur >= limit else 0.0)
