"""Rate limiter library, iteration 2.

Changes from v1:
  * Injectable monotonic clock (testable; immune to wall-clock steps)
  * Per-key limit overrides: set_limit(key, limit, window)
  * Lock striping: keys hash to one of N independent stripes
  * Idle-key eviction: periodic per-stripe sweep bounds memory
"""

import threading
import time
from abc import ABC, abstractmethod
from collections import deque

DEFAULT_STRIPES = 16
SWEEP_EVERY = 256          # ops per stripe between eviction sweeps


class RateLimiter(ABC):
    def __init__(self, limit, window, clock=None, stripes=DEFAULT_STRIPES,
                 idle_ttl=None):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self.limit = limit
        self.window = window
        self.clock = clock or time.monotonic
        self.idle_ttl = idle_ttl  # None -> derived per key from its window
        self._overrides = {}
        self._ov_lock = threading.Lock()
        self._stripes = [
            {"lock": threading.Lock(), "state": {}, "seen": {}, "ops": 0}
            for _ in range(stripes)
        ]

    # -- configuration ----------------------------------------------------
    def set_limit(self, key, limit, window):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        with self._ov_lock:
            self._overrides[key] = (limit, window)

    def clear_limit(self, key):
        with self._ov_lock:
            self._overrides.pop(key, None)

    def _params(self, key):
        ov = self._overrides.get(key)
        return ov if ov is not None else (self.limit, self.window)

    # -- plumbing ----------------------------------------------------------
    def _stripe(self, key):
        return self._stripes[hash(key) % len(self._stripes)]

    def allow(self, key):
        now = self.clock()
        limit, window = self._params(key)
        s = self._stripe(key)
        with s["lock"]:
            verdict = self._allow_locked(s["state"], key, now, limit, window)
            s["seen"][key] = now
            s["ops"] += 1
            if s["ops"] % SWEEP_EVERY == 0:
                self._sweep(s, now)
        return verdict

    def _sweep(self, s, now):
        for key in list(s["seen"]):
            limit, window = self._params(key)
            ttl = self.idle_ttl if self.idle_ttl is not None else 2 * window
            if now - s["seen"][key] > ttl:
                del s["seen"][key]
                s["state"].pop(key, None)

    def key_count(self):
        return sum(len(s["state"]) for s in self._stripes)

    @abstractmethod
    def _allow_locked(self, state, key, now, limit, window):
        """Admission decision; called under the key's stripe lock."""


class TokenBucket(RateLimiter):
    def _allow_locked(self, state, key, now, limit, window):
        rate = limit / window
        tokens, last = state.get(key, (float(limit), now))
        dt = max(0.0, now - last)
        tokens = min(float(limit), tokens + dt * rate)
        if tokens >= 1.0:
            state[key] = (tokens - 1.0, now)
            return True
        state[key] = (tokens, now)
        return False


class SlidingWindowLog(RateLimiter):
    def _allow_locked(self, state, key, now, limit, window):
        log = state.setdefault(key, deque())
        cutoff = now - window
        while log and log[0] <= cutoff:
            log.popleft()
        if len(log) < limit:
            log.append(now)
            return True
        return False


class SlidingWindowCounter(RateLimiter):
    def _allow_locked(self, state, key, now, limit, window):
        win = int(now // window)
        frac = (now % window) / window
        cur_win, cur, prev = state.get(key, (win, 0, 0))
        if win == cur_win + 1:
            prev, cur, cur_win = cur, 0, win
        elif win > cur_win + 1:
            prev, cur, cur_win = 0, 0, win
        est = cur + prev * (1.0 - frac)
        if est < limit:
            state[key] = (cur_win, cur + 1, prev)
            return True
        state[key] = (cur_win, cur, prev)
        return False
