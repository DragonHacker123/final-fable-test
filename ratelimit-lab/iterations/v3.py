"""Rate limiter library, iteration 3.

Changes from v2:
  * SlidingWindowCounter clamps regressing window ids (backwards-clock fix)
  * Defined override semantics: changing a key's limit RESETS that key's
    state (each state entry remembers the params it was built under)
  * LRU-style eviction: per-stripe OrderedDict, at most 2 evictions per
    request -- O(1) amortized, no inline full sweeps, plus explicit sweep()
  * One dict write per request (last-seen lives inside the state entry)
"""

import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict, deque

DEFAULT_STRIPES = 16
EVICT_PER_OP = 2


class RateLimiter(ABC):
    def __init__(self, limit, window, clock=None, stripes=DEFAULT_STRIPES,
                 idle_ttl=None):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self.limit = limit
        self.window = window
        self.clock = clock or time.monotonic
        self.idle_ttl = idle_ttl
        self._overrides = {}
        self._ov_lock = threading.Lock()
        self._stripes = [
            {"lock": threading.Lock(), "state": OrderedDict()}
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
        ov = self._overrides.get(key)   # atomic dict read under the GIL
        return ov if ov is not None else (self.limit, self.window)

    # -- request path -------------------------------------------------------
    def allow(self, key):
        now = self.clock()
        params = self._params(key)
        limit, window = params
        s = self._stripe(key)
        with s["lock"]:
            state = s["state"]
            entry = state.get(key)
            if entry is not None and entry[1] != params:
                entry = None          # params changed: state resets, by design
            algo = entry[2] if entry is not None else None
            verdict, algo = self._decide(algo, now, limit, window)
            state[key] = (now, params, algo)
            state.move_to_end(key)
            self._evict_some(state, now, EVICT_PER_OP)
        return verdict

    def _stripe(self, key):
        return self._stripes[hash(key) % len(self._stripes)]

    def _ttl(self, window):
        return self.idle_ttl if self.idle_ttl is not None else 2 * window

    def _evict_some(self, state, now, budget):
        """Oldest entries sit at the front of the OrderedDict."""
        while budget and state:
            key, (seen, (_, window), _) = next(iter(state.items()))
            if now - seen <= self._ttl(window):
                break
            state.popitem(last=False)
            budget -= 1

    def sweep(self):
        """Optional maintenance: drop every idle key, all stripes."""
        now = self.clock()
        for s in self._stripes:
            with s["lock"]:
                self._evict_some(s["state"], now, len(s["state"]))

    def key_count(self):
        return sum(len(s["state"]) for s in self._stripes)

    @abstractmethod
    def _decide(self, algo_state, now, limit, window):
        """Return (verdict, new_algo_state); runs under the stripe lock."""


class TokenBucket(RateLimiter):
    def _decide(self, st, now, limit, window):
        rate = limit / window
        tokens, last = st if st is not None else (float(limit), now)
        tokens = min(float(limit), tokens + max(0.0, now - last) * rate)
        if tokens >= 1.0:
            return True, (tokens - 1.0, now)
        return False, (tokens, now)


class SlidingWindowLog(RateLimiter):
    def _decide(self, st, now, limit, window):
        log = st if st is not None else deque()
        cutoff = now - window
        while log and log[0] <= cutoff:
            log.popleft()
        if len(log) < limit:
            log.append(now)
            return True, log
        return False, log


class SlidingWindowCounter(RateLimiter):
    def _decide(self, st, now, limit, window):
        win = int(now // window)
        frac = (now % window) / window
        cur_win, cur, prev = st if st is not None else (win, 0, 0)
        if win < cur_win:
            # Clock went backwards: freeze in the current window rather
            # than crediting requests to a window we already left.
            win, frac = cur_win, 1.0
        elif win == cur_win + 1:
            prev, cur, cur_win = cur, 0, win
        elif win > cur_win + 1:
            prev, cur, cur_win = 0, 0, win
        est = cur + prev * (1.0 - frac)
        if est < limit:
            return True, (cur_win, cur + 1, prev)
        return False, (cur_win, cur, prev)
