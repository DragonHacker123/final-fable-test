"""Rate limiter library, iteration 4.

Changes from v3:
  * Hot path allocates less: state entries are mutable lists updated in
    place (one allocation at first sight of a key, ~zero after)
  * SlidingWindowLog defers its deque: keys that never exceed one
    in-window request store a bare float timestamp
  * Documented clock contract: monotonic clocks only; on regression the
    limiter treats elapsed time as zero and must fully recover within
    2 x window after the clock resumes
"""

import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict, deque

DEFAULT_STRIPES = 16
EVICT_PER_OP = 2

# state entry layout: [last_seen, params, algo_state]
SEEN, PARAMS, ALGO = 0, 1, 2


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

    # -- configuration ----------------------------------------------------
    def set_limit(self, key, limit, window):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        with self._ov_lock:
            self._overrides[key] = (limit, window)

    def clear_limit(self, key):
        with self._ov_lock:
            self._overrides.pop(key, None)

    # -- request path -------------------------------------------------------
    def allow(self, key):
        now = self.clock()
        params = self._overrides.get(key) or self._default
        limit, window = params
        s = self._stripes[hash(key) % len(self._stripes)]
        with s["lock"]:
            state = s["state"]
            entry = state.get(key)
            if entry is None or entry[PARAMS] is not params \
                    and entry[PARAMS] != params:
                entry = [now, params, None]
                state[key] = entry
            verdict, entry[ALGO] = self._decide(entry[ALGO], now, limit, window)
            entry[SEEN] = now
            state.move_to_end(key)
            # amortized eviction: oldest entries live at the front
            budget = EVICT_PER_OP
            while budget and state:
                k, e = next(iter(state.items()))
                ttl = self.idle_ttl if self.idle_ttl is not None \
                    else 2 * e[PARAMS][1]
                if now - e[SEEN] <= ttl:
                    break
                state.popitem(last=False)
                budget -= 1
        return verdict

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

    @abstractmethod
    def _decide(self, algo_state, now, limit, window):
        """Return (verdict, new_algo_state); runs under the stripe lock."""


class TokenBucket(RateLimiter):
    def _decide(self, st, now, limit, window):
        rate = limit / window
        if st is None:
            st = [float(limit), now]
        tokens = min(float(limit), st[0] + max(0.0, now - st[1]) * rate)
        if tokens >= 1.0:
            st[0], st[1] = tokens - 1.0, now
            return True, st
        st[0], st[1] = tokens, now
        return False, st


class SlidingWindowLog(RateLimiter):
    def _decide(self, st, now, limit, window):
        cutoff = now - window
        if st is None:                       # first request for this key
            return True, now                 # store a bare float
        if isinstance(st, float):            # single stored timestamp
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
