import os
import sys
import inspect
from collections import deque
from enum import Enum

# Fucking things to import from upper folder
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from audio_streams import AudioData

class DetectionType(Enum):
    UPPER = 0
    LOWER = 1

class SpikeDetector:
    """
    Detects spikes on audio by comparing the current low-frequency energy (e.g., average of first 3 FFT bins)
    to a moving average over a short window.
    """
    def __init__(self, chunks_per_second, sensitivity=2.0, window_size=1, freq_range=[0, 3], detection_type=DetectionType.UPPER):
        """
        :param sensitivity: Factor by which the current energy must exceed the average to trigger a kick.
        :param window_size: Number of recent frames over which to average energy.
        """
        if not chunks_per_second or chunks_per_second <= 0:
            raise ValueError("Chunks per second must be a positive non-nul integer.")
        self.chunks_per_second = chunks_per_second
        self.sensitivity = sensitivity
        self.window_size = int(window_size*chunks_per_second)
        print(self.window_size)
        self.energy_history = deque(maxlen=self.window_size)
        self.freq_range = freq_range
        self.detection_type = detection_type
    
    def clear(self):
        self.energy_history.clear()

    def detect(self, data: AudioData):
        current_energy = data.get_ps_mean(self.freq_range)
        self.energy_history.append(current_energy)
        avg_energy = sum(self.energy_history) / len(self.energy_history)
        limit = self.sensitivity * avg_energy
        result = current_energy > limit if (self.detection_type == DetectionType.UPPER) else current_energy < limit
        return result