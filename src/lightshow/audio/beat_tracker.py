import time
from collections import deque

import numpy as np

NS_PER_S = 1e9


def now_ns() -> int:
    return time.monotonic_ns()


class BeatTracker:
    """Beat history (for BPM) and debounce of beats that arrive too close together."""

    MIN_GAP_NS = 100_000_000  # 0.1 s

    def __init__(self):
        self.times: deque[int] = deque(maxlen=30)
        self._last_accepted_ns = 0

    def record(self) -> None:
        self.times.append(now_ns())

    def accept(self) -> bool:
        now = now_ns()
        if now - self._last_accepted_ns < self.MIN_GAP_NS:
            return False
        self._last_accepted_ns = now
        return True

    def shift(self, ns: int) -> None:
        """Slide history forward so a pause doesn't count as one huge beat gap."""
        self.times = deque((t + ns for t in self.times), maxlen=30)

    def clear(self) -> None:
        self.times.clear()
        self._last_accepted_ns = 0

    @property
    def bpm(self) -> float:
        if len(self.times) < 2:
            return 0.0
        return float(60 / np.mean(np.diff(self.times) / NS_PER_S))
