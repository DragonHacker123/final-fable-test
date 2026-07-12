"""Rate limiter library, iteration 1.

Three algorithms behind one interface:
  * TokenBucket          -- refill tokens continuously, spend one per request
  * SlidingWindowLog     -- remember every request timestamp, count the window
  * SlidingWindowCounter -- two fixed buckets, weighted interpolation

allow(key) -> bool. One lock per limiter. Limits are per-limiter defaults.
"""

import threading
import time
from abc import ABC, abstractmethod
from collections import deque


class RateLimiter(ABC):
    """limit requests per window seconds, tracked independently per key."""

    def __init__(self, limit, window):
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self.limit = limit
        self.window = window
        self._lock = threading.Lock()
        self._state = {}

    @abstractmethod
    def allow(self, key):
        """Return True if the request is admitted, False if throttled."""

    def key_count(self):
        return len(self._state)


class TokenBucket(RateLimiter):
    def allow(self, key):
        now = time.time()
        rate = self.limit / self.window
        with self._lock:
            tokens, last = self._state.get(key, (self.limit, now))
            tokens = min(self.limit, tokens + (now - last) * rate)
            if tokens >= 1.0:
                self._state[key] = (tokens - 1.0, now)
                return True
            self._state[key] = (tokens, now)
            return False


class SlidingWindowLog(RateLimiter):
    def allow(self, key):
        now = time.time()
        with self._lock:
            log = self._state.setdefault(key, deque())
            cutoff = now - self.window
            while log and log[0] <= cutoff:
                log.popleft()
            if len(log) < self.limit:
                log.append(now)
                return True
            return False


class SlidingWindowCounter(RateLimiter):
    def allow(self, key):
        now = time.time()
        win = int(now // self.window)
        frac = (now % self.window) / self.window
        with self._lock:
            cur_win, cur, prev = self._state.get(key, (win, 0, 0))
            if win == cur_win + 1:
                prev, cur = cur, 0
                cur_win = win
            elif win > cur_win + 1:
                prev, cur = 0, 0
                cur_win = win
            est = cur + prev * (1.0 - frac)
            if est < self.limit:
                self._state[key] = (cur_win, cur + 1, prev)
                return True
            self._state[key] = (cur_win, cur, prev)
            return False
