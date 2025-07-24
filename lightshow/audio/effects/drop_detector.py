import time
import numpy as np
from .spike_detector import SpikeDetector

# Similar to BreakDetector but instead of detecting if not enough beats are detected it detects if too many beats are detected in a short time span, indicating a drop in the music.
# It does that by comparing the average time between the last window_size beats and all of the previous beats.
class DropDetector(SpikeDetector):

    def __init__(self, window_size=25, comparing_window_size=10):
        self.beats = []
        self.window_size = window_size
        self.comparing_window_size = comparing_window_size

    def detect(self, data):
        if len(self.beats) < self.comparing_window_size:
            return False

        if self.average_time_between_beats(self.beats) < self.average_time_between_beats(self.beats[-self.window_size:]) * 0.85:
            return True
        return False
    
    def average_time_between_beats(self, beats):
        if len(beats) < 2:
            return 0
        return np.average([beats[i] - beats[i - 1] for i in range(1, len(beats))])
    
    def clear(self):
        self.beats = []
    
    def on_beat(self):
        self.beats.append(time.time_ns())
        if len(self.beats) > self.window_size:
            self.beats.pop(0)