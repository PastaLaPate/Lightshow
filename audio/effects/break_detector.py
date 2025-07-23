import time
import numpy as np
from .spike_detector import SpikeDetector


class BreakDetector(SpikeDetector):
    def __init__(self, window_size=15):
        self.beats = []
        self.window_size = window_size

    def detect(self, data):
        if len(self.beats) < self.window_size - 5:
            return False
        time_since_last_beat = time.time_ns() - self.beats[-1]

        if (
            time_since_last_beat
            > np.average(
                [self.beats[i] - self.beats[i - 1] for i in range(1, len(self.beats))]
            )
            * 2.5
        ):
            return True
        return False

    def clear(self):
        self.beats = []

    def clear_old_beats(self):
        # After a break clear old breaks to re-adapt
        if len(self.beats) > 10:
            self.beats = self.beats[5:]

    def clean_beats(self, offset=0):
        # Destined to be call after a break to compensate for the time the break took
        self.beats = [beat + offset for beat in self.beats]

    def on_beat(self):
        self.beats.append(time.time_ns())
        if len(self.beats) > self.window_size:
            self.beats.pop(0)
